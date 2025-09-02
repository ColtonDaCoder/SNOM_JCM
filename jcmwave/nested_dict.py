# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 3282 $


import string


def set(dict_,path,value):
    """
    Purpose: emulate Matlab struct behavior based on a nested dictionary
             dict_[level0][level1], ... [levelN].
             The sequence of keys 'level0', ..., 'levelN' is called 
             `dictionary path`.
    Input: dict_: dictionary to be manipulated
           path: dictionary path, that is:
              list or tuple, or string from which a path is formed
              by splitting at separators '.'.
           value: value to be set at path position       
    """

    if not isinstance(dict_, dict):
        raise TypeError('first argument must be a dictionary.')
    if not isinstance(path, (list, tuple, str)):
        raise TypeError('second argument must be a list, a tuple or a string.')
    if isinstance(path, str): path = path.split('.');

    data = dict_
    for elem in path[:-1]:
        if elem in data and isinstance(data[elem],dict):
            data = data[elem]
        else:
            data[elem] = {}
            data = data[elem]
    data[path[-1]] = value


def get(dict_, path):
    """
    Purpose: access data in the nested dictionary 
                dict_[level0][level1], ... [levelN]
             by its path 'level0', ..., 'levelN'.
 
    Input: dict_: dictionary from which data is taken.
           path: dictionary path, that is:
              list or tuple, or string from which a path is formed
              by splitting at separators '.'.
           value: value to be set at path position       
    Output: stored data at path position

    Raises an error if one of the keys does not exist.
    """
    if not isinstance(dict_, dict):
        raise TypeError('first argument must be a dictionary.')
    if not isinstance(path, (list, tuple, str)):
        raise TypeError('second argument must be a list, a tuple or a string.')
    if isinstance(path, str): path = path.split('.');

    data = dict_
    for elem in path[:-1]:
        if elem in data and isinstance(data[elem],dict):
            data = data[elem]
        else:
            raise KeyError('Dictionary node "%s" does not exist in path %s.' % 
                (str(elem), str(path)))
    
    if path[-1] in data:
        return data[path[-1]]
    else:
        raise KeyError('Last key in path %s is not in dictionary.' % (str(path),))


def update(dict1, dict2):
    if not isinstance(dict1, dict):
        raise TypeError('first argument must be a dictionary.')
    if not isinstance(dict2, dict):
        raise TypeError('second argument must be a dictionary.')


    keys1 = list(dict1.keys());
    keys2 = list(dict2.keys());

    for key2 in keys2:
       if (key2 in keys1 and 
         isinstance(dict1[key2], dict) and 
         isinstance(dict2[key2], dict)):
           update(dict1[key2], dict2[key2])
       else: 
           dict1[key2] = dict2[key2]
    
