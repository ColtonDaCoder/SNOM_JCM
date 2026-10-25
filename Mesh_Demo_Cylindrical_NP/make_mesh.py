"""
Mesh demo (for slides): cylindrical (axisymmetric) s-SNOM geometry with a nanoparticle under the tip.

Layout2D in cylindrical coordinates: x = r >= 0 (the symmetry axis is the left edge), y = z.
Same tip as Interface_LineScan_2D/3D (75 nm apex radius, 30.14 deg half angle, 12.94 um long), which
in these coordinates is a true cone.  Gap 5 nm above a 5 nm SiN window, water below; a 100 nm
diameter nanoparticle sits in the water, centred on the axis 2 nm below the SiN.
Mesh: one global MaximumSideLength; refinement is left to HAdaptive in project.jcmp.

    python make_mesh.py        # writes layout/materials/sources/project .jcm(p) and meshes -> grid.jcm
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.environ['JCMROOT'], 'ThirdPartySupport', 'Python'))
import jcmwave

HERE = os.path.dirname(os.path.abspath(__file__))

GAP, T_SIN, R_TIP, HALF_ANGLE, TIP_LEN = 5.0, 5.0, 75.0, 30.14, 12940.0
NP_R, NP_SPACING = 50.0, 2.0          # nanoparticle radius, water gap between SiN and particle
LIQ_DEPTH, AIR_ABOVE, R_MAX = 3000.0, 500.0, 9000.0
MAX_SIDE = 400.0


def pts(p):
    return ', '.join('%.4f %.4f' % xy for xy in p)


def tip_profile():
    a = np.deg2rad(HALF_ANGLE)
    prof = [(0.0, GAP)]
    for p in np.linspace(-np.pi/2, -a, 40)[1:]:          # spherical cap from the apex to the tangent point
        prof.append((R_TIP*np.cos(p), GAP + R_TIP + R_TIP*np.sin(p)))
    y_top = GAP + TIP_LEN
    r_t, y_t = prof[-1]
    prof += [(r_t + (y_top - y_t)*np.tan(a), y_top), (0.0, y_top)]
    return prof


def np_profile():
    yc = -T_SIN - NP_SPACING - NP_R
    return [(NP_R*np.cos(t), yc + NP_R*np.sin(t)) for t in np.linspace(-np.pi/2, np.pi/2, 61)]   # counter-clockwise


def write_files():
    y_bot, y_top = -T_SIN - LIQ_DEPTH, GAP + TIP_LEN + AIR_ABOVE
    rect = lambda x0, x1, y0, y1: pts([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    layout = f"""Layout2D {{
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
    Polygon {{
      Name = "Nanoparticle"
      DomainId = 5
      Priority = 2
      Points = [{pts(np_profile())}]
    }}
    Polygon {{
      Name = "Tip"
      DomainId = 3
      Priority = 3
      Points = [{pts(tip_profile())}]
    }}
  }}
}}
"""
    open(os.path.join(HERE, 'layout.jcm'), 'w').write(layout)
    write_common(HERE, cylindrical=True)


def write_common(folder, cylindrical):
    # permittivities at 6.1 um (same data as the line-scan projects); nanoparticle: placeholder polystyrene-like
    mats = [(1, 'Air', 1.0, 0.0), (2, 'Water', 1.723, 0.346), (3, 'Pt', -567.461, 266.645),
            (5, 'Nanoparticle', 2.4, 0.0), (7, 'SiN', 4.887, 0.173)]
    with open(os.path.join(folder, 'materials.jcm'), 'w') as f:
        for i, name, e1, e2 in mats:
            f.write(f'Material {{\n  Name = "{name}"\n  DomainId = {i}\n  RelPermittivity = ({e1}, {e2})\n'
                    f'  RelPermeability = 1.0\n}}\n')
    extra = '        3DTo2D = yes\n' if cylindrical else ''
    beam = ('SourceBag {\n  Source {\n    ElectricFieldStrength {\n      GaussianBeam {\n'
            '        Lambda0 = 6.1e-06\n        ThetaPhi = [60 180]\n        Incidence = FromAbove\n' + extra +
            '        SP = [0 1]\n        Waist = 4.854e-06\n        Focus = [0 0 0]\n'
            '        OpticalSystem {\n          NumericalAperture = 0.4\n        }\n      }\n    }\n  }\n}\n')
    open(os.path.join(folder, 'sources.jcm'), 'w').write(beam)
    project = """Project {
  Electromagnetics {
    TimeHarmonic {
      Scattering {
        FieldComponents = Electric
        Accuracy {
          FiniteElementDegree = 3
          Refinement {
            Strategy = HAdaptive
            MaxNumberSteps = 3
            Adaptivity {
              MinimumRefinementFraction = 0.05
            }
          }
          Precision = 1e-4
        }
      }
    }
  }
}
"""
    open(os.path.join(folder, 'project.jcmp'), 'w').write(project)


if __name__ == '__main__':
    write_files()
    jcmwave.geo(HERE)
    print('wrote grid.jcm in', HERE)
