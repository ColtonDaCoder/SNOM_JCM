"""
Re-plot every old nanoparticle-size sweep (pkl with keys field / radius) found in the repository:
backscattered field amplitude and phase vs particle radius, grouped by project folder.
field = results[1]['ElectricFieldStrength'][0][0][0] in the old scan.py (first far-field direction, x component).

    python replot_np.py      # -> figures/np_size_sweeps.png
"""
import os
import glob
import pickle as pk
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    groups = {}
    for f in sorted(glob.glob(os.path.join(ROOT, '**', '*.pkl'), recursive=True)):
        try:
            d = pk.load(open(f, 'rb'))
        except Exception:
            continue
        if isinstance(d, dict) and {'field', 'radius'} <= set(d):
            rel = os.path.relpath(f, ROOT)
            groups.setdefault(os.path.dirname(rel), []).append((os.path.basename(rel)[:-4].replace('field_vs_NP_', ''), d))
    with plt.rc_context({'font.size': 15, 'axes.titlesize': 16, 'axes.labelsize': 16, 'legend.fontsize': 13}):
        fig, axs = plt.subplots(2, len(groups), figsize=(6*len(groups), 9), sharex=True, squeeze=False)
        for col, (folder, sets) in enumerate(groups.items()):
            for i, (name, d) in enumerate(sets):
                r = np.asarray(d['radius'], float)
                E = np.array([complex(np.ravel(x)[0]) for x in d['field']])
                o = np.argsort(r)
                axs[0, col].plot(r[o], np.abs(E[o]), 'o-', ms=3, lw=1.8, color=f'C{i}', label=name)
                axs[1, col].plot(r[o], np.unwrap(np.angle(E[o])), 'o-', ms=3, lw=1.8, color=f'C{i}', label=name)
                print(f'{folder}/{name}: radius {r.min():g}-{r.max():g} nm ({len(r)} pts)')
            axs[0, col].set_title(folder.replace(os.sep, '/'))
            axs[0, col].set_ylabel('|E| backscattered (arb.)')
            axs[1, col].set_ylabel('phase (rad)')
            axs[1, col].set_xlabel('Nanoparticle radius (nm)')
            axs[0, col].legend()
            for a in axs[:, col]:
                a.grid(alpha=0.3)
        fig.suptitle('Old cylindrical runs: signal vs nanoparticle radius')
        fig.tight_layout()
        out = os.path.join(HERE, 'figures', 'np_size_sweeps.png')
        fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__':
    main()


def plot_onlynp():
    """Silicon Nitride NP/OnlyNP: change of the backscattered field with particle radius, Au / Pt / dielectric."""
    sets = (('Au', 'Au', '#c99700'), ('Pt', 'Pt', '#5a6b7b'), ('Dielectric', 'Dielectric', '#2ca02c'))
    with plt.rc_context({'font.size': 18, 'axes.labelsize': 19, 'xtick.labelsize': 16, 'ytick.labelsize': 16,
                         'legend.fontsize': 16}):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        for key, lab, c in sets:
            d = pk.load(open(os.path.join(ROOT, 'Silicon Nitride NP', 'OnlyNP', f'field_vs_NP_{key}.pkl'), 'rb'))
            r = np.asarray(d['radius'], float)
            E = np.array([complex(np.ravel(x)[0]) for x in d['field']])
            o = np.argsort(r)
            r, E = r[o], E[o]
            ref = E[:5].mean()                                       # smallest particles (10-14 nm) as baseline
            ax[0].plot(r, (np.abs(E)/abs(ref) - 1)*100, 'o-', ms=4, lw=2.5, color=c, label=lab)
            ax[1].plot(r, (np.unwrap(np.angle(E)) - np.angle(ref))*1e3, 'o-', ms=4, lw=2.5, color=c, label=lab)
        ax[0].set(xlabel='Nanoparticle radius (nm)', ylabel='Signal change (%)', title='Amplitude')
        ax[1].set(xlabel='Nanoparticle radius (nm)', ylabel='Phase change (mrad)', title='Phase')
        for a in ax:
            a.axhline(0, color='0.6', lw=1)
            a.grid(alpha=0.3)
            a.legend()
        fig.tight_layout()
        out = os.path.join(HERE, 'figures', 'np_size_onlyNP.png')
        fig.savefig(out, dpi=150)
    print('wrote', out)


if __name__ == '__main__':
    plot_onlynp()
