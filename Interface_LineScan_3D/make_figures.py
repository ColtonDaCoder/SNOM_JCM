"""
Summary figures for the interface line scan, written to figures/ (rerun as more data arrives):

    python make_figures.py

    fig1_setup.png          model geometry and illumination
    fig2_near_field.png     field slices + line cuts: how big the near-field spot is
    fig3_numerical_noise.png  plane wave / 1 refinement step vs focused beam: mesh noise
    fig4_raw_linescan.png   raw signal at 5 nm across the interface: far-field drift dominates
    fig5_height_difference.png  E(5 nm) - E(101 nm): near-field part across the interface
    fig6_plateau_test.png   raw backscatter at 5 nm over +-1 um: line vs line + step (proof of concept)
    fig7_near_field_oil_vs_water.png  near field over pure oil vs pure water
"""
import os
import pickle as pk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')
OUT = os.path.join(HERE, 'figures')
os.makedirs(OUT, exist_ok=True)

C_P, C_S, C_GREY, C_ACC = '#0072B2', '#D55E00', '#7f7f7f', '#009E73'
C_WATER, C_OIL, C_SIN, C_PT = '#9ecae1', '#fdd49e', '#bdbdbd', '#636363'
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.titleweight': 'bold',
                     'figure.titlesize': 13, 'figure.titleweight': 'bold',
                     'axes.spines.top': False, 'axes.spines.right': False})

R_TIP, ALPHA, L_TIP = 75.0, np.deg2rad(30.14), 12940.0


def load(path):
    p = os.path.join(RES, path)
    return pk.load(open(p, 'rb')) if os.path.exists(p) else None


def tip_profile(gap, zmax):
    phi = np.linspace(-np.pi/2, -ALPHA, 60)
    r = np.r_[R_TIP*np.cos(phi), 0]
    z = np.r_[R_TIP + R_TIP*np.sin(phi), 0]
    zc = np.linspace(z[-2], zmax, 50)
    rc = r[-2] + (zc - z[-2])*np.tan(ALPHA)
    r = np.r_[r[:-1], rc]; z = np.r_[z[:-1], zc] + gap
    return np.r_[-r[::-1], r], np.r_[z[::-1], z]


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('wrote figures/' + name)


