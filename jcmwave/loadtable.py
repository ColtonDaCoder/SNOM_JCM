# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 17038 $


import re
from os.path import isfile
import jcmwave
from jcmwave import nested_dict
import jcmwave.__private as __private

def loadtable(file_name, format='named'):
    """
    Loads data from .jcm file stored in JCM table format.

    :param filepath file_name: path to a .jcm table file

    :param str format: output format of the loaded table (see below).  
    
    :returns:
    
      The output depends on the optional `format` specification
 
        format=='named'

            The output is a python dictionary with entries 

            'title'
 
                title of the table

            'header'

                nested dictionary containing meta-information. 

            '<Data1>', ... '<DataN>'

                 fields containing the table's data. `<Data1>`, ..., `<DataN>` 
                 are the column names as found in the .jcm file. A column
                 is not necessarily a (n_row x 1) vector. For example, the
                 xyz-components of n_rows wave vectors are stored as a 
                 (n_row x 3) numpy-matrix. Numbered data of the same type are stored in
                 dictionaries with integer keys (see the example of a Fourier table below).

        format=='list' 
    
            returns data as a list ordered as above

                | table[0]: title
                | table[1]: header
                | table[2 : N+1]: {<Data1>, ..., <DataN>}
         
        format=='matrix'

            drops title and header entry, returns complete table data as a (n_row x ?) numpy-matrix.
   
    Examples: 

      1. Load table containing computed eigenvalues of a resonance mode
         or propagating mode problem:
 
         >>> ev = jcmwave.loadtable('project_results/eigenvalues.jcm')
   
         In case of a propagating mode problem, the dictionary ev will contain
         the following fields (in given order)

            | 'title': title of the table
            | 'effective_refractive_index': computed propagating modes
            | 'precision': estimated accuracy of the computed modes
   
      2. Load Fourier coefficient table as produced by post-process 
         FourierTransform for a electromagnetic field scattering problem:  
         
         >>> ft = jcmwave.loadtable('project_results/fourier_transform.jcm')
   
         When the electric field components were computed, ft is a dictionary
         with the following fields (in given order):
   
             'title': 
                 title of the table
             'header': 
                 header containing meta-information, i.e. incoming field specifcation, 
                 permittivities of the lower and upper half space, reciprocal grid vectors 
                 for periodic problem, etc. 
             'K': 
                 k-vectors of the sampling in k-space (n_row x 3) matrix
             'N1', 'N2': 
                 defractions order with respect to first and second reciprocal grid vectors 
                 as given in the header (only present for periodic problems)
             'ElectricFieldStrength': 
                 electric field vectors of the Fourier modes. This is dictionary with integer 
                 keys, where ft.ElectricFieldStrength[iF] refers to the (iF+1)-th computed 
                 electric field.
   
      3. Load Fourier coefficients in matrix form:    
   
         >>> ft = loadtable('project_results/fourier_transform.jcm',
                format='matrix')

         This yields a (n_row x ?) numpy-matrix containing the data as in 2.:

         >>> 
         ft = [ft.N1; 
               ft.N2;
               ft.ElectricFieldStrength[0]; 
               ...
               ft.ElectricFieldStrength[nF-1]]
         
         where ``nF`` is the number of computed electric fields. 
    """

    if __private.JCMsolve is None: jcmwave.startup()

    
    if not isinstance(file_name,str) or (
        not isfile(file_name)):
        raise TypeError('file_name -> file path expected.')

    if not isinstance(format, str) or not (format in ['named', 
         'list', 'matrix']):
        raise TypeError('Invalid table format')
    
    with open(file_name, 'rb') as ft:

        tables = []

        while True:
            tables.append(loadtable_(ft, format))

            atEnd = True
            while True:
                pos = ft.tell()
                headerstart = ft.readline().decode()
                if ft.tell() == pos: break

                headerstart=headerstart.replace(' ', '').replace('\r\n', '').replace('\n', '')
                if not headerstart: continue
             
                if headerstart == '/*<BLOBHead>':
                    atEnd = False
                    ft.seek(pos)
                    break

            if atEnd: break
       
    if len(tables) == 1:
        return tables[0]
    else:
        return tables

