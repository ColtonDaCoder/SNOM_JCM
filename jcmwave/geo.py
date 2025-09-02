# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 14976 $

import os
import sys
import re
import shutil
import warnings
import jcmwave
import jcmwave.__private as __private
try:
    from past.builtins import long
except:
    pass

def geo(project_dir=None, 
        keys=None,
        process_keys=None,
        working_dir=None,
        jcmt_pattern=None,
        show=None):
    """
    Starts JCMgeo for mesh generation. 
    
    :param filepath project_dir: path name of a JCMwave project directory. 
    
        A layout.jcm file must be present in the project directory.
    
    :param dictionary keys: parameter dictionary for embedded script input file.
    
        When keys is present, the embedded script file layout.jcmt 
        is processed to generate the actual .jcm input file. 
        (call of jcmwave.jcmt2jcm('layout.jcmt', keys))
    
    :param float show: shutdown time in seconds -> shows the created mesh in JCMview. 
    
        Automatically closes graphic window after given shutdown time (set value to float('inf') to keep window alive).
    
    :param directory_path working_dir: path name of a working directory. 
    
        JCMgeo copies .jcm files into working directory, runs JCMgeo therein.
    
    :param str jcmt_pattern: pattern for selection of .jcmt files. 

        layout.<pattern>.jcmt is used instead of sources.jcmt when present. 
    """

    if __private.JCMsolve is None: jcmwave.startup();

    if project_dir is None: project_dir = '.'
    if not isinstance(project_dir,str) or (
        not os.path.isdir(project_dir)):
        raise TypeError('project_dir -> directory path expected.');
    
    if (keys is not None) and (not isinstance(keys, dict)):
        raise TypeError('keys -> dictionary expected.');     

    if working_dir is None: working_dir = '.'
    if not isinstance(working_dir,str): 
        raise TypeError('working_dir -> directory path expected.');
    try:
        if not os.path.isabs(working_dir):
          working_dir = os.path.abspath(os.path.join(project_dir,working_dir))
    except: raise TypeError('working_dir -> directory path expected.')
    try: 
        if not os.path.isdir(working_dir): os.mkdir(working_dir)
    except: raise EnvironmentError('Can`t create working directory');

    if jcmt_pattern is not None and  not isinstance(jcmt_pattern, str):
        raise TypeError('jcmt_pattern -> string expected.');
    if show is not None and not isinstance(show, (int,long,float)):
        raise TypeError('show -> float or integer value expected.');      
        

    # run embedded script when required
    if keys is not None:
        jcm_files = ['layout.jcm', 'triangulator.jcm'];
        for jcm_file in jcm_files:
            jcmt_file = os.path.join(project_dir, jcm_file+'t'); 
            try: 
                jcmt_pattern_file = os.path.join(project_dir, 
                    jcm_file.replace('.jcm', '.'+jcmt_pattern+'.jcm')+'t')
                if os.path.isfile(jcmt_pattern_file):
                    jcmt_file = jcmt_pattern_file;
            except: pass
            jcm_file_wd = os.path.join(working_dir, jcm_file)
            if not os.path.isfile(jcmt_file):
                jcm_file_pd = os.path.join(project_dir, jcm_file);
                try: 
                    jcm_pattern_file = os.path.join(project_dir, 
                        jcm_file.replace('.jcm', '.'+jcmt_pattern+'.jcm')+'t')
                    if os.path.isfile(jcm_pattern_file):
                        jcm_file = jcm_pattern_file;
                except: pass
                if jcm_file_pd!=jcm_file_wd and os.path.isfile(jcm_file_pd):
                   try: shutil.copyfile(jcm_file_pd, jcm_file_wd);
                   except: EnvironmentError('Can`t copy file "%s" to working directory.')
                continue
            try: jcmwave.jcmt2jcm(jcmt_file, keys, outputfile=jcm_file_wd); 
            except Exception as ex: raise ex

    show_str = '';
    if show is not None:
        if (show==float('inf')): show_str = ' --show'
        elif (show>0.0): show_str = ' --show %g' % (show,)
 
    optionStr=''
    if process_keys is not None:
        n_processes=-1
        if ('n_processes' in process_keys):
            n_processes=process_keys['n_processes']
            optionStr=optionStr+' --n_processes '+str(n_processes)
        if ('n_threads' in process_keys):
            optionStr=optionStr+' --n_threads '+str(process_keys['n_threads'])
        elif n_processes!=-1:
            optionStr=optionStr+' --n_threads '+str(n_processes)

    project_dir = working_dir
    try: (out, err, err_code) = __private.call_tool(__private.JCMgeo, '"%s" %s' % (project_dir,optionStr+show_str))
    except: raise EnvironmentError("Can`t execute JCMgeo. Corrupted JCMsuite installation")

    if err_code!=0:
        msg = __private.toolerror(err)
        raise RuntimeError('*** JCMgeo failed. ==>\n\n%s' % (str(msg),));

    # check if grid.jcm is really created
    if not os.path.isfile(os.path.join(project_dir, 'grid.jcm')):
        raise RuntimeError('*** JCMgeo failed.')


    
