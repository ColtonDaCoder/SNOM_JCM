"""
Analysis of the stages written by run_linescan.py (results/<stage>.pkl).

    python plot_linescan.py scan            # S_n amplitude / phase vs position, 10-90 % edge widths
    python plot_linescan.py zsweep          # E(z) and S_n from HEIGHTS vs the dense sweep
    python plot_linescan.py coarse_check    # S_n coarse vs fine mesh (needs zsweep too)
    python plot_linescan.py noise           # remeshing noise of S_n vs the edge contrast (needs scan)
    python plot_linescan.py test            # just print the cost of the test solve
    python plot_linescan.py converge        # gaps 1-6 with more refinement steps vs zsweep: is the noise gone?
    python plot_linescan.py linescan_h5     # raw signal vs interface position at a fixed 5 nm gap
    python plot_linescan.py diff            # E(5 nm) - E(101 nm) vs position (needs linescan_h5 + linescan_h101)
    python plot_linescan.py diff_cap        # same for the oil-capped runs linescan_h5_oilcap + linescan_h101_oilcap
    python plot_linescan.py demod_test      # S_n of far field and local near field at x = -500 / 0 / +500

Demodulation: the tip height follows z(t) = MIN_GAP + A/2 (1 + cos 2 pi t) over one period,
E(z) is interpolated with a cubic spline through the simulated heights, and
S_n = integral_0^1 E(z(t)) exp(-2 pi i n t) dt.  n = 0 is the cycle-averaged field.
Channel: p in / p out (CHANNEL).
"""
import os
import sys
import pickle as pk
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNEL = ('p_in', 1)        # (incident pol, detected component: 0 = Es, 1 = Ep)
HARMONICS = [0, 1, 2, 3, 4]


def load(stage):
    with open(os.path.join(HERE, 'results', stage + '.pkl'), 'rb') as f:
        data = pk.load(f)
    if data['failures']:
        print(f'{stage}: {len(data["failures"])} failed solves, first:\n{data["failures"][0]["traceback"]}')
    return data


def field_table(data):
    """{x_interface: (gaps, E)} sorted by gap, for CHANNEL."""
    pol, comp = CHANNEL
    table = {}
    for r in data['records']:
        table.setdefault(r['x_interface'], []).append((r['gap'], r[pol][comp]))
    return {x: tuple(np.array(v) for v in zip(*sorted(pts))) for x, pts in sorted(table.items())}


def demodulate(gaps, E, settings, harmonics=HARMONICS, n_t=2000):
    gaps, E = np.real(gaps), np.asarray(E)
    t = np.linspace(0, 1, n_t, endpoint=False)
    z = settings['min_gap'] + settings['tap_amplitude']/2*(1 + np.cos(2*np.pi*t))
    if z.max() > gaps.max() + 1e-9 or z.min() < gaps.min() - 1e-9:
        raise ValueError(f'tapping range {z.min()}-{z.max()} nm not covered by heights {gaps.min()}-{gaps.max()}')
    Ez = CubicSpline(gaps, E.real)(z) + 1j*CubicSpline(gaps, E.imag)(z)
    return {n: np.mean(Ez*np.exp(-2j*np.pi*n*t)) for n in harmonics}


def edge_width(x, y, lo=0.1, hi=0.9):
    """10-90 % width of a step y(x), normalized between the first and last point."""
    y = np.asarray(y, float)
    f = (y - y[0])/(y[-1] - y[0])
    def cross(level):
        i = np.where(np.diff(np.sign(f - level)) != 0)[0]
        if len(i) == 0:
            return np.nan
        i = i[0]
        return x[i] + (level - f[i])*(x[i+1] - x[i])/(f[i+1] - f[i])
    return abs(cross(hi) - cross(lo))


def demod_scan(data):
    """x positions and S_n (complex) per harmonic for every complete height sweep."""
    s = data['settings']
    xs, S = [], {n: [] for n in HARMONICS}
    for x, (gaps, E) in field_table(data).items():
        try:
            d = demodulate(gaps, E, s)
        except ValueError:
            continue                        # height sweep at this position not finished yet
        xs.append(x)
        for n in HARMONICS:
            S[n].append(d[n])
    return np.array(xs), {n: np.array(v) for n, v in S.items()}