# --------------------------------------------------------------------------- fig 1
def fig_setup():
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={'width_ratios': [1.25, 1]})
    box = dict(boxstyle='round,pad=0.25', fc='white', ec='none', alpha=0.85)
    a = ax[0]                                   # whole domain, um
    a.add_patch(Rectangle((-8, -2.005), 16, 2.0, color=C_WATER, lw=0))
    a.add_patch(Rectangle((0, -1.005), 7, 1.0, color=C_OIL, lw=0))
    a.add_patch(Rectangle((-8, -0.005), 16, 0.12, color=C_SIN, lw=0))
    tx, tz = tip_profile(1, 12940)
    a.add_patch(Polygon(np.c_[tx, tz]/1e3, closed=True, color=C_PT))
    a.add_patch(Rectangle((-8, -2.005), 16, 15.45, fill=False, ls='--', color=C_GREY))
    th = np.deg2rad(60); w = 4.85                # beam: axis and 1/e half width, from the upper left
    ux, uz = np.sin(th), -np.cos(th)             # propagation direction (+x, down)
    nx, nz = np.cos(th), np.sin(th)              # transverse direction in the x-z plane
    t = np.array([-16, 0])
    band = np.array([[t[0]*ux - w*nx, t[0]*uz - w*nz], [t[1]*ux - w*nx, t[1]*uz - w*nz],
                     [t[1]*ux + w*nx, t[1]*uz + w*nz], [t[0]*ux + w*nx, t[0]*uz + w*nz]])
    a.add_patch(Polygon(band, closed=True, color='#CC79A7', alpha=0.18, lw=0))
    a.plot(t*ux, t*uz, '-', color='#CC79A7', lw=1.5)
    a.annotate('', xy=(-0.35, 0.25), xytext=(-5.2, 3.0), arrowprops=dict(arrowstyle='-|>', color='#CC79A7', lw=2))
    a.annotate('', xy=(-5.4, 3.6), xytext=(-0.6, 0.85), arrowprops=dict(arrowstyle='-|>', color=C_ACC, lw=2, ls='--'))
    a.text(-8.3, 10.2, 'focused Gaussian beam: 6.1 um, 60 deg,\nNA 0.4, waist 4.85 um, focus on the SiN\n(shaded: 1/e width)',
           color='#9c2f6f', fontsize=9, bbox=box)
    a.text(-8.3, 7.6, 'backscatter collected in NA 0.4', color=C_ACC, fontsize=9, bbox=box)
    a.text(0.9, 9.0, 'Pt tip, 12.9 um long,\n75 nm apex radius', color='w', fontsize=9)
    a.text(-7.7, -1.65, 'water (Hale & Querry)', fontsize=9)
    a.text(0.3, -0.75, 'oil / OTS (octane)', fontsize=9)
    a.text(5.0, 0.25, 'SiN 5 nm', fontsize=9)
    a.text(-7.9, 13.0, 'computational domain (absorbing PML boundaries)', color=C_GREY, fontsize=8)
    a.set(xlim=(-8.6, 8.6), ylim=(-2.4, 13.8), xlabel='x / um', ylabel='z / um', aspect='equal',
          title='3D model (x-z cut through the tip axis)')
    a = ax[1]                                   # zoom on the apex, nm
    a.add_patch(Rectangle((-300, -400), 300, 395, color=C_WATER, lw=0))
    a.add_patch(Rectangle((0, -400), 300, 395, color=C_OIL, lw=0))
    a.add_patch(Rectangle((-300, -5), 600, 5, color=C_SIN, lw=0))
    tx, tz = tip_profile(5, 600)
    a.add_patch(Polygon(np.c_[tx, tz], closed=True, color=C_PT))
    a.text(105, 25, 'tip-sample gap 1 - 101 nm\n(tapping amplitude 100 nm)', fontsize=9, bbox=box)
    a.text(-285, -60, 'water', fontsize=11); a.text(200, -60, 'oil', fontsize=11)
    a.annotate('interface at x_interface,\nmoved from -300 to +300 nm\n(tip fixed at x = 0)', xy=(0, -220), xytext=(25, -360),
               fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
    a.text(-285, 12, 'SiN 5 nm', fontsize=8)
    a.set(xlim=(-300, 300), ylim=(-400, 400), xlabel='x / nm', ylabel='z / nm', aspect='equal',
          title='zoom: apex over the water | oil interface')
    fig.suptitle('Setup: Pt tip scanned across a water | oil interface seen through a 5 nm SiN window')
    save(fig, 'fig1_setup.png')


# --------------------------------------------------------------------------- fig 2
def fwhm(x, y):
    y = np.asarray(y); h = y.max()/2; above = np.where(y >= h)[0]
    if len(above) < 2:
        return np.nan
    i0, i1 = above[0], above[-1]
    xl = np.interp(h, [y[i0-1], y[i0]], [x[i0-1], x[i0]]) if i0 > 0 else x[i0]
    xr = np.interp(h, [y[i1+1], y[i1]], [x[i1+1], x[i1]]) if i1 < len(y) - 1 else x[i1]
    return xr - xl


def fig_near_field():
    f = os.path.join(RES, 'fields', 'converge_x+0_g1.npz')
    if not os.path.exists(f):
        print('no field slices yet'); return
    d = np.load(f); gap = 1
    fig = plt.figure(figsize=(15, 10), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1])
    for k, (name, lab, title) in enumerate([('slice_xz', 'x / nm', 'y = 0: across the interface (water x<0 | oil x>0)'),
                                            ('slice_yz', 'y / nm', 'x = 0: along the interface')]):
        a = fig.add_subplot(gs[0, k])
        X, Y, Z = d[name + '_X']*1e9, d[name + '_Y']*1e9, d[name + '_Z']*1e9
        L = X if name == 'slice_xz' else Y
        A = np.linalg.norm(d[name + '_E'][1], axis=-1)
        im = a.pcolormesh(L, Z, A, shading='auto', cmap='magma', norm=LogNorm(vmin=A.max()*1e-3, vmax=A.max()))
        tx, tz = tip_profile(gap, 1000)
        a.plot(tx, tz, color='c', lw=0.8)
        a.axhline(0, color='w', lw=0.5, ls='--'); a.axhline(-5, color='w', lw=0.5, ls='--')
        if name == 'slice_xz':
            a.plot([0, 0], [-305, -5], color='c', ls=':', lw=1)
        a.set(xlim=(-400, 400), ylim=(-300, 500), xlabel=lab, ylabel='z / nm', title=title)
        a.set_aspect('equal')
        fig.colorbar(im, ax=a, shrink=0.8, label='|E|')
    # line cuts: depth profile below the apex and lateral profiles just under the SiN
    X, Z = d['slice_xz_X']*1e9, d['slice_xz_Z']*1e9
    Axz = np.linalg.norm(d['slice_xz_E'][1], axis=-1)
    Ayz = np.linalg.norm(d['slice_yz_E'][1], axis=-1)
    Yl = d['slice_yz_Y'][:, 0]*1e9; xl = X[:, 0]; zl = Z[0]
    i0 = np.argmin(abs(xl))
    a = fig.add_subplot(gs[0, 2])
    m = zl < -5                                   # liquid only (the field jumps at the SiN faces)
    a.semilogy(zl[m], Axz[i0, m], color=C_P, lw=2)
    a.set(xlabel='z / nm (into the liquid, SiN at -5 ... 0)', ylabel='|E| on the tip axis',
          title='depth: field below the apex', xlim=(-300, -5))
    zz = zl[(zl < -5) & (zl > -300)]; aa = Axz[i0, (zl < -5) & (zl > -300)]
    k1 = np.argmin(abs(aa - aa.max()/np.e))
    a.axvline(zz[k1], color=C_GREY, ls=':')
    a.text(zz[k1] - 5, aa.max()*0.6, f'1/e at {abs(zz[k1]):.0f} nm\ninto the liquid', ha='right', fontsize=9)
    a = fig.add_subplot(gs[1, :])
    rows = []
    for depth in (-10, -30, -60):
        kz = np.argmin(abs(zl - depth))
        px, py = Axz[:, kz], Ayz[:, kz]
        wx, wy = fwhm(xl, px), fwhm(Yl, py)
        rows.append((depth, wx, wy))
        a.plot(xl, px/px.max(), lw=2, label=f'{abs(depth)} nm below SiN, across interface (FWHM {wx:.0f} nm)')
        a.plot(Yl, py/py.max(), lw=1, ls='--', color=a.lines[-1].get_color(),
               label=f'{abs(depth)} nm below SiN, along interface (FWHM {wy:.0f} nm)')
    a.axvline(0, color=C_GREY, ls=':')
    a.text(-390, 0.93, 'water side', fontsize=10); a.text(310, 0.93, 'oil side', fontsize=10)
    a.set(xlim=(-400, 400), xlabel='lateral position / nm', ylabel='|E| (normalised)',
          title='lateral size of the near-field spot inside the liquid (sets the attainable resolution)')
    a.legend(fontsize=8, ncol=2)
    E_side = Axz[np.argmin(abs(xl + 600)), np.argmin(abs(zl - 30))]      # air, 600 nm beside the apex
    fig.suptitle(f'The near field (p incidence, gap 1 nm): |E| under the apex is ~{Axz.max()/E_side:.0f}x the field 600 nm to the side, '
                 f'and reaches ~50 nm through the SiN into the liquid')
    save(fig, 'fig2_near_field.png')
    return rows


