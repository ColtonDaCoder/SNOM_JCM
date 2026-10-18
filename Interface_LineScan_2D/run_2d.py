"""
2D (x-y cross-section, invariant along z) s-SNOM line scan of a Pt tip across a lateral
water | oil interface under a 5 nm SiN window -- the 2D counterpart of Interface_LineScan_3D.

Coordinates (JCM 2D convention): x lateral, y vertical (y = 0 is the SiN top surface),
z is the invariant direction.  The tip is the 3D tip profile extruded along z (a ridge with a
75 nm rounded apex and 30.14 deg flanks), so the numbers are not quantitatively those of a
conical tip, but solves take ~minutes and the mesh can be made fine enough that mesh noise
is negligible -> dense scans and full height sweeps for demodulation.

The tip stays at x = 0 and the interface is moved to x_interface (water for x < x_interface,
oil for x > x_interface), so x_interface < 0 means the tip is over oil (same as 3D).
s = E along z (perpendicular to the plane of incidence), p = E in the x-y plane.

    python run_2d.py --stage beamcheck      # incident beam only: direction, s/p, spot (seconds)
    python run_2d.py --stage meshcheck      # mesh only (JCMgeo, no license): element counts per position
    python run_2d.py --stage test           # 1 solve: does it run, cost, far-field sampling
    python run_2d.py --stage exportbench    # time small field exports on the test field bag (no solve)
    python run_2d.py --stage converge_fine      # 3 positions x 3 gaps, 'fine' mesh
    python run_2d.py --stage converge_veryfine  # the same 9 points on 'veryfine' -> mesh convergence
    python run_2d.py --stage scan_h5        # -1000 ... 1000 nm every 10 nm at a 5 nm gap (field slices saved every 100 nm)
    python run_2d.py --stage scan_wide      # -5000 ... 5000 nm every 250 nm at 5 and 101 nm (edge fringe / plateaus)
    python run_2d.py --stage scan_demod     # -1000 ... 1000 nm every 25 nm x 14 heights -> S2, S3
    python run_2d.py --stage scan_demod --part 2/4   # only every 4th point starting at the 2nd (parallel jobs)
    python run_2d.py --jcm                  # only write the .jcm files (JCMcontrol)

Per solve (results/<stage>[.partIofN].pkl): backscattered far field in the NA window for s and p
incidence, the near field on three lines (tip axis, 10 nm into the liquid, middle of the gap),
JCM's error estimates and costs.  Summary per solve in results/run_log.txt, JCM's console
output in results/jcm_<stage>.log.  Stages are resumable (finished points are skipped).
"""
import os
import sys
import time
import re
import json
import socket
import traceback
import pickle as pk
import numpy as np

sys.path.insert(0, os.path.join(os.environ['JCMROOT'], 'ThirdPartySupport', 'Python'))
import jcmwave

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
WORK = os.path.join(HERE, 'work')

# ----------------------------------------------------------------------------
# Instrument (same as 3D)
# ----------------------------------------------------------------------------
THETA = 60              # deg, incidence angle from the surface normal
NA = 0.4                # collection NA around the backscatter direction
TAP_AMPLITUDE = 100     # nm
MIN_GAP = 1             # nm
HEIGHTS = [1, 2, 3, 4, 6, 8, 10, 14, 20, 30, 45, 60, 80, 101]

X_H5 = list(range(-1000, 1001, 10))
X_DEMOD = list(range(-1000, 1001, 25))
X_WIDE = list(range(-5000, 5001, 250))
X_CONV = [-500, 0, 500]

STAGES = {
    'test':              dict(mesh='fine',     wvl=6.1, x=[0], gaps=[5], save_fields=True),
    'converge_fine':     dict(mesh='fine',     wvl=6.1, x=X_CONV, gaps=[1, 5, 101]),
    'converge_veryfine': dict(mesh='veryfine', wvl=6.1, x=X_CONV, gaps=[1, 5, 101]),
    'scan_h5':           dict(mesh='fine',     wvl=6.1, x=X_H5, gaps=[5], save_fields=list(range(-1000, 1001, 100))),
    'scan_wide':         dict(mesh='fine',     wvl=6.1, x=X_WIDE, gaps=[5, 101]),
    'scan_demod':        dict(mesh='fine',     wvl=6.1, x=X_DEMOD, gaps=HEIGHTS),
}
MIN_DIRECTIONS = 20     # far-field directions inside the NA window; fewer -> raise ft_refinements