def show_scan(stage):
    data = load(stage)
    xs, S = demod_scan(data)
    s = data['settings']
    print(f'{stage}: {len(xs)} complete positions, {s["wvl"]*1e6:.2f} um, channel {CHANNEL}')
    fig, ax = plt.subplots(2, sharex=True, figsize=(7, 7))
    for n in HARMONICS:
        ref = S[n][-1]                      # largest x_interface = tip deepest on the water side
        amp = np.abs(S[n]/ref)
        phase = np.angle(S[n]/ref)
        w_amp, w_ph = edge_width(xs, amp), edge_width(xs, phase)
        print(f'  S{n}: oil/water amplitude {amp[0]:.4f}, phase {phase[0]:+.4f} rad; '
              f'10-90 % width amplitude {w_amp:.1f} nm, phase {w_ph:.1f} nm')
        ax[0].plot(xs, amp, '.-', label=f'S{n} ({w_amp:.0f} nm)')
        ax[1].plot(xs, phase, '.-', label=f'S{n} ({w_ph:.0f} nm)')
    ax[0].set(ylabel='|S_n| / |S_n(water)|', title=f'{stage}, {s["wvl"]*1e6:.2f} um; tip over oil <- -> tip over water')
    ax[1].set(xlabel='interface position x_interface / nm', ylabel='phase rel. water / rad')
    for a in ax:
        a.grid()
        a.legend(fontsize=8)
    plt.tight_layout()
    plt.show()


def show_constant_height(stage):
    """Raw collected field vs interface position at a single gap (no demodulation)."""
    data = load(stage)
    s = data['settings']
    table = field_table(data)
    xs = np.array(sorted(table))
    gap = float(table[xs[0]][0][0])
    fig, ax = plt.subplots(2, sharex=True, figsize=(7, 7))
    for pol, comp, label in [('p_in', 1, 'p in / p out'), ('s_in', 0, 's in / s out')]:
        E = np.array([[r[pol][comp] for r in data['records'] if r['x_interface'] == x][0] for x in xs])
        ref = E[-1]                                     # largest x_interface = tip deepest on the water side
        amp, ph = np.abs(E/ref), np.angle(E/ref)
        print(f'{stage} {label}: oil/water amplitude {amp[0]:.4f}, phase {ph[0]:+.4f} rad; '
              f'10-90 % width amplitude {edge_width(xs, amp):.1f} nm, phase {edge_width(xs, ph):.1f} nm')
        ax[0].plot(xs, amp, '.-', label=label)
        ax[1].plot(xs, ph, '.-', label=label)
    ax[0].set(ylabel='|E| / |E(water)|', title=f'{stage}: gap {gap:g} nm, {s["wvl"]*1e6:.2f} um (raw, not demodulated); '
                                               f'tip over oil <- -> tip over water')
    ax[1].set(xlabel='interface position x_interface / nm', ylabel='phase rel. water / rad')
    for a_ in ax:
        a_.grid()
        a_.legend(fontsize=8)
    plt.tight_layout()
    plt.show()