# --------------------------------------------------------------------------- fig 3
def fig_noise():
    pw, gb = load('old_planewave/zsweep.pkl'), load('converge.pkl')
    if pw is None or gb is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    for a, data, gmax, title, col in [(ax[0], pw, 30, 'before: plane wave, 1 refinement step', C_S),
                                      (ax[1], gb, 6, 'after: focused beam (3 refinement steps)', C_P)]:
        r = sorted([r for r in data['records'] if r['gap'] <= gmax], key=lambda r: r['gap'])
        g = np.array([q['gap'] for q in r]); E = np.array([abs(q['p_in'][1]) for q in r])
        y = (E/E[0] - 1)*100
        a.plot(g, y, 'o-', color=col, ms=5)
        steps = np.abs(np.diff(E))/E[:-1]*100
        a.set(xlabel='tip - sample gap / nm', ylabel='|E| change vs gap 1 nm / %', title=title)
        a.text(0.03, 0.92, f'neighbour-to-neighbour change: median {np.median(steps):.3f} %, max {steps.max():.3f} %',
               transform=a.transAxes, fontsize=9)
        a.grid(alpha=0.3)
    ax[0].text(0.03, 0.82, 'zig-zag = different mesh for every height\n(JCM error estimate ~1.9 % per solve)',
               transform=ax[0].transAxes, fontsize=9, color=C_S)
    ax[1].text(0.03, 0.82, 'smooth, monotonic: noise < 1e-4\n(lit spot instead of the whole 13 um tip)',
               transform=ax[1].transAxes, fontsize=9, color=C_P)
    fig.suptitle('Numerical noise: plane wave + 1 refinement step gave ~3 % mesh-to-mesh scatter; with the focused beam it drops\n'
                 'below ~1e-4 (right: 3 refinement steps; the 1-step line scan with the beam in fig. 4 is equally quiet)')
    save(fig, 'fig3_numerical_noise.png')


