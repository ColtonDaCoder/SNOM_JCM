# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 4555 $



import os
import warnings
import jcmwave
import jcmwave.__private as __private

def set_memory_limit(max_ram=None):
    """

    Limits maximum job size. Too large jobs are aborted.
 
    :param int max_ram: maximum RAM usage (in MB). 
    
        (To reset the memory limit, call this method with empty argument)
    """

    if __private.JCMsolve is None: jcmwave.startup();
    if not max_ram is None:  
      if not isinstance(max_ram,int) or (max_ram<1):
          raise TypeError('Positive integer argument expected.')
      os.environ['JCM_MEMORY_LIMIT'] = str(max_ram)
      __private.__system['max_ram'] = max_ram
    else:
      os.environ['JCM_MEMORY_LIMIT'] = ''
      try: del  __private.__system['max_ram']
      except: pass
  
   
