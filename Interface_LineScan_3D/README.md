# Interface_LineScan_3D

3D JCMsuite model of a Pt s-SNOM tip scanned across a lateral **water | oil**
interface underneath a **5 nm SiN window**. Its purpose is to answer the resolution
question: how sharp does a discrete interface look through the window?

Same solver setup as `mod_sb` / `SNx_Water_Simple`: HAdaptive refinement, FE degree 3,
two polarizations per solve, and a far-field Fourier transform of the scattered field.

## Geometry (nm, `layout.jcmt`)

```
          z
          ^        Pt tip (cone, filleted apex), axis at x = y = 0
          |              \      /
  air     |               \    /
          |                \__/     <- apex at z = gap
  0 ------+---------------------------------------  SiN top surface
 -5       |  SiN (5 nm)
          |  water             | oil / OTS (octane)  |  water
          |                    |   block, 1 um deep  |
 -1005    |                    +---------------------+
          |  water
 -2005    +-------------------------------------------> x
                          x = x_interface         x = 7000
```

| DomainId | material |
|---|---|
| 1 | air |
| 2 | water: Hale & Querry 1973 |
| 3 | Pt: Rakic et al. 1998 (Brendel-Bormann fit) |
| 7 | SiN: Kischkat et al. 2012 (sputtered SiNx) |
| 9 | oil / OTS: n-octane, Myers et al. 2018 |

- All n,k data come from refractiveindex.info and are stored in `optical_data/`
  (citation, URL and download date in each file header). They are interpolated at `WVL`,
  so the H-O-H bend (~6.1 um) is followed when the wavelength changes.
  Common range of the four files: 1.54 - 12.4 um.
- SiN is the same data as the `SNx_Water_Simple` tables; Pt agrees with them to within ~0.5 %
  over 5.5 - 6.5 um.
- The refractiveindex.info octane entry carries the comment "Isopropanol"; that is a database
  typo. The spectrum has no O-H or C-O bands, see `optical_data/octane_Myers.csv`.
- The tip stays fixed and the **interface moves**. `x_interface < 0` means the tip is over oil.
- All lateral and vertical boundaries are transparent (PML). Air, SiN and water extend into them.
- The oil is a finite block (`x_interface` < x < 7 um, |y| < 7 um, 1 um deep) in bulk water.
  JCM builds the incident field from the layered stack outside the domain, so the exterior
  must be the same air / SiN / water stack on every side; oil reaching a boundary gives
  "Layered exterior not initialized". 1 um of oil is effectively infinite for the near field,
  and the other block faces are >= 7 um from the tip. The block also reflects some light into
  the collection cone; that part does not depend on tip height, so it drops out of S_1 - S_4
  and only offsets S_0. Size via `oil_depth` and `patch_margin` in `GEOMETRY`.
- 3D construction: the stack is a 2D cross-section (`Extrusion` / `MultiLayer`). The tip is a
  free 3D `Cone` with `EdgeRounding` (fillet).
  - `SolidOfRevolution` was tried: it silently truncates the tip 1000 nm above the apex.
  - Cone + Sphere was tried: the tangent overlap makes JCMgeo run out of memory.

## Illumination and signal

- Two plane waves (`sources.jcmt`) at `THETA` = 60° from the normal, travelling +x and down:
  - source 1 is s-polarized;
  - source 2 is p-polarized.
- `K` and `Amplitude` are given explicitly from python, so no angle convention is involved.
- The far field of the scattered light (`project.jcmp`, `NormalDirection = Z`) is summed
  coherently inside an NA = 0.4 cone around the backscatter direction (`collect_backscatter`).
  The sum is split into local s and p components.
- Instrument model: tapping amplitude 100 nm, closest approach 1 nm. Each position is solved at
  14 heights (1 - 101 nm, dense near contact); `plot_linescan.py` interpolates E(z) with a cubic
  spline and demodulates S_n, n = 0 - 4, amplitude and phase. n = 0 is the cycle-averaged field
  (the analysis in `SNx_Water_Simple/demodulation copy.py`); S2 / S3 are what the instrument records.
- Stored per solve in `results/<stage>.pkl` (`records` list):
  - `s_in = [Es, Ep]`, `p_in = [Es, Ep]` (incident pol -> detected component);
  - the raw far field inside the NA cone (`K_cone`, `E_cone_s_in`, `E_cone_p_in`) and the total
    scattered power, so the collection can be re-analysed without re-solving;
  - `costs` (unknowns, time, memory per adaptive level) and the wall time;
  - `failures` holds the traceback of any failed solve; `settings` holds geometry, mesh, materials
    at the wavelength, host and SLURM job.

## Running on the cluster

```
cd Interface_LineScan_3D
sbatch submit.sbatch                  # stages: test zsweep coarse_check noise scan
sbatch submit.sbatch scan_5.5um       # optional second wavelength, after the first job
```

Then commit and push the whole `results/` folder: `*.pkl`, `run_log.txt` and `slurm-*.out`.
Stages are resumable: if the job hits the time limit, submit again and it continues.

| stage | solves | purpose |
|---|---|---|
| `test` | 1 | does it run (coarse mesh), cost per solve, far-field sampling (stops if < 50 directions in the cone) |
| `zsweep` | 35 | dense height sweep at the interface: are the 14 heights enough for S_n? |
| `coarse_check` | 14 | same position on the coarse mesh: mesh convergence |
| `noise` | 42 | interface 1 um away, moved by 3 nm: remeshing noise compared with the edge contrast |
| `scan` | 434 | 31 positions (5 nm steps within +-50 nm, out to +-300 nm) x 14 heights at 6.1 um |
| `scan_5.5um` | 434 | the same scan at 5.5 um (water contrast from n only, k small) |

Settings are at the top of `run_linescan.py` (`STAGES`, `HEIGHTS`, `X_SCAN`, `THETA`, `NA`,
`TAP_AMPLITUDE`, `MIN_GAP`, `MATERIAL_FILES`, `GEOMETRY`, `MESH`).

```
python plot_linescan.py test | zsweep | coarse_check | noise | scan   # analysis per stage
python run_linescan.py --jcm [--coarse]                              # write .jcm for JCMcontrol
```

## Cost notes

- Every solve changes the geometry, so JCMgeo remeshes every time
  (about 1 minute for the fine mesh, plus the 3D solve; the `test` stage measures the real cost).
- On SLURM the job uses the allocated cores, and with `--mem` set JCM is told 90 % of it, so a
  too-large job aborts with an error in the log instead of being killed silently.
- Requires the `JCMROOT` environment variable; `jcmwave` is imported from the installation.
