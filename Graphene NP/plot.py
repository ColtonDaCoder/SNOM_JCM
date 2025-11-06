import matplotlib.pyplot as plt
import numpy as np
import pickle as pk
import snompy



with open("field_vs_NP_G.pkl", "rb") as f:
    loaded_data = pk.load(f)
with open("field_vs_NP_SN2.pkl", "rb") as f:
    SN_data = pk.load(f)
z = []
real = []
imag = []
intensity = []

z_SN = []
intensity_SN = []
for index, d in enumerate(loaded_data["field"]):
    z.append(loaded_data['radius'][index]+2)
    real.append(np.real(d))
    angle = np.angle(d) if np.angle(d) < -1 else np.angle(d)-2*3.14
    imag.append(angle)
    intensity.append(np.sqrt(np.real(d)**2+np.imag(d)**2))
    try:
        intensity_SN.append(np.sqrt(np.real(SN_data["field"][index])**2+np.imag(SN_data["field"][index])**2))
        z_SN.append(SN_data['radius'][index]+2)
    except:
        pass
    #intensity.append(np.sqrt(np.real(d)**2+np.imag(d)**2)*np.exp(np.angle(d)))

def f(z0):
    return np.interp(z0, loaded_data['radius'], intensity)

fig, ax = plt.subplots()

# iterlist = np.linspace(loaded_data['height'][0]+100, loaded_data['height'][-1]-100, 1000)
# for i in iterlist:
#     complex = snompy.demodulate.demod(f, i, 20, 2)

#     ax.scatter(i, complex,color="purple",s=1)

# ax2 = ax.twinx()
# ax3 = ax.twinx()
#ax.scatter(z, real)
for h in z:
    print(h)
for i in intensity:
    print(i)
ax.scatter(z, intensity,label='Graphene')
ax.scatter(z_SN, intensity_SN,label='Silicon Nitride')
plt.legend()
#ax2.scatter(z, imag, color="orange")
plt.title("Scattered Light Intensity vs. Nanoparticle Radius")
plt.ylabel("Electric Field Intensity")
plt.xlabel("NP Radius (nm)")
plt.show()