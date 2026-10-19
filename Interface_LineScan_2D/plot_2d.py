"""
Plots of the 2D line scans (results/<stage>[.partIofN].pkl -> figures/).

    python plot_2d.py scan_h5      # amplitude / phase vs x: backscatter Ep (p in), Es (s in), gap integral of Ey (p in)

x = x_interface: x < 0 means the tip is over oil, x > 0 over water.
"""
import os
import sys
import glob
import pickle as pk
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGS = os.path.join(HERE, 'figures')


def load(stage):
    """All records of a stage, merged over its parts, sorted by (gap, x)."""
    files = [os.path.join(RESULTS, stage + '.pkl')] + sorted(glob.glob(os.path.join(RESULTS, stage + '.part*.pkl')))
    recs = []
    for f in files:
        if os.path.exists(f):
            recs += pk.load(open(f, 'rb'))['records']
    return sorted(recs, key=lambda r: (r['gap'], r['x_interface']))


def plot_scan(stage, gap=5):
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs])
    quantities = [
        ('Backscattered Ep, p polarized', np.array([r['p_in'][1] for r in recs])),
        ('Backscattered Es, s polarized', np.array([r['s_in'][0] for r in recs])),
        (f'Ey integrated from SiN to tip ({gap:g} nm), p polarized', np.array([r['gap_integral'][1, 1] for r in recs])),
    ]
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.5), sharex=True)
    for j, (title, v) in enumerate(quantities):
        ax[0, j].plot(x, np.abs(v), 'o-', ms=4)
        ax[0, j].set_title(title)
        ax[0, j].set_ylabel('amplitude' + (' (nm V/m)' if j == 2 else ' (arb.)'))
        ax[1, j].plot(x, np.unwrap(np.angle(v)), 'o-', ms=4, color='C1')
        ax[1, j].set_ylabel('phase (rad)')
        ax[1, j].set_xlabel('interface position x (nm)   oil  <  0  <  water')
        for a in ax[:, j]:
            a.axvline(0, color='0.6', lw=0.8)
            a.grid(alpha=0.3)
    fig.suptitle(f'2D line scan, gap {gap:g} nm')
    fig.tight_layout()
    os.makedirs(FIGS, exist_ok=True)
    out = os.path.join(FIGS, f'{stage}_g{gap:g}.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


def plot_combined(stage, gap=5):
    """
    Es and Ep combined (in 2D s and p do not mix: the cross-polarized parts are exactly 0).
    Total |E| = sqrt((|Es|^2 + |Ep|^2) / 2): unpolarized illumination, polarization-blind detector.
    (Es + Ep) / 2: 45 deg (s + p) illumination, 45 deg analyzer -> amplitude and phase.
    """
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs])
    Es = np.array([r['s_in'][0] for r in recs])
    Ep = np.array([r['p_in'][1] for r in recs])
    tot = np.sqrt((np.abs(Es)**2 + np.abs(Ep)**2)/2)
    e45 = (Es + Ep)/2
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True)
    for a, y, title, ylab, c in ((ax[0], tot, 'Total |E| (Es and Ep combined)', 'amplitude (arb.)', 'C0'),
                                 (ax[1], np.abs(e45), '(Es + Ep) / 2 amplitude', 'amplitude (arb.)', 'C0'),
                                 (ax[2], np.unwrap(np.angle(e45)), '(Es + Ep) / 2 phase', 'phase (rad)', 'C1')):
        a.plot(x, y, 'o-', ms=4, color=c)
        a.set_title(title)
        a.set_ylabel(ylab)
        a.set_xlabel('interface position x (nm)   oil  <  0  <  water')
        a.axvline(0, color='0.6', lw=0.8)
        a.grid(alpha=0.3)
    fig.suptitle(f'2D line scan, gap {gap:g} nm')
    fig.tight_layout()
    os.makedirs(FIGS, exist_ok=True)
    out = os.path.join(FIGS, f'{stage}_g{gap:g}_combined.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


def plot_complex(stage, gap=5):
    """
    Amplitude and phase as one signal.  Top: complex contrast |E(x) - E_ref| / |E_ref| with E_ref the
    value at the largest x (water side); it counts amplitude and phase changes together.
    Bottom: the complex signal itself (Im vs Re), points coloured by x.
    """
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs])
    Es = np.array([r['s_in'][0] for r in recs])
    Ep = np.array([r['p_in'][1] for r in recs])
    quantities = [('Backscattered Ep, p polarized', Ep),
                  ('Backscattered Es, s polarized', Es),
                  ('(Es + Ep) / 2', (Es + Ep)/2),
                  (f'Ey integrated from SiN to tip ({gap:g} nm), p polarized',
                   np.array([r['gap_integral'][1, 1] for r in recs]))]
    fig, ax = plt.subplots(2, 4, figsize=(19, 8.5))
    for j, (title, v) in enumerate(quantities):
        ref = v[np.argmax(x)]
        a = ax[0, j]
        a.plot(x, np.abs(v - ref)/np.abs(ref), 'o-', ms=4)
        a.set_title(title, fontsize=10)
        a.set_xlabel('interface position x (nm)   oil  <  0  <  water')
        a.set_ylabel(f'|E - E(x = {x.max():.0f})| / |E(x = {x.max():.0f})|')
        a.axvline(0, color='0.6', lw=0.8)
        a.grid(alpha=0.3)
        b = ax[1, j]
        b.plot(v.real, v.imag, '-', color='0.7', lw=0.8, zorder=1)
        sc = b.scatter(v.real, v.imag, c=x, cmap='coolwarm_r', s=22, zorder=2)
        b.set_xlabel('Re E')
        b.set_ylabel('Im E')
        b.set_aspect('equal', adjustable='datalim')
        b.grid(alpha=0.3)
        fig.colorbar(sc, ax=b, label='x (nm)', shrink=0.8)
    fig.suptitle(f'2D line scan, gap {gap:g} nm: amplitude and phase combined')
    fig.tight_layout()
    os.makedirs(FIGS, exist_ok=True)
    out = os.path.join(FIGS, f'{stage}_g{gap:g}_complex.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__' and (len(sys.argv) < 2 or sys.argv[1] != 'ep_sub'):
    what = sys.argv[1] if len(sys.argv) > 1 else 'scan_h5'
    plot_scan(what)
    plot_combined(what)
    plot_complex(what)


def plot_ep_subtracted(stage='scan_h5', gap=5, n_fit=5, model='quadratic'):
    """
    Ep complex contrast (top-left panel of *_complex.png) minus a fit to its last n_fit points.
    model 'quadratic': c2 x^2 + c1 x + c0;  'inverse': a / x + b (undefined at x = 0, that point is dropped).
    """
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs])
    Ep = np.array([r['p_in'][1] for r in recs])
    ref = Ep[np.argmax(x)]
    c = np.abs(Ep - ref)/np.abs(ref)
    if model == 'quadratic':
        coef = np.polyfit(x[-n_fit:], c[-n_fit:], 2)
        fit = np.polyval(coef, x)
        label = f'quadratic fit to last {n_fit} points'
    else:
        keep = x != 0
        x, c = x[keep], c[keep]
        A = np.vstack([1/x[-n_fit:], np.ones(n_fit)]).T
        coef = np.linalg.lstsq(A, c[-n_fit:], rcond=None)[0]
        fit = coef[0]/x + coef[1]
        label = f'a/x + b fit to last {n_fit} points'
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(x, c, 'o-', ms=4, label='data')
    ax[0].plot(x, fit, '--', color='k', lw=1, label=label)
    ax[0].plot(x[-n_fit:], c[-n_fit:], 'o', ms=7, mfc='none', color='k')
    ax[0].set_title('Backscattered Ep, p polarized')
    ax[0].legend()
    ax[1].plot(x, c - fit, 'o-', ms=4)
    ax[1].set_title('Backscattered Ep, p polarized, minus fit')
    for a in ax:
        a.set_xlabel('interface position x (nm)   oil  <  0  <  water')
        a.set_ylabel(f'|E - E(x = {x.max():.0f})| / |E(x = {x.max():.0f})|')
        a.axvline(0, color='0.6', lw=0.8)
        a.grid(alpha=0.3)
    fig.suptitle(f'2D line scan, gap {gap:g} nm')
    fig.tight_layout()
    out = os.path.join(FIGS, f'{stage}_g{gap:g}_Ep_minus_{model}.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    print(model, 'fit coefficients:', coef)
    for xi, r in zip(x, c - fit):
        print(f'{xi:+6.0f} {r:+.5f}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'ep_sub':
    plot_ep_subtracted(model=sys.argv[2] if len(sys.argv) > 2 else 'quadratic')