def show_difference(near='linescan_h5', far='linescan_h101'):
    """
    D(x) = E(5 nm) - E(101 nm) at every interface position: the far-field drift barely
    depends on tip height and cancels, the near-field part (strongly height dependent) stays.
    Fitted with a step (near-field edge) plus a small linear term.
    """
    from scipy.optimize import curve_fit
    dn, df = load(near), load(far)
    def by_x(data, pol, comp):
        return {r['x_interface']: r[pol][comp] for r in data['records']}
    model = lambda x, a, m, b, x0, w: a + m*x + b/(1 + np.exp(-(x - x0)/w))
    fig, ax = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    for col, (pol, comp, label) in enumerate([('p_in', 1, 'p in / p out'), ('s_in', 0, 's in / s out')]):
        En, Ef = by_x(dn, pol, comp), by_x(df, pol, comp)
        xs = np.array(sorted(set(En) & set(Ef)))
        if len(xs) < 3:
            print(f'{label}: only {len(xs)} positions with both heights so far'); continue
        D = np.array([En[x] - Ef[x] for x in xs])
        R = np.array([En[x] for x in xs])
        oil = xs <= -100
        ref = D[oil].mean() if oil.any() else D[0]
        rref = R[oil].mean() if oil.any() else R[0]
        series = [('amplitude', (np.abs(D)/abs(ref) - 1)*100, '%', (np.abs(R)/abs(rref) - 1)*100),
                  ('phase', np.angle(D/ref)*1e3, 'mrad', np.angle(R/rref)*1e3)]
        print(f'{label}: {len(xs)} positions; |E(5)-E(101)| on the oil side = {abs(ref):.3e} '
              f'({abs(ref)/abs(rref)*100:.3f} % of |E(5)|)')
        for row, (name, y, unit, raw) in enumerate(series):
            a_ = ax[row, col]
            a_.plot(xs, y, 'o-', ms=4, label=f'E(5) - E(101), {name}')
            a_.plot(xs, raw*(np.ptp(y)/np.ptp(raw) if np.ptp(raw) else 1), '.', color='gray', alpha=0.5,
                    label='raw E(5), rescaled to the same range (for shape only)')
            try:
                p0 = [0, 0, y[-1] - y[0] or 1e-3, 0, 20]
                p, cov = curve_fit(model, xs, y, p0=p0, maxfev=50000)
                e = np.sqrt(np.abs(np.diag(cov)))
                w, we = 2*np.log(9)*abs(p[4]), 2*np.log(9)*e[4]
                scatter = np.std(y - model(xs, *p))
                xx = np.linspace(xs.min(), xs.max(), 600)
                a_.plot(xx, model(xx, *p), '-', label=f'fit: step {p[2]:+.3g} {unit}, centre {p[3]:+.0f}$\pm${e[3]:.0f} nm, '
                                                        f'10-90% {w:.0f}$\pm${we:.0f} nm')
                print(f'   {name}: step {p[2]:+.3g}+-{e[2]:.2g} {unit}, centre {p[3]:+.0f}+-{e[3]:.0f} nm, '
                      f'10-90 % width {w:.0f}+-{we:.0f} nm, linear term {p[1]*100:+.3g} {unit}/100 nm, scatter {scatter:.3g} {unit}')
            except Exception as ex:
                print(f'   {name}: fit failed ({ex})')
            a_.set_ylabel(f'{name} rel. oil side [{unit}]')
            a_.axvline(0, color='gray', ls=':'); a_.grid(alpha=0.4); a_.legend(fontsize=7, loc='best')
        ax[0, col].set_title(f'{label}: E(5 nm) - E(101 nm)')
    for a_ in ax[1]:
        a_.set_xlabel('x_interface / nm   (tip over oil <- 0 -> tip over water)')
    plt.tight_layout()
    plt.show()


