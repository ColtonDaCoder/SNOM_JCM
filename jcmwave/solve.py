# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 17420 $

import os
import sys
import re
import warnings
import shutil
import tempfile
from os.path import isfile
from os.path import isdir
from os.path import join as pathjoin
import jcmwave
import subprocess
import jcmwave.__private as __private
import string

class NameSpaceHelper(object):
    pass

class ProjectDataHelper(object):
    pass

def solve(project_file,  
          keys=None, 
          mode='solve',
          process_keys=None,
          return_results=True,
          table_format='named', 
          cartesianfields_format = 'squeeze',
          logfile=None, 
          working_dir=None, 
          project_suffix=None,
          temporary=False,
          cache_finished_jobs=True,
          resultbag=None,
          jcmt_pattern=None,
          resources=[]):
    """
    Starts JCMsolve. 
   
    :param filepath project_file: path name of a JCMwave project or post-process file.

    :param dictionary keys:
 
        parameter (nested) dictionary for embedded script input file. When keys is present, the embedded script files ``materials.jcmt``, ``sources.jcmt``, ``boundary_conditions.jcmt`` and ``<project>.jcmpt`` are processed to generate the actual .jcm input files by call of jcmwave.jcmt2jcm(<jcmt-file>, keys). Additionally, the ``jcmwave.geo(<project_dir>, keys)`` is called to automatically update the grid file.
 
    :param str mode:  sets the solver mode

         The possible modes are

             'version' 

                  prints version tag, needs no project_file

             'solve'

                 starts JCMsolve

             'post_process'

                 starts JCMsolve to execute post-processes

             'license_info'

                 prints license information
      
    :param boolean return_results: If set to ``True``, the function returns a list of references to the computed data.
     
    :param str table_format:
 
             table format option when loading table result files, cf. section 'Output' below. ``table_format`` is equivalent to the ``format`` option of :func:`jcmwave.loadtable`.

    :param str cartesianfields_format:
 
             format option when loading a cartesian fieldbag. ``cartesianfields_format`` is equivalent to the ``format`` option of :func:`jcmwave.loadcartesianfields`, but with a further allowed value ``filepath``, for which the filepath of the cartesian field bag file is returned only.

    :param filepath logfile:
 
             redirects console output to a file. logfile must be
    
                 i) a string refering to a file path to which the output is piped 
                 ii) a valid file descriptor
 
    :param dirpath working_dir:
 
             copies .jcm files into working directory, runs solver therein.

    :param str project_suffix:

             add suffix to project file name, e.g. project.jcmp -> project.<suffix>.jcmp
             
    :param boolean temporary: 

             project runs in a temporary directory
             (excludes working_dir)

    :param boolean cache_finished_jobs:
 
        In daemon mode finished jobs with temporary data storage are cached and temporary 
        disk storage is freed (default: True). 

    :param str jcmt_pattern:  

             pattern for selection of .jcmt files.  For example, 
             sources.<pattern>.jcmt is used instead of sources.jcmt when present. 
             
    :param Resultbag resultbag: 

            An instance of the class :class:`jcmwave.Resultbag`. ``jcmwave.solve`` uses the result bag to check whether the result with the keys parameter was already computed. If not it adds the new result to the result bag. 
            In daemon mode :func:`jcmwave.daemon.wait`` has to be called with the resultbag
            parameter in order for the result to be added to the result bag.
            If the result is already stored in the result bag the daemon is
            not triggered. 
            The resultbag can be created by calling

              my_resultbag = jcmwave.Resultbag('filname.rbg', [keys])

            Results for a specific keys-structure can be retrieved by calling 

              result =  my_resultbag.get_result(keys)

            Logs for a specific keys-structure can be retrieved by calling 

              log =  my_resultbag.get_log(keys)

    :param list resources (default []):   
    
        list of resource identifiers which can be used for this job. This option is only used in daemon mode

    :returns: 

        When return_results==False no output is returned. Otherwise the output is a list containing references to the computed data. 

        When called with mode `solve`, ``results[0]`` refers to the solution. It is a dictionary with the fields 

                'file'

                    file path to the solution fieldbag (if pressent)

                'computational_costs'

                    jcm table with computation costs statistics

                'eigenvalues'

                    eigenvalue table (only for eigenvalue problems)

        ``results[1], ... results[nPost]`` refer to the results of  the post processes 
        in the same order as they appear in the project file. For mode `post_process`, 
        the results list refers to the performed post-process only.
   
        For any postprocess, each entry ``results[i]`` is a dictionary of the shape
        as loaded by loadtable (for tables), or loadcartesianfields (for Cartesian 
        fieldbags). 
    """     
   
    if __private.JCMsolve is None: jcmwave.startup()

    isProjectSequence=isinstance(project_file,list)
    if not isProjectSequence: project_file=[project_file]
    project_list=list()
    for i_project in project_file: 
      project_data=ProjectDataHelper()
      project_data.file=i_project
      project_list.append(project_data)
    del(project_file)

    if not isinstance(mode, str) or not (mode in ['solve', 
           'version', 'post_process', 'license_info']):
        raise TypeError('Invalid solver mode %s' % mode)

    if not (mode=="solve" or mode=="post_process"):
       project_list=list()

    
    for iP in range(0, len(project_list)):
      if not isinstance(project_list[iP].file,str): 
          raise TypeError('project_file -> file path expected.')

      if len(project_list[iP].file)>2 and project_list[iP].file[-1]=='t':
          project_list[iP].file = project_list[iP].file[0 : -1]
      if jcmt_pattern is not None:
        tmp_p_file = project_list[iP].file.replace('.jcm', '.'+jcmt_pattern+'.jcm')
        if ( (not isfile(tmp_p_file)) and
             (not isfile(tmp_p_file+'t')) and
             (not isfile(project_list[iP].file)) and
             (not isfile(project_list[iP].file+'t')) ):
             raise TypeError('project_file -> file path expected.')
      else:
        if (not isfile(project_list[iP].file)) and (not isfile(project_list[iP].file+'t')):
            raise TypeError('project_file -> file path expected.')


    if (keys is not None) and (not isinstance(keys, dict)):
        raise TypeError('keys -> dictionary expected.')   

    if not isinstance(return_results, bool):
        raise TypeError('return_results -> boolean expected.')     

    if not isinstance(table_format, str) or not (table_format in ['named', 
         'list', 'matrix']):
        raise TypeError('Invalid table format')

    if not isinstance(cartesianfields_format, str) or not (cartesianfields_format 
         in ['squeeze', 'full', 'filepath']):
        raise TypeError('Invalid cartesian field format')

    if logfile is None:
        stdout = sys.stdout
        stderr = None 
    elif isinstance(logfile, str):
        try:  logfd=open(logfile, 'w')
        except: raise EnviromentError('Can`t open logfile for reading.')
        stdout = logfd
        stderr = subprocess.STDOUT
    else: 
        stdout = logfile
        stderr = subprocess.STDOUT

    if temporary and working_dir is not None:
        raise TypeError('The temporary option excludes the use of the working_dir option.')
    if working_dir is None: working_dir = '.'
    if not isinstance(working_dir,str): 
        raise TypeError('working_dir -> directory path expected.')

    for i_project in range(0, len(project_list)):
      (project_list[i_project].dir, project_list[i_project].file) = os.path.split(os.path.abspath(project_list[i_project].file))

    clean_up = False
    if temporary:
        try:
            import tempfile
            #working_dir = tempfile.mkdtemp(dir = '%s/tmp' % project_list[-1].dir , prefix ='__JCMwave__')
            working_dir = tempfile.mkdtemp(prefix ='__JCMwave__')
        except: raise EnvironmentError('Can`t create temporary directory.')
        clean_up = True

    def cleanUp(directory):
        from time import time
        start = time()
        # try to delete tmp directory for 5 seconds
        while time() - start < 5.0:
            try: shutil.rmtree(directory); break
            except: pass
        try: os.rmdir(os.path.dirname(directory)) 
        except: pass        

    try:
       if not os.path.isabs(working_dir) and len(project_list)>0:
          working_dir = os.path.abspath(os.path.join(project_list[-1].dir,working_dir))
    except: raise TypeError('working_dir -> directory path expected.')

    working_dir_base=working_dir
    del(working_dir)
    if len(project_list)>0:
      common_base_dir=os.path.commonprefix([i_project.dir for i_project in project_list])
      if not os.path.isdir(common_base_dir): common_base_dir=os.path.dirname(common_base_dir) # fix faulty commonprefix
      if not os.path.isdir(common_base_dir): raise EnvironmentError('Multiple project files require common base folder')
    for i_project in range(0, len(project_list)):
      working_dir=os.path.relpath(project_list[i_project].dir, common_base_dir)
      working_dir=os.path.abspath(os.path.join(working_dir_base, working_dir))
      try: 
        if not os.path.isdir(working_dir): os.makedirs(working_dir)
      except: raise EnvironmentError('Can`t create working directory %s' % working_dir)
      project_list[i_project].working_dir=working_dir
      del(working_dir)

    if project_suffix is not None and not isinstance(project_suffix, str):
        raise TypeError('project_suffix -> string expected.')  

    if jcmt_pattern is not None and not isinstance(jcmt_pattern, str):
        raise TypeError('jcmt_pattern -> string expected.')  
    
    if jcmt_pattern is None: jcmt_pattern = '.'

    if resultbag is not None and not isinstance(resultbag, jcmwave.Resultbag):
        raise TypeError('resultbag -> instance of jcmwave.Resultbag expected.')  

    if resultbag is not None and keys is None:
        raise TypeError('resultbag -> keys parameter must be set.')  

    if mode in ['version', 'license_info']:
        try: (out, err, err_code) = __private.call_tool(
            __private.JCMsolve, '--'+mode, stdout, stderr)
        except: raise EnvironmentError("Can`t excecute JCMsolve. Corrupted JCMsuite installation")
        try: logfd.close()
        except: pass
        return

    for i_project in range(0, len(project_list)):
      project=project_list[i_project]
      jcm_files = ['layout.jcm', 'grid.jcm', 'materials.jcm', 'sources.jcm',
                    'boundary_conditions.jcm', project.file]
      # get all files the project depends on
      jcm_src_files = []
      layoutfile_exists = True
      for jcm_file in jcm_files:
        
        #ignore grid file if layout exists
        if jcm_file=='grid.jcm' and layoutfile_exists: continue
        
        jcm_pattern_file =  jcm_file.replace('.jcm', '.'+jcmt_pattern+'.jcm')
        jcmt_pattern_file = jcm_pattern_file + 't'
        jcmt_file = jcm_file + 't'
        if isfile(pathjoin(project.dir, jcmt_pattern_file)):
            jcm_src_files.append(pathjoin(project.dir, jcmt_pattern_file))
        elif isfile(pathjoin(project.dir, jcm_pattern_file)):
            jcm_src_files.append(pathjoin(project.dir, jcm_pattern_file))
        elif isfile(pathjoin(project.dir, jcmt_file)):
            jcm_src_files.append(pathjoin(project.dir, jcmt_file))
        elif isfile(pathjoin(project.dir, jcm_file)):
            jcm_src_files.append(pathjoin(project.dir, jcm_file))
        elif jcm_file=='layout.jcm':
            layoutfile_exists = False
      project_list[i_project].jcm_src_files=jcm_src_files
      del(project)
      del(jcm_src_files)
      
    if resultbag is not None:
        
        #Calculation already running => job_id = 0
        project_files_all = ', '.join([i_project.file for i_project in project_list])
        if resultbag.is_running(keys): 
            print('%s: Results with tag %s already running' % (project_files_all, resultbag.get_tag(keys)) ) 
            return 0
        jcm_src_files_all=list()
        for i_project in project_list: jcm_src_files_all.extend(i_project.jcm_src_files)
        if not resultbag.check_source_files(jcm_src_files_all):
            if resultbag.has_results():
                raise EnvironmentError('%s: The resultbag is invalidated due to a change in the project files. Please revert the changes to the project files or reset the resultbag before continuing (i.e. call resultbag.reset()).'% project_files_all)
            else:
                print('%s: Project files are not set. Resetting resultbag.' % project_files_all)
                resultbag.reset()
                resultbag.set_source_files(jcm_src_files_all)
        elif resultbag.check_result(keys):
            print('%s: Results with tag %s already in result bag' % (project_files_all, resultbag.get_tag(keys)) )
            if jcmwave.daemon.daemonCheck(warn=False):
                if clean_up: cleanUp(working_dir_base) 
                return 0
            else: return resultbag.get_result(keys)
        
    #run embedded script when required
    produced_jcm_files = []
    for i_project in range(0, len(project_list)):
      project=project_list[i_project];
      if keys is not None or (project.working_dir != project.dir):
        for jcm_file_src in project.jcm_src_files:
          filepath, ext = os.path.splitext(jcm_file_src)        
          path, filename = os.path.split(filepath)

          #get base name for target
          basename = filename.replace('.'+jcmt_pattern,'')
          jcm_file_base = basename + '.jcm'
          if basename + '.jcmp' == project.file:
              jcm_file_base = basename + '.jcmp'
              if project_suffix is not None: 
                project.file = jcm_file_base.replace('.jcmp', '.'+project_suffix+'.jcmp')
                jcm_file_base = project.file
        
          jcm_file_target = pathjoin(project.working_dir, jcm_file_base)
            
          if ext == '.jcmt' or ext == '.jcmpt':
            try:
              tag = jcmwave.jcmt2jcm(jcm_file_src, keys, outputfile = jcm_file_target)
            except Exception as ex:
              msg = __private.toolerror(ex.args[0],jcmt2jcm_error=True)
              ex.__cause__ = None
              raise ex 
            produced_jcm_files.append(tag)

          else: 
            if not jcm_file_src == jcm_file_target and isfile(jcm_file_src):
              try: shutil.copyfile(jcm_file_src, jcm_file_target)
              except: 
                raise EnvironmentError('Can`t copy file {0} to working directory.'.format(jcm_file_src))

      #copy gds files
      if project.working_dir != project.dir:
        import glob
        gds_files = glob.iglob(os.path.join(project.dir, "*.gds"))
        for gds_file in gds_files:
            if os.path.isfile(gds_file): 
                shutil.copy2(gds_file, project.working_dir)
        
 
      project.file = os.path.join(project.working_dir,project.file)
      project.eigdate_old = 0.0
      if return_results:
        with open(project.file, 'r') as f: project.jcm = f.read()
        project.jcm = re.sub('\r\n', ' \n', project.jcm)
        project.jcm = re.sub('#.*', '', project.jcm)    
        project.result_dir=None;
        if (mode=='solve' and 
          re.search('(Project|Problem)[\n ]*[=]?[\n ]*{', project.jcm) is not None): 
          project.result_dir = pathjoin(project.dir, re.sub('.jcmp', '_results', project.file))
        try: 
          project.eigdate_old = os.path.getmtime(os.path.join(result_dir, 'eigenvalues.jcm'))
        except: pass
      project_list[i_project]=project

    if jcmwave.daemon.daemonCheck(warn=False):
