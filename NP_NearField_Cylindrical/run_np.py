"""
Near field around a nanoparticle under the s-SNOM tip (cylindrical / axisymmetric JCMsuite model).

Geometry (nm), x = r >= 0, y along the tip axis, y = 0 is the SiN top surface:
    air above, Pt tip (75 nm apex radius, 30.14 deg half angle) -- SHORT tip (TIP_LEN, default 2 um
    instead of 12.94 um) so the domain and the mesh are much smaller
    Au sphere of radius R on top of the SiN (1 nm air gap), centred on the axis
    tip apex GAP_ABOVE = 5 nm above the top of the particle (or above the SiN for R = 0, no particle)
    5 nm SiN window, water below
Illumination as in the line scans: Gaussian beam, 6.1 um, 60 deg, NA 0.4, waist lambda/(pi NA), p polarized,
focus on the SiN surface.  Accuracy: FE degree 4, HAdaptive 3 steps, Precision 1e-5 (same as the 2D runs).

Per case (work/<case>/ is the solve folder):
    1. solve (project.jcmp) -> fieldbag, far field (ft.jcm), JCM error estimates
    2. separate post-process (export.jcmp) on the field bag: |E| map on a 2.5 nm grid around apex and particle
    -> results/<case>.npz (X, Y, E), results/<case>_grid.jcm (start mesh), results/<case>_console.log,
       results/summary.json (time, unknowns, error estimates, export time)

    python run_np.py --case R50        # one case;  cases: R0 (no particle), R25, R50, R75
    python run_np.py --all             # all cases (finished ones are skipped)
    python run_np.py --mesh            # write the case files and mesh them only (no license needed)

Caveat: with the short tip the far field / absolute signal is not comparable to the long-tip runs; the near
field around the apex and particle is the purpose of this project.
"""
import os
import sys
import json
import time
import shutil
import numpy as np

sys.path.insert(0, os.path.join(os.environ['JCMROOT'], 'ThirdPartySupport', 'Python'))
import jcmwave

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
WORK = os.path.join(HERE, 'work')
OPTICAL = os.path.join(HERE, '..', 'Interface_LineScan_2D', 'optical_data')

WVL = 6.1e-6
THETA, NA = 60.0, 0.4
T_SIN, R_TIP, HALF_ANGLE = 5.0, 75.0, 30.14
TIP_LEN = 2000.0              # short tip (the line scans used 12940 nm)
GAP_ABOVE = 5.0               # tip apex above the particle top (or above the SiN when there is no particle)
NP_SPACING = 1.0              # air gap between SiN top and particle
LIQ_DEPTH, AIR_ABOVE, R_MAX = 1500.0, 300.0, 3000.0
MAX_SIDE = 300.0
EPS_AU = (-1682.1, 175.2)     # Au, value used in the old Silicon Nitride NP runs (~6 um)
CASES = {'R0': 0.0, 'R25': 25.0, 'R50': 50.0, 'R75': 75.0}
MAP_STEP = 2.5                # nm, export grid


def nk_eps(fname):
    d = np.array([l.split(',') for l in open(os.path.join(OPTICAL, fname)) if l[0].isdigit()], float)
    w = WVL*1e6
    e = (np.interp(w, d[:, 0], d[:, 1]) + 1j*np.interp(w, d[:, 0], d[:, 2]))**2
    return e.real, e.imag


def pts(p):
    return ', '.join('%.4f %.4f' % xy for xy in p)


def geometry(R):
    gap = (NP_SPACING + 2*R if R > 0 else 0.0) + GAP_ABOVE      # apex height above the SiN top
    a = np.deg2rad(HALF_ANGLE)
    tip = [(0.0, gap)]
    for p in np.linspace(-np.pi/2, -a, 40)[1:]:
        tip.append((R_TIP*np.cos(p), gap + R_TIP + R_TIP*np.sin(p)))
    y_top = gap + TIP_LEN
    r_t, y_t = tip[-1]
    tip += [(r_t + (y_top - y_t)*np.tan(a), y_top), (0.0, y_top)]
    part = [(R*np.cos(t), NP_SPACING + R + R*np.sin(t)) for t in np.linspace(-np.pi/2, np.pi/2, 61)] if R > 0 else None
    return gap, tip, part