def show_difference_cap(near='linescan_h5_oilcap', far='linescan_h101_oilcap'):
    """
    E(5 nm) - E(101 nm) on the oil-capped mesh, points only (no fits drawn).  Printed: plateau levels
    (mean +- standard error for x <= -300 and x >= +300), their difference, and a step fit
    (constant + logistic, amplitude and phase) for the centre and 10-90 % width.
    """
    from scipy.optimize import curve_fit
    dn, df = load(near), load(far)
    fig, ax = plt.subplots(2, 2, figsize=(13, 7.5), sharex=True)
    for col, (pol, comp, label, c) in enumerate([('p_in', 1, 'p in / p out', '#0072B2'), ('s_in', 0, 's in / s out', '#D55E00')]):
        En = {r['x_interface']: r[pol][comp] for r in dn['records']}
        Ef = {r['x_interface']: r[pol][comp] for r in df['records']}
        xs = np.array(sorted(set(En) & set(Ef)))
        if len(xs) < 3:
            print(f'{label}: only {len(xs)} positions with both heights so far'); continue
        D = np.array([En[x] - Ef[x] for x in xs])
        oil, water = xs <= -300, xs >= 300
        ref = D[oil].mean() if oil.any() else D[0]
        print(f'{label}: {len(xs)} positions with both heights; |E(5) - E(101)| = {abs(ref):.3e} on the oil side')
        for row, (y, unit, name) in enumerate([((np.abs(D)/abs(ref) - 1)*100, '%', 'amplitude'), (np.angle(D/ref)*1e3, 'mrad', 'phase')]):
            a_ = ax[row, col]
            a_.plot(xs, y, 'o', color=c, ms=5)
            a_.axvline(0, color='grey', ls=':'); a_.grid(alpha=0.3)
            a_.set_ylabel(f'{name} of E(5) - E(101), rel. oil side [{unit}]')
            if oil.sum() > 1 and water.sum() > 1:
                mo, mw = y[oil].mean(), y[water].mean()
                so, sw = y[oil].std(ddof=1)/np.sqrt(oil.sum()), y[water].std(ddof=1)/np.sqrt(water.sum())
                print(f'   {name}: oil plateau {mo:+.2f} +- {so:.2f} {unit} ({oil.sum()} pts), water plateau {mw:+.2f} +- {sw:.2f} {unit} '
                      f'({water.sum()} pts), step {mw - mo:+.2f} +- {np.hypot(so, sw):.2f} {unit}')
                try:
                    st = lambda x, a, b, x0, w: a + b/(1 + np.exp(-(x - x0)/w))
                    p, cov = curve_fit(st, xs, y, p0=[mo, mw - mo, 0, 50], bounds=([-np.inf, -np.inf, -300, 10], [np.inf, np.inf, 300, 400]))
                    e = np.sqrt(np.abs(np.diag(cov)))
                    print(f'   {name}: step fit centre {p[2]:+.0f} +- {e[2]:.0f} nm, 10-90 % width {2*np.log(9)*p[3]:.0f} +- {2*np.log(9)*e[3]:.0f} nm')
                except Exception as ex:
                    print(f'   {name}: step fit failed ({ex})')
        ax[0, col].set_title(f'{label}: E(5 nm) - E(101 nm)')
    for a_ in ax[1]:
        a_.set_xlabel('x_interface / nm   (tip over oil  <-  0  ->  tip over water)')
    plt.tight_layout()
    plt.show()


