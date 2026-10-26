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


def plot_withlayer():
    """Silicon Nitride NP/WithLayer: change of the backscattered field with particle radius, graphene vs SiN layer."""
    sets = (('Graphene', 'graphene layer', '#333333'), ('SN', 'SiN layer', '#1f77b4'))
    with plt.rc_context({'font.size': 18, 'axes.labelsize': 19, 'xtick.labelsize': 16, 'ytick.labelsize': 16,
                         'legend.fontsize': 16}):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        for key, lab, c in sets:
            d = pk.load(open(os.path.join(ROOT, 'Silicon Nitride NP', 'WithLayer', f'field_vs_NP_{key}.pkl'), 'rb'))
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
        out = os.path.join(HERE, 'figures', 'np_size_withLayer.png')
        fig.savefig(out, dpi=150)
    print('wrote', out)


def _withlayer_common():
    """Graphene and SiN WithLayer sweeps on their common radii: r, {key: complex E}."""
    data = {}
    for key in ('Graphene', 'SN'):
        d = pk.load(open(os.path.join(ROOT, 'Silicon Nitride NP', 'WithLayer', f'field_vs_NP_{key}.pkl'), 'rb'))
        data[key] = dict(zip(np.asarray(d['radius'], float), [complex(np.ravel(x)[0]) for x in d['field']]))
    r = np.array(sorted(set(data['Graphene']) & set(data['SN'])))
    return r, {k: np.array([v[x] for x in r]) for k, v in data.items()}


