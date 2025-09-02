# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 3297 $

import os
import sys
import jcmwave
import jcmwave.__private as __private


def view(jcm_file):
    """    
    Starts JCMview for field and mesh visualization. 

    :param filepath jcm_file: path to a .jcm fieldbag or grid file.
    
    Examples: 
    
        1. open a grid file for visualization:
          
        >>> jcmwave.view('grid.jcm')

        2. open a fieldbag file:
         
        >>> jcmwave.view('project_results/fieldbag.jcm')
    """


    if __private.JCMsolve is None: jcmwave.startup();

    if not isinstance(jcm_file, str) or (not os.path.isfile(jcm_file)):
        raise TypeError('jcm_file -> path to existing file expected.');

    try: __private.call_tool(__private.JCMview, '"%s"' % (jcm_file,), background=True)
    except: raise EnvironmentError("Can`t excecute JCMview. Corrupted JCMsuite installation")


