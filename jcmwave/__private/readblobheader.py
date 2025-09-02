# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 16602 $


import re
import array 
from jcmwave import nested_dict


def readblobheader(f, blobtype):
    import numpy as np
    headerstart = f.readline().decode()
    headerstart=headerstart.replace('\r\n', '').replace('\n', '')
    if headerstart.replace(' ', '')!='/*<BLOBHead>':
        raise Exception('Missing header')
    header = dict()
    while True:
        headerentry = f.readline().decode()
        headerentry = headerentry.replace('\r\n', '').replace('\n', '')
        if headerentry=='*/': break
        dealentry(f, blobtype, header, headerentry)    
    if header['__MODE__']=='BINARY0':
       zero = array.array('B')
       zero.fromfile(f, 1);
       if not zero[0]==48: raise RuntimeError('file corrupted!')
       header['__MODE__']='BINARY'
       
    return header
     
def dealentry(f, blobtype, header, headerentry):
    
    import numpy as np
    keyValue=re.search('(<[IFS]>)?(.*)=(.*)', headerentry)
    if keyValue.group(1) is None: type='<S>'
    else: type=keyValue.group(1)
    key=keyValue.group(2) 
    key=re.sub('(_)(\d{1,})', lambda m: ':%s' % (m.group(2),), key) 
    value=keyValue.group(3)    

    if key[0]=='_' and key=='__BLOBTYPE__' and value!=blobtype:
        raise TypeError('Wrong file format. `%s` expected' % (blobtype,))
    
    # Placeholder <DerivativeSep> serves as split indicator to turn the key into
    # a path of the nested dict
    def placeholder(m): return 'd_%s<DerivativeSep>%s' % (m.group(2), m.group(1))
    key = re.sub('d\((.*)\)_(.*)', placeholder, key)
    key = re.sub('d\((.*)\)_(.*)', placeholder, key)
    #def mark_derivative(k):
    #    return re.sub('d\((.*)\)_(.*)', lambda m: 'd_%s<DerivativeSep>%s' % (
    #    m.group(2), m.group(1)), k);
    #key = mark_derivative(mark_derivative(key));
            
    key=key.split(':')
    for iK in range(0, len(key)): 
       try: key[iK] = int(key[iK])-1
       except: pass
    if type=='<I>': value = int(value)
    elif type=='<F>': value = float(value)
     
    for iK in range(len(key)-1, -1, -1):
       if not isinstance(key[iK], int):
          final_key = key[iK]
          break
    index = -1;
    if final_key[-1]=='X': index=0
    elif final_key[-1]=='Y': index=1
    elif final_key[-1]=='Z': index=2   

    if index!=-1: final_key = final_key[0 : -1]

    complex = False
    if type=='<F>':
      if final_key.count('Real'):
        final_key = final_key.replace('Real', '');
        complex=True
      elif final_key.count('Imag'):
        value*=1j
        final_key = final_key.replace('Imag', '');
        complex=True
    key[iK] = final_key

    #split key array elements at <DerivativeSep>
    path = []
    for k in key:
        try: path += k.split('<DerivativeSep>')
        except: path += [k]

    value_old = None
    try: value_old = nested_dict.get(header, path)
    except: pass

    if value_old is None: nested_dict.set(header, path, value);
    else:
       if index==-1: 
           nested_dict.set(header, path, value_old+value)
           return
        
       if type=='<I>': dtype='int32'
       elif complex: dtype='complex128'
       else: dtype='float64'
       if isinstance(value_old, np.ndarray) and value_old.dtype=='complex128':
          dtype='complex128'
       len_old = 1
       if isinstance(value_old, np.ndarray): len_old=value_old.shape[0]
       len_new = max(index+1, len_old)
       value_new=np.ndarray([len_new, 1], dtype=dtype); value_new.fill(0.0);
       value_new[0 : len_old, 0 : 1]=value_old
       value_new[index, 0] += value 
       nested_dict.set(header, path, value_new)

    