def withlayer_figures(k_sigma=3.0, inst=((0.1, 'amp', '%'), (1.0, 'ph', 'mrad'))):
    """
    1) amplitude / phase change vs radius, common radii only
    2) direct comparison: graphene minus SiN, and the complex change |E - E_ref| / |E_ref| of both
    3) detection limit: smallest radius where the fitted change (a + b r^3) exceeds k_sigma x the simulation
       scatter, and where it exceeds an assumed instrument noise level (inst)
    """
    r, E = _withlayer_common()
    cols = {'Graphene': ('graphene layer', '#333333'), 'SN': ('15 nm SiN layer', '#1f77b4')}
    ch = {}
    for k, e in E.items():
        ref = e[:5].mean()
        ch[k] = {'amp': (np.abs(e)/abs(ref) - 1)*100, 'ph': (np.unwrap(np.angle(e)) - np.angle(ref))*1e3,
                 'cplx': np.abs(e - ref)/abs(ref)*100}
    rc = {'font.size': 18, 'axes.labelsize': 19, 'xtick.labelsize': 16, 'ytick.labelsize': 16, 'legend.fontsize': 15}
    # --- 1) common radii
    with plt.rc_context(rc):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        for k, (lab, c) in cols.items():
            ax[0].plot(r, ch[k]['amp'], 'o-', ms=4, lw=2.5, color=c, label=lab)
            ax[1].plot(r, ch[k]['ph'], 'o-', ms=4, lw=2.5, color=c, label=lab)
        ax[0].set(xlabel='Nanoparticle radius (nm)', ylabel='Signal change (%)', title='Amplitude')
        ax[1].set(xlabel='Nanoparticle radius (nm)', ylabel='Phase change (mrad)', title='Phase')
        for a in ax:
            a.axhline(0, color='0.6', lw=1)
            a.grid(alpha=0.3)
            a.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'figures', 'np_size_withLayer.png'), dpi=150)
        plt.close(fig)
    # --- 2) comparison
    with plt.rc_context(rc):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        ax[0].plot(r, ch['Graphene']['amp'] - ch['SN']['amp'], 'o-', ms=4, lw=2.5, color='C3', label='amplitude (%)')
        ax0b = ax[0].twinx()
        ax0b.plot(r, ch['Graphene']['ph'] - ch['SN']['ph'], 's-', ms=4, lw=2.5, color='C2', label='phase (mrad)')
        ax[0].set(xlabel='Nanoparticle radius (nm)', ylabel='Amplitude change: graphene − SiN (%)',
                  title='Difference between the two layers')
        ax0b.set_ylabel('Phase change: graphene − SiN (mrad)')
        ax[0].axhline(0, color='0.6', lw=1)
        h1, l1 = ax[0].get_legend_handles_labels()
        h2, l2 = ax0b.get_legend_handles_labels()
        ax[0].legend(h1 + h2, l1 + l2, loc='upper center', fontsize=13)
        for k, (lab, c) in cols.items():
            ax[1].plot(r, ch[k]['cplx'], 'o-', ms=4, lw=2.5, color=c, label=lab)
        ax[1].set(xlabel='Nanoparticle radius (nm)', ylabel='|E − E_ref| / |E_ref| (%)',
                  title='Total change (amp. + phase)')
        ax[1].legend()
        for a in ax:
            a.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'figures', 'np_size_withLayer_compare.png'), dpi=150)
        plt.close(fig)
    # --- 3) detection limits
    rows = []
    rr = np.linspace(r.min(), r.max(), 2000)
    with plt.rc_context(rc):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        for j, (q, lab_q, unit) in enumerate((('amp', 'Amplitude', '%'), ('ph', 'Phase', 'mrad'))):
            for k, (lab, c) in cols.items():
                y = ch[k][q]
                A = np.vstack([np.ones_like(r), r**3]).T
                cf = np.linalg.lstsq(A, y, rcond=None)[0]
                sig = np.std(y - A @ cf)
                fit = np.abs(cf[1]*rr**3)                            # change relative to a tiny particle
                lim_sim = rr[np.argmax(fit > k_sigma*sig)] if (fit > k_sigma*sig).any() else np.nan
                lev = dict((n, v) for v, n, _ in inst)[q]
                lim_inst = rr[np.argmax(fit > lev)] if (fit > lev).any() else np.nan
                rows.append((lab, lab_q, sig, lim_sim, lev, unit, lim_inst))
                ax[j].plot(r, np.abs(y - cf[0]), 'o', ms=3.5, color=c, alpha=0.7)
                ax[j].plot(rr, fit, '-', lw=2.5, color=c, label=f'{lab}: r ≥ {lim_sim:.0f} nm ({k_sigma:g}σ sim)')
                ax[j].axhline(k_sigma*sig, color=c, ls=':', lw=1.5)
            ax[j].axhline(lev, color='C3', ls='--', lw=1.8, label=f'assumed instrument noise {lev:g} {unit}')
            ax[j].set_yscale('log')
            ax[j].set_ylim(1e-3 if q == 'amp' else 1e-2, None)
            ax[j].set(xlabel='Nanoparticle radius (nm)', ylabel=f'|{lab_q.lower()} change| ({unit})',
                      title=f'{lab_q}: detection limit')
            ax[j].grid(alpha=0.3, which='both')
            ax[j].legend(fontsize=12, loc='lower right')
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, 'figures', 'np_size_withLayer_detection.png'), dpi=150)
        plt.close(fig)
    print(f'common radii {r.min():g}-{r.max():g} nm ({len(r)})')
    for lab, q, sig, ls, lev, unit, li in rows:
        print(f'{lab:16s} {q:9s} sim scatter {sig:.3g} {unit}; {k_sigma:g}σ limit r = {ls:.0f} nm; '
              f'limit at {lev:g} {unit} noise r = {li:.0f} nm')


def withlayer_raw():
    """Raw |E| and phase vs radius (common radii) for the graphene and 15 nm SiN layer runs."""
    r, E = _withlayer_common()
    cols = {'Graphene': ('graphene layer', '#333333'), 'SN': ('15 nm SiN layer', '#1f77b4')}
    with plt.rc_context({'font.size': 18, 'axes.labelsize': 19, 'xtick.labelsize': 16, 'ytick.labelsize': 16,
                         'legend.fontsize': 16}):
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        for k, (lab, c) in cols.items():
            ax[0].plot(r, np.abs(E[k])*1e3, 'o-', ms=4, lw=2.5, color=c, label=lab)
            ax[1].plot(r, np.unwrap(np.angle(E[k])), 'o-', ms=4, lw=2.5, color=c, label=lab)
        ax[0].set(xlabel='Nanoparticle radius (nm)', ylabel='|E| (×10⁻³, arb.)', title='Amplitude')
        ax[1].set(xlabel='Nanoparticle radius (nm)', ylabel='Phase (rad)', title='Phase')
        for a in ax:
            a.grid(alpha=0.3)
            a.legend()
        fig.tight_layout()
        out = os.path.join(HERE, 'figures', 'np_size_withLayer_raw.png')
        fig.savefig(out, dpi=150)
    print('wrote', out)