MATERIAL_FILES = {
    'water': 'water_HaleQuerry.csv',   # Hale & Querry 1973
    'oil':   'octane_Myers.csv',       # n-octane (Myers 2018) as OTS stand-in
    'pt':    'Pt_Rakic_BB.csv',        # Rakic 1998, Brendel-Bormann fit
    'SN':    'SiN_Kischkat.csv',       # Kischkat 2012, sputtered SiNx
}

# ----------------------------------------------------------------------------
# Geometry and mesh (nm); see layout.jcmt
# ----------------------------------------------------------------------------
GEOMETRY = {
    't_SiN': 5,
    'liquid_depth': 3000,       # water below the SiN, into the bottom boundary
    'oil_depth': 1000,          # depth of the oil block
    'patch_margin': 1000,       # oil block stops this far from the side boundary (layered exterior)
    'cd_width': 30000,          # +-15 um: the tip top (+-7.6 um) and the beam footprint fit well inside
    'tip_radius': 75,
    'tip_half_angle': 30.14,
    'tip_length': 12940,
    'air_above_tip': 500,
    'tip_curv': 3,              # curved elements on the tip surface (set to 1 to mesh locally: curving needs the license)
}

# Mesh presets: geometry identical, only the global element size / degree / adaptive steps change.
# No local refinement regions: the start mesh grades smoothly from the geometry (apex rounding,
# 5 nm SiN) and HAdaptive refines where JCM's error estimate asks for it.
MESH = {
    'fine':     {'max_side': 600,  'fe_degree': 4, 'max_steps': 5, 'ft_refinements': 5},
    'veryfine': {'max_side': 300,  'fe_degree': 5, 'max_steps': 7, 'ft_refinements': 5},
    'coarse':   {'max_side': 1500, 'fe_degree': 3, 'max_steps': 2, 'ft_refinements': 5},
}


def nk_permittivity(path, wvl):
    """eps = (n + ik)^2 at wavelength wvl (m) from a wavelength_um,n,k csv."""
    with open(path) as f:
        rows = [line.split(',') for line in f if line[0].isdigit()]
    d = np.array(rows, float)
    w_um = wvl*1e6
    if not d[0, 0] <= w_um <= d[-1, 0]:
        raise ValueError(f'{w_um} um outside the data range of {path}')
    eps = (np.interp(w_um, d[:, 0], d[:, 1]) + 1j*np.interp(w_um, d[:, 0], d[:, 2]))**2
    return eps.real, eps.imag


def material_keys(wvl):
    keys = {}
    for name, fname in MATERIAL_FILES.items():
        keys[name + '_eps1'], keys[name + '_eps2'] = nk_permittivity(os.path.join(HERE, 'optical_data', fname), wvl)
    return keys


BEAM_FILE = os.path.join(RESULTS, 'beamcheck.json')


def beam_convention():
    if not os.path.exists(BEAM_FILE):
        raise SystemExit('no results/beamcheck.json: run  python run_2d.py --stage beamcheck  first')
    with open(BEAM_FILE) as f:
        b = json.load(f)
    return {'beam_phi': b['beam_phi'], 'sp_s': b['sp_s'], 'sp_p': b['sp_p']}


def source_keys(wvl, theta_deg, beam=None):
    keys = {'wvl': wvl, 'theta': float(theta_deg), 'waist': wvl/(np.pi*NA), 'beam_na': NA}
    b = beam or beam_convention()
    keys.update(beam_phi=float(b['beam_phi']), sp_s=np.array(b['sp_s'], float), sp_p=np.array(b['sp_p'], float))
    return keys


def solve(project, keys, workdir, logname):
    """jcmwave.solve in its own working directory; JCM's console output appended to results/<logname>."""
    os.makedirs(os.path.join(workdir, 'project_results'), exist_ok=True)
    jcm_log = os.path.join(workdir, 'jcm_console.log')
    try:
        return jcmwave.solve(os.path.join(HERE, project), keys=keys, logfile=jcm_log, working_dir=workdir)
    finally:
        text = open(jcm_log, errors='replace').read() if os.path.exists(jcm_log) else ''
        with open(os.path.join(RESULTS, logname), 'a') as f:
            f.write(f'\n######## x_interface={keys.get("x_interface")} gap={keys.get("gap")} '
                    f'({time.strftime("%Y-%m-%d %H:%M:%S")})\n' + text)
        solve.last_log = text


