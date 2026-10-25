"""
Mesh demo (for slides): full 3D s-SNOM geometry with an array of nanoparticles under the tip.

Same tip as Interface_LineScan_3D (75 nm spherical apex tangent to a 30.14 deg cone, 12.94 um long:
a SolidOfRevolution cap for the lowest 900 nm plus a Cone).  5 nm SiN window with water below.  A 3 x 3
array of 100 nm diameter nanoparticles (250 nm pitch) sits on top of the SiN (1 nm air gap), centred
under the apex; the tip apex is 5 nm above the top of the central particle.  One global MaximumSideLength; the spheres get a
surface element size so they are not faceted at the global size.  Refinement is left to HAdaptive.

    python make_mesh.py        # writes layout/materials/sources/project .jcm(p) and meshes -> grid.jcm
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.environ['JCMROOT'], 'ThirdPartySupport', 'Python'))
import jcmwave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'Mesh_Demo_Cylindrical_NP'))
from make_mesh import write_common            # same materials / Gaussian beam / HAdaptive project  # noqa: E402

T_SIN, R_TIP, HALF_ANGLE, TIP_LEN, CAP_H = 5.0, 75.0, 30.14, 12940.0, 900.0
NP_R, NP_SPACING, NP_PITCH, NP_N = 50.0, 1.0, 250.0, 3   # NP_SPACING: air gap between SiN top and particles
GAP = NP_SPACING + 2*NP_R + 5.0                          # tip apex 5 nm above the top of the central particle
CD_WIDTH, LIQ_DEPTH, AIR_ABOVE = 16000.0, 2000.0, 500.0
MAX_SIDE, NP_SIDE = 1500.0, 15.0


def write_files():
    a = np.deg2rad(HALF_ANGLE)
    prof = [(0.0, 0.0)]
    for p in np.linspace(-np.pi/2, -a, 9)[1:]:
        prof.append((R_TIP*np.cos(p), R_TIP + R_TIP*np.sin(p)))
    r_joint = R_TIP*np.cos(a) + (CAP_H - (R_TIP - R_TIP*np.sin(a)))*np.tan(a)
    prof += [(r_joint, CAP_H), (0.0, CAP_H)]
    profile = ', '.join('%.4f %.4f' % xy for xy in prof)
    zc = NP_SPACING + NP_R               # particles on top of the SiN (air side)
    spheres = []
    k = 0
    for i in range(NP_N):
        for j in range(NP_N):
            x = (i - (NP_N - 1)/2)*NP_PITCH
            y = (j - (NP_N - 1)/2)*NP_PITCH
            k += 1
            spheres.append(f"""    Sphere {{
      Name = "NP{k}"
      DomainId = 5
      Priority = 3
      Radius = {NP_R}
      GlobalPosition = [{x} {y} {zc}]
      MeshOptions {{
        BoundaryMeshConstraint {{
          MaximumSideLength = {NP_SIDE}
        }}
        MaximumSideLength = {NP_SIDE}
      }}
    }}""")
    layout = f"""Layout3D {{
  UnitOfLength = 1e-09
  MeshOptions {{
    MaximumSideLength = {MAX_SIDE}
  }}
  Extrusion {{
    Objects {{
      Parallelogram {{
        Name = "CD"
        DomainId = 101
        Priority = ComputationalDomain
        Width = {CD_WIDTH}
        Height = {CD_WIDTH}
        Boundary {{
          Class = Transparent
        }}
      }}
    }}
    MultiLayer {{
      LayerInterface {{
        BoundaryClass = Transparent
        GlobalZ = {-T_SIN - LIQ_DEPTH}
      }}
      Layer {{
        Name = "Water"
        Thickness = {LIQ_DEPTH}
        DomainIdMapping = [101 2]
      }}
      Layer {{
        Name = "SiN"
        Thickness = {T_SIN}
        DomainIdMapping = [101 7]
      }}
      Layer {{
        Name = "Air"
        Thickness = {GAP + TIP_LEN + AIR_ABOVE}
        DomainIdMapping = [101 1]
      }}
      LayerInterface {{
        BoundaryClass = Transparent
      }}
    }}
  }}
  Objects {{
{chr(10).join(spheres)}
    SolidOfRevolution {{
      Name = "TipApex"
      DomainId = 3
      Priority = 2
      GlobalPosition = [0 0 {GAP}]
      Generator {{
        Polygon {{
          Points = [{profile}]
        }}
      }}
    }}
    Cone {{
      Name = "TipShaft"
      DomainId = 3
      Priority = 2
      BottomRadius = {r_joint}
      TopRadius = {r_joint + (TIP_LEN - CAP_H)*np.tan(a)}
      Height = {TIP_LEN - CAP_H}
      GlobalPosition = [0 0 {GAP + CAP_H}]
    }}
  }}
}}
"""
    open(os.path.join(HERE, 'layout.jcm'), 'w').write(layout)
    write_common(HERE, cylindrical=False)


if __name__ == '__main__':
    write_files()
    jcmwave.geo(HERE)
    print('wrote grid.jcm in', HERE)
