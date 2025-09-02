# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 3237 $


import traceback
import warnings
import jcmwave
import os

def warning(msg):
    pkgroot = os.path.dirname(jcmwave.__file__)    
    tb = traceback.extract_stack();
    call_level = len(tb)
    for tbs in tb:
        if tbs[0].find(pkgroot)==0: break
        call_level-=1
    warnings.warn(str(msg), RuntimeWarning, call_level+1)
