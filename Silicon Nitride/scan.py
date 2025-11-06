import jcmwave
import numpy as np
import pickle as pk

field = []
height = []
with open('field_vs_height_focused.pkl', 'rb') as f:
    data = pk.load(f)
field = data['field']
height = data['height']
runs = [j*100+1600 for j in range(15)] 
for i in runs:
    keys = {"height": i}
    #jcmwave.geo('.', keys)
    results = jcmwave.solve("project.jcmp", keys=keys)
    field.append(results[1]["ElectricFieldStrength"][0][0][0])
    height.append(i)
    data = {"field": field, "height": height}
    # Pickle to a file
    with open('field_vs_height_focused.pkl', 'wb') as f:
        pk.dump(data, f)