def run_beamcheck():
    """
    Incident beam only, beam_phi = 0 and 180: find the setting travelling along +x, which SP is
    s (E along z) and check the spot position.  Writes results/beamcheck.json.
    """
    os.makedirs(RESULTS, exist_ok=True)
    wvl = 6.1e-6
    k0 = 2*np.pi/wvl
    report = {'wvl': wvl, 'theta': THETA, 'waist': wvl/(np.pi*NA), 'cases': {}}
    for phi in (0.0, 180.0):
        keys = dict(GEOMETRY, **MESH['coarse'], x_interface=0.0, gap=float(MIN_GAP))
        keys.update(material_keys(wvl))
        keys.update(source_keys(wvl, THETA, {'beam_phi': phi, 'sp_s': [1, 0], 'sp_p': [0, 1]}))
        wd = os.path.join(WORK, 'beamcheck')
        solve('beamcheck.jcmp', keys, wd, 'jcm_beamcheck.log')
        lx = jcmwave.loadcartesianfields(os.path.join(wd, 'project_results', 'beamcheck_x.jcm'))
        x = np.ravel(lx['X'])*1e9
        for src, sp in ((0, [1, 0]), (1, [0, 1])):
            E = np.reshape(lx['field'][src], (-1, 3))
            I = np.sum(np.abs(E)**2, axis=1)
            c = int(np.argmax(np.sum(np.abs(E)**2, axis=0)))
            lit = I > 0.3*I.max()
            kx = np.polyfit(x[lit]*1e-9, np.unwrap(np.angle(E[lit, c])), 1)[0]
            ipk = int(np.argmax(I))
            report['cases'][f'phi{phi:g}_SP{sp}'] = {
                'beam_phi': phi, 'SP': sp, 'kx_over_k0': float(kx/k0),
                'expected_abs_kx_over_k0': float(np.sin(np.deg2rad(THETA))),
                'peak_x_nm': float(x[ipk]), 'Ez_fraction_at_peak': float(np.abs(E[ipk, 2])**2/I[ipk]),
                'dominant_component': 'xyz'[c]}
    cases = report['cases']
    for name, cse in cases.items():
        print(f"beamcheck {name}: kx/k0 = {cse['kx_over_k0']:+.3f}, spot at x = {cse['peak_x_nm']:+.0f} nm, "
              f"|Ez|^2 fraction {cse['Ez_fraction_at_peak']:.2f}, dominant {cse['dominant_component']}", flush=True)
    good = [c for c in cases.values() if c['kx_over_k0'] > 0]
    problems = []
    if len(good) != 2 or len({c['beam_phi'] for c in good}) != 1:
        problems.append('could not find a single beam_phi for which both sources travel along +x')
    else:
        report['beam_phi'] = good[0]['beam_phi']
        s_like = [c for c in good if c['Ez_fraction_at_peak'] > 0.9]
        p_like = [c for c in good if c['Ez_fraction_at_peak'] < 0.1]
        if len(s_like) != 1 or len(p_like) != 1:
            problems.append('could not identify s (E along z) and p sources from the SP settings')
        else:
            report['sp_s'], report['sp_p'] = s_like[0]['SP'], p_like[0]['SP']
        for c in good:
            if abs(c['kx_over_k0'] - c['expected_abs_kx_over_k0']) > 0.1:
                problems.append(f"kx/k0 = {c['kx_over_k0']:.3f}, expected {c['expected_abs_kx_over_k0']:.3f}")
            if abs(c['peak_x_nm']) > 2500:
                problems.append(f"spot not centred on the focus: x {c['peak_x_nm']:.0f} nm")
    report['problems'] = problems
    with open(BEAM_FILE if not problems else BEAM_FILE.replace('.json', '_FAILED.json'), 'w') as f:
        json.dump(report, f, indent=2)
    if problems:
        raise SystemExit('beam check failed: ' + '; '.join(problems) + ' (details in results/beamcheck_FAILED.json)')
    print(f"beam check OK: beam_phi = {report['beam_phi']:g}, SP s = {report['sp_s']}, SP p = {report['sp_p']}", flush=True)


