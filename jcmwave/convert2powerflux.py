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
# Primary author: Carlo Barth (directly based on Matlab-version by
#                    Lin Zschiedrich)
# Date:           23/08/17
#
# ==============================================================================
import numpy as np

def convert2powerflux(FT_results):

    """Converts a Fourier transform results dict into a power flux density
    results dict. In the input Fourier transform dict, each row corresponds to an electric plane wave E(k)*exp(i*k*x) and a magnetic plane wave H(k)*exp(i*k*x). In the output dict the power flux density is formed as P(k) = 0.5*E(k) x conj(H(k)).
   
    :param dictionary FT_results: 
        A dict as returned by the JCMsuite FourierTransform post process.
   
    :returns: Dictionary of powerfluxes. 


    """
   
    # Check if the FT was applied to electric or magnetic fields
    if 'ElectricFieldStrength' in FT_results['title']:
        field_type = 'ElectricFieldStrength'
    elif 'MagneticFieldStrength' in FT_results['title']:
        field_type = 'MagneticFieldStrength'
    else:
        raise TypeError('Invalid input `FT_results`. Invalid type')
        return
   
    # Load/set constants
    try:
        from scipy import constants
        eps0 = constants.epsilon_0
        mu0 = constants.mu_0
    except:
        eps0=8.85418781762039e-12
        mu0=1.25663706143592e-06
   
    # Extract and convert FT data
    eps = np.real(FT_results['header']['RelPermittivity']*eps0)
    mu = np.real(FT_results['header']['RelPermeability']*mu0)
    k = FT_results['K']
    fourier_fields = FT_results[field_type]
   
    if field_type == 'ElectricFieldStrength':
        factor = 0.5*np.sqrt(eps/mu)
    else:
        factor = 0.5*np.sqrt(mu/eps)

    power_fields = {}
    k_holo_norm = np.linalg.norm(k, axis=1)
    ones = np.ones((3,1))
    for i, field in fourier_fields.items():
        nfield = np.sum(np.square(np.abs(field)), axis=1) / k_holo_norm
        kron = np.kron(ones, nfield).T
        power_fields[i] = factor * kron * k
   
    # Compose the output dict
    power_flux = dict(title=FT_results['title'].replace(field_type,
                                                'PowerFluxDensity'),
                      header=FT_results['header'],
                      PowerFluxDensity=power_fields)
    return power_flux
