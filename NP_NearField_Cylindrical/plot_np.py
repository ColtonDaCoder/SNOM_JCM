"""
Near-field maps of the cylindrical nanoparticle runs (results/<case>.npz), p polarized, |E| on a log scale,
starting mesh overlaid (mirrored to x < 0), tip / particle drawn from the mesh.

    python plot_np.py          # -> figures/np_nearfield.png (+ np_nearfield_mesh.png), all finished cases
"""
import os
import re
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, ListedColormap
from matplotlib.tri import Triangulation

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')
FIGS = os.path.join(HERE, 'figures')
ORDER = ('R0', 'R25', 'R50', 'R75')


def read_grid(path):
    """Points (nm) and triangles (0-based, domain id) from a binary cylindrical 2D grid.jcm (JCMsuite 6)."""
    b = open(path, 'rb').read()
    h = b[:b.index(b'*/')].decode('latin1')
    H = {k: float(v) for k, v in re.findall(r'<[IF]>(\w+)=([-\d.e+]+)', h)}
    s = b.index(b'*/') + 4
    n_p, n_t = int(H['NPoints']), int(H['NTriangles'])
    rec = np.frombuffer(b[s:s + 20*n_p], dtype=np.dtype([('id', '<i4'), ('x', '<f8'), ('y', '<f8')]))
    t = np.frombuffer(b[s + 20*n_p:s + 20*n_p + 16*n_t], dtype='<i4').reshape(-1, 4)
    return rec['x']*1e9, rec['y']*1e9, t[:, :3] - 1, t[:, 3]


def main(mesh=True):
    cases = [c for c in ORDER if os.path.exists(os.path.join(RES, f'{c}.npz'))]
    data = {}
    for c in cases:
        z = np.load(os.path.join(RES, f'{c}.npz'))
        data[c] = (z['X'], z['Y'], np.linalg.norm(z['E'], axis=-1), float(z['radius']), float(z['gap']))
    vmax = max(d[2].max() for d in data.values())
    lo = 0.3
    norm = LogNorm(vmin=lo, vmax=vmax)
    with plt.rc_context({'font.size': 15, 'axes.titlesize': 17, 'axes.labelsize': 16}):
        fig, axs = plt.subplots(1, len(cases), figsize=(5*len(cases) + 1.5, 6), squeeze=False)
        axs = axs[0]
        for ax, c in zip(axs, cases):
            X, Y, A, R, gap = data[c]
            x, y, t, d = read_grid(os.path.join(RES, f'{c}_grid.jcm'))
            xx, yy = np.r_[x, -x], np.r_[y, y]                         # mirror the r >= 0 mesh to x < 0
            tt, dd = np.r_[t, t + len(x)], np.r_[d, d]
            keep = (yy[tt].min(1) < Y.max()) & (yy[tt].max(1) > Y.min()) & (np.abs(xx[tt]).min(1) < X.max())
            tip = Triangulation(xx, yy, tt[keep & (dd == 3)])          # for drawing (both halves)
            tip_half = Triangulation(x, y, t[d == 3])                  # geometry is axisymmetric: test |x|
            inside = (tip_half.get_trifinder()(np.abs(X), Y) >= 0) | (A < lo)
            from scipy.ndimage import distance_transform_edt
            idx = distance_transform_edt(inside, return_distances=False, return_indices=True)
            im = ax.pcolormesh(X, Y, np.clip(A, lo, None)[tuple(idx)], norm=norm, cmap='inferno', shading='auto')
            ax.tripcolor(tip, np.zeros(len(tip.triangles)), cmap=ListedColormap(['#140b34']), shading='flat', zorder=3)
            if R > 0:
                th = np.linspace(0, 2*np.pi, 200)
                ax.plot(R*np.cos(th), 1 + R + R*np.sin(th), color='w', lw=1.0, ls='--', zorder=5)
            if mesh:
                ax.triplot(Triangulation(xx, yy, tt[keep]), color='w', lw=0.3, alpha=0.4, zorder=4)
            ax.set_xlim(X.min(), X.max())
            ax.set_ylim(Y.min(), Y.max())
            ax.set_aspect('equal')
            ax.set_title('no particle' if R == 0 else f'Au particle, r = {R:g} nm')
            ax.set_xlabel('x (nm)')
        axs[0].set_ylabel('y (nm)')
        cb = fig.colorbar(im, ax=list(axs), shrink=0.9, pad=0.015, fraction=0.03)
        cb.set_label('|E|  (incident = 1)')
        os.makedirs(FIGS, exist_ok=True)
        out = os.path.join(FIGS, 'np_nearfield' + ('_mesh' if mesh else '') + '.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
    print('wrote', out, cases, 'max |E|', vmax)


if __name__ == '__main__':
    main(mesh=True)
    main(mesh=False)
