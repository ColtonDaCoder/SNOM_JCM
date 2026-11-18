"""
Depth sensitivity maps from the depthmap_<wvl> stages (tip over water, 5 nm SiN, field exported inside the
water at 15 tip heights).

Reciprocity: a small permittivity change d_eps at r changes the backscattered (p in, p out) far field by
    dE  ~  d_eps  E(r, h) . E(r, h)            (E: total field with the tip at height h, p incidence)
Demodulating E.E over the tapping cycle (same spline + Fourier coefficient as the far-field S_n) gives the
sensitivity density w_n(r) of harmonic n.  Its in-phase part
    p_n(r) = Re( w_n(r) exp(-i arg W_n) ),   W_n = integral of w_n over the map
adds up to the total; contours enclose the smallest region holding 50 / 90 % of the total.

    python depthmap.py           # figures/depthmap_<wvl>.png, depthmap_profiles.png, depthmap_edge_check.png
"""
import os
import glob
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = os.path.join(HERE, 'results', 'fields')
FIGS = os.path.join(HERE, 'figures')
HARM = (1, 2, 3, 4)
WVLS = (('6p1um', 'H–O–H bend, 1639 cm$^{-1}$'), ('2p95um', 'O–H stretch, 3390 cm$^{-1}$'))
T_SIN = 5.0


def demod_cycle(gaps, F, n_t=2000, harmonics=HARM):
    """S_n of F(gap) along the last axis-0 (gaps first), same tapping as plot_2d.demodulate."""
    from scipy.interpolate import CubicSpline
    t = np.linspace(0, 1, n_t, endpoint=False)
    z = 1 + 50*(1 + np.cos(2*np.pi*t))
    Fz = CubicSpline(gaps, F.real, axis=0)(z) + 1j*CubicSpline(gaps, F.imag, axis=0)(z)
    return {n: np.tensordot(np.exp(-2j*np.pi*n*t), Fz, axes=(0, 0))/n_t for n in harmonics}


def cell_widths(v):
    """Trapezoid integration weights of a sorted 1D grid."""
    w = np.zeros_like(v)
    w[1:] += 0.5*np.diff(v)
    w[:-1] += 0.5*np.diff(v)
    return w


def load(tag):
    files = glob.glob(os.path.join(FIELDS, f'depthmap_{tag}_x+5000_g*.npz'))
    gaps = sorted(float(re.search(r'_g([\d.]+)\.npz$', f).group(1)) for f in files)
    EE, X, Y = [], None, None
    for g in gaps:
        z = np.load(os.path.join(FIELDS, f'depthmap_{tag}_x+5000_g{g:g}.npz'))
        E = z['E'][1].astype(complex)                     # p incidence
        EE.append(np.sum(E*E, axis=-1))                   # E.E (not |E|^2)
        X, Y = z['X'], z['Y']
    x, depth = X[:, 0], -Y[0, :] - T_SIN                  # depth below the window (nm)
    return np.array(gaps), x, depth, np.array(EE)


def maps(tag):
    gaps, x, depth, EE = load(tag)
    w = demod_cycle(gaps, EE)
    dA = np.outer(cell_widths(x), cell_widths(depth[::-1])[::-1])
    out = {}
    for n, wn in w.items():
        W = np.sum(wn*dA)
        p = np.real(wn*np.exp(-1j*np.angle(W)))
        out[n] = dict(w=wn, p=p, W=W, dA=dA)
    return gaps, x, depth, out


def hdr_levels(p, dA, fracs):
    """Density levels whose super-level sets hold the given fractions of sum(p dA) (p > 0 part)."""
    q = np.clip(p, 0, None)
    order = np.argsort(q.ravel())[::-1]
    cum = np.cumsum((q*dA).ravel()[order])
    cum /= np.sum(p*dA)
    return [q.ravel()[order][min(np.searchsorted(cum, f), len(cum) - 1)] for f in fracs]


def diagnostics():
    for tag, _ in WVLS:
        gaps, x, depth, M = maps(tag)
        print(f'== {tag}: gaps {gaps.tolist()}')
        for n in HARM:
            m = M[n]
            p, dA = m['p'], m['dA']
            tot = np.sum(p*dA)
            neg = -np.sum(np.clip(p, None, 0)*dA)/np.sum(np.abs(p)*dA)
            inphase = abs(tot)/np.sum(np.abs(m['w'])*dA)
            edge = (np.sum((p*dA)[[0, -1], :]) + np.sum((p*dA)[:, depth.argmax()]))/tot
            # depth holding 50 / 90 % (cumulative from the surface, in-phase part)
            prof = np.sum(p*dA, axis=0)
            o = np.argsort(depth)
            cum = np.cumsum(prof[o])/tot
            d50, d90 = np.interp(0.5, cum, depth[o]), np.interp(0.9, cum, depth[o])
            print(f'  S{n}: in-phase fraction {inphase:.2f}, negative {neg:.3f}, outer-row share {edge:+.3f}, '
                  f'50% depth {d50:.1f} nm, 90% depth {d90:.1f} nm')


