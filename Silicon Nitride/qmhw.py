import numpy as np
import matplotlib.pyplot as plt

alpha = 1
m = 1
hbar = 1
a = 1
beta = m * alpha * a / hbar**2

E_vals = np.linspace(0.001, 30, 30000)
z = np.sqrt(2 * m * E_vals) * a / hbar
f_z = np.cos(z) + beta * np.sin(z) / z

mask = np.abs(f_z) <= 1
E_allowed = E_vals[mask]
f_allowed = f_z[mask]

q1 = np.arccos(f_allowed) / a
q2 = -q1

plt.figure(figsize=(8,6))
plt.plot(q1, E_allowed, 'b.', markersize=1)
plt.plot(q2, E_allowed, 'b.', markersize=1)
plt.xlabel("q (1/a)")
plt.ylabel("E")
plt.title("Kronig–Penney Band Structure (α = 1, m = ħ = a = 1)")
plt.grid(True)
plt.show()
