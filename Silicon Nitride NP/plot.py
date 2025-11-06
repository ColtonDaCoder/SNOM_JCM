import matplotlib.pyplot as plt
import numpy as np
import pickle as pk
import snompy



with open("field_vs_height_wvl.pkl", "rb") as f:
    loaded_data = pk.load(f)
z = []
real = []
imag = []
intensity = []
for index, d in enumerate(loaded_data["field"]):
    z.append(loaded_data['height'][index])
    real.append(np.real(d))
    angle = np.angle(d) if np.angle(d) < -1 else np.angle(d)-2*3.14
    imag.append(angle)
    intensity.append(np.sqrt(np.real(d)**2+np.imag(d)**2))
    #intensity.append(np.sqrt(np.real(d)**2+np.imag(d)**2)*np.exp(angle))

def f(z0):
    return np.interp(z0, loaded_data['height'], intensity)

fig, ax = plt.subplots()

# iterlist = np.linspace(loaded_data['height'][0]+100, loaded_data['height'][-1]-100, 1000)
# for i in iterlist:
#     complex = snompy.demodulate.demod(f, i, 20, 2)

#     ax.scatter(i, complex,color="purple",s=1)

# ax2 = ax.twinx()
# ax3 = ax.twinx()
# ax.scatter(z, real)
# for h in z:
#     print(h)
# for i in intensity:
#     print(i)
ax.scatter(z, intensity, color='purple')
#ax2.scatter(z, imag, color="orange")

plt.ylabel("Electric Field Intensity")
plt.xlabel("NP Radius (nm)")
plt.show()