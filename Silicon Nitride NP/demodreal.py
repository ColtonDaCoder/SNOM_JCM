import matplotlib.pyplot as plt
import numpy as np
import pickle as pk

# with open("field_vs_height_wvl_ref.pkl", "rb") as f:
#     ref_loaded_data = pk.load(f)
# with open("field_vs_height_wvl_Dispersive.pkl", "rb") as f:
#     loaded_data = pk.load(f)

with open("field_vs_height_wvl_smooth_FE5.pkl", "rb") as f:
    loaded_data = pk.load(f)
with open("field_vs_height_wvl_smooth_FE5_ref.pkl", "rb") as f:
    ref_loaded_data = pk.load(f)

# with open("field_vs_height_wvl_ref_half.pkl", "rb") as f:
#     half_ref_loaded_data = pk.load(f)
# with open("field_vs_height_wvl_Dispersive_half.pkl", "rb") as f:
#     half_loaded_data = pk.load(f)

num_wvl = 2
ref_all_intensity = [[] for i in range(num_wvl)]
ref_all_field = [[] for i in range(num_wvl)]
ref_all_height = [[] for i in range(num_wvl)]
ref_all_wvl = [[] for i in range(num_wvl)]
all_intensity = [[] for i in range(num_wvl)]
all_field = [[] for i in range(num_wvl)]
all_height = [[] for i in range(num_wvl)]
all_wvl = [[] for i in range(num_wvl)]
skips = 10
half_skips = 9
# for j in range(num_wvl):
#     for i in range(skips*2-1):
#         if i % 2 == 0:
#             new_i = int(i/2)
#             field = loaded_data["field"][new_i+j*skips]
#             all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
#             all_field[j].append(field)
#             all_height[j].append(loaded_data["height"][new_i+j*skips])
#             all_wvl[j].append(loaded_data["wvl"][new_i+j*skips])
#             ref_field = ref_loaded_data["field"][new_i+j*skips]
#             ref_all_intensity[j].append(np.sqrt(np.real(ref_field)**2+np.imag(ref_field)**2))
#             ref_all_field[j].append(ref_field)
#             ref_all_height[j].append(ref_loaded_data["height"][new_i+j*skips])
#             ref_all_wvl[j].append(ref_loaded_data["wvl"][new_i+j*skips])
#         else:
#             new_i = int((i-1)/2)
#             field = half_loaded_data["field"][new_i+j*half_skips]
#             all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
#             all_field[j].append(field)
#             all_height[j].append(half_loaded_data["height"][new_i+j*half_skips])
#             all_wvl[j].append(half_loaded_data["wvl"][new_i+j*half_skips])
#             ref_field = half_ref_loaded_data["field"][new_i+j*half_skips]
#             ref_all_intensity[j].append(np.sqrt(np.real(ref_field)**2+np.imag(ref_field)**2))
#             ref_all_field[j].append(ref_field)
#             ref_all_height[j].append(half_ref_loaded_data["height"][new_i+j*half_skips])
#             ref_all_wvl[j].append(half_ref_loaded_data["wvl"][new_i+j*half_skips])
#     plt.scatter(all_height[j], np.abs(all_field[j]),label=all_wvl[j])

#     plt.title(10000/all_wvl[j][-1])
# plt.show()

# all_intensity = [[] for i in range(num_wvl)]
# all_field = [[] for i in range(num_wvl)]
# all_height = [[] for i in range(num_wvl)]
# all_wvl = [[] for i in range(num_wvl)]
skips= 21
for j in range(num_wvl):
    for i in range(21):
        print(i+j*skips)
        field = loaded_data["field"][i+j*skips]
        all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
        all_field[j].append(field)
        all_height[j].append(loaded_data["height"][i+j*skips])
        all_wvl[j].append(loaded_data["wvl"][i+j*skips])
    plt.scatter(all_height[j], np.abs(all_field[j]),label=all_wvl[j])
plt.show()
for j in range(num_wvl):
    for i in range(21):
        print(i+j*skips)
        field = ref_loaded_data["field"][i+j*skips]
        ref_all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
        ref_all_field[j].append(field)
        ref_all_height[j].append(ref_loaded_data["height"][i+j*skips])
        ref_all_wvl[j].append(ref_loaded_data["wvl"][i+j*skips])
    plt.scatter(ref_all_height[j], np.abs(ref_all_field[j]),label=ref_all_wvl[j])
plt.show()
# skips= 21
# for j in range(num_wvl):
#     for i in range(21):
#         print(i+j*skips)
#         field = ref_loaded_data["field"][i+j*skips]
#         ref_all_intensity[j].append(np.sqrt(np.real(field)**2+np.imag(field)**2))
#         ref_all_field[j].append(field)
#         ref_all_height[j].append(ref_loaded_data["height"][i+j*skips])
#         ref_all_wvl[j].append(ref_loaded_data["wvl"][i+j*skips])
    # plt.scatter(ref_all_height[j], np.abs(ref_all_field[j]),label=ref_all_wvl[j])
# plt.show()

def E(z0, field_data, height_data):
    return np.interp(z0, height_data, field_data)
fig, ax = plt.subplots(2)
for n in [2]:
    ref_signal = []
    ref_phase = []
    signal = []
    phase = []
    wvl_list = []
    ref_intensity = []
    intensity = []
    total_ref_integral = []
    total_integral = []
    for j in range(num_wvl):
        freq = 250000
        omega = 2*np.pi*freq
        T = 2*np.pi/omega
        A = 100
        t_list = [t for t in np.arange(0,T,T/300)]
        z_list = [A/2*(1+np.cos(omega*t)) for t in t_list]
        E_list = [E(z, all_field[j], all_height[j])*np.exp(-1j*omega*n*t_list[index]) for index, z in enumerate(z_list)]
        integral = np.trapezoid(E_list, t_list)
        #E_list = [INDEX*1.1 for INDEX in z_list]
        t_list = [t for t in np.arange(0,T,T/300)]
        z_list = [A/2*(1+np.cos(omega*t)) for t in t_list]
        ref_E_list = [E(z, ref_all_field[j], ref_all_height[j])*np.exp(-1j*omega*n*t_list[index]) for index, z in enumerate(z_list)]
        ref_integral = np.trapezoid(ref_E_list, t_list)
        wvl_list.append(loaded_data["wvl"][j*skips])

        ref_signal.append(np.abs(ref_integral))
        signal.append(np.abs(integral))

        ref_phase.append(np.angle(ref_integral))
        phase.append(np.angle(integral))

        total_ref_integral.append(ref_integral)
        total_integral.append(integral)

        ref_intensity.append(np.abs(ref_integral)*np.exp(1j*np.angle(ref_integral)))
        intensity.append(np.abs(integral)*np.exp(1j*np.angle(integral)))

    ax[0].scatter(wvl_list, signal, label=n)
    ax[0].scatter(wvl_list, ref_signal, label=n)
    #ax[0].scatter(wvl_list, np.divide(signal, ref_signal), label=n)

    ax[1].plot(wvl_list, phase, label=n)
    ax[1].plot(wvl_list, ref_phase, label=n)
    #ax[1].plot(wvl_list, np.subtract(phase, ref_phase), label=n)


ax[0].set_ylabel(r"signal / a.u.")
ax[1].set(
    xlabel=r"$\nu$ / cm$^{-1}$",
    ylabel=r"$\phi$ / radians",
)
plt.legend()
#ax[0].invert_xaxis()
#plt.gca().invert_xaxis()
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