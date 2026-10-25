"""
Near-field maps at several tip heights from saved 3D slices (results/fields/converge_x+0_g<gap>.npz):
|E| in the vertical x-z slice through the tip axis (perpendicular to the water | oil interface at x = 0),
p-polarized incidence, one shared log colour scale.

    python nearfield_heights.py      # -> figures/nearfield_heights.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

HERE = os.path.dirname(os.path.abspath(__file__))
GAPS = [1, 2, 3, 4, 5, 6]
R_TIP, HALF_ANGLE, T_SIN = 75.0, 30.14, 5.0
XLIM, ZLIM = (-150, 150), (-40, 90)


def tip_outline(gap):
    """Spherical apex tangent to the cone (x, z in nm)."""
    a = np.deg2rad(HALF_ANGLE)
    p = np.linspace(-np.pi/2, -a, 60)
    xr, zr = R_TIP*np.cos(p), gap + R_TIP + R_TIP*np.sin(p)
    xf = np.array([xr[-1], xr[-1] + (ZLIM[1] - zr[-1])*np.tan(a)])
    zf = np.array([zr[-1], ZLIM[1]])
    x = np.concatenate([-xf[::-1], -xr[::-1], xr, xf])
    z = np.concatenate([zf[::-1], zr[::-1], zr, zf])
    return x, z


def main():
    data = {}
    for g in GAPS:
        f = np.load(os.path.join(HERE, 'results', 'fields', f'converge_x+0_g{g}.npz'))
        X, Z = f['slice_xz_X']*1e9, f['slice_xz_Z']*1e9
        A = np.linalg.norm(f['slice_xz_E'][1], axis=-1)        # source 1 = p-polarized, |E|
        data[g] = (X, Z, A)
    m = (data[GAPS[0]][0] >= XLIM[0]) & (data[GAPS[0]][0] <= XLIM[1]) & \
        (data[GAPS[0]][1] >= ZLIM[0]) & (data[GAPS[0]][1] <= ZLIM[1])
    vmax = max(np.nanmax(A[m]) for X, Z, A in data.values())
    norm = LogNorm(vmin=vmax/100, vmax=vmax)
    with plt.rc_context({'font.size': 16, 'axes.titlesize': 19, 'axes.labelsize': 17,
                         'xtick.labelsize': 14, 'ytick.labelsize': 14}):
        fig, axs = plt.subplots(2, 3, figsize=(17, 6.6), sharex=True, sharey=True)
        for ax, g in zip(axs.flat, GAPS):
            X, Z, A = data[g]
            im = ax.pcolormesh(X, Z, np.clip(A, vmax/100, None), norm=norm, cmap='inferno', shading='auto')
            tx, tz = tip_outline(g)
            ax.plot(tx, tz, '-', color='w', lw=1.2)
            for z0 in (0.0, -T_SIN):
                ax.axhline(z0, color='w', lw=0.8, ls='--')
            ax.plot([0, 0], [ZLIM[0], -T_SIN], color='c', lw=1.2)
            ax.text(-142, -33, 'water', color='w', fontsize=14)
            ax.text(142, -33, 'oil', color='w', fontsize=14, ha='right')
            ax.set_title(f'Tip height {g} nm')
            ax.set_xlim(*XLIM)
            ax.set_ylim(*ZLIM)
            ax.set_aspect('equal')
        for ax in axs[1]:
            ax.set_xlabel('x (nm)')
        for ax in axs[:, 0]:
            ax.set_ylabel('z (nm)')
        cb = fig.colorbar(im, ax=axs, shrink=0.85, pad=0.02)
        cb.set_label('|E|  (incident = 1)')
        fig.suptitle('3D near field |E|, p-polarized, 6.1 µm, 5 nm SiN, tip over the water | oil interface')
        out = os.path.join(HERE, 'figures', 'nearfield_heights.png')
        fig.savefig(out, dpi=130, bbox_inches='tight')
    print('wrote', out, 'max |E| in view', vmax)


if __name__ == '__main__':
    main()
