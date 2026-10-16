"""
Plot the two vertical field slices through the tip axis saved by run_linescan.py
(stages with save_fields=True, files results/fields/<stage>_x<x>_g<gap>.npz).

    python plot_fields.py results/fields/converge_x+0_g1.npz            # p-incidence, |E|
    python plot_fields.py results/fields/converge_x+0_g1.npz s Ez       # s-incidence, Re(Ez)

    slice_yz: x = 0, parallel to the water | oil interface
    slice_xz: y = 0, perpendicular to the interface (interface at x = x_interface)
Fields are the total electric field in V/m for an incident amplitude of 1 V/m.
"""
import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

path = sys.argv[1]
pol = sys.argv[2] if len(sys.argv) > 2 else 'p'          # incident polarization: s (source 1) or p (source 2)
quantity = sys.argv[3] if len(sys.argv) > 3 else 'abs'   # abs, Ex, Ey, Ez (real part)
src = {'s': 0, 'p': 1}[pol]

d = np.load(path)
m = re.search(r'_x([+-]?\d+)_g(\d+)', path)
x_if, gap = (float(m.group(1)), float(m.group(2))) if m else (None, None)

# tip outline (same construction as layout.jcmt): 75 nm sphere tangent to a 30.14 deg cone
R, alpha = 75.0, np.deg2rad(30.14)
phi = np.linspace(-np.pi/2, -alpha, 50)
cap_r, cap_z = R*np.cos(phi), R + R*np.sin(phi)
cone_z = np.linspace(cap_z[-1], 2000, 50)
cone_r = cap_r[-1] + (cone_z - cap_z[-1])*np.tan(alpha)
tip_r = np.concatenate([cap_r, cone_r])
tip_z = np.concatenate([cap_z, cone_z])

fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
for ax, name, lat_label in [(axes[0], 'slice_xz', 'x / nm'), (axes[1], 'slice_yz', 'y / nm')]:
    X, Y, Z = d[name + '_X']*1e9, d[name + '_Y']*1e9, d[name + '_Z']*1e9
    lat = X if name == 'slice_xz' else Y
    E = d[name + '_E'][src]
    if quantity == 'abs':
        val = np.linalg.norm(E, axis=-1)
        im = ax.pcolormesh(lat, Z, val, shading='auto', cmap='inferno', norm=LogNorm(vmin=val.max()*1e-3, vmax=val.max()))
    else:
        val = E[..., 'xyz'.index(quantity[-1].lower())].real
        v = np.abs(val).max()
        im = ax.pcolormesh(lat, Z, val, shading='auto', cmap='RdBu_r', vmin=-v, vmax=v)
    plt.colorbar(im, ax=ax, label=f'{quantity} (|E| in V/m)' if quantity == 'abs' else f'Re {quantity} / (V/m)')
    for zl in (0, -5):                                      # SiN window
        ax.axhline(zl, color='w', lw=0.6, ls='--')
    if gap is not None:
        ax.plot(tip_r, tip_z + gap, 'c-', lw=0.8)
        ax.plot(-tip_r, tip_z + gap, 'c-', lw=0.8)
    if name == 'slice_xz' and x_if is not None:
        ax.plot([x_if, x_if], [Z.min(), -5], 'c:', lw=1.2)
        ax.text(x_if, Z.min(), '  water | oil', color='c', va='bottom', fontsize=8)
    ax.set(xlabel=lat_label, title={'slice_xz': 'y = 0 (perpendicular to interface)',
                                    'slice_yz': 'x = 0 (parallel to interface)'}[name])
    ax.set_xlim(lat.min(), lat.max())
    ax.set_ylim(Z.min(), Z.max())
axes[0].set_ylabel('z / nm')
fig.suptitle(f'{path}: {pol}-incidence, {quantity}')
plt.tight_layout()
plt.show()