def loadtable_(ft, format='named'):

    import numpy as np
    try: header=__private.readblobheader(ft, 'Table')
    except TypeError as tEx: raise tEx
    except Exception as ex: raise('Corrupted file.')

    table = dict()
    table['title'] = header['Title']
    try: table['header'] = header['MetaData']
    except: pass

    nColumns = header['NColumns']
    nRows = header['NRows']

    columns = [{} for iC in range(0,nColumns)]
    for iC in range(0,nColumns):
        columns[iC]['name'] = header['Column'+str(iC+1)]['Name']
        columns[iC]['type'] = header['Column'+str(iC+1)]['Type']
        dataType = columns[iC]['type']
        if dataType=='int': dtype='int32'
        elif dataType=='double': dtype='float64'
        elif dataType=='doublecomplex': dtype='complex128'
        else: raise RuntimeError('file corrupted!')
        columns[iC]['type'] = dtype
        columns[iC]['data'] = np.ndarray([nRows,],dtype=dtype)
    
    try:
        if header['__MODE__']=='BINARY':
            for iC in columns:
                iC['data']=np.fromfile(ft, iC['type'], nRows)
        else:
            nEntries=nRows*nColumns
            iE=0
            while iE<nEntries:
                l=ft.readline().decode()
                l=re.sub('\([ ]*', '(', l)
                l=re.sub(',[ ]*', ',', l)
                tline = l.split('#')[0].split()
                for tag in tline:              
                    col = columns[iE % nColumns]
                    row = int(iE//nColumns)
                    if col['type']=='int32': col['data'][row]=int(tag)
                    elif col['type']=='float64': col['data'][row]=float(tag)
                    else: 
                        (tagReal, tagImag) = tag.split(',')
                        col['data'][row]=complex(float(tagReal[1 :]), 
                                                 float(tagImag[0 : -1]))
                    iE+=1
    except: raise RuntimeError('File corrupted!')         
         
    if format=='matrix':
        table = np.matrix([iC['data'].flatten() for iC in columns])
        table = table.transpose()
    else:
        last_path = ''
        for iC in columns:
            key = iC['name']
            
            # Placeholder <DerivativeSep> serves as split indicator to turn the kay into
            # a path of the nested dict 
            def placeholder(m): return 'd_%s<DerivativeSep>%s' % (m.group(2), m.group(1))
            key = re.sub('d\((.*)\)_(.*)', placeholder, key)
            key = re.sub('d\((.*)\)_(.*)', placeholder, key)
           
            nameIndices = list()
            while True:  				
                nameIndex = re.search('(.*)(_\d{1,})',  key)
                if nameIndex is None: break
                key = nameIndex.group(1)
                nameIndices.append(int(nameIndex.group(2)[1 : ])-1)
            nameIndices.reverse()
              
            #determine index (X=0,Y=1,Z=2)
            index=-1
            if  key[-1] == 'X': index = 0
            elif key[-1] == 'Y': index = 1  
            elif key[-1] == 'Z': index = 2  
            if index > -1: key = key[:-1]

            #set path to value in nested dict
            path = key.split('<DerivativeSep>') + nameIndices

            if index>-1:
                if last_path != path:
                    try:
                        value_np = nested_dict.get(table,path)                    
                    except:
                        #initialize numpy array that collects values of X,Y,Z components
                        value_np=np.ndarray([nRows, 3], dtype=iC['type'])
                value_np[:, index] = iC['data'] 
                nested_dict.set(table,path,value_np)
            else:
                nested_dict.set(table,path,iC['data']) 

            last_path = path

        if format=='list':
            table=nested_dict.toNestedList(table) 
         
    return table
