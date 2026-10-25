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
if '--set' in sys.argv:                      # e.g.  python plot_2d.py demod --set sin20
    _i = sys.argv.index('--set')
    _SET_ARG = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
else:
    _SET_ARG = None
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


if __name__ == '__main__' and (len(sys.argv) < 2 or sys.argv[1] not in ('ep_sub', 'ep_step', 'ep_lines', 'approach', 'demod', 's2s3', 'nearfield', 'compare', 's2s3_prov', 's2s3_both', 's2s3_wl', 's2s3_wl3', 'explain', 'tapview', 'tapview_inphase')):
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


def plot_ep_step_fit(stage='scan_h5', gap=5):
    """
    Complex Ep fitted over all points with  B(x) + D * (1 - tanh((x - x0) / w)) / 2,
    B(x) = b0 + b1 x + b2 x^2 a smooth complex background (b*, D complex; x0, w real).
    Plotted: the data minus B(x) only (the step model is not subtracted), as complex contrast
    relative to the water end in units of the fitted step |D|, and the complex plane.
    """
    from scipy.optimize import least_squares
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs], float)
    E = np.array([r['p_in'][1] for r in recs])
    u = x/1000

    def design(x0, w):
        return np.vstack([np.ones_like(u), u, u**2, 0.5*(1 - np.tanh((x - x0)/w))]).T

    def res(pr):
        M = design(*pr)
        r = M @ np.linalg.lstsq(M, E, rcond=None)[0] - E
        return np.r_[r.real, r.imag]
    best = min((least_squares(res, [x0, w]) for x0 in (-300, -100, 0, 100) for w in (50, 150, 400)),
               key=lambda s: s.cost)
    x0, w = best.x
    M = design(x0, w)
    c = np.linalg.lstsq(M, E, rcond=None)[0]
    B = M[:, :3] @ c[:3]
    S = E - B                                   # data minus background
    ref = S[np.argmax(x)]
    con = np.abs(S - ref)/np.abs(c[3])           # in units of the fitted step |D|
    rms = np.sqrt(np.mean(np.abs(M @ c - E)**2))/np.mean(np.abs(E))

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(x, con, 'o-', ms=4)
    ax[0].set_title('Backscattered Ep, p polarized, minus background')
    ax[0].set_xlabel('interface position x (nm)   oil  <  0  <  water')
    ax[0].set_ylabel(f'|S - S(x = {x.max():.0f})| / |step|')
    ax[0].axvline(0, color='0.6', lw=0.8)
    ax[0].grid(alpha=0.3)
    ax[1].plot(S.real, S.imag, '-', color='0.7', lw=0.8, zorder=1)
    sc = ax[1].scatter(S.real, S.imag, c=x, cmap='coolwarm_r', s=22, zorder=2)
    ax[1].set_title('Backscattered Ep minus background, complex plane')
    ax[1].set_xlabel('Re')
    ax[1].set_ylabel('Im')
    ax[1].set_aspect('equal', adjustable='datalim')
    ax[1].grid(alpha=0.3)
    fig.colorbar(sc, ax=ax[1], label='x (nm)', shrink=0.8)
    fig.suptitle(f'2D line scan, gap {gap:g} nm')
    fig.tight_layout()
    out = os.path.join(FIGS, f'{stage}_g{gap:g}_Ep_minus_background.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    print(f'x0 = {x0:.1f} nm, w = {w:.1f} nm (10-90 % width {2*w*np.arctanh(0.8):.0f} nm), '
          f'step |D|/|E| = {abs(c[3])/np.mean(np.abs(E)):.3f}, rms residual / |E| = {rms:.2e}')
    for xi, ci in zip(x, con):
        print(f'{xi:+6.0f} {ci:.4f}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'ep_step':
    plot_ep_step_fit()


def plot_ep_two_lines(stage='scan_h5', gap=5, n=6):
    """
    Ep complex contrast (top-left panel of *_complex.png): straight lines fitted to the first n and
    the last n points; baseline = left line up to where it meets the right line, right line after.
    Plotted: data with both lines / baseline, and data minus baseline.
    """
    recs = [r for r in load(stage) if r['gap'] == gap]
    x = np.array([r['x_interface'] for r in recs], float)
    Ep = np.array([r['p_in'][1] for r in recs])
    ref = Ep[np.argmax(x)]
    c = np.abs(Ep - ref)/np.abs(ref)
    L = np.polyfit(x[:n], c[:n], 1)
    R = np.polyfit(x[-n:], c[-n:], 1)
    x_int = (R[1] - L[1])/(L[0] - R[0])
    base = np.where(x <= x_int, np.polyval(L, x), np.polyval(R, x))
    xx = np.linspace(x.min(), x.max(), 400)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(x, c, 'o-', ms=4, label='data')
    ax[0].plot(xx, np.polyval(L, xx), ':', color='C3', lw=1, label=f'line through first {n} points')
    ax[0].plot(xx, np.polyval(R, xx), ':', color='C2', lw=1, label=f'line through last {n} points')
    ax[0].plot(xx, np.where(xx <= x_int, np.polyval(L, xx), np.polyval(R, xx)), '--', color='k', lw=1.2, label='baseline')
    ax[0].axvline(x_int, color='k', lw=0.6, ls=':')
    ax[0].set_title('Backscattered Ep, p polarized')
    ax[0].legend(fontsize=8)
    ax[1].plot(x, c - base, 'o-', ms=4)
    ax[1].axvline(x_int, color='k', lw=0.6, ls=':')
    ax[1].set_title('Backscattered Ep, p polarized, minus baseline')
    for a in ax:
        a.set_xlabel('interface position x (nm)   oil  <  0  <  water')
        a.set_ylabel(f'|E - E(x = {x.max():.0f})| / |E(x = {x.max():.0f})|')
        a.axvline(0, color='0.6', lw=0.8)
        a.grid(alpha=0.3)
    fig.suptitle(f'2D line scan, gap {gap:g} nm')
    fig.tight_layout()
    out = os.path.join(FIGS, f'{stage}_g{gap:g}_Ep_minus_two_lines.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    print(f'left line {L}, right line {R}, intersection at x = {x_int:.1f} nm')
    for xi, v in zip(x, c - base):
        print(f'{xi:+6.0f} {v:+.5f}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'ep_lines':
    plot_ep_two_lines()


LOG_RE = (r'x=([+-]?\d+) nm gap=([\d.]+) nm\s+\|Ep\|\(p_in\)=([\d.eE+-]+) arg=([+-][\d.]+)\s+'
          r'\|gap int Ey\|\(p_in\)=([\d.eE+-]+) arg=([+-][\d.]+)')


SETS = {'sin5': (('scan_demod', 'scan_h5', 'scan_demod_fill'), '', '5 nm SiN, 6.1 um'),
        'sin20': (('scan_demod_sin20',), '_sin20', '20 nm SiN, 6.1 um'),
        'wl5p5': (('scan_demod_5p5um',), '_5p5um', '5 nm SiN, 5.5 um'),
        'wl2p95': (('scan_demod_2p95um',), '_2p95um', '5 nm SiN, 2.95 um')}
SET = _SET_ARG or 'sin5'


def approach_points(stages=None, logfile=None):
    """{(x, gap): (Ep, gap_integral)} from the pkl files, plus run_log-format lines (e.g. pasted) if given."""
    import re
    stages = stages or SETS[SET][0]
    pts = {}
    if logfile:
        for m in re.finditer(LOG_RE, open(logfile).read()):
            x, g, a, p, ga, gp = (float(v) for v in m.groups())
            pts[(x, g)] = (a*np.exp(1j*p), ga*np.exp(1j*gp))
    for st in stages:
        for r in load(st):
            pts[(r['x_interface'], r['gap'])] = (r['p_in'][1], r['gap_integral'][1, 1])
    return pts


def plot_approach(logfile=None, xs=None):
    """Approach curves: backscattered Ep (p in) and the gap field vs gap, one curve per position."""
    pts = approach_points(logfile=logfile)
    allx = sorted({x for x, g in pts})
    xs = [x for x in (xs or allx) if sum(1 for k in pts if k[0] == x) > 2]
    fig, ax = plt.subplots(2, 2, figsize=(12, 8.5), sharex=True)
    cmap = plt.get_cmap('coolwarm_r')
    for x in xs:
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        Ep = np.array([pts[(x, g)][0] for g in gs])
        Gi = np.array([pts[(x, g)][1] for g in gs])
        col = cmap((x + 1000)/2000)
        kw = dict(color=col, ms=4, label=f'x = {x:+.0f} nm')
        ax[0, 0].plot(gs, np.abs(Ep), 'o-', **kw)
        ax[1, 0].plot(gs, np.unwrap(np.angle(Ep)), 'o-', **kw)
        ax[0, 1].plot(gs, np.abs(Gi)/gs, 'o-', **kw)
        ax[1, 1].plot(gs, np.unwrap(np.angle(Gi)), 'o-', **kw)
    ax[0, 0].set(title='Backscattered Ep, p polarized', ylabel='amplitude (arb.)')
    ax[1, 0].set(ylabel='phase (rad)', xlabel='gap (nm)')
    ax[0, 1].set(title='Ey in the gap (integral / gap), p polarized', ylabel='mean Ey (V/m, incident = 1)')
    ax[1, 1].set(ylabel='phase (rad)', xlabel='gap (nm)')
    for a in ax.flat:
        a.grid(alpha=0.3)
    ax[0, 0].legend(fontsize=8)
    fig.suptitle(f'2D approach curves, {SETS[SET][2]}')
    fig.tight_layout()
    out = os.path.join(FIGS, 'approach_curves' + SETS[SET][1] + '.png')
    fig.savefig(out, dpi=130)
    print('wrote', out, 'positions:', xs)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'approach':
    plot_approach(logfile=sys.argv[2] if len(sys.argv) > 2 else None)


TAP_AMPLITUDE = 100     # nm, as in run_2d.py
MIN_GAP = 1
N_HEIGHTS = 15         # a position is demodulated only when all heights (14 + 5 nm) are there


def demodulate(gaps, E, n_t=2000, harmonics=(1, 2, 3, 4)):
    """S_n: gap(t) = MIN_GAP + A/2 (1 + cos wt), cubic spline through E(gap) (same as the 3D analysis)."""
    from scipy.interpolate import CubicSpline
    t = np.linspace(0, 1, n_t, endpoint=False)
    z = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*t))
    Ez = CubicSpline(gaps, E.real)(z) + 1j*CubicSpline(gaps, E.imag)(z)
    return {n: np.mean(Ez*np.exp(-2j*np.pi*n*t)) for n in harmonics}


def plot_demod(logfile=None, harmonics=(2, 3)):
    """S_n vs x for the backscattered Ep (p in) and the mean gap field, positions with the full height set."""
    pts = approach_points(logfile=logfile)
    need = MIN_GAP + TAP_AMPLITUDE
    rows = []
    for x in sorted({x for x, g in pts}):
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        if len(gs) < N_HEIGHTS or gs.min() > MIN_GAP or gs.max() < need:
            continue
        Ep = np.array([pts[(x, g)][0] for g in gs])
        Gm = np.array([pts[(x, g)][1] for g in gs])/gs
        rows.append((x, demodulate(gs, Ep), demodulate(gs, Gm)))
    x = np.array([r[0] for r in rows])
    fig, ax = plt.subplots(2, 2*len(harmonics), figsize=(5*2*len(harmonics), 7.5), sharex=True)
    for k, (name, idx) in enumerate((('Backscattered Ep, p polarized', 1), ('Mean Ey in the gap, p polarized', 2))):
        for j, n in enumerate(harmonics):
            col = 2*k + j
            S = np.array([r[idx][n] for r in rows])
            ax[0, col].plot(x, np.abs(S), 'o-', ms=4)
            ax[0, col].set_title(f'{name}: S{n}', fontsize=10)
            ax[0, col].set_ylabel('amplitude')
            ax[1, col].plot(x, np.unwrap(np.angle(S)), 'o-', ms=4, color='C1')
            ax[1, col].set_ylabel('phase (rad)')
            ax[1, col].set_xlabel('interface position x (nm)   oil  <  0  <  water')
            for a in ax[:, col]:
                a.axvline(0, color='0.6', lw=0.8)
                a.grid(alpha=0.3)
    fig.suptitle(f'2D demodulated signal, {SETS[SET][2]} (tapping {TAP_AMPLITUDE} nm from {MIN_GAP} nm)')
    fig.tight_layout()
    out = os.path.join(FIGS, 'demod_vs_x' + SETS[SET][1] + '.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    for r in rows:
        print(f"{r[0]:+6.0f}  " + '  '.join(f"S{n} |{abs(r[1][n]):.4e}| {np.angle(r[1][n]):+.4f}" for n in harmonics)
              + '   gap: ' + '  '.join(f"S{n} |{abs(r[2][n]):.4f}| {np.angle(r[2][n]):+.4f}" for n in harmonics))


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'demod':
    plot_demod(logfile=sys.argv[2] if len(sys.argv) > 2 else None)


def plot_s2_over_s3(logfile=None):
    """Complex ratio S2 / S3 vs x for the backscattered Ep (p in) and the mean gap field."""
    pts = approach_points(logfile=logfile)
    rows = []
    for x in sorted({x for x, g in pts}):
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        if len(gs) < N_HEIGHTS or gs.min() > MIN_GAP or gs.max() < MIN_GAP + TAP_AMPLITUDE:
            continue
        Sf = demodulate(gs, np.array([pts[(x, g)][0] for g in gs]))
        Sg = demodulate(gs, np.array([pts[(x, g)][1] for g in gs])/gs)
        rows.append((x, Sf[2]/Sf[3], Sg[2]/Sg[3]))
    x = np.array([r[0] for r in rows])
    fig, ax = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)
    for col, (name, idx) in enumerate((('Backscattered Ep, p polarized: S2 / S3', 1),
                                       ('Mean Ey in the gap, p polarized: S2 / S3', 2))):
        R = np.array([r[idx] for r in rows])
        ax[0, col].plot(x, np.abs(R), 'o-', ms=4)
        ax[0, col].set_title(name, fontsize=10)
        ax[0, col].set_ylabel('amplitude')
        ax[1, col].plot(x, np.unwrap(np.angle(R)), 'o-', ms=4, color='C1')
        ax[1, col].set_ylabel('phase (rad)')
        ax[1, col].set_xlabel('interface position x (nm)   oil  <  0  <  water')
        for a in ax[:, col]:
            a.axvline(0, color='0.6', lw=0.8)
            a.grid(alpha=0.3)
    fig.suptitle(f'2D S2 / S3, {SETS[SET][2]} (tapping {TAP_AMPLITUDE} nm from {MIN_GAP} nm)')
    fig.tight_layout()
    out = os.path.join(FIGS, 'S2_over_S3_vs_x' + SETS[SET][1] + '.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    for r in rows:
        print(f'{r[0]:+6.0f}  Ep: |{abs(r[1]):.4f}| {np.angle(r[1]):+.4f}   gap: |{abs(r[2]):.4f}| {np.angle(r[2]):+.4f}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 's2s3':
    plot_s2_over_s3(logfile=sys.argv[2] if len(sys.argv) > 2 else None)


def plot_near_field_low_gap(gap=1, stages=('scan_demod', 'scan_h5', 'scan_demod_fill')):
    """
    Near field (p polarized, Ey = vertical component) on the tip axis at one gap vs x:
    mean over the gap (SiN surface to apex) and 10 / 30 / 100 nm below the SiN.
    """
    recs = []
    for st in stages:
        recs += [r for r in load(st) if r['gap'] == gap]
    recs = sorted({r['x_interface']: r for r in recs}.values(), key=lambda r: r['x_interface'])
    x = np.array([r['x_interface'] for r in recs])
    series = [('in the gap (mean)', np.array([r['gap_integral'][1, 1] for r in recs])/gap)]
    for d in (10, 30, 100):
        series.append((f'{d} nm below the SiN', np.array([r[f'E_liquid_{d}nm'][1, 1] for r in recs])))
    fig, ax = plt.subplots(2, 4, figsize=(18, 7.5), sharex=True)
    for j, (name, v) in enumerate(series):
        ax[0, j].plot(x, np.abs(v), 'o-', ms=4)
        ax[0, j].set_title(f'|Ey| {name}', fontsize=10)
        ax[0, j].set_ylabel('|Ey| (incident = 1)')
        ax[1, j].plot(x, np.unwrap(np.angle(v)), 'o-', ms=4, color='C1')
        ax[1, j].set_ylabel('phase (rad)')
        ax[1, j].set_xlabel('interface position x (nm)   oil  <  0  <  water')
        for a in ax[:, j]:
            a.axvline(0, color='0.6', lw=0.8)
            a.grid(alpha=0.3)
    fig.suptitle(f'2D near field on the tip axis, gap {gap:g} nm, p polarized')
    fig.tight_layout()
    out = os.path.join(FIGS, f'near_field_gap{gap:g}_vs_x.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    for r, *vals in zip(recs, *[s[1] for s in series]):
        print(f"{r['x_interface']:+6.0f} " + '  '.join(f'{abs(v):8.4f} {np.angle(v):+.3f}' for v in vals))


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'nearfield':
    plot_near_field_low_gap(gap=float(sys.argv[2]) if len(sys.argv) > 2 else 1)


def demod_rows(set_name):
    """[(x, {n: S_n of Ep}, {n: S_n of mean gap Ey})] for positions with the full tapping range."""
    pts = approach_points(stages=SETS[set_name][0])
    rows = []
    for x in sorted({x for x, g in pts}):
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        if len(gs) < N_HEIGHTS or gs.min() > MIN_GAP or gs.max() < MIN_GAP + TAP_AMPLITUDE:
            continue
        rows.append((x, demodulate(gs, np.array([pts[(x, g)][0] for g in gs])),
                     demodulate(gs, np.array([pts[(x, g)][1] for g in gs])/gs)))
    return rows


def plot_compare_sin():
    """5 nm vs 20 nm SiN: S2, S3 and S2/S3 of the backscattered Ep vs x, each normalized to its oil end."""
    fig, ax = plt.subplots(2, 3, figsize=(16, 7.5), sharex=True)
    for set_name, c in (('sin5', 'C0'), ('sin20', 'C3')):
        rows = demod_rows(set_name)
        if not rows:
            continue
        x = np.array([r[0] for r in rows])
        for j, (lab, v) in enumerate((('S2', np.array([r[1][2] for r in rows])),
                                      ('S3', np.array([r[1][3] for r in rows])),
                                      ('S2 / S3', np.array([r[1][2]/r[1][3] for r in rows])))):
            ax[0, j].plot(x, np.abs(v)/np.abs(v[0]), 'o-', ms=4, color=c, label=SETS[set_name][2])
            ax[1, j].plot(x, np.unwrap(np.angle(v)) - np.angle(v[0]), 'o-', ms=4, color=c)
            ax[0, j].set_title(f'Backscattered Ep, p polarized: {lab}', fontsize=10)
    for j in range(3):
        ax[0, j].set_ylabel(f'amplitude / value at x = -1000')
        ax[1, j].set_ylabel('phase - phase at x = -1000 (rad)')
        ax[1, j].set_xlabel('interface position x (nm)   oil  <  0  <  water')
        for a in ax[:, j]:
            a.axvline(0, color='0.6', lw=0.8)
            a.grid(alpha=0.3)
    ax[0, 0].legend()
    fig.suptitle(f'2D, 5 nm vs 20 nm SiN window (tapping {TAP_AMPLITUDE} nm from {MIN_GAP} nm)')
    fig.tight_layout()
    out = os.path.join(FIGS, 'compare_sin5_sin20.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'compare':
    plot_compare_sin()


def plot_s2s3_provisional(heights=(1, 3, 5, 8, 14, 30, 60, 101)):
    """
    S2 / S3 of the backscattered Ep from a reduced height set (as in a half-finished split run).
    20 nm SiN with the heights available; 5 nm SiN both with all 15 heights and with the same reduced set,
    which shows the error of demodulating from the reduced set.
    """
    def ratio(set_name, hs=None):
        pts = approach_points(stages=SETS[set_name][0])
        out = []
        for x in sorted({x for x, g in pts}):
            gs = np.array(sorted(g for xx, g in pts if xx == x and (hs is None or g in hs)))
            if hs is not None and len(gs) != len(hs):
                continue
            if hs is None and (len(gs) < 10 or gs.min() > MIN_GAP or gs.max() < MIN_GAP + TAP_AMPLITUDE):
                continue
            S = demodulate(gs, np.array([pts[(x, g)][0] for g in gs]))
            out.append((x, S[2]/S[3]))
        return np.array([o[0] for o in out]), np.array([o[1] for o in out])
    curves = [('5 nm SiN, 15 heights', 'C0', 'o-', ratio('sin5')),
              (f'5 nm SiN, {len(heights)} heights', 'C0', 's--', ratio('sin5', heights)),
              (f'20 nm SiN, {len(heights)} heights (provisional)', 'C3', 'o-', ratio('sin20', heights))]
    fig, ax = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for j, norm in enumerate((False, True)):
        for lab, c, st, (x, R) in curves:
            if len(x) == 0:
                continue
            a = np.abs(R)/np.abs(R[0]) if norm else np.abs(R)
            p = np.unwrap(np.angle(R)) - (np.angle(R[0]) if norm else 0)
            ax[0, j].plot(x, a, st, ms=4, color=c, mfc='none' if 's' in st else c, label=lab)
            ax[1, j].plot(x, p, st, ms=4, color=c, mfc='none' if 's' in st else c)
        ax[0, j].set_title('Backscattered Ep, p polarized: S2 / S3' + (' (normalized to x = -1000)' if norm else ''), fontsize=10)
        ax[0, j].set_ylabel('amplitude' + (' / value at x = -1000' if norm else ''))
        ax[1, j].set_ylabel('phase' + (' - phase at x = -1000' if norm else '') + ' (rad)')
        ax[1, j].set_xlabel('interface position x (nm)   oil  <  0  <  water')
        for a in ax[:, j]:
            a.axvline(0, color='0.6', lw=0.8)
            a.grid(alpha=0.3)
    ax[0, 0].legend(fontsize=8)
    fig.suptitle(f'2D S2 / S3: 20 nm SiN (part 1 of 2, heights {", ".join(str(h) for h in heights)} nm) vs 5 nm SiN')
    fig.tight_layout()
    out = os.path.join(FIGS, 'S2_over_S3_sin20_provisional.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)
    for lab, c, st, (x, R) in curves:
        print(lab)
        for xi, r in zip(x, R):
            print(f'  {xi:+6.0f}  |{abs(r):.4f}|  {np.angle(r):+.4f}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 's2s3_prov':
    plot_s2s3_provisional()


def plot_s2s3_sin5_sin20(sets=(('sin5', 'C0'), ('sin20', 'C3')), title='5 nm vs 20 nm SiN',
                         fname='S2_over_S3_sin5_vs_sin20.png'):
    """S2 / S3 of the backscattered Ep for two data sets: raw (left) and normalized to x = -1000 (right)."""
    fig, ax = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for set_name, c in sets:
        rows = demod_rows(set_name)
        if not rows:
            continue
        x = np.array([r[0] for r in rows])
        R = np.array([r[1][2]/r[1][3] for r in rows])
        amp, ph = np.abs(R), np.unwrap(np.angle(R))
        kw = dict(ms=4, color=c, label=SETS[set_name][2])
        ax[0, 0].plot(x, amp, 'o-', **kw)
        ax[1, 0].plot(x, ph, 'o-', **kw)
        ax[0, 1].plot(x, amp/amp[0], 'o-', **kw)
        ax[1, 1].plot(x, ph - ph[0], 'o-', **kw)
    ax[0, 0].set(title='S2 / S3 amplitude', ylabel='amplitude')
    ax[1, 0].set(title='S2 / S3 phase', ylabel='phase (rad)')
    ax[0, 1].set(title='S2 / S3 amplitude, normalized', ylabel='amplitude / value at x = -1000')
    ax[1, 1].set(title='S2 / S3 phase, normalized', ylabel='phase - phase at x = -1000 (rad)')
    for a in ax.flat:
        a.axvline(0, color='0.6', lw=0.8)
        a.grid(alpha=0.3)
    for a in ax[1]:
        a.set_xlabel('interface position x (nm)   oil  <  0  <  water')
    ax[0, 0].legend()
    fig.suptitle(f'2D backscattered Ep, p polarized: S2 / S3, {title}')
    fig.tight_layout()
    out = os.path.join(FIGS, fname)
    fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 's2s3_both':
    plot_s2s3_sin5_sin20()


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 's2s3_wl':
    plot_s2s3_sin5_sin20(sets=(('sin5', 'C0'), ('wl5p5', 'C2')), title='6.1 um vs 5.5 um (5 nm SiN)',
                         fname='S2_over_S3_6p1_vs_5p5um.png')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 's2s3_wl3':
    plot_s2s3_sin5_sin20(sets=(('sin5', 'C0'), ('wl5p5', 'C2'), ('wl2p95', 'C4')),
                         title='6.1 / 5.5 / 2.95 um (5 nm SiN)', fname='S2_over_S3_wavelengths.png')


def plot_demod_explained(x, set_name='sin5'):
    """
    Illustration of how S2 is obtained at one tip position x.
    Plotted quantity: Re[E * exp(-i arg S2)], the part of the complex backscattered field E that is in phase
    with S2 (then the whole S2 is the real amplitude of the 2w wiggle); the cycle average is subtracted.
    Left : approach curve (15 solved heights, colour = height, spline) with the straight chord between h = 1 and
           101 nm, and below it the deviation from that chord (the curvature that S2 senses).
    Right: the same curve read out over one tapping cycle h(t) = 1 + 50 (1 + cos wt) nm:
           tip height, signal and its 1w part, signal minus 1w part and its 2w part (= S2).
    """
    from scipy.interpolate import CubicSpline
    from matplotlib.gridspec import GridSpec
    pts = approach_points(stages=SETS[set_name][0])
    gs = np.array(sorted(g for xx, g in pts if xx == x))
    if len(gs) < N_HEIGHTS:
        raise SystemExit(f'x = {x}: only {len(gs)} heights')
    E = np.array([pts[(x, g)][0] for g in gs])
    n_t = 2000
    t = np.linspace(0, 1, n_t, endpoint=False)
    z = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*t))
    spl = lambda h: CubicSpline(gs, E.real)(h) + 1j*CubicSpline(gs, E.imag)(h)
    Ez = spl(z)
    S = {n: np.mean(Ez*np.exp(-2j*np.pi*n*t)) for n in range(0, 5)}
    rot = np.exp(-1j*np.angle(S[2]))
    sc = 1e3                                           # plot units: 1e-3 of the incident-normalised field
    S0 = (S[0]*rot).real
    proj = lambda e: (e*rot).real - S0                 # in-phase part, cycle average removed
    sig = sc*proj(Ez)
    c1 = sc*(2*S[1]*rot).real*np.cos(2*np.pi*t)        # 1w part of the signal
    c2 = sc*2*abs(S[2])*np.cos(4*np.pi*t)              # 2w part: amplitude 2 |S2|
    hh = np.linspace(MIN_GAP, MIN_GAP + TAP_AMPLITUDE, 300)
    curve = sc*proj(spl(hh))
    pointsE = sc*proj(E)
    chord = lambda h: np.interp(h, [hh[0], hh[-1]], [curve[0], curve[-1]])

    fig = plt.figure(figsize=(15, 9))
    G = GridSpec(3, 2, height_ratios=[0.8, 2.2, 2.2], hspace=0.45, wspace=0.22)
    cmap, norm = plt.get_cmap('viridis'), plt.Normalize(MIN_GAP, MIN_GAP + TAP_AMPLITUDE)

    axL1 = fig.add_subplot(G[0:2, 0])
    axL1.axvspan(MIN_GAP, MIN_GAP + TAP_AMPLITUDE, color='0.95', zorder=0)
    axL1.plot(hh, curve, '-', color='0.35', lw=1.5, label='spline through the solved heights', zorder=2)
    axL1.plot([hh[0], hh[-1]], [curve[0], curve[-1]], '--', color='C3', lw=1.2, label='straight line (h = 1 to 101 nm)', zorder=1)
    axL1.fill_between(hh, chord(hh), curve, color='C1', alpha=0.25, label='curvature: what S2 senses')
    axL1.scatter(gs, pointsE, c=gs, cmap=cmap, norm=norm, s=55, edgecolor='k', linewidth=0.6, zorder=3)
    axL1.plot([], [], 'o', color='0.6', mec='k', ms=7, label=f'{len(gs)} solves (one per height)')
    axL1.set(xlabel='tip height h above the SiN (nm)', ylabel='in-phase part of E  (x 1e-3, arb.)',
             title='Approach curve: backscattered field vs tip height')
    axL1.legend(fontsize=8, loc='upper right')
    axL1.grid(alpha=0.3)

    axL2 = fig.add_subplot(G[2, 0], sharex=axL1)
    axL2.axhline(0, color='C3', lw=1.2, ls='--')
    axL2.plot(hh, curve - chord(hh), '-', color='0.35', lw=1.5)
    axL2.fill_between(hh, 0, curve - chord(hh), color='C1', alpha=0.25)
    axL2.scatter(gs, pointsE - chord(gs), c=gs, cmap=cmap, norm=norm, s=40, edgecolor='k', linewidth=0.6, zorder=3)
    axL2.set(xlabel='tip height h (nm)', ylabel='curve minus straight line  (x 1e-3)',
             title='Curvature: approach curve minus the straight line')
    axL2.grid(alpha=0.3)

    axH = fig.add_subplot(G[0, 1])
    axH.scatter(t, z, c=z, cmap=cmap, norm=norm, s=4)
    axH.set(ylabel='tip height (nm)', title=f'One tapping cycle:  h(t) = {MIN_GAP} + {TAP_AMPLITUDE//2} (1 + cos wt) nm')
    axH.set_xticks([0, 0.5, 1]); axH.set_xticklabels(['top', 'bottom', 'top'])
    axH.set_xlim(0, 1)
    axH.grid(alpha=0.3)

    axS = fig.add_subplot(G[1, 1], sharex=axH)
    axS.scatter(t, sig, c=z, cmap=cmap, norm=norm, s=4)
    axS.plot([], [], 'o', color='0.4', ms=3, label='signal  E(t) = E(h(t))')
    axS.plot(t, c1, '-', color='C3', lw=1.6, label='its 1w part (dominant: the approach curve is mostly a slope)')
    axS.set(ylabel='signal  (x 1e-3)', title='The approach curve read out in time')
    axS.legend(fontsize=8, loc='best')
    axS.grid(alpha=0.3)

    axR = fig.add_subplot(G[2, 1], sharex=axH)
    axR.scatter(t, sig - c1, c=z, cmap=cmap, norm=norm, s=4)
    axR.plot([], [], 'o', color='0.4', ms=3, label='signal minus 1w part')
    axR.plot(t, c2, '-', color='C1', lw=2, label=f'2w part: amplitude 2 |S2| = {2*sc*abs(S[2]):.2f}e-3')
    axR.axhline(0, color='0.6', lw=0.8)
    axR.set(xlabel='time within one tapping cycle', ylabel='remainder  (x 1e-3)',
            title='Remove the 1w part: the 2w wiggle left over is S2')
    axR.set_xticks([0, 0.25, 0.5, 0.75, 1]); axR.set_xticklabels(['top', '', 'bottom', '', 'top'])
    axR.legend(fontsize=8, loc='best')
    axR.grid(alpha=0.3)

    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=[axL1, axL2, axH, axS, axR],
                      location='right', shrink=0.6, pad=0.02)
    cb.set_label('tip height (nm)')
    where = 'oil' if x < 0 else 'water' if x > 0 else 'at the interface'
    fig.suptitle(f'How demodulation works: tip over {where} (x = {x:+.0f} nm), {SETS[set_name][2]}\n'
                 f'S2 = average over one tapping cycle of E(t) exp(-2i wt)   ->   |S2| = {abs(S[2]):.3e},  '
                 f'arg S2 = {np.angle(S[2]):+.2f} rad', fontsize=12)
    out = os.path.join(FIGS, f'demod_explained_x{x:+.0f}.png')
    fig.savefig(out, dpi=130, bbox_inches='tight')
    print('wrote', out, f'|S1|={abs(S[1]):.3e} |S2|={abs(S[2]):.3e} |S3|={abs(S[3]):.3e}')


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'explain':
    for _x in ([float(sys.argv[2])] if len(sys.argv) > 2 else (-1000.0, 0.0, 1000.0)):
        plot_demod_explained(_x, SET)


def plot_approach_and_tapping(xs=((-1000.0, 'oil', '#7f2704'), (-500.0, 'oil', '#d94801'), (-40.0, 'oil', '#fd8d3c'),
                                  (-20.0, 'oil', '#fdbe85'), (20.0, 'water', '#9ecae1'), (40.0, 'water', '#6baed6'),
                                  (500.0, 'water', '#2171b5'), (1000.0, 'water', '#08306b')),
                              set_name='sin5', norm=False):
    """
    norm=True: every curve divided by its own |Ep| at the top of the tap (101 nm) -> *_norm.png.
    2 x 2: approach curves |Ep| vs height; the same signal over one tapping cycle (ticks = tip height);
    that signal with its average and 1w part removed (what is left carries S2, S3, ...); |S2|, |S3| per position.
    """
    from scipy.interpolate import CubicSpline
    pts = approach_points(stages=SETS[set_name][0])
    t = np.linspace(0, 1, 1000)
    z = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*t))
    tc = np.linspace(0, 1, 4000, endpoint=False)       # one full cycle for the Fourier coefficients
    zc = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*tc))
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    ax = [axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]]
    Sn = []
    for x, name, c in xs:
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        E = np.array([pts[(x, g)][0] for g in gs])
        Sn.append(demodulate(gs, E))
        k_n = 1/np.abs(E[-1]) if norm else 1.0
        spl = lambda h: k_n*np.abs(CubicSpline(gs, E.real)(h) + 1j*CubicSpline(gs, E.imag)(h))
        hh = np.linspace(gs.min(), gs.max(), 300)
        lab = f'tip over {name} (x = {x:+.0f} nm)'
        ax[0].plot(hh, spl(hh), '-', color=c, lw=1.8)
        ax[0].plot(gs, k_n*np.abs(E), 'o', color=c, ms=5, label=lab)
        ax[1].plot(t, spl(z), '-', color=c, lw=2, label=lab)
        sc = spl(zc)
        a0, a1 = np.mean(sc), 2*np.mean(sc*np.cos(2*np.pi*tc))
        ax[2].plot(t, (spl(z) - a0 - a1*np.cos(2*np.pi*t))*1e3, '-', color=c, lw=2, label=lab)
    ticks = [0, 0.25, 0.5, 0.75, 1]
    for a in (ax[1], ax[2]):
        a.set_xticks(ticks)
        a.set_xticklabels([f'{z0:.0f}' for z0 in MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*np.array(ticks)))])
        a.set_xlim(0, 1)
        a.set_xlabel('tip height during one tapping cycle (nm)')
    yl = '|Ep| / |Ep| at 101 nm' if norm else 'backscattered |Ep| (arb.)'
    ax[0].set(xlabel='tip height (nm)', ylabel=yl, title='Approach curve')
    ax[1].set(ylabel=yl, title='Signal during one tapping cycle')
    ax[2].axhline(0, color='0.6', lw=0.8)
    ax[2].set(ylabel=('normalized |Ep|' if norm else '|Ep|') + ' minus average and 1w part (x 1e-3)',
              title='Signal during one tapping cycle, 1w wiggle removed')
    # |S2| and |S3| per position, relative to the oil end (absolute values on the bars)
    w = 0.8/len(xs)
    for k, n in enumerate((2, 3)):
        ref = abs(Sn[0][n])
        for j, ((x, name, c), S) in enumerate(zip(xs, Sn)):
            pos = k + (j - (len(xs) - 1)/2)*w
            ax[3].bar(pos, abs(S[n])/ref, width=w*0.9, color=c, label=f'x = {x:+.0f} nm' if k == 0 else None)
            ax[3].text(pos, abs(S[n])/ref + 0.01, f'{abs(S[n]):.2e}', ha='center', va='bottom', fontsize=7, rotation=90)
    ax[3].set_xticks([0, 1])
    ax[3].set_xticklabels(['S2', 'S3'])
    ax[3].set_ylim(0.6, 1.25)
    ax[3].set(ylabel='|Sn| / |Sn| at x = -1000 nm (oil)', title='Demodulated signal: S2 and S3')
    for a in ax:
        a.grid(alpha=0.3)
    ax[3].legend(fontsize=8, loc='upper right', ncol=2)
    fig.suptitle(f'2D, {SETS[set_name][2]} (tapping {TAP_AMPLITUDE} nm from {MIN_GAP} nm)')
    h, l = ax[0].get_legend_handles_labels()           # same colours in all panels: one legend under the title
    fig.legend(h, l, loc='upper center', ncol=4, fontsize=9, bbox_to_anchor=(0.5, 0.965), frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = os.path.join(FIGS, 'approach_and_tapping' + ('_norm' if norm else '') + '.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'tapview':
    plot_approach_and_tapping(set_name=SET, norm='--norm' in sys.argv)


def plot_approach_and_tapping_inphase(xs=((-1000.0, 'oil', '#d95f02'), (-40.0, 'oil', '#fdae6b'),
                                          (40.0, 'water', '#9ecae1'), (1000.0, 'water', '#08519c')), set_name='sin5',
                                      norm=False):
    """
    Same 2 x 2 layout as plot_approach_and_tapping, but the three signal panels show Re[E exp(-i arg S2)]:
    the part of the complex backscattered field E that is in phase with S2 at that position.  With this choice
    the 2w part of the wiggle in the third panel has amplitude exactly 2 |S2|, consistent with the S2 bars.
    """
    from scipy.interpolate import CubicSpline
    pts = approach_points(stages=SETS[set_name][0])
    t = np.linspace(0, 1, 1000)
    z = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*t))
    tc = np.linspace(0, 1, 4000, endpoint=False)
    zc = MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*tc))
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    ax = [axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]]
    Sn = []
    for x, name, c in xs:
        gs = np.array(sorted(g for xx, g in pts if xx == x))
        E = np.array([pts[(x, g)][0] for g in gs])
        S = demodulate(gs, E)
        Sn.append(S)
        rot = np.exp(-1j*np.angle(S[2]))/(np.abs(E[-1]) if norm else 1.0)   # norm: divide by |Ep| at 101 nm
        f = lambda h: ((CubicSpline(gs, E.real)(h) + 1j*CubicSpline(gs, E.imag)(h))*rot).real
        hh = np.linspace(gs.min(), gs.max(), 300)
        lab = f'tip over {name} (x = {x:+.0f} nm)'
        ax[0].plot(hh, f(hh), '-', color=c, lw=1.8)
        ax[0].plot(gs, (E*rot).real, 'o', color=c, ms=5, label=lab)
        ax[1].plot(t, f(z), '-', color=c, lw=2, label=lab)
        fc = f(zc)
        a0, a1 = np.mean(fc), 2*np.mean(fc*np.cos(2*np.pi*tc))
        ax[2].plot(t, (f(z) - a0 - a1*np.cos(2*np.pi*t))*1e3, '-', color=c, lw=2,
                   label=f'{lab}: 2|S2|{"/|Ep(101)|" if norm else ""} = {2e3*abs(S[2]*rot):.2f}e-3')
    ticks = [0, 0.25, 0.5, 0.75, 1]
    for a in (ax[1], ax[2]):
        a.set_xticks(ticks)
        a.set_xticklabels([f'{z0:.0f}' for z0 in MIN_GAP + TAP_AMPLITUDE/2*(1 + np.cos(2*np.pi*np.array(ticks)))])
        a.set_xlim(0, 1)
        a.set_xlabel('tip height during one tapping cycle (nm)')
    yl = 'Ep in phase with S2, / |Ep| at 101 nm' if norm else 'backscattered Ep, in phase with S2 (arb.)'
    ax[0].set(xlabel='tip height (nm)', ylabel=yl, title='Approach curve')
    ax[1].set(ylabel=yl, title='Signal during one tapping cycle')
    ax[2].axhline(0, color='0.6', lw=0.8)
    ax[2].set(ylabel='minus average and 1w part (x 1e-3, arb.)',
              title='Signal during one tapping cycle, 1w wiggle removed')
    w = 0.8/len(xs)
    for k, n in enumerate((2, 3)):
        ref = abs(Sn[0][n])
        for j, ((x, name, c), S) in enumerate(zip(xs, Sn)):
            pos = k + (j - (len(xs) - 1)/2)*w
            ax[3].bar(pos, abs(S[n])/ref, width=w*0.9, color=c, label=f'x = {x:+.0f} nm' if k == 0 else None)
            ax[3].text(pos, abs(S[n])/ref + 0.01, f'{abs(S[n]):.2e}', ha='center', va='bottom', fontsize=7, rotation=90)
    ax[3].set_xticks([0, 1])
    ax[3].set_xticklabels(['S2', 'S3'])
    ax[3].set_ylim(0.6, 1.25)
    ax[3].set(ylabel='|Sn| / |Sn| at x = -1000 nm (oil)', title='Demodulated signal: S2 and S3')
    for a in ax:
        a.grid(alpha=0.3)
    for a in ax[:3]:
        a.legend(fontsize=8.5)
    ax[3].legend(fontsize=8, loc='upper right', ncol=2)
    fig.suptitle(f'2D, {SETS[set_name][2]} (tapping {TAP_AMPLITUDE} nm from {MIN_GAP} nm); '
                 f'signals: part of the complex Ep in phase with each position\'s S2')
    fig.tight_layout()
    out = os.path.join(FIGS, 'approach_and_tapping_inphase' + ('_norm' if norm else '') + '.png')
    fig.savefig(out, dpi=130)
    print('wrote', out)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'tapview_inphase':
    plot_approach_and_tapping_inphase(set_name=SET, norm='--norm' in sys.argv)