def show_demod_test(stage='demod_test', extra=('linescan_h5_oilcap',), z_local=-15.0, n_mc=400):
    """
    Demodulation test at x = -500 / 0 / +500 (oil / edge / water).  Two observables per height:
      far field : backscattered E (p in / p out, s in / s out), as everywhere else
      local     : E_z on the tip axis at z = z_local (10 nm into the liquid), from the saved slices
    S_n (n = 1..4) from a cubic spline through E(gap) over the tapping cycle (min_gap ... min_gap + A).
    Error bars: Monte-Carlo with the rms residual of a smooth fit to E(gap) (polynomial in log gap)
    as the per-point noise -> shows whether oil / edge / water differ by more than the noise.
    """
    main = load(stage)
    sett = main['settings']
    recs = list(main['records'])
    for e in extra:
        try:
            recs += [r for r in load(e)['records'] if r['x_interface'] in (-500, 0, 500)]
        except FileNotFoundError:
            pass
    rng = np.random.default_rng(0)

    def local_field(r, stage_of):
        f = os.path.join(HERE, 'results', 'fields', f'{stage_of}_x{r["x_interface"]:+.0f}_g{r["gap"]:.0f}.npz')
        if not os.path.exists(f):
            return None
        d = np.load(f)
        X = d['slice_xz_X'][:, 0]*1e9; Z = d['slice_xz_Z'][0]*1e9
        Ez = d['slice_xz_E'][1][np.argmin(abs(X)), :, 2]
        return np.interp(z_local, Z, Ez.real) + 1j*np.interp(z_local, Z, Ez.imag)

    data = {}
    for r in recs:
        st = stage if r in main['records'] else extra[0]
        key = r['x_interface']
        data.setdefault(key, {})[r['gap']] = {'p': r['p_in'][1], 's': r['s_in'][0], 'local': local_field(r, st)}

    def demod_with_errors(gaps, E):
        S = demodulate(gaps, E, sett, HARMONICS)
        lg = np.log(gaps)
        res = []
        for part in (E.real, E.imag):
            c = np.polyfit(lg, part, min(3, len(gaps) - 2)); res.append(part - np.polyval(c, lg))
        sigma = np.sqrt(np.mean(np.concatenate(res)**2))
        draws = [demodulate(gaps, E + sigma/np.sqrt(2)*(rng.standard_normal(len(E)) + 1j*rng.standard_normal(len(E))), sett, HARMONICS)
                 for _ in range(n_mc)]
        err = {n: np.std([abs(d[n]) for d in draws]) for n in HARMONICS}
        perr = {n: np.std([np.angle(d[n]/S[n]) for d in draws]) for n in HARMONICS}
        return S, err, perr, sigma

    results = {}
    for obs in ('p', 's', 'local'):
        for x in sorted(data):
            pts = sorted((g, v[obs]) for g, v in data[x].items() if v[obs] is not None)
            if len(pts) < 5:
                continue
            g, E = np.array([p_[0] for p_ in pts], float), np.array([p_[1] for p_ in pts])
            try:
                results[(obs, x)] = demod_with_errors(g, E) + (len(g),)
            except ValueError as ex:
                print(f'{obs} x={x}: {ex}')
    names = {'p': 'far field, p in / p out', 's': 'far field, s in / s out', 'local': f'local E_z at z = {z_local:g} nm (p)'}
    fig, ax = plt.subplots(2, 3, figsize=(17, 8))
    for col, obs in enumerate(('p', 's', 'local')):
        if (obs, -500) not in results:
            continue
        S0, e0, pe0, sig0, n0 = results[(obs, -500)]
        print(f'\n{names[obs]} ({n0} heights at x = -500; per-point noise estimate {sig0:.2e}, |E| ~ {abs(data[-500][1.0][obs]) if 1.0 in data[-500] else float("nan"):.3g})')
        for k, x in enumerate((-500, 0, 500)):
            if (obs, x) not in results:
                continue
            S, e, pe, sig, nh = results[(obs, x)]
            amp = [(abs(S[n])/abs(S0[n]) - 1)*100 for n in HARMONICS[1:]]
            amp_err = [100*np.hypot(e[n]/abs(S[n]), e0[n]/abs(S0[n]))*abs(S[n])/abs(S0[n]) for n in HARMONICS[1:]]
            ph = [np.angle(S[n]/S0[n])*1e3 for n in HARMONICS[1:]]
            ph_err = [np.hypot(pe[n], pe0[n])*1e3 for n in HARMONICS[1:]]
            off = (k - 1)*0.12
            ax[0, col].errorbar(np.array(HARMONICS[1:]) + off, amp, yerr=amp_err, fmt='o', ms=6, capsize=3, label=f'x = {x:+d}')
            ax[1, col].errorbar(np.array(HARMONICS[1:]) + off, ph, yerr=ph_err, fmt='o', ms=6, capsize=3, label=f'x = {x:+d}')
            for n, a_, ae, p_, pe_ in zip(HARMONICS[1:], amp, amp_err, ph, ph_err):
                print(f'   x={x:+5d}  S{n}: |S| = {abs(S[n]):.3e} ({nh} heights), vs oil {a_:+7.2f} +- {ae:5.2f} %, phase {p_:+7.1f} +- {pe_:5.1f} mrad')
        ax[0, col].set(title=names[obs], ylabel='|S_n| rel. x = -500 (oil) [%]', xticks=HARMONICS[1:])
        ax[1, col].set(ylabel='phase of S_n rel. oil [mrad]', xlabel='harmonic n', xticks=HARMONICS[1:])
        for a_ in ax[:, col]:
            a_.axhline(0, color='grey', lw=0.8); a_.grid(alpha=0.3); a_.legend(fontsize=8)
    fig.suptitle(f'Demodulation test (tapping {sett["tap_amplitude"]} nm from {sett["min_gap"]} nm): oil (-500) / edge (0) / water (+500); '
                 'error bars = numerical-noise estimate')
    plt.tight_layout()
    fig.savefig(os.path.join(HERE, 'figures', 'fig13_demod_test.png'), dpi=110)
    plt.show()


def show_zsweep():
    data = load('zsweep')
    s = data['settings']
    (x, (gaps, E)), = field_table(data).items()
    sparse = np.isin(gaps, s['heights'])
    dense_S = demodulate(gaps, E, s)
    sparse_S = demodulate(gaps[sparse], E[sparse], s)
    print(f'zsweep at x_interface={x}: {len(gaps)} heights; S_n from HEIGHTS vs dense:')
    for n in HARMONICS:
        print(f'  S{n}: relative difference {abs(sparse_S[n]/dense_S[n] - 1):.2e}')
    fig, ax = plt.subplots(2, sharex=True)
    ax[0].plot(gaps, np.abs(E), '.-', label='dense')
    ax[0].plot(gaps[sparse], np.abs(E[sparse]), 'o', mfc='none', label='HEIGHTS')
    ax[1].plot(gaps, np.unwrap(np.angle(E)), '.-')
    ax[0].set(ylabel='|E| / a.u.', title='zsweep, ' + str(CHANNEL))
    ax[1].set(xlabel='gap / nm', ylabel='phase / rad')
    ax[0].legend()
    for a in ax:
        a.grid()
    plt.show()