# --------------------------------------------------------------------------- fig 4
def fig_raw():
    d = load('linescan_h5.pkl')
    if d is None:
        return
    r = sorted(d['records'], key=lambda q: q['x_interface'])
    x = np.array([q['x_interface'] for q in r])
    fig, ax = plt.subplots(2, 2, figsize=(13, 7), sharex=True)
    for col, (pol, comp, lab, c) in enumerate([('p_in', 1, 'p in / p out (tip near field active)', C_P),
                                               ('s_in', 0, 's in / s out (no near-field hot spot)', C_S)]):
        E = np.array([q[pol][comp] for q in r]); ref = E[:4].mean()
        for row, (y, unit, name) in enumerate([((np.abs(E)/abs(ref) - 1)*1e4, 'x1e-4', 'amplitude'),
                                               (np.angle(E/ref)*1e3, 'mrad', 'phase')]):
            a = ax[row, col]
            pl = np.polyfit(x, y, 1)
            a.plot(x, y, 'o', color=c, ms=4, label='simulation (gap 5 nm)')
            a.plot(x, np.polyval(pl, x), '-', color=C_GREY, lw=1.5,
                   label=f'straight line (far-field drift), scatter {np.std(y - np.polyval(pl, x)):.2f} {unit}')
            a.axvline(0, color=C_GREY, ls=':'); a.grid(alpha=0.3)
            a.set_ylabel(f'{name} rel. oil side [{unit}]'); a.legend(fontsize=8, loc='best')
        ax[0, col].set_title(lab)
    for a in ax[1]:
        a.set_xlabel('x_interface / nm   (tip over oil  <-  0  ->  tip over water)')
    fig.suptitle('Raw signal at a fixed 5 nm gap: both polarizations drift linearly - far-field change of the oil block\n'
                 'under the ~10 um beam footprint; the near-field edge is buried (amplitude change only ~0.1 %)')
    save(fig, 'fig4_raw_linescan.png')


# --------------------------------------------------------------------------- fig 5
def fig_difference():
    h5, h1 = load('linescan_h5.pkl'), load('linescan_h101.pkl')
    if h5 is None or h1 is None:
        return
    a5 = {q['x_interface']: q for q in h5['records']}; a1 = {q['x_interface']: q for q in h1['records']}
    xs = np.array(sorted(set(a5) & set(a1)))
    fig, ax = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
    D = np.array([a5[x]['p_in'][1] - a1[x]['p_in'][1] for x in xs])
    R5 = np.array([a5[x]['p_in'][1] for x in xs])
    oil = xs <= -100
    ref = D[oil].mean(); rref = R5[oil].mean()
    amp, ph = (np.abs(D)/abs(ref) - 1)*100, np.angle(D/ref)*1e3
    raw_amp = (np.abs(R5)/abs(rref) - 1)*100
    for a, y, unit, name, raw in [(ax[0], amp, '%', 'amplitude', raw_amp), (ax[1], ph, 'mrad', 'phase', None)]:
        sd = np.std(y[oil], ddof=1) if oil.sum() > 1 else np.nan
        a.axhspan(-sd, sd, color=C_GREY, alpha=0.15, label=f'oil-side scatter (+-1 sigma = {sd:.1f} {unit})')
        a.plot(xs, y, 'o-', color=C_P, ms=5, lw=1.2, label='E(5 nm) - E(101 nm)  (near-field part)')
        a.axvline(0, color=C_GREY, ls=':'); a.grid(alpha=0.3)
        a.set_ylabel(f'{name} rel. oil side [{unit}]'); a.legend(fontsize=8, loc='best')
    all_x = sorted(a5)
    ax[1].set_xlabel('x_interface / nm   (tip over oil  <-  0  ->  tip over water)')
    ax[1].set_xlim(min(all_x) - 20, max(all_x) + 20)
    done = f'{len(xs)} of {len(all_x)} positions so far' if len(xs) < len(all_x) else 'all positions'
    fig.suptitle(f'Height difference E(5 nm) - E(101 nm): cancels the height-independent far-field drift, keeps the near field\n'
                 f'({done}; grey band = point-to-point scatter on the oil side)')
    save(fig, 'fig5_height_difference.png')


