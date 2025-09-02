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

def set_nodes(nodes=None):
    """

    Sets nodes for a cluster parallelization of JCMsolve

    :param str nodes: comma separated list of nodes. The leading host
            must be 'localhost'. Individual JCMROOT installation
            paths can be passed behind the host name with '::' separators.
            A missing are empty nodes parameter reset the solver to
            non-cluster behavior.

    Example: 

      jcmwave.set_nodes('localhost,maxwell2::/local/JCMsuite,maxwell3')

    .. Note::  To run a job on a remote computer (nodes), or to distribute
               multiple jobs in parallel use the JCMsuite daemon tool.

    .. Warning:: All cluster nodes must be accessible by an password-free ssh-login
    """

    if __private.JCMsolve is None: jcmwave.startup();
    
    if nodes is not None and not isinstance(nodes,str):
        raise TypeError('nodes -> string expected.')

    if nodes is None or len(nodes)==0: __private.__system.pop('nodes', None)
    else: __private.__system['nodes'] = nodes
    

