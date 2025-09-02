# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 14520 $



import os
import warnings
import jcmwave
import jcmwave.__private as __private

def set_num_threads(n_threads=None):
    """

    Sets number of threads used by JCMsolve for parallelization on SMP machines.
 
    :param int n_threads: number of parallel threads to be used by
      JCMsuite. If missing the number of available CPU cores is used.

    Detailed Description 

      Sets the environment variable OMP_NUM_THREADS. A value larger than one will 
      cause JCMsolve to run in parallel mode. 

    .. Warning:: A value larger than the number of idle CPUs may cause a performance loss.
    """

    if __private.JCMsolve is None: jcmwave.startup();
    if n_threads==None: n_threads = __private.__system['n_cores'];
    if (not isinstance(n_threads,int) or
        n_threads<1):
        raise TypeError('Positive integer argument expected.')

    n_cores = __private.__system['n_cores'];
    if n_threads>n_cores:
        warnings.warn('Number of threads reduced to number of cores.', Warning, 2)
        n_threads = n_cores;

    os.environ['OMP_NUM_THREADS'] = str(n_threads)
    __private.__system['n_threads'] = n_threads

