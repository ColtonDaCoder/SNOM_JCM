#!/usr/bin/env python

# ==============================================================================
#
# Copyright(C) 2013 JCMwave GmbH, Berlin.
# All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Martin Hammerschidt 
#                 
# Date:           1/07/14
#
# ==============================================================================


# Imports
# ------------------------------------------------------------------------------
import jcmwave
import os
import tempfile
import re # regular expression parsing

# Function definitions
# ------------------------------------------------------------------------------

def call_templates(project_dir,parameters_):
    parameters = [{key:parameters_[key][index] for key in list(parameters_.keys())} for index in range(len(list(parameters_.values())[0]))]
    working_dir = tempfile.mkdtemp(prefix='__JCMwave__')
    jcm_files = [ 'materials.jcm', 'sources.jcm', 'boundary_conditions.jcm']
    return_list=[]
    for keys in parameters:
        project_tree=''
        for jcm_file in jcm_files:
            jcmt_file = os.path.join(project_dir, jcm_file+'t'); 
            jcm_file_wd = os.path.join(working_dir, jcm_file)
            if not os.path.isfile(jcmt_file):
                jcm_file_pd = os.path.join(project_dir, jcm_file);
                if jcm_file_pd!=jcm_file_wd and os.path.isfile(jcm_file_pd):
                    try:
                        with open(jcm_file_pd, 'r') as f: project_tree+=f.read()
                    except: EnvironmentError('Can`t read  file {0}.'.format(jcm_file_pd))
                continue
            try: 
                jcmwave.jcmt2jcm(jcmt_file, keys, outputfile=jcm_file_wd)
                with open(jcm_file_wd, 'r') as f:  project_tree+=f.read()
            except Exception as ex: raise ex 
        list_str ='##StartTag_{0:6d}_characters\n'.format(len(project_tree))
        list_str+= project_tree
        list_str+= '##EndTag_{0:6d}_characters\n'.format(len(project_tree))
        return_list.append(list_str)
    return return_list


def find_parameters(project_dir):
    jcmt_files = [ 'materials.jcmt', 'sources.jcmt', 'boundary_conditions.jcmt']
    jcm_files = list(3);
    
    for iF,jcmt_file in enumerate(jcmt_files):
        jcmt_file = os.path.join(project_dir, jcmt_file)
        if os.path.isfile(jcmt_file):
            try: 
                with open(jcmt_file, 'r') as f: jcm_ = f.read()
                jcm_files[iF]=jcm_
            except: EnvironmentError('Can`t read  file {0}.'.format(jcmt_file))
        else:
            continue
    for iF in range(3):
        jcm=jcm_files[iF]
        # skip comments
        jcm = re.sub('#.*', '', jcm)
        jcm = re.sub('\r\n', ' \n',jcm)
        matches=re.findall('([%]([?]?)\()([^)]*)(?=\)([\d]{0,2})([sdiefg]))')
        for match in matches:
            match=re.sub('[%]([?]?)\(','',match)
#            print(match[2])
        
    return 
