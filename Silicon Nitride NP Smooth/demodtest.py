import matplotlib.pyplot as plt
from snompy.demodulate import demod
import numpy as np


x = np.arange(-2*np.pi,2*np.pi,0.01)
for i in range(100):
    d = demod(lambda a: np.sin(a), i/20*np.pi*2, 2*np.pi, 0)
    print(d)
    plt.scatter( i/20*np.pi*2,d)

plt.show()



