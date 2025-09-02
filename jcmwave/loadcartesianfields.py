# Copyright(C) 2012 JCMwave GmbH, Berlin.
#  All rights reserved.
#
# The information and source code contained herein is the exclusive property 
# of JCMwave GmbH and may not be disclosed, examined or reproduced in whole 
# or in part without explicit written authorization from JCMwave.
#
# Primary author: Lin Zschiedrich 
#
#SVN-File version: $Rev: 16472 $


from os.path import isfile
import jcmwave
from jcmwave import nested_dict
import jcmwave.__private as __private

def loadcartesianfields(file_name, format='squeeze'):
    """
    Loads a tensor fields given on a Cartesian grid stored in .jcm format.
   
    :param filepath file_name: path to a Cartesian fieldbag in .jcm format. 

    :param str format: format of the table after load. 

        Allowed values are: 'squeeze' (default) and 'full'. For details the "Results". 
        
   
    :returns: Dictionary with the following entries:

        - 'X', 'Y', 'Z' (numpy arrays): 
            x, y, z-coordinates of the Cartesian grid. 
            Each ``X``, ``Y``, ``Z`` has the shape ``[nx, ny, nz]``, where ``nx``, ``ny``, ``nz`` are the number of 
            grid points in each direction. ``X[ix, iy, iz]`` is the value of sampling vector 
            in x-direction at position ``ix``, ``0<=ix<nx``, irrespective of ``iy``, ``iz``. 
            Accordingly, we have ``Y[ix, iy, iz]=y[iy]`` and ``Z[ix, iy, iz]=z[iz]``. 
            For a Cartesian field in polar coordinates, XYZ arrays are changed to
            R, Theta and Phi holding the corresponding coordinate values.
        - 'field' (list of numpy arrays): 
            ``Fj=['field'][j]`` contains the field values of the (j+1)'th field of the fieldbag. ``Fj[ix, iy, iz, k]`` gives the k'th field component at the point with coordinates ``[x(ix), y(iy), z(iz)]`` of the (j+1)'th field. 
          When 'format' is 'squeeze', singleton dimensions are removed accordingly to the commands
            >>> X = X.squeeze() 
            >>> Y = Y.squeeze() 
            >>> Z = Z.squeeze() 
            >>> Fj = Fj.squeeze()
   
   
    Example::

        Plot Cartesian fieldbag on xy-mesh. Real part of the z-component of the first
        field is plotted. (matplotlib required):
   
        >>> cfb = jcmwave.loadcartesianfields('./project_results/cartesian_xy.jcm');
        >>> pcolormesh(cfb['X'], cfb['Y'], cfb['field'][0][:, :, 2].real, shading='gouraud') 
   
    """

    import numpy as np
    if __private.JCMsolve is None: jcmwave.startup();

    
    if not isinstance(file_name,str) or (
        not isfile(file_name)):
        raise TypeError('file_name -> file path expected.');

    if not isinstance(format, str) or not (format in ['squeeze', 
        'full']):
        raise TypeError('Invalid format');
    with open(file_name, 'rb') as ffb:
        try: header=__private.readblobheader(ffb, 'CartesianFieldBag')
        except TypeError as tEx: raise tEx
        except Exception as ex: raise Exception('Corrupted file.')

        nFields = header['NFields']
        numbertype = 'complex128';
        nSubs = 0;
        while True:
            try:
                header['TensorQuantityVector'][nSubs]
                nSubs+=1;
            except: break
        
        nComponents = list();
        for iSubField in range(0, nSubs):  
            nComponents.append(header['TensorQuantityVector'][
                iSubField]['NComponents']) 

        spaceDim = header['Grid']['SpaceDim'];
        lattice = header['Grid']['NPoints'];

        for iX in range(spaceDim, 3): np.append(lattice, 1)
    
    
        nP = lattice.prod();
        nCells = np.matrix([max(iX[0]-1, 1) for iX in lattice]).prod()

        if not header['__MODE__'] == 'BINARY':
            raise  RuntimeError('file not in binary format')

        fieldbag = dict();
        
        points = [np.arange(0, 0.1, 0.1), np.arange(0, 0.1, 0.1), np.arange(0, 0.1, 0.1)]
        fieldbag['field'] = list()
        fieldlist = fieldbag['field']
        try:
            for iX in range(0, spaceDim):
                points[iX] = np.fromfile(ffb, 'float64', lattice[iX][0]);
            
            try:
                containsDomainIds = nested_dict.get(header, 'Grid.ContainsDomainIds')=='yes';
            except: containsDomainIds = False;
            try:
                containsDomainIds = nested_dict.get(header, 'Grid.ContainsMaterialIds')=='yes';
            except: pass
            if containsDomainIds:
                nested_dict.set(fieldbag, 'grid.domainIds', np.fromfile(ffb, 'int32', nCells))

            nComp = nComponents[0]
            for iF in range(0, nFields):
                values = np.fromfile(ffb, numbertype, nComp*nP);
                values.shape = (nP, nComp)
                fieldlist.append(values)
        except: raise RuntimeError('Corrupted file')


    pol = nested_dict.get(header, ['TensorQuantityVector', 0, 'Polarization'])
    ttype = nested_dict.get(header, ['TensorQuantityVector', 0, 'Type'])

    # return full tensor in any case
    if pol!='xyz' and ttype.find('Strength')!=-1:
        indices = list()
        for iX in range(0, 3):
           if pol.count('xyz'[iX]): indices.append(iX)
        for  iF in range(0, nFields):
            pol_data = fieldlist[iF]
            fieldlist[iF] = np.ndarray([pol_data.shape[0], 3], dtype=numbertype)
            fieldlist[iF].fill(0.0)
            fieldlist[iF][:, indices] = pol_data
        nComp=3

    lattice = lattice.reshape(3,)
    X = np.ndarray(lattice);
    Y = np.ndarray(lattice);
    Z = np.ndarray(lattice);

    for iY in range(0, lattice[1]):
        for iZ in range(0, lattice[2]):
             X[:, iY, iZ] = points[0]

    for iX in range(0, lattice[0]):
        for iZ in range(0, lattice[2]):
             Y[iX, :, iZ] = points[1]

    for iX in range(0, lattice[0]):
        for iY in range(0, lattice[1]):
             Z[iX, iY, :] = points[2]
        
    if format=='squeeze':  
        X=np.squeeze(X)
        Y=np.squeeze(Y)
        Z=np.squeeze(Z)
        
    if 'CoordinateSystem' in header and header['CoordinateSystem'] == 'Polar':
        fieldbag['Theta'] = X
        fieldbag['Phi'] = Y
        fieldbag['R'] = Z
    else:    
        fieldbag['X'] = X
        fieldbag['Y'] = Y
        fieldbag['Z'] = Z
 
    shape = list(X.shape); shape.append(nComp);
    for iF in range(0, nFields):
        fieldlist[iF] = fieldlist[iF].reshape(shape, order='F')

    try:
        fieldbag['header'] = {'Origin' : header['Grid']['Origin'], 'Rotation':np.eye(3), 'QuantityType': ttype }            
        for iD,dir_ in enumerate(['X','Y','Z']):    
            fieldbag['header']['Rotation'][:,iD] = header['Grid']['Rotation'+dir_].transpose()

    except:
        pass
    return fieldbag

