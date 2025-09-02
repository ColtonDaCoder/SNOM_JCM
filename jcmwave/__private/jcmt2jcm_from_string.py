
import os
import re
import string
import sys
import traceback
from jcmwave.__private import smartpath
import jcmwave
import copy



def jcmt2jcm_from_string(jcmt, keys, jcmt_file=None):
    if jcmt_file is None:
        jcmt_file="__from_string"
    jcmt_orig = jcmt

    #  fix window's line ends
    jcmt = re.sub('\r\n',' \n', jcmt);

    # quote start and end script tags and subsitutions in comments 
    jcmt = re.sub('(#.*)(<[?])(Python)?(.*)', lambda m:  
                      '%s?<%s%s' % (m.group(1), m.group(3), m.group(4)), 
                  jcmt)
    jcmt = re.sub('(#.*)([?]>)(.*)', lambda m: 
                      '%s>?%s' % (m.group(1), m.group(3)), 
                  jcmt)
    jcmt = re.sub('(#.*)([%])([^?]?)(\(.*\))(.*)', lambda m: 
                      '%s%s?%s%s%s' % (m.group(1), m.group(2), 
                                       m.group(3), m.group(4), m.group(5)), 
                  jcmt)

    # check for erroneous script start blocks
    for sTM in re.finditer('<[?]([^ \n]*)', jcmt):
       sT = sTM.group(1)
       if sT!='Python' and sT!='':
           raise SyntaxError(jcmt_file, jcmt, sTM.start()+2, 
                     jcmt_orig, 'Wrong script start tag `%s`' % sT);


    # add line counter
    jcmt = jcmt.split('\n')
    for il in range(0, len(jcmt)): jcmt[il]+='# __LINE %d' % (il+1,)
    jcmt = '\n'.join(jcmt)

    # transform jcmt file into executable script
    jcmt+='<?';
    jcmpy = str();
    jcm_echo_ = "\n%s(jcm_, jcm_lines_)=jcm_echo('''%s''', keys); jcm+=jcm_; jcm_lines.extend(jcm_lines_)"
    inScript = False
    pos_previous = 0;
    for tM in re.finditer('(<[?](Python)?|[?]>)', jcmt):
       # check script block consistency, sort opening/ending mismatch
       startTag = tM.group(1)=='<?' or tM.group(1)=='<?Python'
       pos = tM.start();
       if startTag and inScript:
           if pos<len(jcmt)-3:
               raise SyntaxError(jcmt_file, jcmt, pos, jcmt_orig, 
                               'Double script block opening tag.');
           else:
               raise SyntaxError(jcmt_file, jcmt, pos, jcmt_orig, 
                              'Script block not closed.')
       if not startTag and not inScript:
           raise SyntaxError(jcmt_file, jcmt, pos, jcmt_orig, 
                           'Non matching script block ending.')
       snippet=jcmt[pos_previous : pos] 
       if inScript: jcmpy+=snippet
       else:
          pos_bl = len(jcmpy)
          while (pos_bl>0):
            if (jcmpy[pos_bl-1]!=' ') and (jcmpy[pos_bl-1]!='\t'): break
            pos_bl-=1
          indentation = jcmpy[pos_bl : ];
          fist_line_info = re.search('# __LINE (\d*)', snippet);
          if fist_line_info is not None:
              jcmpy+='# __LINE %s' % fist_line_info.group(1)
          jcmpy+=jcm_echo_ % (indentation, snippet)
       inScript = startTag
       pos_previous = tM.end()
    #  execute jcmpy script
    try: jcmpyo = compile(jcmpy, '<jcmpy>', 'exec')
    except Exception as ex: 
        (type, msg, tb) = sys.exc_info()
        m = re.search('(.*)\(<jcmpy>, line (\d*)\)', str(msg))
        msg = m.group(1)
        line_jcmpy = int(m.group(2))
        line = int(re.search('# __LINE (\d*)', jcmpy.split('\n')[line_jcmpy-1]).group(1));
        raise Exception(error_message(jcmt_file, None, (line, None), jcmt_orig, msg))

    #(jcm, jcm_lines)=exec_jcmpyo(jcmpyo, copy.deepcopy(keys))

    try: (jcm, jcm_lines)=exec_jcmpyo(jcmpyo, copy.deepcopy(keys))
    except __SubstitutionError as subError:
      raise SubstitutionError(jcmt_file, None, subError.pos, 
                      jcmt_orig, str(subError)) 
    except Exception as ex:
      (type, msg, tb) = sys.exc_info()
      tb = traceback.format_tb(tb); tb.reverse()
      for jcmpy_trace in tb:
          if jcmpy_trace.count('<jcmpy>'): break
      line_jcmpy = int(re.search('line (\d*),',  jcmpy_trace).group(1))
      line = int(re.search('# __LINE (\d*)', jcmpy.split('\n')[line_jcmpy-1]).group(1));
      raise Exception(error_message(jcmt_file, None, (line, None), jcmt_orig, msg))

    # add line counts to JCMwaveGlobal for backtracking
    backtrace = dict()
    backtrace['jcmt'] = os.path.abspath(jcmt_file)
    backtrace['lines'] = jcm_lines

    return [jcm,backtrace]