def write_case(case):
    R = CASES[case]
    wd = os.path.join(WORK, case)
    os.makedirs(os.path.join(wd, 'project_results'), exist_ok=True)
    gap, tip, part = geometry(R)
    y_bot, y_top = -T_SIN - LIQ_DEPTH, gap + TIP_LEN + AIR_ABOVE
    rect = lambda x0, x1, y0, y1: pts([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    np_block = (f'    Polygon {{\n      Name = "Nanoparticle"\n      DomainId = 5\n      Priority = 2\n'
                f'      Points = [{pts(part)}]\n    }}\n') if part else ''
    open(os.path.join(wd, 'layout.jcm'), 'w').write(f"""Layout2D {{
  UnitOfLength = 1e-09
  CoordinateSystem = Cylindrical
  MeshOptions {{
    MaximumSideLength = {MAX_SIDE}
  }}
  BoundaryConditions {{
    Boundary {{
      Direction = All
      Class = Transparent
    }}
  }}
  Objects {{
    Polygon {{
      Name = "CD"
      DomainId = 1
      Priority = ComputationalDomain
      Points = [{rect(0, R_MAX, y_bot, y_top)}]
    }}
    Polygon {{
      Name = "Water"
      DomainId = 2
      Priority = 1
      Points = [{rect(0, R_MAX, y_bot, -T_SIN)}]
    }}
    Polygon {{
      Name = "SiN"
      DomainId = 7
      Priority = 1
      Points = [{rect(0, R_MAX, -T_SIN, 0)}]
    }}
{np_block}    Polygon {{
      Name = "Tip"
      DomainId = 3
      Priority = 3
      Points = [{pts(tip)}]
    }}
  }}
}}
""")
    mats = [(1, 'Air', (1.0, 0.0)), (2, 'Water', nk_eps('water_HaleQuerry.csv')),
            (3, 'Pt', nk_eps('Pt_Rakic_BB.csv')), (5, 'Au', EPS_AU), (7, 'SiN', nk_eps('SiN_Kischkat.csv'))]
    with open(os.path.join(wd, 'materials.jcm'), 'w') as f:
        for i, name, (e1, e2) in mats:
            f.write(f'# {name}\nMaterial {{\n  DomainId = {i}\n  RelPermittivity = ({e1:.6e}, {e2:.6e})\n'
                    f'  RelPermeability = 1\n}}\n')
    open(os.path.join(wd, 'sources.jcm'), 'w').write(f"""SourceBag {{
  Source {{
    ElectricFieldStrength {{
      GaussianBeam {{
        Lambda0 = {WVL:.6e}
        ThetaPhi = [{THETA} 0]
        Incidence = FromAbove
        3DTo2D = yes
        SP = [0 1]
        Waist = {WVL/(np.pi*NA):.6e}
        Focus = [0 0 0]
        OpticalSystem {{
          NumericalAperture = {NA}
        }}
      }}
    }}
  }}
}}
""")
    open(os.path.join(wd, 'project.jcmp'), 'w').write("""Project {
  Electromagnetics {
    TimeHarmonic {
      Scattering {
        FieldComponents = Electric
        Accuracy {
          FiniteElementDegree = 4
          Refinement {
            Strategy = HAdaptive
            MaxNumberSteps = 3
            Adaptivity {
              MinimumRefinementFraction = 0.05
            }
          }
          Precision = 1e-5
        }
      }
    }
  }
}

PostProcess {
  FourierTransform {
    FieldBagPath = "project_results/fieldbag.jcm"
    OutputFileName = "project_results/ft.jcm"
    NormalDirection = Y
    ScatteredFieldOnly = yes
  }
}
""")
    y1 = gap + 150.0
    gx = ' '.join('%.6e' % (v*1e-9) for v in np.arange(-250.0, 250.0 + 1e-6, MAP_STEP))
    gy = ' '.join('%.6e' % (v*1e-9) for v in np.arange(-60.0, y1 + 1e-6, MAP_STEP))
    open(os.path.join(wd, 'export.jcmp'), 'w').write(f"""PostProcess {{
  ExportFields {{
    FieldBagPath = "project_results/fieldbag.jcm"
    OutputFileName = "project_results/map.jcm"
    OutputQuantity = ElectricFieldStrength
    Cartesian {{
      GridPointsX = [{gx}]
      GridPointsY = [{gy}]
      GridPointsZ = 0
    }}
  }}
}}
""")
    return wd, gap


def run_case(case):
    out_npz = os.path.join(RESULTS, f'{case}.npz')
    if os.path.exists(out_npz):
        print(case, 'already done')
        return
    wd, gap = write_case(case)
    os.makedirs(RESULTS, exist_ok=True)
    log = os.path.join(RESULTS, f'{case}_console.log')
    t0 = time.time()
    res = jcmwave.solve(os.path.join(wd, 'project.jcmp'), logfile=log)
    t_solve = time.time() - t0
    shutil.copy(os.path.join(wd, 'grid.jcm'), os.path.join(RESULTS, f'{case}_grid.jcm'))
    t1 = time.time()
    jcmwave.solve(os.path.join(wd, 'export.jcmp'), logfile=log.replace('_console', '_export'))
    t_export = time.time() - t1
    c = jcmwave.loadcartesianfields(os.path.join(wd, 'project_results', 'map.jcm'))
    np.savez_compressed(out_npz, X=np.asarray(c['X'])*1e9, Y=np.asarray(c['Y'])*1e9,
                        E=np.asarray(c['field'][0], np.complex64), radius=CASES[case], gap=gap)
    costs = res[0].get('computational_costs', res[0]) if isinstance(res[0], dict) else {}
    text = open(log, errors='replace').read()
    summ_f = os.path.join(RESULTS, 'summary.json')
    summ = json.load(open(summ_f)) if os.path.exists(summ_f) else {}
    summ[case] = {'radius_nm': CASES[case], 'apex_above_SiN_nm': gap, 'solve_s': t_solve, 'export_s': t_export,
                  'unknowns': np.asarray(costs.get('Unknowns', [])).tolist(),
                  'farfield_err_lines': [l.strip() for l in text.splitlines() if 'e-0' in l and l.strip()[:1].isdigit()][-6:],
                  'host': os.uname().nodename if hasattr(os, 'uname') else '', 'finished': time.strftime('%Y-%m-%d %H:%M:%S')}
    json.dump(summ, open(summ_f, 'w'), indent=1)
    print(f'{case}: solve {t_solve:.0f} s, export {t_export:.0f} s, unknowns {summ[case]["unknowns"]}', flush=True)


def mesh_only():
    import re
    for case in CASES:
        wd, gap = write_case(case)
        t0 = time.time()
        jcmwave.geo(wd)
        head = open(os.path.join(wd, 'grid.jcm'), errors='replace').read(3000)
        n = dict(re.findall(r'<I>(NTriangles|NPoints)=(\d+)', head))
        print(f'{case}: apex at {gap:g} nm, {n}, {time.time() - t0:.1f} s')


if __name__ == '__main__':
    n = os.environ.get('SLURM_CPUS_ON_NODE')
    if n:
        jcmwave.set_num_threads(int(n))
    if '--mesh' in sys.argv:
        mesh_only()
    elif '--all' in sys.argv:
        for c in CASES:
            run_case(c)
    elif '--case' in sys.argv:
        run_case(sys.argv[sys.argv.index('--case') + 1])
    else:
        print(__doc__)
