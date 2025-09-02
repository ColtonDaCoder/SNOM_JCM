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

import sys
import re
import threading
import os

JCMgeo = None
JCMgeo_unstable = None
JCMsolve = None
JCMview = None
JCMoptimizer = None
version = None
buildtag = None
socket_lock = threading.Lock()
license = dict()
license['file'] = None
license['period'] = None
license['server'] = None
__system = dict()
__system['n_cores'] = None
__system['n_threads'] = None
jcmt2jcm = dict()
optimizer = None
optimizer_client = None
optimizer_process = None

if 'LINUX' in sys.platform.upper():
    __system['os'] = 'LINUX'
    __system['binext'] = ''
elif 'WIN' in sys.platform.upper():
    __system['os'] = 'WINDOWS'
    __system['binext'] = '.exe'
else:
    __system['os'] = 'Unknown'
    __system['binext'] = ''
    

try: 
  import multiprocessing
  __system['n_cores'] = multiprocessing.cpu_count()
except: 
   try:
      with open('/proc/cpuinfo', 'r') as f: fsys = f.read()
      np = re.findall('(processor)', fsys);
      __system['n_cores'] = max(1, len(np));
   except:  __system['n_cores'] = 1;

from jcmwave.__private.call_tool import call_tool
from jcmwave.__private.socket_communication import *
from jcmwave.__private.smartpath import smartpath 
from jcmwave.__private.toolerror import toolerror
from jcmwave.__private.warning import warning
from jcmwave.__private.readblobheader import readblobheader
from jcmwave.__private.jcmt2jcm_from_string import jcmt2jcm_from_string