def tolist(data, nTypes): 

    import numpy
    import numpy as np

    if isinstance(data, tuple): data = list(data); 
    elif isinstance(data, list): pass
    elif isinstance(data, (int,numpy.int64,numpy.int32,float,complex)): return [data,]
    elif isinstance(data, np.matrix): return data.ravel().tolist()[0]
    elif isinstance(data, np.ndarray): return data.ravel().tolist()
    
    for v in data: 
        if not isinstance(v, nTypes): return None
    return data 


def jcm_sub(m, keys):  
    import numpy
    import numpy as np

    opt = m.group(1)
    key = m.group(2)
    prec = m.group(3)
    type = m.group(4)

    try: value=jcmwave.nested_dict.get(keys, key) 
    except:
      if opt=='?': return m.group(0)
      subError =  __SubstitutionError(m.start(), 'No value provided for key `%s`.' % (key,))
      subError.__cause__ = subError
      raise subError

    if type=='s':
        if not isinstance(value,str):
            raise __SubstitutionError(m.start(), 'Value for key `%s` not a string.' % (key,))
        return value
    
    if isinstance(value, (np.matrix, np.ndarray)) and len(value.shape)==2:
         return '[%s]' % (';\n'.join([str(value[ii]).strip('[]') for ii in range(len(value))]),)
     
    if type=='d' or type=='i' and isinstance(value, (int,np.int64)): return str(value)


    if type=='d' or type=='i': nTypes = (int,); type_='an integer'; fmt = '%d';
    
    else: 
       nTypes = (int,float,complex,); type_= 'a float'
       if len(prec)==0: prec='15'; type='g'
       fmt = '%%.%s%s' % (prec, type);
       fmt_c = '(%s, %s) ' % (fmt, fmt)
       fmt+=' ';
    value = tolist(value, nTypes);
        
    if value is None: 
         what = '%s' % type_
         raise __SubstitutionError(m.start(), 'Value for key `%s` not %s.' % (key, what))

    value_string = str();
    for iV in value:
         if iV.imag!=0: 
              value_string+= fmt_c % (iV.real, iV.imag)
         else: 
             value_string+=fmt % (iV.real,)
    value_string = value_string[0 : -1]
    if len(value)>1 or len(value)==0: value_string = '[%s]' % value_string;
    return value_string




def jcm_echo(jcm, keys):

    import numpy
    import numpy as np

    jcm_lines = list();
    if len(jcm)==0: return (jcm, jcm_lines)
    try:
       jcm = re.sub('[%]([?]?)\(([^)]*)\)([\d]{0,2})([sdiefg])', 
                    lambda m: jcm_sub(m, keys), jcm);
    except __SubstitutionError as subErr:
        pos_jcm = subErr.pos_jcm
        line = re.search('(.*)# __LINE (\d*)', jcm[pos_jcm : -1])
        col = 0
        while col<pos_jcm and jcm[pos_jcm-col-1]!='\n': col+=1 
        subErr.pos = (int(line.group(2)), col+1)
        subErr.__cause__ =subErr
        raise subErr

    jcm_lines = re.findall('# __LINE \d*', jcm)
    if len(jcm_lines)>0:
       first_line = int(re.search('# __LINE (\d*)', jcm).group(1)) 
       jcm_lines  = list(range(first_line, first_line+len(jcm_lines)))
    else: jcm_lines = list() 

    jcm = re.sub('# __LINE \d*', '', jcm);
    return (jcm, jcm_lines)



def exec_jcmpyo(jcmpyo, keys):     

    import numpy                # 
    import numpy as np

    jcm = str(); jcm_lines = list();
    jcmNameSpaceL=locals()
    exec(jcmpyo,globals(),jcmNameSpaceL)
    jcm = jcmNameSpaceL['jcm']
    jcm_lines = jcmNameSpaceL['jcm_lines']
    return (jcm, jcm_lines)

def error_message(jcmt_file, jcmt, pos, jcmt_orig, msg):
    if jcmt is not None:
        jcmt_ = jcmt[0 : pos]
        line_ = jcmt_.count('\n')+1       
        col = pos-max(0, jcmt_.rfind('\n'))
        pos = (line_, col)
      
    line_text = jcmt_orig.split('\n')[pos[0]-1]    
    if pos[1] is not None:
        pos_msg = str('\n  File "%s", line: %d, column: %d\n    %s\n' %
             (smartpath(jcmt_file), pos[0], pos[1], line_text))
    else: 
        pos_msg = str('\n  File "%s", line: %d\n    %s\n' %
            (smartpath(jcmt_file), pos[0], line_text))
    return '%s%s' % (pos_msg, msg) 


           
class __SubstitutionError(Exception):
    def __init__(self, pos, msg):
         
        self.pos_jcm = pos
        self.pos = None
        self.args = (str(msg),)

class SubstitutionError(Exception):
    def __init__(self, jcmt_file, jcmt, pos, jcmt_orig, msg):
        self.args = (error_message(jcmt_file, jcmt, pos, jcmt_orig, msg),)



class SyntaxError(Exception):
    def __init__(self, jcmt_file, jcmt, pos, jcmt_orig, msg):
        self.args = (error_message(jcmt_file, jcmt, pos, jcmt_orig, msg),)
 
         
    
