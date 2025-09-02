# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Philipp Schneider
#
#SVN-File version: $Rev: 14989 $

"""Launch the jupyter notebook
   In order to launch a jupyter server, run e.g.
       JCMsuite/ThirdPartyLibs/Python/bin/python start_jupyter.py 

   Get more information on optional command line arguments by running
       JCMsuite/ThirdPartyLibs/Python/bin/python start_jupyter.py --help
"""
if __name__ == '__main__':
    import notebook.notebookapp as app
    app.main()
