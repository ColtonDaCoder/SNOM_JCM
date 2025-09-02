# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 3273 $

import os
import warnings
import jcmwave
import jcmwave.__private as __private

def info():
    """
    Prints details about the JCMsuite installation and license status.
    """

    if __private.JCMsolve is None: jcmwave.startup();

    jcm_root = os.environ['JCMROOT']
    jcm_version = __private.version
    jcm_buildtag = __private.buildtag
    n_cores = __private.__system['n_cores']
    n_threads = __private.__system['n_threads']
    if n_threads is None: n_threads = 'default'
    else: n_threads=str(n_threads)

    w=20
    print("\nCopyright (c) 2001-2022 JCMwave GmbH, Berlin. All Rights Reserved")   
    print("\n\n")
    print("%s : %s" % ('JCMROOT'.rjust(w), jcm_root))
    print("%s : %s" % ('JCMsuite version'.rjust(w), jcm_version))
    print("%s : %s" % ('Buildtag'.rjust(w), jcm_buildtag))
    print("%s : %s" % ('Number CPUs'.rjust(w), n_cores))
    print("%s : %s" % ('Number threads'.rjust(w), n_threads))
    if 'nodes' in __private.__system:
        print("%s : %s" % ('Nodes'.rjust(w), __private.__system['nodes']))

    if 'ooc_dir' in  __private.__system.keys():
      print("%s : %s" % ('OOC directory'.rjust(w), __private.__system['ooc_dir']))

    if 'max_core_size' in  __private.__system.keys():
      print("%s : %d[MB]" % ('Maximum core size'.rjust(w), __private.__system['max_core_size']))

    if 'max_ram' in  __private.__system.keys():
      print("%s : %d[MB]" % ('Memory limit'.rjust(w), __private.__system['max_ram']))

    if __private.license['file'] is not None:
        print("%s : %s" % ('License file'.rjust(w),  __private.license['file']))
        print("%s : %s" % ('License file'.rjust(w),  __private.license['period']))
    elif __private.license['server'] is not None:
        print("%s : %s" % ('License server'.rjust(w),  __private.license['server']))
    else:
        print("\n\n  No valid license found.")
    print("\n\n")

