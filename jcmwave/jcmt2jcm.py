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
import re
import sys
import string
import copy
import jcmwave 
import hashlib
import traceback
import jcmwave.__private as __private
from jcmwave.__private import smartpath

def jcmt2jcm(jcmt_file, keys, outputfile=None):
    """
    Process template .jcmt file with embedded python blocks to create a .jcm.
    
    :param filepath jcmt_file: pathname of the .jcmt file to be processed. 
   
    :param dictionary keys: contains values for template parameter substitution. 
   
    :param filepath outputfile: sets file path of .jcm output file. 

        If not set, the output file has the same basename as the jcmt_file input file, but with extension .jcm (jcmp), and is placed in the same directory  
          
    
    To embed a python into a file use the tag ``<?`` to start a script block 
    and use ``?>`` to end a script block. 
   
    Outside a script block one refers to the values of a parameter 
    by the following tags:

        * ``%(parName)i, %(parName)d`` --> integer values
        * ``%(parName)f, %(parName)e`` --> float values
        * ``%(parName)[3-15]e`` --> rounded float values, e.g. ``%(parName)10e`` truncates floating point number to ten digits.    
        * ``%(parName)s`` --> string values

    Here, ``parName`` is the parameter name. The tags are the substituted
    by the value of the field "parName" if present in the dictionary "keys"
    (e.g. ``%(parName)i --> keys['parName']``) and if the types are matching (integer,
    floats, and string). Integer and float vector arguments are also allowed.
   
    Simple Example: Definition of a material block (materials.jcm file). 
    The user provides the refractive index, e.g: 

    >>> keys['refractive_index'] = 1.5)

 
    The refractive index is converted to the relative permittivity value
    needed as needed by JCMsolve.


    >>> ... # non script block
    Material {
      MaterialId = 1
    <? # start script block
    keys['permittivity'] = keys['refractive_index']**2
    ?> # end python block
      RelPermittvity = %(permittivity)e # keyword substitution
      RelPermeability = 1.0
    }
    ...
   
    After processing the file the following Material definition is created,

    >>> ... # non script block
    Material {
      MaterialId = 1
      RelPermittvity = 2.25
      RelPermeability = 1.0
    }
    """

    try: 
        jcmt_filetag=__jcmt2jcm(jcmt_file, keys, outputfile)
        return jcmt_filetag
    except Exception as ex: raise ex
    
def __jcmt2jcm(jcmt_file, keys, outputfile):
    import numpy
    import numpy as np

    if __private.JCMsolve is None: jcmwave.startup();

    if not isinstance(jcmt_file,str):
        raise TypeError('jcmt_file -> file path or string expected.')
    if not os.path.isfile(jcmt_file):
        raise EnvironmentError('jcmt_file="%s" ->  not a file path.' % 
            (jcmt_file,))

    if not isinstance(keys, dict):
        raise TypeError('keys -> not a dictionary.');
    if outputfile is not None and not isinstance(outputfile, str):
        raise TypeError('outputfile -> file path expected.')


    # check if input file has jcmt or jcmpt extension
    jcmt_dir = os.path.dirname(jcmt_file)
    jcmt_name, jcmt_extension = os.path.splitext(os.path.basename(jcmt_file))
    if jcmt_extension!='.jcmt' and jcmt_extension!='.jcmpt':
        raise TypeError('File  "%s" has wrong extension %s.' % 
                 (jcmt_file, '(jcmt or jcmpt expected)'))


    # determine working directory and final jcm-file
    if outputfile is not None: jcm_file = outputfile
    else: jcm_file = jcmt_file[0 : -1]
    (jcm_dir, jcm_name) = os.path.split(jcm_file)

    if len(jcm_dir)==0: jcm_dir='.';
    if not os.path.isdir(jcm_dir):
        raise EnvironmentError('Directory "%s" not existing' % (jcm_dir,));
     
    try:
        with open(jcmt_file, 'r') as f: jcmt = f.read()
    except: raise EnvironmentError('Can`t read file "%s".' % (jcmt_file,))

    [jcm,backtrace]=__private.jcmt2jcm_from_string(jcmt, keys, jcmt_file)
    backtrace['jcm'] = os.path.abspath(jcm_file)
    
    # create final .jcm file
    try:
        with open(jcm_file, 'w') as f: f.write(jcm)
    except: raise EnvironmentError('Can`t create .jcm file "%s".' % (jcm_file,))

    jcmfile_tag=hashlib.md5(backtrace['jcm'].encode()).hexdigest()
    __private.jcmt2jcm[jcmfile_tag] = backtrace
    return jcmfile_tag


