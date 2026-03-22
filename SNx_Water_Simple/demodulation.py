import matplotlib.pyplot as plt
import numpy as np
import pickle as pk

with open("results_example.pkl", "rb") as f:
    normal = pk.load(f) 
with open("dev_v13_base_ref.pkl", "rb") as f:
    ref = pk.load(f) 
def E(z0, field_data, height_data):
    return np.interp(z0, height_data, field_data)
fig, ax = plt.subplots(2)
ax[0].grid()
ax[1].grid()
for data_index, loaded_data in enumerate([ref, normal]):

    num_wvl = 20
    all_intensity = [[] for i in range(num_wvl)]
    all_field = [[] for i in range(num_wvl)]
    all_height = [[] for i in range(num_wvl)]
    all_wvl = [[] for i in range(num_wvl)]
    if data_index == 0:
        skips= 11
    else:
        skips= 21
    offset = 0 
    all_dif = [[] for i in range(num_wvl)]
    for j in range(num_wvl):
        for i in range(skips):
            # print(i+j*skips)
            field = loaded_data["field"][i+j*skips+offset]
            field = field[0]
            all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
            all_field[j].append(field)
            all_height[j].append(loaded_data["height"][i+j*skips+offset])
            all_wvl[j].append(loaded_data["wvl"][i+j*skips+offset])
    #     plt.scatter(all_height[j], all_field[j])
    # plt.show()

    offset = 0
    wvl_list = [all_wvl[j][0] for j in range(num_wvl)]
    for n in [2,3]:
        signal = []
        phase = []
        intensity = []
        total_integral = []
        for j in range(num_wvl):
            freq = 250000
            omega = 2*np.pi*freq
            T = 2*np.pi/omega
            A = 100
            t_list = [t for t in np.arange(0,T,T/1000)]
            z_list = [A/2*(1+np.cos(omega*t))-75 for t in t_list]
            E_list = [E(z, all_field[j], all_height[j])*np.exp(-1j*omega*n*t_list[index]) for index, z in enumerate(z_list)]
            integral = np.trapezoid(E_list, t_list)
            signal.append(np.abs(integral))
            phase.append(np.angle(integral))

        ax[0].plot(wvl_list, signal, label=n)
        if n == 3:
            phase = np.add(phase,np.pi)
        if data_index == 0:
            ref_phase = phase 
            ax[1].plot(wvl_list, phase, label="adsorbed : " +str(n))
        else:
            ax[1].plot(wvl_list, np.subtract(phase, ref_phase), label="adsorbed : " +str(n))
        for p in phase:
            print(p)

    ax[1].set_axisbelow("True")
    ax[0].set(
        ylabel=r"Signal / a.u.",
    )
    ax[1].set(
        xlabel=r"Wavlength / µm",
        ylabel=r"Phase $\phi$ / radians",
    )
    plt.legend()
    #ax[0].invert_xaxis()
    #plt.gca().invert_xaxis()
plt.show()