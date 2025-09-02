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

def set_ooc_drive(ooc_dir=None, max_core_size=None):
    """

    Sets swapping directory for out-of-core computation.
 
    :param ooc_dir: base swap directory. 

        Data are swapped into a sub-directory of this path. Ideally, this base directory should be located on a fast SSD drive.

    :param float max_core_size: Maximum core RAM size (in MB). 

        By default, 90% of the free RAM are used.

    Detailed Description

      This command sets the environment variable JCM_MAX_CORE_SIZE and JCM_OOC_DIR.
      Only some parts of the runtime data are suitable for swapping to a fast SSD disk.
      Therefore, the actual RAM usage may exceed the value given in max_core_size. 
 
      Use set_memory_limit to define a `hard` memory restriction.
    """

    if __private.JCMsolve is None: jcmwave.startup();
    if not ooc_dir is None:
      if not isinstance(ooc_dir,str): 
          raise TypeError('ooc_dir -> directory path expected.');
      if (not os.path.isdir(ooc_dir)):
          raise TypeError('Argument "ooc_dir" not a valid directory path');
      os.environ['JCM_OOC_DIR'] = ooc_dir
      __private.__system['ooc_dir'] = ooc_dir
    else:
      os.environ['JCM_OOC_DIR'] = ''
      try: del  __private.__system['ooc_dir']
      except: pass
  
                        
    if not max_core_size is None:
      if (not isinstance(max_core_size,int)) or (max_core_size<1):
          raise TypeError('max_core_size: Positive integer argument expected.')
      os.environ['JCM_MAX_CORE_SIZE'] = str(max_core_size)
      __private.__system['max_core_size'] = max_core_size
    else:
      os.environ['JCM_MAX_CORE_SIZE'] = ''
      try: del  __private.__system['max_core_size']
      except: pass
