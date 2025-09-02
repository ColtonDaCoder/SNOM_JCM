# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Philipp Schneider
#
#SVN-File version: $Rev: 11363 $


import os
try:
    import cPickle as pickle
except:
    import pickle as pickle # no cPickle in python 3
import contextlib
import hashlib
import numpy as np
import re
import inspect
import warnings
import shutil

class Resultbag(object):

    '''
     This class provides a handle to store and access computational 
     results and logs. It can be passed as a parameter to :func:`jcmwave.solve` 
     and :func:`jcmwave.daemon.wait` such that new computational results are
     automatically added to the resultbag and the numerical computations
     of results that are already included in the resultbag are skipped.
     Example::

        resultbag=jcmwave.Resultbag('resultbag.db')
        jcmwave.solve('project.jcmp', keys = keys, resultbag = resultbag)    
        result = resultbag.get_result(keys)


     :param filepath filepath: Path to a file that saves the content of the fieldbag.
              The path can be given relative to the script that creates the 
              resultbag. If file does not exist it will be created. 
              Whenever some result is added, the file is automatically updated.
              If the file exists, the resultbag is loaded from the file.
     :param dictionary keys (optional): Prototype of parameter dictionary for templated  
              jcmt-files or list of fieldnames. If keys is present, when adding or 
              getting results the keys dictionary is filtered to the prototypic 
              dictionary, such that other fieldnames in keys dictionary are ignored.

    '''
    
    def __init__(self, filepath, keys = None):

        #chose path relative to calling script 
        if not os.path.isabs(filepath):
            calling_script_dir,_ = os.path.split(os.path.abspath(inspect.stack()[1][1]))
            filepath = os.path.join(calling_script_dir, filepath)

        #check if directory of filepath exists
        (dir_name, file_name) = os.path.split(filepath)
            
        if not os.path.isdir(dir_name):
            raise EnvironmentError('Cannot access file %s because the directory %s does not exist.' % 
                                   (file_name, dir_name))
            
        self._filepath =  os.path.realpath(filepath)
        self._keys = dict()

        #set fieldnames
        if keys is None: fns = list()
        elif isinstance(keys, dict): fns = list(keys.keys())
        elif isinstance(keys, list): fns = keys
        else: raise TypeError('keys parameter is neither a list nor a dictionary.')
        
        if hasattr(self,'_fieldnames') and self._fieldnames != fns:
            print('Key fieldnames of fieldbag have changed. Resetting fieldbag.')
            self.reset()
        
        
        self.results = PersistentDict(filepath,'results')
        self.config = PersistentDict(filepath,'config')
        self.config['fieldnames'] = fns
        
                  
    ## Methods for handling keys
    
    def _to_md5(self, keys = None, string = None):
        #Get md5 string for string or keys dictionary
        if keys is not None :
            string = self._keys_to_string(keys)
        return hashlib.md5(string.encode()).hexdigest()
        
    def _keys_to_string(self,data,N=12):

        string = ''
        
        #recurse over dict
        if isinstance(data, dict):
            string += '{'
            for key in sorted(list(data.keys())):
                string += '\n %s: %s' % (key, self._keys_to_string(data[key],N))
            string += '\n}'
            return string
        
        if isinstance(data, set):
            string += '{'
            for value in data:
                string += self._keys_to_string(value,N)+' ' 
            string += '}'
            return string
        
        #string (not compatible with Python 3 ==> replace basestring->str)
        if isinstance(data, str):
            string += data
            return string
        
        #Reshape everything to a list
        if isinstance(data, tuple): data = list(data); 
        elif isinstance(data, list): pass
        elif type(data) in (int, float, complex, np.float64, np.int64, bool): data = [data,]
        elif isinstance(data, np.matrix): data = data.ravel().tolist()[0]
        elif isinstance(data, np.ndarray): data = data.ravel().tolist()
        
        #fallback: pickle object
        else:
            string += 'Object( %s )' % pickle.dumps(data)
            warnings.warn('Non primitive data of type {} encountered. This may lead to problems in the usage of resultbag as keys might not be generated deterministically. Consider using a reduced set of fieldnames to get rid of this warning and potential issues.'.format(type(data)),
                          RuntimeWarning)
            return string

        #Output N digits of precision
        fmt = '%%0.%de' % N

        #Real Scalar?
        if len(data) == 1 and type(data[0]) in (float, int, np.float64, np.int64):
            string += fmt % data[0]
            return string

        try:
            #From here we have to divide by absolute maximum
            m = max(map(abs,data))
            maxstring = fmt % m + ' * '
            string += maxstring
            if m>0.0: data = [x/float(m) for x in data];
            fmt = '%%0.%df' % N
            
            string += '['
            for value in data:
                if isinstance(value, complex): 
                    string += ' ' + ('(%s, %s)' % (fmt, fmt)) % (value.real, value.imag)
                else: string += ' ' + fmt % value
            string += ']'
        except:
            #For more complex data (e.g. list of numpy arrays): iterate over entries, pickle objects if necessary with warnings
            string = '['
            for value in data:
                string += self._keys_to_string(value,N)+' ' 
            string += ']'
            return string
            
        return string
    
    def _filter_keys(self, keys):
        #Filter keys array to only those field names, set in the constructor
        if not self.config['fieldnames']: return keys
        filtered = dict()
        for key, value in list(keys.items()):
            if key in self.config['fieldnames']: filtered[key] = value
        return filtered

    ## Methods for file handling 

    def _get_hash(self, file):      
        #Get hash of content of file

        try:
            with open(file, 'r') as f: content = f.read()
        except:
            try:
                hash_md5 = hashlib.md5()
                with open(file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                        return hash_md5.hexdigest()
            except:
                raise EnvironmentError('Can`t read file "%s."'% file)


        #fix windows' line ends
        content = content.replace('\r\n',' \n')
        #remove comments
        content = re.sub(re.compile("#.*?\n" ) ,'\n' ,content)
        return self._to_md5(string = content)
    
    ## Public methods
    
    def reset(self):
        """Purpose: Clear all results in resultbag. 
        Usage: resultbag.reset()

        """    
        #Reset the resultbag (deletes all results, creates backup before)
        self.results.clear()

    def backup(self,backup_path=None):
        """Purpose: Create a backup of the resultbag. If no backup_path is provided, it is derived from the resultbag's name.

        Usage: resultbag.backup(backup_path='resultbag_bkp.db')

        """    
        #Reset the resultbag (deletes all results, creates backup before)
        filepath_bkp =backup_path
        if filepath_bkp is None: 
            [fpath,ext]=os.path.splitext(self._filepath)
            filepath_bkp =fpath+'_bkp'+ext
        try: shutil.copyfile(self._filepath,filepath_bkp)
        except: 
            raise EnvironmentError('Can`t backup resultbag {0} to {1}.'.format(self._filepath,filepath_bkp))
        
    def get_tag(self, keys):
        """Purpose: Get md5 tag of keys dict. Usefull e.g. for creating
        unique folder names for workingdir option of jcmwave_solve

        Usage: tag=resultbag.get_tag(keys)

        :param dict keys: Parameter dictionary for templated jcmt-files.

        :returns: string

        """
           
        # Get tag for specific keys

        filtered_keys = self._filter_keys(keys)
        return self._to_md5(keys = filtered_keys)

    ## Handling of job ids

    def set_job_id(self, keys, id):
        """Set job id of keys dict

        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """

        #Associate keys struct to specific job id

        assert type(keys) is dict, "keys is not a dict: %r" % keys
        self._keys[id] = self._filter_keys(keys)

    def is_running(self, keys):    
        """Check if computation of keys is running

        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """
        #Check if a comutation with specific keys is running (valid job id)
        filtered_keys = self._filter_keys(keys)
        try:
            for key in self._keys.values(): 
                if (key == filtered_keys): return True
        except:
            fkeys = self._keys_to_string(filtered_keys)
            for key in self._keys.values(): 
                if (self._keys_to_string(key) == fkeys): return True

        return False

    def release(self, id):
        """Release job id

        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """
        #Release job id
        del self._keys[id]

    def release_all(self):
        """In daemon mode jcmwave.solve associates the job to a 
        keys dict. Once the computation is running additional
        computations with the same corresponding keys dict are
        skipped. The jobid-keys association is released by
        jcmwave.daemon.wait after the computation has finished. In case
        of a scripting error in Matlab the jcmwave.daemon.wait()
        command may not be reached such that the associations are not
        released and new jobs are not started. In this case call
        release_all().
        Example::

            resultbag.release_all()  

        """
        # Release all job ids in resultbag

        self._keys = dict()

    def get_keys_by_job_id(self, id):
        """Get keys of job id
        
        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """
        #Get keys struct for specific job id
        if id not in self._keys:
            raise EnvironmentError( 'The job id does not exist in the result bag.\
            Please call jcmwave_solve with the resultbag parameter.')
        return self._keys[id]

    ## Handling of results

    def add(self, keys = None, id = None, result = None, log = dict()):
        """Add results and log for specific keys
        
        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """

        #Add new result struct and log for specific keys struct or job id
           
        assert type(keys) is dict or id is not None, "Neither keys nor job id given"
        assert type(result) is list, "Added result is not a list: %r" % result
        assert type(log) is dict, "Added log is not a dict: %r" % log

        if keys is not None: filtered_keys = self._filter_keys(keys)
        else: filtered_keys = self._keys[id]
     
        md5 = self._to_md5(keys = filtered_keys)
        result = {
            'keys': filtered_keys,
            'result': result,
            'log': log,
        }
        self.results[md5] = result

    def get_result(self, keys):
        """Get results for specific keys. Example::

            result=resultbag.get_result(keys)

        :param dict keys: Parameter dictionary for templated jcmt-files.
        :returns: result list

        """
        # Get result for specific keys

        filtered_keys = self._filter_keys(keys)
        md5 = self._to_md5(keys = filtered_keys)
        if md5 not in self.results.keys():
            raise EnvironmentError('Result for keys with tag %s does not exist.' % md5)

        res = self.results[md5]['result']
        if not res:
            raise EnvironmentError('The result for keys with tag %s is empty. Please check the logging information by calling get_log(keys).' % md5)
      
        return res

    def get_log(self, keys):
        """Get log for specific keys. Example::

            log=resultbag.get_log(keys)

        :param dict keys: Parameter dictionary for templated jcmt-files.
        :returns: log dict

        """
        # Get log for specific keys
        
        filtered_keys = self._filter_keys(keys)
        md5 = self._to_md5(keys = filtered_keys)
        if md5 not in self.results.keys():
            raise EnvironmentError('Log for keys with tag %s does not exist.' % md5)

        return self.results[md5]['log']

    def check_result(self, keys):
        """Check if results for specific keys exist. Example::

            exists=resultbag.check_result(keys)

        :param dict keys: Parameter dictionary for templated jcmt-files.
        :returns: bool (true if results exist)

        """
        #Check if result for specific keys exists

        filtered_keys = self._filter_keys(keys)
        md5 = self._to_md5(keys = filtered_keys)
        
        return md5 in self.results.keys() and 'result' in self.results[md5]

    def has_results(self):
        """Check if any results are registered
            has_any=resultbag.has_results()

        :returns: bool (true if any results are registered)

        """
        return self.results.count() >0

    def remove(self, fun):
        """Remove result and log for keys meeting certain criteria. Example::

            resultbag.remove(lambda keys: keys['somefield'] > 0) 
        
        :param function fun: boolean function with keys as argument 
    
        """
        # Remove result and log for keys meeting certain conditions from
        
        for md5, result in self.results.items():
            if fun(result['keys']): del self.results[md5]
            
    def remove_result(self, keys):
        """Remove result and log for specific keys. Example::

            resultbag.remove_result(keys) 
        
        :param dict keys: Parameter dictionary for templated jcmt-files.
    
        """
        # Remove result and log for keys meeting certain conditions from
        
        filtered_keys = self._filter_keys(keys)
        md5 = self._to_md5(keys = filtered_keys)
        del self.results[md5]
        
    ## Handling of source files
    def ignore_source_files(self, ignore=True):
        """Set flag to ignore dependency of resultbag on source files
        """
        self.config['ignore_source_files'] = ignore

            
    def set_source_files(self, files):
        """Set source files of results 

        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """
        #memorize hash of source files
      
        source_files = dict()
        for file in files:
            file = os.path.realpath(file)
            hash = self._get_hash(file)
            timestamp = os.path.getmtime(file)
            (_, file_name) = os.path.split(file)
            md5 = self._to_md5(string = file_name)
            file_name = os.path.relpath(file,os.path.commonpath([self._filepath,file]))
            source_files[md5] = {
                'file': file_name,
                'hash': hash,
                'timestamp': timestamp,
            }
        self.config['source_files'] = source_files


    def check_source_files(self, files):
        """Check if source files are unchanged 

        Internal method used by :func:`jcmwave.solve` or :func:`jcmwave.daemon.wait`
        """
        #check if content of source files is unchanged
        if 'ignore_source_files' in self.config and self.config['ignore_source_files']:
            return True
        #check if source files set
        if not 'source_files' in self.config: return False
        source_files = self.config['source_files']
      
        #check files
        for file in files:
            file = os.path.realpath(file)
            (_, file_name) = os.path.split(file)
            md5 = self._to_md5(file_name)
          
            # check if filenames changed
            if md5 not in source_files: return False
         
            #check if file date changed
            timestamp = os.path.getmtime(file)
         
            #file date changed ==> check md5
            if timestamp != source_files[md5]['timestamp']:
                hash = self._get_hash(file)
                if hash != source_files[md5]['hash']: 
                    return False
                else:
                    #update timestamp
                    source_files[md5]['timestamp'] = timestamp

        self.config['source_files'] = source_files
      
        return True

import sqlite3
import threading
class PersistentDict(dict):
    def __init__(self, filepath, name):
        self._cache = dict()
        self._filepath = filepath
        self._connection = sqlite3.connect(filepath, check_same_thread=False)
        self._name = name
        self._lock = threading.Lock()
        c = self._connection.cursor()
        c.execute(
          'CREATE TABLE IF NOT EXISTS "%s" (key TEXT PRIMARY KEY, value BLOB)'%
          self._name)
        self._connection.commit()

    def __setitem__(self,key,value):
        with self._lock:
            self._cache[key] = value
            c = self._connection.cursor()
            value = pickle.dumps(value)
            c.execute("REPLACE INTO %s (key, value) VALUES (?,?)" %
                      self._name, (key,value))
            self._connection.commit()

    def __getitem__(self,key):
        if key in self._cache: return self._cache[key]
        c = self._connection.cursor()
        c.execute('SELECT value FROM %s WHERE key=?' % self._name, (key,))
        result = c.fetchone()
        if result is None: raise KeyError(key)
        value = self.unpickle(result[0])
        self._cache[key] = value
        return value

    def __contains__(self, key):
        if key in self._cache: return True
        c = self._connection.cursor()
        c.execute('SELECT 1 FROM %s WHERE key=?' % self._name, (key,))
        result = c.fetchone()
        return result is not None

    def __delitem__(self, key):
        with self._lock:
            c = self._connection.cursor()
            c.execute('DELETE FROM %s WHERE key=?' % self._name,(key,))
            self._connection.commit()
            del self._cache[key]
    
    def clear(self):
        with self._lock:
            c = self._connection.cursor()
            c.execute("DELETE FROM %s" % self._name)
            self._connection.commit()
            self._cache = dict()

    def keys(self):
        c = self._connection.cursor()
        for key in c.execute("SELECT key FROM %s" % self._name):
            yield key[0]

    def items(self):
        c = self._connection.cursor()
        for key,value in c.execute("SELECT key, value FROM %s" % self._name):
            value = self.unpickle(value)
            self._cache[key] = value
            yield key, value

    def unpickle(self,value):
        try:
            try:
                return pickle.loads(value)
            except:            
                return pickle.loads(value.encode('ascii'))
        except:
            raise EnvironmentError('Cannot load data from resultbag. Please ensure that you are using the same python version for writing and reading of the database.')

    def count(self):
        c = self._connection.cursor()
        counter = c.execute("SELECT COUNT(*) FROM %s" % self._name)
        values = counter.fetchone()
        return values[0]
        
if __name__=='__main__':
    import unittest
    import os
    import time
    import random
    import string
    
    class Test_Resultbag(unittest.TestCase):
        
        def setUp(self):
            self.keys = {'radius': 1.0}
            self.resultbag = Resultbag('test.rbg',self.keys)
            self.assertEqual(self.resultbag.has_results(),0)
            
        def test_Resultbag(self):
            rb = Resultbag('test.rbg',self.keys)
            self.assertEqual(rb.__dict__, self.resultbag.__dict__)

        def test_keys_to_string(self):
            #compare keys with precision of 4 significant bits (3 after dot)
            keys1 = {
                'float': 123.41,
                'string' : 'abc',
                'int' : 1,
                'complex': complex(1,2),
                'array': np.array([[1000,2,complex(3,1)],[4,5,0.001]]),
                'dict': {'test': 1},
                'rb': object()
                }
            str1 = self.resultbag._keys_to_string(keys1,N=3)
            keys2 = {
                'float': 123.40,
                'string' : 'abc',
                'int' : 1,
                'complex': complex(1,2.0001),
                'array': np.array([[1000,2.1,complex(3.1,1)],[4,5,0.001]]),
                'dict': {'test': 1.0001},
                'rb': object()
                }
            str2 = self.resultbag._keys_to_string(keys2,N=3)

            keys1['dict']['test'] = 1.1
            str3 = self.resultbag._keys_to_string(keys1,N=3)

            self.assertEqual(str1,str2)
            self.assertNotEqual(str1,str3)
        
        def test_filter_keys(self):
            keys = {'radius': 2.0, 'something_unimportant': 1}
            keys = self.resultbag._filter_keys(keys)
            self.assertEqual(keys,{'radius': 2.0})

        def test_get_hash(self):
            content1 = 'a=7 #some comment\n' + 'b=5'
            content2 = 'a=7 \n' + 'b=5'
            with open('test1.txt', 'w') as f: f.write(content1)
            with open('test2.txt', 'w') as f: f.write(content2)
            
            self.assertEqual(
                self.resultbag._get_hash('test1.txt'),
                self.resultbag._get_hash('test2.txt')            
            )
            os.remove('test1.txt')
            os.remove('test2.txt')

        def test_get_tag(self):
            tag1 = self.resultbag.get_tag(self.keys)
            keys2 = {'radius': 1.0, 'something_unimportant': 1}
            tag2 = self.resultbag.get_tag(keys2)
            self.assertEqual(tag1,tag2)            

        def test_id_handling(self):
            keys1 = {'radius': 1.0, 'something_unimportant': 1}
            keys2 = {'radius': 1.0, 'something_unimportant': 2}
            keys3 = {'radius': 2.0}
            self.resultbag.set_job_id(keys1,7)
            self.assertTrue(self.resultbag.is_running(keys2))
            self.assertFalse(self.resultbag.is_running(keys3))
            self.assertEqual({'radius': 1.0},self.resultbag.get_keys_by_job_id(7))
            self.resultbag.release(7)
            self.assertFalse(self.resultbag.is_running(keys1))
            
        def test_handling(self):
            keys1 = {'radius': 1.0, 'something_unimportant': 1}
            result = [{'result':1},{'postprocess':2}]
            log = {'info':'ok'}

            self.resultbag.add(keys = keys1, result = result, log = log)
            self.assertTrue(self.resultbag.has_results()>0)
            result_out = self.resultbag.get_result({'radius': 1.0})
            self.assertEqual(result_out,result)
            log_out = self.resultbag.get_log(keys1)
            self.assertEqual(log_out,log)
            self.assertTrue(self.resultbag.check_result(keys1))
            self.assertFalse(self.resultbag.check_result({'radius': 2.0}))

            self.resultbag.add(keys = {'radius': 2.0}, result = result, log = log)
            self.assertTrue(self.resultbag.check_result({'radius': 2.0}))
            self.resultbag.remove(lambda keys: keys['radius'] == 2.0)
            self.assertFalse(self.resultbag.check_result({'radius': 2.0}))
            
        def test_file_handling(self):
            content1 = 'a=7 #some comment\n' + 'b=5'
            content2 = 'a=8 \n' + 'b=6'
            with open('test1.txt', 'w') as f: f.write(content1)
            with open('test2.txt', 'w') as f: f.write(content2)
            
            source_files = [os.path.abspath('test1.txt'), os.path.abspath('test2.txt')]
                
            self.resultbag.set_source_files(source_files)
            self.assertTrue(self.resultbag.check_source_files(source_files))
            with open('test1.txt', 'w') as f: f.write(content1)
            self.assertTrue(self.resultbag.check_source_files(source_files))
            with open('test1.txt', 'w') as f: f.write(content2)
            self.assertFalse(self.resultbag.check_source_files(source_files))
            
            self.resultbag.ignore_source_files(ignore=True)
            self.assertTrue(self.resultbag.check_source_files(source_files))
            os.remove('test1.txt')
            os.remove('test2.txt')

        def test_performance(self):
            payload = ''.join(random.choice(string.ascii_uppercase) for _ in range(1000))
            result=[{'data': payload}]
            start = time.time()

            for i in range(500):
                keys = {'radius' : i}
                self.resultbag.add(keys = keys, result = result)
                if i % 100 == 0:
                    print('Time for adding data %s s' % (time.time() - start) )
                    start = time.time()

 
        def tearDown(self):
            self.resultbag.backup(backup_path='backup_test.rbg')
            self.resultbag.backup()
            self.resultbag.reset()
            os.remove('test.rbg')
            os.remove('backup_test.rbg')
            os.remove('test_bkp.rbg')
            
    unittest.main()
    
