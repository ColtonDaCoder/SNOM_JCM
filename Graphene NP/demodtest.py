import matplotlib.pyplot as plt
from snompy.demodulate import demod
import numpy as np
import random

d = []
y = []
X = np.arange(0,0.1,0.0001)
y = [1/x+random.random()*100 for x in X]
runs = np.arange(0,5)
for i in runs:
    d.append(demod(lambda a: 1/a+1, 10, 9, i))
fig, ax = plt.subplots(2)
ax[0].scatter(X,y,s=5)
ax[1].plot(runs,d)

plt.show()



