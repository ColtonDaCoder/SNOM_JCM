# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 17416 $

import os
import sys
import re
import warnings
import jcmwave.set_num_threads 
import jcmwave.__private as __private

def startup(jcm_root=None, n_threads=None, nodes=None):
    """
    Deploys JCMsuite. 
    
    :param filepath jcm_root: installation directory of JCMsuite.

        When not set, the enviroment variable <JCMROOT> is used. 

    :param int n_threads: number of threads used by JCMsuite (calls ``set_num_threads``)
    :param str nodes: list of computer nodes to form a cluster for MPI computation (calls ``set_nodes``)


    """

    if jcm_root is not None and not isinstance(jcm_root,str):
        raise TypeError('jcm_root -> file path expected.');
    if (n_threads is not None and 
        (not isinstance(n_threads,int) or n_threads<1)):
        raise TypeError('n_threads -> positive integer expected.')
    if nodes is not None and not isinstance(n_nodes,str):
        raise TypeError('nodes -> string expected.')
    
    binext = __private.__system['binext'];
    if jcm_root is None:    
      install_dir = os.path.dirname(jcmwave.__file__);
      install_dir = os.path.dirname(install_dir);
      install_dir = os.path.dirname(install_dir);
      install_dir = os.path.dirname(install_dir);

      jcmsolvepath = os.path.join(install_dir, 'bin', 'JCMsolve'+binext);
      if not os.path.isfile(jcmsolvepath):
          try: jcm_root = os.environ['JCMROOT']; 
          except: pass 
      else: jcm_root = install_dir;
    if jcm_root is None: 
        raise EnvironmentError(
          'Environmental variable <JCMROOT> not set. Parameter "jcm_root" required.');       

    try: jcm_root = os.path.abspath(jcm_root)
    except: raise TypeError('jcm_root -> file path expected.');

    if not os.path.isdir(jcm_root):
        raise EnvironmentError('"%s" not a valid directory path' % jcm_root);

    os.environ['JCMROOT'] = jcm_root;  
    
    __private.JCMgeo = os.path.join(jcm_root, 'bin', 'JCMgeo'+binext);
    __private.JCMgeo_unstable = os.path.join(jcm_root, 'bin', 'JCMgeo_unstable'+binext);
    __private.JCMsolve = os.path.join(jcm_root, 'bin', 'JCMsolve'+binext);
    __private.JCMview = os.path.join(jcm_root, 'bin', 'JCMview'+binext);
    __private.JCMoptimizer = os.path.join(jcm_root, 'ThirdPartySupport', 'Python', 'bin', 'JCMoptimizer'+binext);

    try:
      (version_tag, err, err_code) = __private.call_tool(__private.JCMsolve, '--version');
    except RuntimeError as details:
        raise RuntimeError(
            """Initialization of JCMsolve failed. -> %s  Check your installation (JCMROOT = %s).'""" % (details, jcm_root))   

    
    version_tag  = re.search('Version[ ]*(?P<version_tag>\d*.\d*.\d*).*Buildtag:[ ]*(?P<build_tag>.*-\d*.\d*.\d*.\d*.\d*)', 
                       str(version_tag), flags=re.DOTALL)

    try: 
        __private.version = version_tag.group('version_tag');
        __private.buildtag = version_tag.group('build_tag');
    except:         
        raise EnvironmentError('Invalid version tag returned by JCMsolve. %s' %
                        'Please check your JCMsuite installation');   
    try:
      (license_info, err, err_code) = __private.call_tool(__private.JCMsolve, '--license_info')
      lf = re.search('License File:[ ]*(?P<license_file>.*.jcm)', license_info)
      __private.license['file'] = lf.group('license_file')
      lp = re.search('License period:[ ]*(?P<license_period>\d*-\d*-\d* -> \d*-\d*-\d*)', license_info)
      __private.license['period'] = lp.group('license_period')
    except:
      try:
        lp = re.search('server address :[ ]*(?P<license_server>.*)', license_info)
        __private.license['server'] = lp.group('license_server')
      except:
        __private.warning('No valid license found')

    if n_threads is not None: jcmwave.set_num_threads(n_threads)  
    if nodes is not None: jcmwave.set_num_nodes(nodes)    
    