#        resource_ids=optionStr.resources
        project_files = [i_project.file for i_project in project_list]
        eigdate_old = [i_project.eigdate_old for i_project in project_list]
        logFile = None
        if isinstance(logfile, str):
            logFile = logfile
        elif logfile is not None:
            print('invalid logfile parameter: file descriptors not supported in daemon mode')
            
        job_id = jcmwave.daemon.submit_job(
                                    project=project_files,
                                    mode=mode,
                                    resources = resources,
                                    logFile=logFile)
#        time.sleep(10)
        backtrace = NameSpaceHelper()
        backtrace.isProjectSequence=isProjectSequence
        backtrace.files = project_files
        backtrace.mode = mode
        backtrace.eigdate_old = eigdate_old
        backtrace.table_format = table_format
        backtrace.cartesianfields_format = cartesianfields_format
        backtrace.produced_jcm_files = produced_jcm_files
        backtrace.clean_up = clean_up
        backtrace.working_dir_base = working_dir_base
   
        setattr(__private.JCMdaemon,'job_{0}'.format(job_id),backtrace)     

        if resultbag is not None: resultbag.set_job_id(keys, job_id)

        if cache_finished_jobs:
            __private.JCMdaemon.temporaryIDs.add(job_id);
            jcmwave.daemon.wait(job_ids=__private.JCMdaemon.temporaryIDs, resultbag=resultbag, 
                                verbose=False, break_condition='cache')
        return job_id

    optionStr=''
    if process_keys is not None:
        if ('n_processes' in process_keys):
            optionStr=optionStr+' --n_processes '+str(process_keys['n_processes'])
        if ('nodes' in process_keys):
            optionStr=optionStr+' --cluster --hosts '+str(process_keys['nodes'])
        if ('n_threads' in process_keys):
            optionStr=optionStr+' --n_threads '+str(process_keys['n_threads'])
        if ('memory_limitGB' in process_keys):
            if (process_keys['memory_limitGB']>0):
                optionStr=optionStr+' --memory_limitGB '+str(process_keys['memory_limitGB'])
        if ('watchdog_memory_limitMB' in process_keys):
            if (process_keys['watchdog_memory_limitMB']>0):
                optionStr=optionStr+' --watchdog_memory_limitMB '+str(process_keys['watchdog_memory_limitMB'])
        if ('watchdog_kill_runtime' in process_keys):
            if (process_keys['watchdog_kill_runtime']):
                optionStr=optionStr+' --watchdog_kill_runtime'
    else:
        if 'nodes' in __private.__system:
            optionStr=optionStr+' --cluster --hosts '+__private.__system['nodes']
            
    try:
        project_list_str=" ".join(['"%s"' % (pathjoin(project.dir, project.file),) for project in project_list])
        (out, err, err_code) = __private.call_tool(__private.JCMsolve, '--%s %s %s' % (mode, optionStr, project_list_str), stdout, stderr)
    except: raise EnvironmentError("Can`t excecute JCMsolve. Corrupted JCMsuite installation")

    try: logfd.close()
    except: pass 
         
    if err_code!=0:
        msg = __private.toolerror(err)
        raise RuntimeError('*** JCMsolve failed. ==>\n\n%s' % (str(msg),))
    if not err is None and len(err)>0:
        msg = __private.toolerror(err)
        print('*** JCMsolve partially failed. ==>\n\n%s' % (str(msg),))

    # find output files
    if return_results or resultbag is not None:        
      results = list()
      for project in project_list:
        thisResults=list()
        if (mode=='solve' and  
           re.search('(Project|Problem)[\n ]*[=]?[\n ]*{', project.jcm) is not None): 
           fieldbagFile =  pathjoin(project.result_dir, 'fieldbag.jcm')  
           solveResults = dict()
           if isfile(fieldbagFile): solveResults['file'] = fieldbagFile
           try: solveResults['computational_costs'] = jcmwave.loadtable(
               pathjoin(project.result_dir, 'computational_costs.jcm')) 
           except: pass 
           try:
               eigdate = os.path.getmtime(pathjoin(project.result_dir, 'eigenvalues.jcm'))
               if eigdate>project.eigdate_old:
                    solveResults['eigenvalues'] = jcmwave.loadtable(
                        pathjoin(project.result_dir, 'eigenvalues.jcm'))
           except: pass 
           thisResults.append(solveResults)
    
        outs = re.findall('OutputFileName[\n ]*=[\n ]*"([^"]*)"',  project.jcm)
        for iO in outs:
          resultFile = os.path.abspath(pathjoin(project.working_dir, iO))
          if not isfile(resultFile):
              thisResults.append(None)
              continue
          try:
              thisResults.append(jcmwave.loadtable(resultFile, table_format))
              continue
          except: pass      
          if cartesianfields_format!='filepath':
            try: 
              thisResults.append(jcmwave.loadcartesianfields(resultFile, cartesianfields_format))
              continue
            except: pass
          thisResults.append(resultFile)
        results.append(thisResults)  
        del(project)
        
      if not isProjectSequence: results=results[0]

    if resultbag is not None: resultbag.add(keys = keys, result = results)

    
    # clean mode: clean files
    if clean_up: cleanUp(working_dir_base)  
    if not return_results: return None
    return results