def show_coarse_check():
    fine = field_table(load('zsweep'))
    coarse = field_table(load('coarse_check'))
    s = load('zsweep')['settings']
    for x, (gaps, E) in coarse.items():
        gf, Ef = fine[x]
        Sc, Sf = demodulate(gaps, E, s), demodulate(gf[np.isin(gf, gaps)], Ef[np.isin(gf, gaps)], s)
        print(f'x_interface={x}: coarse vs fine mesh')
        for n in HARMONICS:
            print(f'  S{n}: relative difference {abs(Sc[n]/Sf[n] - 1):.2e}, '
                  f'phase difference {np.angle(Sc[n]/Sf[n]):+.2e} rad')


def show_noise():
    noise = load('noise')
    xs_n, S_n = demod_scan(noise)
    xs, S = demod_scan(load('scan'))
    print(f'noise: interface at {xs_n} nm (far from the tip, physically ~identical)')
    for n in HARMONICS:
        spread = np.std(np.abs(S_n[n]))/np.mean(np.abs(S_n[n]))
        contrast = abs(abs(S[n][0]) - abs(S[n][-1]))/abs(S[n][-1]) if len(xs) else np.nan
        print(f'  S{n}: remeshing noise {spread:.2e} (relative), oil/water contrast {contrast:.2e}, '
              f'ratio {contrast/spread if spread else np.inf:.0f}')


def show_converge():
    """Gaps 1-6 nm with more refinement steps vs the 1-step zsweep at the same gaps."""
    data = load('converge')
    pol, comp = CHANNEL
    recs = sorted(data['records'], key=lambda r: r['gap'])
    ref = {}
    try:
        ref = {r['gap']: r[pol][comp] for r in load('zsweep')['records']}
    except FileNotFoundError:
        pass
    print(f'converge ({data["settings"]["mesh"]}): {CHANNEL}')
    print(' gap   |E|        arg      est.err FarField per level              PML quality (+X, level)   unknowns   | zsweep |E|')
    for r in recs:
        errs = ' '.join(f'L{l}:{e:.1e}' for l, e in r.get('est_error_FarField', []))
        z = ref.get(r['gap'])
        tail = f'| {abs(z):.4e}' if z is not None else ''
        print(f'{r["gap"]:4.0f}  {abs(r[pol][comp]):.4e}  {np.angle(r[pol][comp]):+.3f}   {errs:38s} '
              f'{r.get("pml_quality", {}).get("X")}   {r["costs"].get("Unknowns")}   ' + tail)
    E = np.array([r[pol][comp] for r in recs])
    if len(E) > 2:
        step = np.abs(np.diff(E))/np.abs(E[:-1])
        print(f'\npoint-to-point change |dE|/|E| between neighbouring gaps: median {np.median(step):.2%}, max {np.max(step):.2%}')
        if ref:
            Ez = np.array([ref[r['gap']] for r in recs if r['gap'] in ref])
            if len(Ez) > 2:
                sz = np.abs(np.diff(Ez))/np.abs(Ez[:-1])
                print(f'same gaps in zsweep (1 refinement step):            median {np.median(sz):.2%}, max {np.max(sz):.2%}')


def show_test():
    r = load('test')['records'][0]
    print({k: r[k] for k in ('x_interface', 'gap', 'wall_time_s', 'costs', 'n_directions', 'n_directions_total')})


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'scan'
    {'zsweep': show_zsweep, 'coarse_check': show_coarse_check, 'noise': show_noise,
     'test': show_test, 'converge': show_converge,
     'linescan_h5': lambda: show_constant_height('linescan_h5'),
     'diff': show_difference, 'diff_cap': show_difference_cap, 'demod_test': show_demod_test}.get(stage, lambda: show_scan(stage))()
