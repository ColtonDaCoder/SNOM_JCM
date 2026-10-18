"""
3D s-SNOM line scan of a Pt tip across a lateral water | oil interface under a SiN window.

The tip stays at x = 0 and the interface is moved to x_interface (water for x < x_interface),
so x_interface < 0 means the tip is over oil.  Every (x_interface, gap) pair is one 3D solve;
both incident polarizations (s, p) come out of the same solve.  The height sweep at each
position is turned into demodulated harmonics S_n afterwards (plot_linescan.py), with
TAP_AMPLITUDE = 100 nm and the closest approach MIN_GAP = 1 nm.

The work is split into stages (see STAGES); each stage writes its own results file and can
be stopped and restarted (finished points are skipped):

    python run_linescan.py --stage beamcheck      # incident Gaussian beam only: direction, s/p, spot position
    python run_linescan.py --stage converge       # gaps 1-6 nm with 3 refinement steps: is the noise gone?
    python run_linescan.py --stage test           # 1 coarse solve: does it run, cost, far-field sampling
    python run_linescan.py --stage zsweep         # dense height sweep at one position (validates HEIGHTS)
    python run_linescan.py --stage coarse_check   # HEIGHTS on the coarse mesh (mesh convergence)
    python run_linescan.py --stage noise          # interface far away, moved a few nm (remeshing noise)
    python run_linescan.py --stage linescan_h5    # raw signal across the interface at a fixed 5 nm gap
    python run_linescan.py --stage linescan_h101  # same positions at 101 nm; with linescan_h5 -> E(5) - E(101)
    python run_linescan.py --stage linescan_h5_wide  # 5 nm scan extended to +-1 um (plateaus), saves fields
    python run_linescan.py --stage scan           # the line scan at 6.1 um
    python run_linescan.py --stage scan_5.5um     # the same line scan at 5.5 um
    python run_linescan.py --jcm [--coarse]       # only write the .jcm files for JCMcontrol

Everything needed for the analysis is stored per solve in results/<stage>.pkl
(see run_point), including JCM's own error estimates; a one-line summary of every solve
goes to results/run_log.txt and JCM's full console output to results/jcm_<stage>.log.
Stages with save_fields=True also store two vertical field slices through the tip axis
in results/fields/<stage>_x<x>_g<gap>.npz (plot with plot_fields.py).
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

# jcmwave from the JCMsuite installation (works from any folder, also on the cluster)
sys.path.insert(0, os.path.join(os.environ['JCMROOT'], 'ThirdPartySupport', 'Python'))
import jcmwave

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')

# ----------------------------------------------------------------------------
# Instrument
# ----------------------------------------------------------------------------
THETA = 60              # deg, incidence angle from the surface normal
NA = 0.4                # collection NA around the backscatter direction
TAP_AMPLITUDE = 100     # nm, tapping amplitude (used in the analysis)
MIN_GAP = 1             # nm, closest tip - SiN distance during the tapping cycle

# Heights for demodulation: MIN_GAP ... MIN_GAP + TAP_AMPLITUDE, dense near contact
# where the near field changes fastest.
HEIGHTS = [1, 2, 3, 4, 6, 8, 10, 14, 20, 30, 45, 60, 80, 101]
# Dense sweep used once to check that HEIGHTS is fine enough (contains all of HEIGHTS)
HEIGHTS_DENSE = sorted(set(list(range(1, 11)) + list(range(12, 31, 2)) + list(range(35, 101, 5)) + [101]))

# Interface positions (nm): 5 nm steps within +-50 nm, sparser out to +-300 nm
X_SCAN = sorted(set([-300, -200, -150, -100, -75] + list(range(-50, 51, 5)) + [75, 100, 150, 200, 300]))

STAGES = {
    'converge':     dict(mesh='coarse_3steps', wvl=6.1, x=[0], gaps=[1, 2, 3, 4, 5, 6], save_fields=True),
    'test':         dict(mesh='coarse', wvl=6.1, x=[0],                    gaps=[MIN_GAP], save_fields=True),
    # exploratory: raw signal across the interface at a fixed 5 nm gap (no demodulation;
    # 1 refinement step, so expect the ~3 % mesh noise seen in zsweep)
    'linescan_h5':  dict(mesh='fine',   wvl=6.1, x=X_SCAN,                 gaps=[5]),
    # same positions at the top of the tapping range: E(5 nm) - E(101 nm) removes the
    # height-independent far-field drift (plot_linescan.py diff)
    'linescan_h101': dict(mesh='fine',  wvl=6.1, x=X_SCAN,                 gaps=[101]),
    # proof of concept: extend the 5 nm scan to +-1 um so the near-field step is complete on both
    # sides and can be told apart from the slow far-field drift; fields saved to compare the near
    # field over pure oil (x_interface = -1000) and pure water (+1000)
    'linescan_h5_wide': dict(mesh='fine', wvl=6.1, x=[-1000, -700, -500, -400, 400, 500, 700, 1000],
                             gaps=[5], save_fields=True),
    'zsweep':       dict(mesh='fine',   wvl=6.1, x=[0],                    gaps=HEIGHTS_DENSE),
    'coarse_check': dict(mesh='coarse', wvl=6.1, x=[0],                    gaps=HEIGHTS),
    'noise':        dict(mesh='fine',   wvl=6.1, x=[1000, 1003, 1006],     gaps=HEIGHTS),
    'scan':         dict(mesh='fine',   wvl=6.1, x=X_SCAN,                 gaps=HEIGHTS),
    'scan_5.5um':   dict(mesh='fine',   wvl=5.5, x=X_SCAN,                 gaps=HEIGHTS),
}
MIN_DIRECTIONS = 50     # fewer far-field directions in the NA cone -> sampling too coarse, stop

# Materials: tabulated n,k from refractiveindex.info (sources in the file headers),
# interpolated at the wavelength.  Template key prefix -> data file.
MATERIAL_FILES = {
    'water': 'water_HaleQuerry.csv',   # Hale & Querry 1973
    'oil':   'octane_Myers.csv',       # n-octane (Myers 2018) as OTS stand-in
    'pt':    'Pt_Rakic_BB.csv',        # Rakic 1998, Brendel-Bormann fit
    'SN':    'SiN_Kischkat.csv',       # Kischkat 2012, sputtered SiNx
}

# ----------------------------------------------------------------------------
# Geometry and mesh (nm); see layout.jcmt for the coordinate system
# ----------------------------------------------------------------------------
GEOMETRY = {
    't_SiN': 5,
    'liquid_depth': 2000,       # water below the SiN, into the bottom boundary
    'oil_depth': 1000,          # depth of the oil block (>> near-field reach of ~100 nm)
    'patch_margin': 1000,       # oil block stops this far from the side walls (layered exterior)
    'cd_width': 16000,          # lateral size of the computational domain (x and y)
    'tip_radius': 75,           # apex radius: sphere tangent to the cone
    'tip_cap_height': 900,      # revolved apex section (must be < 1000, see layout.jcmt)
    'tip_half_angle': 30.14,    # same opening angle as the 2D tip (7514 / 12940)
    'tip_length': 12940,
    'air_above_tip': 500,
}

# Mesh presets: only element sizes change, the geometry stays identical,
# so coarse and fine results can be compared directly (convergence check).
MESH = {
    'fine':          {'max_side': 1500, 'tip_side': 1500, 'max_steps': 1},
    'coarse':        {'max_side': 3000, 'tip_side': 3000, 'max_steps': 1},
    # same start mesh as coarse, but JCM refines 3 times (mesh and PML) towards Precision
    'coarse_3steps': {'max_side': 3000, 'tip_side': 3000, 'max_steps': 3},
}


def nk_permittivity(path, wvl):
    """eps = (n + ik)^2 at wavelength wvl (m) from a wavelength_um,n,k csv."""
    with open(path) as f:
        rows = [line.split(',') for line in f if line[0].isdigit()]   # skips # comments and header
    d = np.array(rows, float)
    w_um = wvl*1e6
    if not d[0, 0] <= w_um <= d[-1, 0]:
        raise ValueError(f'{w_um} um outside the data range of {path}')
    eps = (np.interp(w_um, d[:, 0], d[:, 1]) + 1j*np.interp(w_um, d[:, 0], d[:, 2]))**2
    return eps.real, eps.imag


def material_keys(wvl):
    """Template keys <name>_eps1, <name>_eps2 for every material at wavelength wvl (m)."""
    keys = {}
    for name, fname in MATERIAL_FILES.items():
        keys[name + '_eps1'], keys[name + '_eps2'] = nk_permittivity(
            os.path.join(HERE, 'optical_data', fname), wvl)
    return keys


BEAM_FILE = os.path.join(RESULTS, 'beamcheck.json')


def beam_convention():
    """beam_phi / SP vectors found by the beam check (beam along +x, source 1 = s)."""
    if not os.path.exists(BEAM_FILE):
        raise SystemExit('no results/beamcheck.json: run  python run_linescan.py --stage beamcheck  first')
    with open(BEAM_FILE) as f:
        b = json.load(f)
    return {'beam_phi': b['beam_phi'], 'sp_s': b['sp_s'], 'sp_p': b['sp_p']}


def source_keys(wvl, theta_deg, beam=None):
    """Focused Gaussian beam (sources.jcmt): focus on the SiN surface, waist lambda/(pi NA)."""
    keys = {'wvl': wvl, 'theta': float(theta_deg), 'waist': wvl/(np.pi*NA), 'beam_na': NA}
    b = beam or beam_convention()
    keys.update(beam_phi=float(b['beam_phi']), sp_s=np.array(b['sp_s'], float), sp_p=np.array(b['sp_p'], float))
    return keys


def run_beamcheck():
    """
    Evaluate only the incident beam (no tip solve) for ThetaPhi phi = 0 and 180 and find
    the setting that travels along +x, which SP gives s (E along y), and check that the
    spot is centred on the focus.  Writes results/beamcheck.json; stops if anything is off.
    """
    os.chdir(HERE)
    os.makedirs(RESULTS, exist_ok=True)
    wvl = STAGES['converge']['wvl']*1e-6
    k0 = 2*np.pi/wvl
    report = {'wvl': wvl, 'theta': THETA, 'waist': wvl/(np.pi*NA), 'cases': {}}
    for phi in (0.0, 180.0):
        keys = dict(GEOMETRY, **MESH['coarse'], x_interface=0.0, gap=float(MIN_GAP))
        keys.update(material_keys(wvl))
        keys.update(source_keys(wvl, THETA, {'beam_phi': phi, 'sp_s': [1, 0], 'sp_p': [0, 1]}))
        jcm_log = os.path.join(HERE, 'project_results', 'jcm_console.log')
        os.makedirs(os.path.dirname(jcm_log), exist_ok=True)
        try:
            jcmwave.solve('beamcheck.jcmp', keys=keys, logfile=jcm_log)
        finally:
            text = open(jcm_log, errors='replace').read() if os.path.exists(jcm_log) else ''
            with open(os.path.join(RESULTS, 'jcm_beamcheck.log'), 'a') as f:
                f.write(f'\n######## beam_phi={phi:g}\n' + text)
        lx = jcmwave.loadcartesianfields(os.path.join('project_results', 'beamcheck_x.jcm'))
        ly = jcmwave.loadcartesianfields(os.path.join('project_results', 'beamcheck_y.jcm'))
        x = np.ravel(lx['X'])*1e9
        y = np.ravel(ly['Y'])*1e9
        for src, sp in ((0, [1, 0]), (1, [0, 1])):
            Ex = np.reshape(lx['field'][src], (-1, 3))
            Ey = np.reshape(ly['field'][src], (-1, 3))
            I = np.sum(np.abs(Ex)**2, axis=1)
            c = int(np.argmax(np.sum(np.abs(Ex)**2, axis=0)))           # dominant component
            lit = I > 0.3*I.max()
            ph = np.unwrap(np.angle(Ex[lit, c]))
            kx = np.polyfit(x[lit]*1e-9, ph, 1)[0]
            ipk = int(np.argmax(I))
            Iy = np.sum(np.abs(Ey)**2, axis=1)
            report['cases'][f'phi{phi:g}_SP{sp}'] = {
                'beam_phi': phi, 'SP': sp, 'kx_over_k0': float(kx/k0),
                'expected_abs_kx_over_k0': float(np.sin(np.deg2rad(THETA))),
                'peak_x_nm': float(x[ipk]), 'peak_y_nm': float(y[int(np.argmax(Iy))]),
                'Ey_fraction_at_peak': float(np.abs(Ex[ipk, 1])**2/I[ipk]), 'dominant_component': 'xyz'[c]}
    cases = report['cases']
    for name, cse in cases.items():
        print(f"beamcheck {name}: kx/k0 = {cse['kx_over_k0']:+.3f}, spot at x = {cse['peak_x_nm']:+.0f} nm, "
              f"y = {cse['peak_y_nm']:+.0f} nm, |Ey|^2 fraction {cse['Ey_fraction_at_peak']:.2f}", flush=True)
    good = [c for c in cases.values() if c['kx_over_k0'] > 0]
    problems = []
    if len(good) != 2 or len({c['beam_phi'] for c in good}) != 1:
        problems.append('could not find a single beam_phi for which both sources travel along +x')
    else:
        report['beam_phi'] = good[0]['beam_phi']
        s_like = [c for c in good if c['Ey_fraction_at_peak'] > 0.9]
        p_like = [c for c in good if c['Ey_fraction_at_peak'] < 0.1]
        if len(s_like) != 1 or len(p_like) != 1:
            problems.append('could not identify s (E along y) and p sources from the SP settings')
        else:
            report['sp_s'], report['sp_p'] = s_like[0]['SP'], p_like[0]['SP']
        for c in good:
            if abs(c['kx_over_k0'] - c['expected_abs_kx_over_k0']) > 0.1:
                problems.append(f"kx/k0 = {c['kx_over_k0']:.3f}, expected {c['expected_abs_kx_over_k0']:.3f} for {THETA} deg")
            if abs(c['peak_x_nm']) > 1500 or abs(c['peak_y_nm']) > 1500:
                problems.append(f"spot not centred on the focus: x {c['peak_x_nm']:.0f} nm, y {c['peak_y_nm']:.0f} nm")
    report['problems'] = problems
    with open(BEAM_FILE if not problems else BEAM_FILE.replace('.json', '_FAILED.json'), 'w') as f:
        json.dump(report, f, indent=2)
    if problems:
        raise SystemExit('beam check failed: ' + '; '.join(problems) + ' (details in results/beamcheck_FAILED.json)')
    print(f"beam check OK: beam_phi = {report['beam_phi']:g}, SP s = {report['sp_s']}, SP p = {report['sp_p']}", flush=True)


def scan_keys(mesh, wvl):
    """Template keys shared by all points of a stage (x_interface and gap are added per point)."""
    keys = dict(GEOMETRY, **MESH[mesh])
    keys.update(material_keys(wvl))
    keys.update(source_keys(wvl, THETA))
    return keys


def collect_backscatter(ft, theta_deg, na):
    """
    Far field of the scattered light inside an NA cone around the backscatter
    direction (straight back towards the source).

    For every plane wave k in the cone the field is split into a local s part
    (perpendicular to the plane containing k and z) and a p part, then summed coherently.
    Returns {'s_in': [Es, Ep], 'p_in': [Es, Ep]} for the two incident polarizations,
    plus the raw K and E inside the cone so the analysis can be redone later.
    """
    th = np.deg2rad(theta_deg)
    back_dir = np.array([-np.sin(th), 0.0, np.cos(th)])
    K = np.real(np.array(ft['K']))
    k_hat = K/np.linalg.norm(K, axis=1)[:, None]
    inside = k_hat @ back_dir >= np.cos(np.arcsin(na))

    s_hat = np.cross(k_hat[inside], [0.0, 0.0, 1.0])
    s_hat /= np.linalg.norm(s_hat, axis=1)[:, None]
    p_hat = np.cross(s_hat, k_hat[inside])

    out = {'n_directions': int(inside.sum()), 'n_directions_total': len(K),
           'K_cone': K[inside]}
    for name, src in (('s_in', 0), ('p_in', 1)):
        E = np.array(ft['ElectricFieldStrength'][src])
        out[name] = [np.sum(E[inside]*s_hat), np.sum(E[inside]*p_hat)]
        out['E_cone_' + name] = E[inside]
        out['E_total_power_' + name] = float(np.sum(np.abs(E)**2))   # whole upper hemisphere
    return out


def costs_summary(costs):
    """Unknowns, time and memory of every adaptive refinement level."""
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
        for l in lines[heads[-1] + 1:]:            # table: header, dashes, '-/-' row, then 'level  error  ratio'
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


def save_slices(path):
    """The two vertical field slices through the tip axis -> one compressed npz."""
    arrays = {}
    for name in ('slice_yz', 'slice_xz'):
        c = jcmwave.loadcartesianfields(os.path.join('project_results', name + '.jcm'))
        for k in ('X', 'Y', 'Z'):
            arrays[f'{name}_{k}'] = np.asarray(c[k], dtype=np.float32)
        arrays[f'{name}_E'] = np.stack([np.asarray(f, dtype=np.complex64) for f in c['field']])   # [source, ..., xyz]
    np.savez_compressed(path, **arrays)


def run_point(base_keys, x, gap, stage, save_fields=False):
    keys = dict(base_keys, x_interface=x, gap=gap)
    t0 = time.time()
    jcm_log = os.path.join(HERE, 'project_results', 'jcm_console.log')
    os.makedirs(os.path.dirname(jcm_log), exist_ok=True)
    try:
        results = jcmwave.solve('project.jcmp', keys=keys, logfile=jcm_log)
    finally:
        text = open(jcm_log, errors='replace').read() if os.path.exists(jcm_log) else ''
        with open(os.path.join(RESULTS, f'jcm_{stage}.log'), 'a') as f:
            f.write(f'\n######## x_interface={x:g} gap={gap:g} ({time.strftime("%Y-%m-%d %H:%M:%S")})\n' + text)
    signal = collect_backscatter(results[1], THETA, NA)
    record = {'x_interface': x, 'gap': gap, 'wall_time_s': time.time() - t0,
              'costs': costs_summary(results[0]), 'finished': time.strftime('%Y-%m-%d %H:%M:%S')}
    record.update(signal)
    record.update(parse_jcm_log(text))
    if save_fields:
        os.makedirs(os.path.join(RESULTS, 'fields'), exist_ok=True)
        fname = os.path.join(RESULTS, 'fields', f'{stage}_x{x:+.0f}_g{gap:.0f}.npz')
        save_slices(fname)
        record['fields_file'] = os.path.relpath(fname, HERE)
    return record


def log(msg):
    print(msg, flush=True)
    with open(os.path.join(RESULTS, 'run_log.txt'), 'a') as f:
        f.write(msg + '\n')


def configure_resources():
    """Use exactly the cores / memory SLURM gave the job (no-op when run locally)."""
    n = os.environ.get('SLURM_CPUS_ON_NODE') or os.environ.get('SLURM_NTASKS_PER_NODE')
    if n:
        jcmwave.set_num_threads(int(n))
    mem_mb = os.environ.get('SLURM_MEM_PER_NODE')
    if mem_mb:
        jcmwave.set_memory_limit(int(0.9*int(mem_mb)))   # JCM aborts cleanly instead of being OOM-killed
    return {'threads': n, 'mem_limit_mb': mem_mb}


def run_stage(name):
    cfg = STAGES[name]
    os.chdir(HERE)
    os.makedirs(RESULTS, exist_ok=True)
    out_file = os.path.join(RESULTS, name + '.pkl')

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
        raise SystemExit(f'{out_file} was made with different geometry / mesh / wavelength / materials / illumination; '
                         f'move it away (e.g. results/old/) before rerunning stage {name}, '
                         f'so old and new points are not mixed')
    data['settings'] = {
        'stage': name, 'mesh': cfg['mesh'], 'wvl': wvl, 'theta': THETA, 'NA': NA,
        'tap_amplitude': TAP_AMPLITUDE, 'min_gap': MIN_GAP, 'heights': HEIGHTS,
        'geometry': dict(GEOMETRY, **MESH[cfg['mesh']]),
        'material_files': MATERIAL_FILES, 'materials': material_keys(wvl), 'source': source,
        'host': socket.gethostname(), 'resources': configure_resources(),
        'slurm_job': os.environ.get('SLURM_JOB_ID'),
    }
    base_keys = scan_keys(cfg['mesh'], wvl)

    done = {(r['x_interface'], r['gap']) for r in data['records']}
    jobs = [(float(x), float(g)) for x in cfg['x'] for g in cfg['gaps'] if (float(x), float(g)) not in done]
    log(f'=== stage {name} on {socket.gethostname()} ({time.strftime("%Y-%m-%d %H:%M:%S")}): '
        f'{len(jobs)} solves to run, {len(done)} already done, {cfg["mesh"]} mesh, {cfg["wvl"]} um')

    consecutive_failures = 0
    for n, (x, gap) in enumerate(jobs):
        try:
            rec = run_point(base_keys, x, gap, name, cfg.get('save_fields', False))
        except Exception:
            tb = traceback.format_exc()
            data['failures'].append({'x_interface': x, 'gap': gap, 'traceback': tb})
            with open(out_file, 'wb') as f:
                pk.dump(data, f)
            log(f'[{n+1}/{len(jobs)}] x={x:+.0f} gap={gap:g} FAILED\n{tb}')
            consecutive_failures += 1
            if name == 'test' or consecutive_failures >= 3:
                raise
            continue
        consecutive_failures = 0
        data['records'].append(rec)
        with open(out_file, 'wb') as f:
            pk.dump(data, f)

        c = rec['costs']
        log(f'[{n+1}/{len(jobs)}] x={x:+.0f} nm gap={gap:g} nm  '
            f'|Ep|(p_in)={abs(rec["p_in"][1]):.4e} arg={np.angle(rec["p_in"][1]):+.3f}  '
            f'{rec["n_directions"]} dirs  unknowns={c.get("Unknowns")}  '
            f'mem={c.get("TotalMemory_GB")} GB  {rec["wall_time_s"]:.0f} s  '
            f'est.err FarField={rec.get("est_error_FarField")}  PML(+X)={rec.get("pml_quality", {}).get("X")}')

        if rec['n_directions'] < MIN_DIRECTIONS:
            raise RuntimeError(f'only {rec["n_directions"]} far-field directions in the NA cone '
                               f'(< {MIN_DIRECTIONS}); increase NRefinements in project.jcmp')


def write_jcm(mesh='fine', wvl_um=6.1, x_interface=0.0, gap=MIN_GAP):
    """Write layout/materials/sources .jcm for one point, e.g. to inspect in JCMcontrol."""
    os.chdir(HERE)
    beam = None if os.path.exists(BEAM_FILE) else {'beam_phi': 0, 'sp_s': [1, 0], 'sp_p': [0, 1]}
    if beam:
        print('no results/beamcheck.json yet: sources.jcm written with beam_phi = 0, SP = [1 0] / [0 1] (unchecked)')
    keys = dict(GEOMETRY, **MESH[mesh], x_interface=x_interface, gap=gap)
    keys.update(material_keys(wvl_um*1e-6))
    keys.update(source_keys(wvl_um*1e-6, THETA, beam))
    for name in ('layout.jcmt', 'materials.jcmt', 'sources.jcmt', 'project.jcmpt'):
        jcmwave.jcmt2jcm(name, keys)
        print(f'wrote {name[:-1]}  ({mesh} mesh, {wvl_um} um, x_interface={x_interface} nm, gap={gap} nm)')


if __name__ == '__main__':
    if '--jcm' in sys.argv:
        write_jcm('coarse' if '--coarse' in sys.argv else 'fine')
    elif '--stage' in sys.argv:
        stage = sys.argv[sys.argv.index('--stage') + 1]
        run_beamcheck() if stage == 'beamcheck' else run_stage(stage)
    else:
        print(__doc__)
