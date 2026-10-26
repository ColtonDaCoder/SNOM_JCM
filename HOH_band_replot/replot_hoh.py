"""
Re-plot every old wavelength sweep that crosses the water H-O-H bend (~6.1 um, 1640 cm^-1).

Finds all *.pkl in the repository (outside Interface_LineScan_*) with keys field / height / wvl whose
wavelengths span 6.0 - 6.2 um, drops byte-identical copies, and for each wavelength with a complete
height set demodulates the approach curve: tip height h(t) = h_min + (h_max - h_min)/2 (1 + cos wt) over the
dataset's own height range (as the old demod scripts did), cubic spline, S_n = <E e^{-i n w t}>.
field: complex scalar, or [Ep, Es] (Ep used, as in SNx_Water_Simple/demodulation.py), or a 3-vector (x used).

    python replot_hoh.py      # -> figures/<folder>__<file>.png (one per dataset) + figures/overview_*.png
"""
import os
import glob
import hashlib
import pickle as pk
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGS = os.path.join(HERE, 'figures')
WATER = os.path.join(ROOT, 'Interface_LineScan_2D', 'optical_data', 'water_HaleQuerry.csv')


def scalar(f):
    a = np.asarray(f)
    return complex(a) if a.ndim == 0 else complex(a.ravel()[0])


