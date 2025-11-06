import jcmwave
import numpy as np
import pickle as pk

field = []
radius = []
# with open('field_vs_NP.pkl', 'rb') as f:
#     data = pk.load(f)
# field = data['field']
# radius = data['radius']
# runs = np.arange(radius[-1]+2,101)
runs = np.arange(10,100)
for i in runs:
    keys = {"radius": i}
    #jcmwave.geo('.', keys)
    results = jcmwave.solve("project.jcmp", keys=keys)
    field.append(results[1]["ElectricFieldStrength"][0][0][0])
    radius.append(i)
    data = {"field": field, "radius": radius}
    # Pickle to a file
    with open('field_vs_NP.pkl', 'wb') as f:
        pk.dump(data, f)