MESHCHECK_X = list(range(-1000, 1001, 100))
MESHCHECK_GAPS = [1, 5, 101]


def run_meshcheck(mesh='fine'):
    """Mesh only (no license needed): triangle / point counts per position -> results/meshcheck.json."""
    os.makedirs(RESULTS, exist_ok=True)
    out = {}
    for gap in MESHCHECK_GAPS:
        for x in MESHCHECK_X:
            wd = os.path.join(WORK, 'meshcheck')
            os.makedirs(wd, exist_ok=True)
            keys = dict(GEOMETRY, **MESH[mesh], x_interface=float(x), gap=float(gap))
            jcmwave.jcmt2jcm(os.path.join(HERE, 'layout.jcmt'), keys, outputfile=os.path.join(wd, 'layout.jcm'))
            t0 = time.time()
            try:
                jcmwave.geo(wd)
                head = open(os.path.join(wd, 'grid.jcm'), errors='replace').read(20000)
                st = {k: int(v) for k, v in re.findall(r'<I>(N\w+)=(\d+)', head)}
            except Exception as ex:
                st = {'error': repr(ex)}
            st['mesh_time_s'] = time.time() - t0
            out[f'x{x:+d}_g{gap}'] = st
            print(f'x{x:+5d} g{gap:3d}: {st}', flush=True)
    with open(os.path.join(RESULTS, 'meshcheck.json'), 'w') as f:
        json.dump({'mesh': mesh, 'geometry': dict(GEOMETRY, **MESH[mesh]), 'meshes': out}, f, indent=1)