# --------------------------------------------------------------------------- fig 6
def fit_line_vs_step(x, y):
    """
    Far-field baseline = quadratic in x (the drift is not exactly linear: the interface moves through
    the Gaussian beam profile).  Compare  baseline  with  baseline + b / (1 + exp(-(x - x0)/w)),
    the step restricted to be physical: centre within +-150 nm of the tip, 10-90 % width >= ~90 nm
    (w >= 20 nm) and <= ~900 nm.  Returns both fits and an F-test (3 extra parameters).
    """
    from scipy.optimize import curve_fit
    from scipy.stats import f as fdist
    xs = x/1000.0                                       # um, for conditioning
    base = np.polyfit(xs, y, 2); rss1 = np.sum((y - np.polyval(base, xs))**2)
    model = lambda x, c0, c1, c2, b, x0, w: c0 + c1*(x/1000) + c2*(x/1000)**2 + b/(1 + np.exp(-(x - x0)/w))
    best = None
    for x0 in (-100, 0, 100):
        for w in (25, 60, 150):
            for sign in (1, -1):
                try:
                    p, cov = curve_fit(model, x, y, p0=[base[2], base[1], base[0], sign*np.ptp(y)/4, x0, w],
                                       bounds=([-np.inf]*4 + [-150, 20], [np.inf]*4 + [150, 200]), maxfev=20000)
                except Exception:
                    continue
                rss = np.sum((y - model(x, *p))**2)
                if best is None or rss < best[0]:
                    best = (rss, p, cov)
    n = len(x)
    rss2, p, cov = best
    F = ((rss1 - rss2)/3)/(rss2/(n - 6))
    pval = 1 - fdist.cdf(F, 3, n - 6)
    err = np.sqrt(np.abs(np.diag(cov)))
    return {'base': base, 'rss_line': rss1, 'rss_step': rss2, 'p': p, 'err': err, 'F': F, 'p_value': pval,
            'model': model, 'noise': np.sqrt(rss2/(n - 6))}