def load_sets():
    seen, sets = {}, []
    for f in sorted(glob.glob(os.path.join(ROOT, '**', '*.pkl'), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith('Interface_LineScan') or rel.startswith('HOH_band_replot'):
            continue
        try:
            d = pk.load(open(f, 'rb'))
        except Exception:
            continue
        if not (isinstance(d, dict) and {'field', 'height', 'wvl'} <= set(d)):
            continue
        w = np.round(np.asarray(d['wvl'], float), 4)
        if not (w.min() <= 6.0 and w.max() >= 6.2):
            continue
        h = hashlib.md5(open(f, 'rb').read()).hexdigest()
        if h in seen:
            seen[h].append(rel)
            continue
        seen[h] = [rel]
        sets.append((rel, d, seen[h]))
    return sets


def demod(d):
    """{wvl: (S2, S3)} for the wavelengths that have the full height set."""
    w = np.round(np.asarray(d['wvl'], float), 4)
    h = np.asarray(d['height'], float)
    E = np.array([scalar(f) for f in d['field']])
    hmin, hmax = h.min(), h.max()
    n_full = max(len(np.unique(h[w == x])) for x in np.unique(w))
    t = np.linspace(0, 1, 2000, endpoint=False)
    z = hmin + (hmax - hmin)/2*(1 + np.cos(2*np.pi*t))
    out = {}
    for x in np.unique(w):
        m = w == x
        hs, idx = np.unique(h[m], return_index=True)
        if len(hs) < n_full or len(hs) < 5:
            continue
        e = E[m][idx]
        ez = CubicSpline(hs, e.real)(z) + 1j*CubicSpline(hs, e.imag)(z)
        out[x] = tuple(np.mean(ez*np.exp(-2j*np.pi*n*t)) for n in (2, 3))
    return out, (hmin, hmax), n_full


def water_k():
    d = np.array([l.split(',') for l in open(WATER) if l[0].isdigit()], float)
    m = (d[:, 0] > 5.3) & (d[:, 0] < 6.7)
    return 1e4/d[m, 0], d[m, 2]


def plot_one(ax_a, ax_p, res, label=None, colors=('C0', 'C3')):
    wl = np.array(sorted(res))
    wn = 1e4/wl
    for k, (n, c) in enumerate(zip((2, 3), colors)):
        S = np.array([res[x][k] for x in wl])
        ax_a.plot(wn, np.abs(S)/np.abs(S).max(), 'o-', ms=3.5, lw=1.8, color=c, label=f'S{n}')
        ax_p.plot(wn, np.unwrap(np.angle(S)) - np.angle(S[0]), 'o-', ms=3.5, lw=1.8, color=c, label=f'S{n}')


def decorate(ax_a, ax_p, kwn, kk):
    for a in (ax_a, ax_p):
        a.axvline(1639, color='0.5', ls='--', lw=0.8)
        a.grid(alpha=0.3)
        a.set_xlim(1840, 1530)
    t = ax_a.twinx()
    t.fill_between(kwn, 0, kk, color='C0', alpha=0.10, lw=0)
    t.set_ylim(0, kk.max()*1.1)
    t.set_yticks([])


def main():
    os.makedirs(FIGS, exist_ok=True)
    kwn, kk = water_k()
    sets = load_sets()
    rows = []
    for rel, d, copies in sets:
        res, (hmin, hmax), n_h = demod(d)
        if len(res) < 6:
            print(f'skip {rel}: only {len(res)} complete wavelengths')
            continue
        rows.append((rel, res, hmin, hmax, n_h, copies))
        fig, (a, p) = plt.subplots(2, 1, figsize=(8, 7.5), sharex=True)
        plot_one(a, p, res)
        decorate(a, p, kwn, kk)
        a.set_ylabel('|Sn| / max')
        p.set_ylabel('phase − phase at 1818 cm⁻¹ (rad)')
        p.set_xlabel('Wavenumber (cm⁻¹)')
        a.legend(loc='lower left')
        a.set_title(f'{rel}\nheights {hmin:g}…{hmax:g} ({n_h}), {len(res)} wavelengths'
                    + (f'\n(identical copies: {", ".join(c for c in copies if c != rel)})' if len(copies) > 1 else ''),
                    fontsize=9)
        fig.tight_layout()
        name = rel.replace(os.sep, '__').replace(' ', '_').replace('.pkl', '.png')
        fig.savefig(os.path.join(FIGS, name), dpi=120)
        plt.close(fig)
        print(f'{rel:75s} h {hmin:g}..{hmax:g} ({n_h})  {len(res)} wvl {min(res):.2f}-{max(res):.2f} um')
    # overview: every dataset, S2 amplitude and phase
    n = len(rows)
    cols = 6
    r = int(np.ceil(n/cols))
    for kind in ('amp', 'phase'):
        fig, axs = plt.subplots(r, cols, figsize=(3.4*cols, 2.6*r), sharex=True, squeeze=False)
        for ax, (rel, res, hmin, hmax, n_h, copies) in zip(axs.flat, rows):
            wl = np.array(sorted(res))
            for k, (nn, c) in enumerate(zip((2, 3), ('C0', 'C3'))):
                S = np.array([res[x][k] for x in wl])
                y = np.abs(S)/np.abs(S).max() if kind == 'amp' else np.unwrap(np.angle(S)) - np.angle(S[0])
                ax.plot(1e4/wl, y, '-', lw=1.5, color=c, label=f'S{nn}')
            ax.axvline(1639, color='0.5', ls='--', lw=0.7)
            ax.set_xlim(1840, 1530)
            ax.set_title(rel.replace(os.sep, '/'), fontsize=6.5)
            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.3)
        for ax in axs.flat[n:]:
            ax.axis('off')
        axs.flat[0].legend(fontsize=7)
        fig.suptitle(('|S2|, |S3| (each / its max)' if kind == 'amp' else 'S2, S3 phase (rad, relative to 1818 cm⁻¹)')
                     + ' vs wavenumber across the H–O–H bend (dashed: 1639 cm⁻¹)')
        fig.tight_layout()
        fig.savefig(os.path.join(FIGS, f'overview_{kind}.png'), dpi=110)
        plt.close(fig)
    print(len(rows), 'datasets plotted')


if __name__ == '__main__':
    main()


def highlight(files=('SNx_Water_Simple/results_example.pkl', 'SNx_Water_Simple/dev_v3_NA.pkl',
                     'SNx_Water_Simple/dev_v11_adsorbed.pkl', 'SNx_Water_Simple/dev_v12_strong_adsorbed.pkl',
                     'SNx_Water_Simple/dev_v13_base_ref.pkl')):
    """The cleanest sweeps (2D SiN / water, NA-filtered backscatter Ep): S2, S3 vs wavenumber + water k."""
    d_w = np.array([l.split(',') for l in open(WATER) if l[0].isdigit()], float)
    m = (d_w[:, 0] > 5.4) & (d_w[:, 0] < 6.6)
    with plt.rc_context({'font.size': 15, 'axes.labelsize': 16, 'axes.titlesize': 16, 'legend.fontsize': 11}):
        fig, axs = plt.subplots(3, 2, figsize=(14, 11), sharex=True, gridspec_kw={'height_ratios': [1, 2, 2]})
        for col in range(2):
            axs[0, col].plot(1e4/d_w[m, 0], d_w[m, 2], '-', color='k', lw=2)
            axs[0, col].set_ylabel('k (water)')
            axs[0, col].set_title(f'S{col + 2}')
        for i, f in enumerate(files):
            d = pk.load(open(os.path.join(ROOT, f), 'rb'))
            res, _, _ = demod(d)
            wl = np.array(sorted(res))
            for col in range(2):
                S = np.array([res[x][col] for x in wl])
                lab = os.path.basename(f).replace('.pkl', '')
                axs[1, col].plot(1e4/wl, np.abs(S)/np.abs(S[0]), 'o-', ms=4, lw=2, color=f'C{i}', label=lab)
                axs[2, col].plot(1e4/wl, np.unwrap(np.angle(S)) - np.angle(S[0]), 'o-', ms=4, lw=2, color=f'C{i}')
        for a in axs.flat:
            a.axvline(1639, color='0.5', ls='--', lw=1)
            a.grid(alpha=0.3)
            a.set_xlim(1840, 1530)
        for col in range(2):
            axs[1, col].set_ylabel(f'|S{col + 2}| / value at 1818 cm⁻¹')
            axs[2, col].set_ylabel(f'S{col + 2} phase (rad, rel. 1818 cm⁻¹)')
            axs[2, col].set_xlabel('Wavenumber (cm⁻¹)')
        axs[1, 0].legend(loc='lower left')
        fig.suptitle('Old 2D SiN / water runs (SNx_Water_Simple): demodulated signal across the H–O–H bend')
        fig.tight_layout()
        out = os.path.join(FIGS, 'hoh_sweep_highlight.png')
        fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__':
    highlight()
