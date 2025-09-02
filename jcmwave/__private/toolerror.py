import os
import re
import hashlib
from jcmwave.__private import jcmt2jcm
from jcmwave.__private import smartpath
import jcmwave

def toolerror(msg,jcmt2jcm_error=False):
    err_parts = re.search(
        'File[ ]*"([^"]*)", line:[ ]*(\d*)[ ]*(, column:)?[ ]*(\d{1,})?(.*)', 
                          str(msg), re.DOTALL)

    if err_parts is None: return msg
    file = os.path.abspath(err_parts.group(1))
    line = int(err_parts.group(2))
    jcm_msg = err_parts.group(5)

    try:
      if jcmt2jcm_error:
        jcmwave.edit(
            file_name=smartpath(file), 
            line=line, 
            hint=jcm_msg)
        return jcm_msg
      bt=jcmt2jcm[hashlib.md5(file.encode()).hexdigest()];
      jcmt_line = bt['lines'][line-1]
      with open(bt['jcmt'], 'r') as f: jcmt_content = f.read().split('\n')[jcmt_line-1]
      sub_keys = re.search('[%]([?]?)\(([^)]*)\)([\d]{0,2})([sdiefg])', 
          jcmt_content)
      if sub_keys is not None:
        jcmt_msg = '\n>>>  %s\n*** Converted File: "%s", line: %d' % (
            jcmt_content, smartpath(file), line) 
        jcm_content = re.search('>>>(.*)', jcm_msg);
        if jcm_content is not None:
          jcm_msg = jcm_msg[0 : jcm_content.start()]+jcm_msg[jcm_content.end() : ];
          jcm_content = jcm_content.group(1);
          if len(jcm_content)>256: jcm_content=jcm_content[1 : 256]+' ...'
          jcmt_msg += '\n>>>%s' % (jcm_content,) 
      else: jcmt_msg = ''
     
      msg = '*** Error: File "%s", line: %d%s%s' % (
        smartpath(bt['jcmt']), jcmt_line, jcmt_msg, jcm_msg)
        
      #Open JCMwave editor and show error message      
      jcmwave.edit(
        file_name=smartpath(bt['jcmt']), 
        line=jcmt_line, 
        hint=jcmt_msg+jcm_msg)
      
      return msg

    except: pass
    jcmwave.edit(
        file_name=smartpath(file), 
        line=line, 
        hint=jcm_msg)
    return jcm_msg