def fig_wide(show=False):
    base, wide = load('linescan_h5.pkl'), load('linescan_h5_wide.pkl')
    if base is None:
        return
    recs = base['records'] + (wide['records'] if wide else [])
    recs = sorted({r['x_interface']: r for r in recs}.values(), key=lambda q: q['x_interface'])
    x = np.array([q['x_interface'] for q in recs])
    bad = x == -1000                       # oil under the apex meshed with ~1 um tetrahedra (fig 8 / 10)
    ref_i = np.argmin(abs(x + 700))       # reference: last well-meshed point on the oil side

    def scatter(a, y, c):
        a.plot(x[~bad], y[~bad], 'o', color=c, ms=4, label=f'simulation, gap 5 nm ({(~bad).sum()} positions)')
        if bad.any():
            a.plot(x[bad], y[bad], 'o', mfc='none', mec=c, ms=6, label='x = -1000: oil mesh too coarse (unreliable)')
        a.axvline(0, color=C_GREY, ls=':'); a.grid(alpha=0.3); a.legend(fontsize=7, loc='best')

    fig, ax = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    lines = []
    for col, (pol, comp, lab, c) in enumerate([('p_in', 1, 'p in / p out (near field active)', C_P),
                                               ('s_in', 0, 's in / s out (no near-field hot spot)', C_S)]):
        E = np.array([q[pol][comp] for q in recs]); ref = E[ref_i]
        for row, (y, unit, name) in enumerate([((np.abs(E)/abs(ref) - 1)*1e4, 'x1e-4', 'amplitude'),
                                               (np.angle(E/ref)*1e3, 'mrad', 'phase')]):
            scatter(ax[row, col], y, c)
            ax[row, col].set_ylabel(f'{name} rel. x = {x[ref_i]:.0f} nm [{unit}]')
            r = fit_line_vs_step(x[~bad], y[~bad])            # statistics only, not drawn
            pp, ee = r['p'], r['err']
            lines.append(f'{lab:40s} {name:9s}: drift+step vs drift F-test p = {r["p_value"]:.2e}; step {pp[3]:+.3g}+-{ee[3]:.2g} {unit}, '
                         f'centre {pp[4]:+.0f}+-{ee[4]:.0f} nm, 10-90 % {2*np.log(9)*pp[5]:.0f} nm, noise {r["noise"]:.3g} {unit}')
        ax[0, col].set_title(lab)
    for a in ax[1]:
        a.set_xlabel('x_interface / nm   (tip over oil  <-  0  ->  tip over water)')
    fig.suptitle('Raw backscattered light at a 5 nm gap across the water | oil interface (+-1 um)')
    save(fig, 'fig6_plateau_test.png')

    # total collected field, combining BOTH incident polarizations (per incidence the cross-polarized
    # part is only ~1e-4 of the main channel, so sqrt(|Es|^2 + |Ep|^2) alone equals the main channel)
    def comps(q):
        (Es_s, Ep_s), (Es_p, Ep_p) = q['s_in'], q['p_in']
        return Es_s, Ep_s, Es_p, Ep_p
    C = np.array([comps(q) for q in recs])
    unpol = np.sqrt(np.sum(np.abs(C)**2, axis=1)/2)                                      # incoherent: unpolarized in, all out
    pol45 = np.sqrt((np.abs(C[:, 0] + C[:, 2])**2 + np.abs(C[:, 1] + C[:, 3])**2)/2)      # coherent: 45 deg linear in, all out
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.4), sharex=True, constrained_layout=True)
    for a, (T, lab, c) in zip(ax, [(unpol, 'unpolarized illumination, polarization-blind detector', '#6a3d9a'),
                                   (pol45, '45 deg (s + p) illumination, polarization-blind detector', '#009E73')]):
        y = (T/T[ref_i] - 1)*1e4
        scatter(a, y, c)
        a.set(title=lab, ylabel=f'total |E| rel. x = {x[ref_i]:.0f} nm [x1e-4]',
              xlabel='x_interface / nm   (tip over oil  <-  0  ->  tip over water)')
    fig.suptitle('Total backscattered field: s and p incidence and both detected polarizations combined (gap 5 nm)\n'
                 'left: |E|tot = sqrt[(|Es,s|^2 + |Ep,s|^2 + |Es,p|^2 + |Ep,p|^2) / 2];  right: |E(s in) + E(p in)| / sqrt 2 summed over both detected components')
    save(fig, 'fig6b_total_E.png')
    for l in lines:
        print('  ' + l)
    # near field over pure oil vs pure water (fields saved by linescan_h5_wide)
    fo, fw = [os.path.join(RES, 'fields', f'linescan_h5_wide_x{v:+d}_g5.npz') for v in (-700, 700)]   # -1000 is mis-meshed
    if os.path.exists(fo) and os.path.exists(fw):
        fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
        out = {}
        for f, lab, c in ((fo, 'tip over oil (x_interface = -700)', C_S), (fw, 'tip over water (x_interface = +700)', C_P)):
            d = np.load(f); xl = d['slice_xz_X'][:, 0]*1e9; zl = d['slice_xz_Z'][0]*1e9
            A = np.linalg.norm(d['slice_xz_E'][1], axis=-1)
            k = np.argmin(abs(zl + 15)); i0 = np.argmin(abs(xl))
            ax[0].plot(xl, A[:, k], color=c, label=lab)
            m = zl < -5
            ax[1].semilogy(zl[m], A[i0, m], color=c, label=lab)
            out[lab] = (A[i0, k], np.trapz(A[i0, m]**2, zl[m]))
        (lo, (ao, io)), (lw, (aw, iw)) = out.items()
        ax[0].set(xlabel='x / nm', ylabel='|E| 10 nm below the SiN', title=f'lateral: |E| under apex water/oil = {aw/ao:.3f}')
        ax[1].set(xlabel='z / nm (liquid)', ylabel='|E| on the tip axis', title=f'depth: integral |E|^2 water/oil = {iw/io:.3f}')
        for a in ax:
            a.legend(fontsize=8); a.grid(alpha=0.3)
        fig.suptitle('Does the near field itself see the liquid? same tip, gap 5 nm, over pure oil vs pure water')
        save(fig, 'fig7_near_field_oil_vs_water.png')
        print(f'  near field under the apex, water / oil: |E| ratio {aw/ao:.4f}, depth-integrated |E|^2 ratio {iw/io:.4f}')


if __name__ == '__main__':
    fig_setup()
    rows = fig_near_field()
    if rows:
        for depth, wx, wy in rows:
            print(f'  near-field spot {abs(depth)} nm below the SiN: FWHM {wx:.0f} nm across, {wy:.0f} nm along the interface')
    fig_noise()
    fig_raw()
    fig_difference()
    fig_wide()
