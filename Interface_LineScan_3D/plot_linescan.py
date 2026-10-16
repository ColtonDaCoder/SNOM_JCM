"""
Analysis of the stages written by run_linescan.py (results/<stage>.pkl).

    python plot_linescan.py scan            # S_n amplitude / phase vs position, 10-90 % edge widths
    python plot_linescan.py zsweep          # E(z) and S_n from HEIGHTS vs the dense sweep
    python plot_linescan.py coarse_check    # S_n coarse vs fine mesh (needs zsweep too)
    python plot_linescan.py noise           # remeshing noise of S_n vs the edge contrast (needs scan)
    python plot_linescan.py test            # just print the cost of the test solve
    python plot_linescan.py converge        # gaps 1-6 with more refinement steps vs zsweep: is the noise gone?
    python plot_linescan.py linescan_h5     # raw signal vs interface position at a fixed 5 nm gap

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
     'linescan_h5': lambda: show_constant_height('linescan_h5')}.get(stage, lambda: show_scan(stage))()