def run_exportbench():
    """
    Time JCM's Cartesian field export on the field bag already written by the test stage
    (work/test/project_results/fieldbag.jcm, no re-solve): which kind of point set is slow?
    Each variant is its own post-process-only project; times -> results/exportbench.json.
    """
    fb = os.path.join(WORK, 'test', 'project_results', 'fieldbag.jcm')
    if not os.path.exists(fb):
        raise SystemExit(f'{fb} not found: the test stage must have finished its solve first')
    gap = STAGES['test']['gaps'][0]
    t = GEOMETRY['t_SiN']
    ax_uneven = np.concatenate([np.arange(-50.0, -t, 2.5), np.linspace(-t, 0, 6)[1:-1], (np.arange(10) + 0.5)/10*gap])
    variants = {
        'axis_20_uneven':    ([0.0], ax_uneven[::max(1, len(ax_uneven)//20)][:20]),
        'axis_20_even_liq':  ([0.0], np.linspace(-100, -10, 20)),
        'air_20_away':       ([3000.0], np.linspace(500, 600, 20)),
        'liquid_20_far':     (np.linspace(-1000, -800, 20), [-t - 10.0]),
        'liquid_20_under':   (np.linspace(-50, 50, 20), [-t - 10.0]),
        'block_5x5_far_air': (np.linspace(4000, 4100, 5), np.linspace(2000, 2100, 5)),
        'single_point_gap':  ([0.0], [gap/2]),
        'single_point_far':  ([5000.0], [3000.0]),
    }
    bd = os.path.join(WORK, 'exportbench')
    os.makedirs(os.path.join(bd, 'project_results'), exist_ok=True)
    out = {}
    for name, (xs, ys) in variants.items():
        fmt = lambda v: '[' + ' '.join('%.6e' % (1e-9*float(a)) for a in v) + ']'
        with open(os.path.join(bd, 'bench.jcmp'), 'w') as f:
            f.write('PostProcess {\n  ExportFields {\n    FieldBagPath = "%s"\n'
                    '    OutputFileName = "project_results/bench.jcm"\n    OutputQuantity = ElectricFieldStrength\n'
                    '    Cartesian {\n      GridPointsX = %s\n      GridPointsY = %s\n    }\n  }\n}\n'
                    % (fb.replace('\\', '/'), fmt(xs), fmt(ys)))
        t0 = time.time()
        try:
            jcmwave.solve(os.path.join(bd, 'bench.jcmp'), logfile=os.path.join(bd, 'bench.log'), working_dir=bd)
            err = None
        except Exception as ex:
            err = repr(ex)
        dt = time.time() - t0
        n = len(xs)*len(ys)
        out[name] = {'points': n, 'seconds': dt, 'seconds_per_point': dt/n, 'error': err}
        print(f'{name:20s} {n:4d} points  {dt:8.1f} s  ({dt/n:.2f} s/point)' + (f'  ERROR {err}' if err else ''), flush=True)
        with open(os.path.join(RESULTS, 'exportbench.json'), 'w') as f:
            json.dump(out, f, indent=1)


def scan_keys(mesh, wvl):
    keys = dict(GEOMETRY, **MESH[mesh])
    keys.update(material_keys(wvl))
    keys.update(source_keys(wvl, THETA))
    return keys


def collect_backscatter(ft, theta_deg, na):
    """
    Far field of the scattered light in the NA window around the backscatter direction
    (-sin theta, cos theta) in the x-y plane, summed coherently.  s part: E_z; p part: E along
    p_hat = z x k_hat (in-plane, perpendicular to k).
    Returns {'s_in': [Es, Ep], 'p_in': [Es, Ep]} plus the raw K and E inside the window.
    """
    th = np.deg2rad(theta_deg)
    back_dir = np.array([-np.sin(th), np.cos(th), 0.0])
    K = np.real(np.array(ft['K']))
    k_hat = K/np.linalg.norm(K, axis=1)[:, None]
    inside = k_hat @ back_dir >= np.cos(np.arcsin(na))
    s_hat = np.tile([0.0, 0.0, 1.0], (int(inside.sum()), 1))
    p_hat = np.cross(s_hat, k_hat[inside])
    out = {'n_directions': int(inside.sum()), 'n_directions_total': len(K), 'K_cone': K[inside]}
    for name, src in (('s_in', 0), ('p_in', 1)):
        E = np.array(ft['ElectricFieldStrength'][src])
        out[name] = [np.sum(E[inside]*s_hat), np.sum(E[inside]*p_hat)]
        out['E_cone_' + name] = E[inside]
        out['E_total_power_' + name] = float(np.sum(np.abs(E)**2))
    return out


def costs_summary(costs):
    keep = ('Level', 'Unknowns', 'TotalTime', 'CpuTime', 'TotalMemory_GB', 'MaxNodeTotalMemory_GB')
    try:
        costs = costs.get('computational_costs', costs)
        return {k: np.array(costs[k]).tolist() for k in keep if k in costs}
    except Exception as e:
        return {'error': repr(e)}


def parse_jcm_log(text):
    """JCM's own accuracy estimates from its console output (last refinement level)."""
    out = {}
    lines = text.splitlines()
    for name in ('FarField', 'NearField'):
        heads = [i for i, l in enumerate(lines) if f'rel. error ({name})' in l]
        if not heads:
            continue
        levels = []
        for l in lines[heads[-1] + 1:]:
            m = re.match(r'\s*(\d+)\s+([\d.eE+-]+)', l)
            if m:
                levels.append((int(m.group(1)), float(m.group(2))))
            elif levels or not (l.strip() == '' or 'level' in l or l.strip().startswith(('-', '-/-'))):
                break
        out['est_error_' + name] = levels
    blocks = text.split('A posteriori exterior domain quality check:')
    if len(blocks) > 1:
        out['pml_quality'] = {c: (float(q), int(lv)) for c, q, lv in
                              re.findall(r'Compartment\s+"(-?[XYZ])":\s*([\d.eE+-]+)\s*\(thickness level=(\d+)\)', blocks[-1])}
    return out


def load_line(wd, name):
    c = jcmwave.loadcartesianfields(os.path.join(wd, 'project_results', name + '.jcm'))
    E = np.stack([np.reshape(np.asarray(f), (-1, 3)) for f in c['field']]).astype(np.complex64)   # [source, point, xyz]
    return np.ravel(c['X'])*1e9, np.ravel(c['Y'])*1e9, E


def near_field(wd, gap):
    """Local near-field observables from the exported lines (nm; components x, y (vertical), z)."""
    _, ya, Ea = load_line(wd, 'line_axis')
    xl, _, El = load_line(wd, 'line_liquid')
    xg, _, Eg = load_line(wd, 'line_gap')
    in_gap = (ya > 0) & (ya < gap)
    dy = gap/np.count_nonzero(in_gap)                     # midpoint rule, 40 equal cells
    out = {'axis_y': ya.astype(np.float32), 'axis_E': Ea,
           'liquid_x': xl.astype(np.float32), 'liquid_E': El,
           'gapline_x': xg.astype(np.float32), 'gapline_E': Eg,
           # integral of E over the gap on the tip axis, from the SiN surface to the apex (nm * V/m)
           'gap_integral': Ea[:, in_gap, :].sum(axis=1)*dy}
    for depth in (10, 30, 100):                            # below the SiN, on the tip axis
        i = int(np.argmin(np.abs(ya - (-GEOMETRY['t_SiN'] - depth))))
        out[f'E_liquid_{depth}nm'] = Ea[:, i, :]
    return out


def save_slice(wd, path):
    c = jcmwave.loadcartesianfields(os.path.join(wd, 'project_results', 'slice_xy.jcm'))
    np.savez_compressed(path, X=np.asarray(c['X'], np.float32), Y=np.asarray(c['Y'], np.float32),
                        E=np.stack([np.asarray(f, np.complex64) for f in c['field']]))


def run_point(base_keys, x, gap, stage, wd, save_fields=False):
    keys = dict(base_keys, x_interface=x, gap=gap, save_slice=int(bool(save_fields)))
    t0 = time.time()
    results = solve('project.jcmp', keys, wd, f'jcm_{stage}.log')
    record = {'x_interface': x, 'gap': gap, 'wall_time_s': time.time() - t0,
              'costs': costs_summary(results[0]), 'finished': time.strftime('%Y-%m-%d %H:%M:%S')}
    record.update(collect_backscatter(results[1], THETA, NA))
    record.update(near_field(wd, gap))
    record.update(parse_jcm_log(solve.last_log))
    if save_fields:
        os.makedirs(os.path.join(RESULTS, 'fields'), exist_ok=True)
        fname = os.path.join(RESULTS, 'fields', f'{stage}_x{x:+.0f}_g{gap:.0f}.npz')
        save_slice(wd, fname)
        record['fields_file'] = os.path.relpath(fname, HERE)
    return record


def log(msg):
    print(msg, flush=True)
    with open(os.path.join(RESULTS, 'run_log.txt'), 'a') as f:
        f.write(msg + '\n')


def configure_resources():
    n = os.environ.get('SLURM_CPUS_ON_NODE') or os.environ.get('SLURM_NTASKS_PER_NODE')
    if n:
        jcmwave.set_num_threads(int(n))
    mem_mb = os.environ.get('SLURM_MEM_PER_NODE')
    if mem_mb:
        jcmwave.set_memory_limit(int(0.9*int(mem_mb)))
    return {'threads': n, 'mem_limit_mb': mem_mb}


def run_stage(name, part=None):
    """part = (i, n): only every n-th point starting at the i-th (1-based) -> results/<name>.part<i>of<n>.pkl"""
    cfg = STAGES[name]
    os.makedirs(RESULTS, exist_ok=True)
    tag = name if part is None else f'{name}.part{part[0]}of{part[1]}'
    out_file = os.path.join(RESULTS, tag + '.pkl')
    wd = os.path.join(WORK, tag)
    if os.path.exists(out_file):
        with open(out_file, 'rb') as f:
            data = pk.load(f)
    else:
        data = {'records': [], 'failures': []}
    wvl = cfg['wvl']*1e-6
    old = data.get('settings')
    source = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in source_keys(wvl, THETA).items()}
    if data['records'] and old and (old['geometry'] != dict(GEOMETRY, **MESH[cfg['mesh']])
                                    or old['wvl'] != wvl or old['materials'] != material_keys(wvl)
                                    or old.get('source') != source):
        raise SystemExit(f'{out_file} was made with different settings; move it away (e.g. results/old/) first')
    data['settings'] = {
        'stage': name, 'part': part, 'mesh': cfg['mesh'], 'wvl': wvl, 'theta': THETA, 'NA': NA,
        'tap_amplitude': TAP_AMPLITUDE, 'min_gap': MIN_GAP, 'heights': HEIGHTS,
        'geometry': dict(GEOMETRY, **MESH[cfg['mesh']]),
        'material_files': MATERIAL_FILES, 'materials': material_keys(wvl), 'source': source,
        'host': socket.gethostname(), 'resources': configure_resources(),
        'slurm_job': os.environ.get('SLURM_JOB_ID'),
    }
    base_keys = scan_keys(cfg['mesh'], wvl)

    all_jobs = [(float(x), float(g)) for x in cfg['x'] for g in cfg['gaps']]
    if part is not None:
        all_jobs = all_jobs[part[0] - 1::part[1]]
    done = {(r['x_interface'], r['gap']) for r in data['records']}
    jobs = [j for j in all_jobs if j not in done]
    log(f'=== stage {tag} on {socket.gethostname()} ({time.strftime("%Y-%m-%d %H:%M:%S")}): '
        f'{len(jobs)} solves to run, {len(done)} already done, {cfg["mesh"]} mesh, {cfg["wvl"]} um')
    sf = cfg.get('save_fields', False)

    consecutive_failures = 0
    for n, (x, gap) in enumerate(jobs):
        save = (x in sf) if isinstance(sf, list) else sf
        try:
            rec = run_point(base_keys, x, gap, name, wd, save)
        except Exception:
            tb = traceback.format_exc()
            data['failures'].append({'x_interface': x, 'gap': gap, 'traceback': tb})
            with open(out_file, 'wb') as f:
                pk.dump(data, f)
            log(f'[{tag} {n+1}/{len(jobs)}] x={x:+.0f} gap={gap:g} FAILED\n{tb}')
            consecutive_failures += 1
            if name == 'test' or consecutive_failures >= 3:
                raise
            continue
        consecutive_failures = 0
        data['records'].append(rec)
        with open(out_file, 'wb') as f:
            pk.dump(data, f)
        c = rec['costs']
        gi = rec['gap_integral'][1, 1]
        log(f'[{tag} {n+1}/{len(jobs)}] x={x:+.0f} nm gap={gap:g} nm  '
            f'|Ep|(p_in)={abs(rec["p_in"][1]):.5e} arg={np.angle(rec["p_in"][1]):+.4f}  '
            f'|gap int Ey|(p_in)={abs(gi):.4e} arg={np.angle(gi):+.4f}  {rec["n_directions"]} dirs  '
            f'unknowns={c.get("Unknowns")}  {rec["wall_time_s"]:.0f} s  est.err FarField={rec.get("est_error_FarField")}')
        if rec['n_directions'] < MIN_DIRECTIONS:
            raise RuntimeError(f'only {rec["n_directions"]} far-field directions in the NA window '
                               f'(< {MIN_DIRECTIONS}); increase ft_refinements')


def write_jcm(mesh='fine', wvl_um=6.1, x_interface=0.0, gap=5.0):
    """Write layout/materials/sources/project .jcm for one point into this folder (JCMcontrol)."""
    os.chdir(HERE)
    beam = None if os.path.exists(BEAM_FILE) else {'beam_phi': 0, 'sp_s': [1, 0], 'sp_p': [0, 1]}
    if beam:
        print('no results/beamcheck.json yet: sources.jcm written with beam_phi = 0, SP = [1 0] / [0 1] (unchecked)')
    keys = dict(GEOMETRY, **MESH[mesh], x_interface=x_interface, gap=gap, save_slice=0)
    keys.update(material_keys(wvl_um*1e-6))
    keys.update(source_keys(wvl_um*1e-6, THETA, beam))
    for name in ('layout.jcmt', 'materials.jcmt', 'sources.jcmt', 'project.jcmpt'):
        jcmwave.jcmt2jcm(name, keys)
        print(f'wrote {name[:-1]}  ({mesh} mesh, x_interface={x_interface} nm, gap={gap} nm)')


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


if __name__ == '__main__':
    if '--jcm' in sys.argv:
        write_jcm(arg('--mesh', 'fine'), x_interface=float(arg('--x', 0)), gap=float(arg('--gap', 5)))
    elif '--stage' in sys.argv:
        stage = arg('--stage')
        p = arg('--part')
        part = tuple(int(v) for v in p.split('/')) if p else None
        if stage == 'beamcheck':
            run_beamcheck()
        elif stage == 'exportbench':
            run_exportbench()
        elif stage == 'meshcheck':
            run_meshcheck(arg('--mesh', 'fine'))
        else:
            run_stage(stage, part)
    else:
        print(__doc__)
