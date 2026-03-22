import jcmwave
import numpy as np
import pickle as pk

field = []                                                                                                                                                                                                       
height = []
wvl = []                                                                                                                                                                                                                                                                                                                                                                                                                          
SN_eps1 = [5.214240758,5.189577913,5.158596071,5.132234122,5.105476174,5.078323095,5.044912859,5.016982676,4.988657899,4.960383558,4.926336716,4.897716309,4.870017466,4.841908539,4.808918896,4.782182184,4.755462076,4.729192562,4.698031228,4.672649601]                                                                                                                                                                       
SN_eps2 = [0.052369789,0.0579366392,0.0654543234,0.072514124,0.0803332992,0.088994664,0.1006117904,0.11131008,0.1229785872,0.13564866,0.1522028068,0.1670054568,0.182778232,0.1994103436,0.220372171,0.238590625,0.257386459,0.2766623496,0.3003250768,0.3204249834]                                                                                                                                                              
pt_eps1 = [-461.91,-470.569639889197,-479.308559556787,-488.12675900277,-497.024238227147,-506.000997229917,-515.05703601108,-524.192354570637,-533.406952908587,-542.70083102493,-552.073988919667,-561.526426592797,-571.058144044321,-580.669141274238,-590.359418282548,-600.128975069251,-609.977811634348,-619.905927977838,-629.913324099722,-640]                                                                         
pt_eps2 = [206.8,211.818282548476,216.894182825485,222.027700831025,227.218836565097,232.467590027701,237.773961218836,243.137950138504,248.559556786704,254.038781163435,259.575623268698,265.170083102493,270.82216066482,276.531855955679,282.299168975069,288.124099722992,294.006648199446,299.946814404432,305.94459833795,312]                                                                                             
water_eps1 = [1.68466944,1.67297584,1.6582095039,1.6426922604,1.6264349851,1.6070444736,1.5840760944,1.5651490064,1.5609382144,1.5785945364,1.6284318,1.6954608,1.76080923,1.82452608,1.845517,1.83946575,1.8278883344,1.8149778679,1.8018807975,1.79138436]                                                                                                                                                                      
water_eps2 = [0.0301136,0.0333723,0.038144636,0.045785896,0.05502507,0.07080512,0.097814656,0.133835136,0.178099248,0.235752488,0.29262608,0.33018968,0.31466564,0.26163144,0.20572272,0.16318352,0.14114496,0.12431256,0.1129463,0.1049776] 

def filter_by_na(k_list, NA=0.4):
    """
    Filters k-vectors inside a numerical aperture cone
    around a beam in the xy-plane at 30 degrees from x-axis.

    Parameters:
        k_list : list or Nx3 numpy array of [Kx, Ky, Kz]
        NA     : numerical aperture (default 0.4)

    Returns:
        numpy array of filtered k-vectors
    """

    k_array = np.array(k_list)
    indices = []

    # Beam direction: 30 degrees in xy-plane
    beam_dir = np.array([
        np.cos(np.deg2rad(30)),
        np.sin(np.deg2rad(30)),
        0.0
    ])

    beam_dir = beam_dir / np.linalg.norm(beam_dir)

    # NA half-angle
    alpha = np.arcsin(NA)
    cos_alpha = np.cos(alpha)

    filtered = []

    for k_index, k in enumerate(k_array):
        k_norm = np.linalg.norm(k)
        if k_norm == 0:
            continue

        k_unit = k / k_norm

        # Cosine of angle between k and beam direction
        cos_angle = np.dot(k_unit, beam_dir)

        # Keep vectors inside NA cone
        if cos_angle >= cos_alpha:
            indices.append(k_index)
            filtered.append(k)

    return np.array(filtered), indices


heights = [i-75 for i in np.arange(0, 105, 5)]
WVL = list([round(j,2) for j in np.linspace(5.5,6.5,20)])
for index, j in enumerate(WVL):
    for i in heights:
        keys = {"height": i,"waist": j/2*pow(10,-6), "wvl": j*pow(10,-6),
                "SN_eps1": SN_eps1[index], "SN_eps2": SN_eps2[index],
                "pt_eps1": pt_eps1[index], "pt_eps2": pt_eps2[index],
                "water_eps1": water_eps1[index], "water_eps2": water_eps2[index]
        }
        results = jcmwave.solve("project.jcmp", keys=keys)
        E = np.array(jcmwave.loadtable("project_results/ft.jcm",format="named")["ElectricFieldStrength"][0])
        K = jcmwave.loadtable('project_results/ft.jcm',format="named")["K"]

        vectors, indices = filter_by_na(K)
        Ep = 0 + 0j
        Es = 0 + 0j
        for field_index in indices:
            k_hat = np.divide(K[field_index],np.linalg.norm(K[field_index]))
            k_dir = (np.abs(np.dot(k_hat, E[index])))
            k_p = [-k_hat[1], k_hat[0], k_hat[2]]
            k_s = [-k_hat[2], k_hat[1], k_hat[0]]
            Ep = Ep + np.dot(k_p, E[field_index])
            Es = Es + np.dot(k_s, E[field_index])

        field.append([Ep, Es])
        height.append(i)
        wvl.append(j)
        data = {"field": field, "height": height, "wvl": wvl}
        # Pickle to a file
        with open('example_results.pkl', 'wb') as f:
            pk.dump(data, f)