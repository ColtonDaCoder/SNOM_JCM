import matplotlib.pyplot as plt
import numpy as np
import pickle as pk
import snompy



with open("field_vs_height_focused.pkl", "rb") as f:
    loaded_data = pk.load(f)

def E(z0):
    return np.interp(z0, loaded_data['height'], loaded_data["field"])

signal = []
phase = []
for n in np.arange(0,5):
    freq = 250000
    omega = 2*np.pi*freq
    T = 2*np.pi/omega
    A = 100
    t_list = [t for t in np.arange(0,T,T/100)]
    z_list = [A/2*(1+np.cos(omega*t))+2 for t in t_list]
    E_list = [E(z)*np.exp(-omega*n*t_list[index]) for index, z in enumerate(z_list)]

    integral = np.trapezoid(E_list, t_list)
    signal.append(np.abs(integral))
    phase.append(np.atan(np.imag(integral)/np.real(integral)))
fig, ax = plt.subplots(2)
ax[0].plot(np.arange(0,5), signal)
ax[1].plot(np.arange(0,5), phase)
plt.show()
exit()



fig, ax = plt.subplots()


ax2 = ax.twinx()
ax3 = ax.twinx()
ax.scatter(z, real)
for h in z:
    print(h)
for i in intensity:
    print(i)
ax3.scatter(z, intensity, color='purple')
ax2.scatter(z, imag, color="orange")

plt.ylabel("Electric Field Intensity")
plt.xlabel("Tip - Sample Distance (nm)")
plt.show()