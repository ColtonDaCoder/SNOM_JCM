import matplotlib.pyplot as plt
import numpy as np
import pickle as pk



with open("field_vs_height_wvl.pkl", "rb") as f:
    loaded_data = pk.load(f)
num_wvl = 14
print(len(loaded_data['wvl']))
all_intensity = [[] for i in range(num_wvl)]
all_field = [[] for i in range(num_wvl)]
all_height = [[] for i in range(num_wvl)]
all_wvl = [[] for i in range(num_wvl)]
for j in range(num_wvl):
    for i in range(10):
        field = loaded_data["field"][i+j*10]
        all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
        all_field[j].append(field)
        all_height[j].append(loaded_data["height"][i+j*10])
        all_wvl[j].append(loaded_data["wvl"][i+j*10])
    plt.plot(all_height[j], all_intensity[j])
plt.show()

def E(z0, field_data, height_data):
    return np.interp(z0, height_data, field_data)

fig, ax = plt.subplots(2)
for n in [2,3,4]:
    signal = []
    phase = []
    wvl_list = []
    intensity = []
    for j in range(num_wvl):
        freq = 250000
        omega = 2*np.pi*freq
        T = 2*np.pi/omega
        A = 80
        t_list = [t for t in np.arange(0,T,T/100)]
        z_list = [A/2*(1+np.cos(omega*t))+2 for t in t_list]
        E_list = [E(z, all_field[j], all_height[j])*np.exp(-1j*omega*n*t_list[index]) for index, z in enumerate(z_list)]
        wvl_list.append(loaded_data["wvl"][j*10])
        integral = np.trapezoid(E_list, t_list)
        signal.append(np.abs(integral))
        #phase.append(np.atan(np.imag(integral)/np.real(integral)))
        phase.append(np.angle(integral))
        intensity.append(np.abs(integral)*np.exp(1j*np.angle(integral)))
    # if n==5:
    #     ref = intensity
    # if not n == 5:
    #     intensity = intensity/ref
    ax[0].plot(np.divide(10000,wvl_list), signal, label=n)
    ax[1].plot(np.divide(10000,wvl_list), phase, label=n)
    if n == 5:
        ref = integral
plt.legend()
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