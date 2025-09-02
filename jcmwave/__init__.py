# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 17417 $

__doc__ = """
This module defines the python interface to JCMsuite.

Copyright(C) 2011 JCMwave GmbH, Berlin.
 All rights reserved.

SVN-File Version: $Rev: 17417 $
"""

## version check
import sys
if sys.version_info < (2, 6):
  raise ImportError("must use python 2.6 or greater")

## imports
from . import __private

# load functions into namespace
from .startup import startup
from .set_nodes import set_nodes
from .set_num_threads import set_num_threads
from .set_memory_limit import set_memory_limit
from .set_ooc_drive import set_ooc_drive
from .info import info
from .jcmt2jcm import jcmt2jcm
from . import nested_dict
from .geo import geo
from .solve import solve
from .view import view
from .edit import edit
from .loadtable import loadtable
from .loadcartesianfields import loadcartesianfields
from .resultbag import Resultbag
from .convert2powerflux import convert2powerflux
from . import daemon
from . import optimizer

__all__ = ['startup', 'set_num_threads', 'info',
           'jcmt2jcm', 'nested_dict', 
           'geo', 'solve', 'view', 'edit'
           'loadtable', 'loadcartesianfields',
           'Resultbag','daemon','call_templates',
           'convert2powerflux', 'optimizer'] 