def fine_density(x, depth, p, W, step=2.0):
    """In-phase density normalised to integral 1 (per nm^2), linearly interpolated to a regular grid."""
    from scipy.interpolate import RegularGridInterpolator
    o = np.argsort(depth)
    q = p[:, o]/np.real(W*np.exp(-1j*np.angle(W)))
    xf = np.arange(x.min(), x.max() + 1e-9, step)
    df = np.arange(0.0, depth.max() + 1e-9, step/2)
    d_in = np.r_[0.0, depth[o]]
    q_in = np.c_[q[:, :1], q]                              # density at the window bottom = first row
    f = RegularGridInterpolator((x, d_in), q_in)
    XX, DD = np.meshgrid(xf, df, indexing='ij')
    return xf, df, f((XX, DD))


def plot_maps():
    from matplotlib.colors import LogNorm
    fr = (0.5, 0.9)
    with plt.rc_context({'font.size': 15, 'axes.titlesize': 17, 'axes.labelsize': 16}):
        fig, axs = plt.subplots(2, 4, figsize=(21, 6.3), sharex=True, sharey=True,
                                gridspec_kw=dict(hspace=0.08, wspace=0.06))
        norm = LogNorm(vmin=1e-7, vmax=1e-3)
        for i, (tag, label) in enumerate(WVLS):
            gaps, x, depth, M = maps(tag)
            for j, n in enumerate(HARM):
                ax = axs[i, j]
                xf, df, q = fine_density(x, depth, M[n]['p'], M[n]['W'])
                dA = np.outer(cell_widths(xf), cell_widths(df))
                lv = hdr_levels(q, dA, fr)
                im = ax.pcolormesh(xf, df, np.clip(q, 1e-7, None).T, norm=norm, cmap='inferno', shading='gouraud',
                                   rasterized=True)
                cs = ax.contour(xf, df, q.T, levels=sorted(lv), colors='w', linewidths=[1.6, 2.2][::-1])
                ax.clabel(cs, fmt={min(lv): '90%', max(lv): '50%'}, fontsize=13, inline_spacing=4)
                ax.set_ylim(depth.max(), 0)
                ax.set_aspect('equal')
                if i == 0:
                    ax.set_title(f'S{n}')
                if i == 1:
                    ax.set_xlabel('x (nm)')
            axs[i, 0].set_ylabel(label.split(',')[0] + '\nDepth (nm)')
        cb = fig.colorbar(im, ax=list(axs.ravel()), shrink=0.85, pad=0.012, fraction=0.025)
        cb.set_label('Signal density (nm$^{-2}$)')
        os.makedirs(FIGS, exist_ok=True)
        out = os.path.join(FIGS, 'depthmap_maps.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
    print('wrote', out)


def plot_profiles():
    """Fraction of the signal coming from shallower than a depth d, S1..S4, both wavelengths."""
    with plt.rc_context({'font.size': 15, 'axes.titlesize': 17, 'axes.labelsize': 16}):
        fig, axs = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
        for ax, (tag, label) in zip(axs, WVLS):
            gaps, x, depth, M = maps(tag)
            o = np.argsort(depth)
            for n in HARM:
                m = M[n]
                prof = np.sum(m['p']*m['dA'], axis=0)[o]
                cum = np.r_[0.0, np.cumsum(prof)/np.sum(prof)]
                ax.plot(np.r_[0.0, depth[o]], 100*cum, lw=2.5, label=f'S{n}')
            for f in (50, 90):
                ax.axhline(f, color='0.6', lw=1, ls='--')
            ax.set_xlim(0, depth.max())
            ax.set_ylim(0, 105)
            ax.set_title(label)
            ax.set_xlabel('Depth below window (nm)')
        axs[0].set_ylabel('Signal from above this depth (%)')
        axs[1].legend(loc='lower right')
        out = os.path.join(FIGS, 'depthmap_profiles.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
    print('wrote', out)


def plot_edge_check():
    """Edge predicted from the maps (water for x < x_interface) vs the demodulated line scans (real part)."""
    import sys
    sys.argv = sys.argv[:1]
    import plot_2d as p2
    with plt.rc_context({'font.size': 15, 'axes.titlesize': 17, 'axes.labelsize': 16}):
        fig, axs = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
        for ax, (tag, label), setname in zip(axs, WVLS, ('sin5', 'wl2p95')):
            gaps, x, depth, M = maps(tag)
            rows = p2.demod_rows(setname)
            xs = np.array([r[0] for r in rows])
            for k, n in enumerate((2, 3)):
                m = M[n]
                cum = np.cumsum(np.sum(m['w']*m['dA'], axis=1))
                ax.plot(x, (cum/cum[-1]).real, color=f'C{k}', lw=2.5, label=f'S{n} predicted from map')
                S = np.array([r[1][n] for r in rows])
                s0, s1 = S[xs == -600][0], S[xs == 600][0]          # same +-600 nm span as the map
                ax.plot(xs, ((S - s0)/(s1 - s0)).real, 'o-', color=f'C{k}', ms=5, lw=1, alpha=0.7,
                        label=f'S{n} line scan')
            ax.set_xlim(-600, 600)
            ax.set_title(label)
            ax.set_xlabel('Interface position (nm)')
        axs[0].set_ylabel('Normalised signal change')
        axs[1].legend(loc='lower right', fontsize=12)
        out = os.path.join(FIGS, 'depthmap_edge_check.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
    print('wrote', out)


if __name__ == '__main__':
    diagnostics()
    plot_maps()
    plot_profiles()
    plot_edge_check()
