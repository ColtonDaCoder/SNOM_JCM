# Interface_LineScan_3D

3D JCMsuite model of a Pt s-SNOM tip scanned across a lateral **water | oil**
interface underneath a **5 nm SiN window**. Its purpose is to answer the resolution
question: how sharp does a discrete interface look through the window?

Same solver setup as `mod_sb` / `SNx_Water_Simple`: HAdaptive refinement, FE degree 3,
two polarizations per solve, and a far-field Fourier transform of the scattered field.

## Geometry (nm, `layout.jcmt`)

```
          z
          ^        Pt tip (cone + 75 nm spherical apex), axis at x = y = 0
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
- The oil is a finite 3D `Box` (`x_interface` < x < 7 um, |y| < 7 um, 1 um deep) in bulk water.
  - Finite: JCM builds the incident field from the layered stack outside the domain, so the
    exterior must be the same air / SiN / water stack on every side; oil reaching a boundary
    gives "Layered exterior not initialized".
  - A `Box`, not part of the extruded cross-section: an extruded edge at `x_interface` also runs
    up through the air and cut the tip apex; JCMgeo then failed or hung at 16 of the 31 scan
    positions (all within +-45 nm of the tip).
  - 1 um of oil is effectively infinite for the near field, and the other block faces are
    >= 7 um from the tip. The block also reflects some light into the collection cone; that
    part does not depend on tip height, so it drops out of S_1 - S_4 and only offsets S_0.
    Size via `oil_depth` and `patch_margin` in `GEOMETRY`.
- 3D construction: the water / SiN / air stack is an extruded 2D cross-section
  (`Extrusion` / `MultiLayer`); the oil `Box` and the tip are free 3D objects.
- Tip: a 75 nm sphere at the apex, tangent to a 30.14 deg cone (same opening angle as the 2D
  tip), 12.94 um long. The lowest 900 nm is a `SolidOfRevolution` of that exact profile, a
  `Cone` is stacked on top. Tested alternatives (JCMgeo 5.2.1, mesh volumes checked):
  - `Cone` with a filleted end (previous version): works but ~7x more elements; the coarse
    `test` solve needed 8.5 M unknowns and 231 GB.
  - Revolved section only 300 nm tall: the air domain is silently missing from the mesh.
  - `SolidOfRevolution` alone: truncated 1000 nm above its base.
  - Cone + Sphere overlap: JCMgeo runs out of memory.

## Illumination and signal

- A focused Gaussian beam (`sources.jcmt`), as the instrument's parabolic mirror: focus on the
  SiN top surface at x = y = 0, waist lambda / (pi NA) = 4.85 um at 6.1 um, angular spectrum
  limited to NA 0.4, `THETA` = 60 deg from the normal, travelling +x and down; source 1 is
  s-polarized, source 2 p-polarized. With a waist of a few um the upper shaft and the 15 um
  wide flat tip top are barely lit (a plane wave lit them fully, see below).
- JCM defines the beam by angles (`ThetaPhi`, `SP`), so the `beamcheck` stage evaluates only the
  incident beam and stores in `results/beamcheck.json` which `ThetaPhi` travels along +x and which
  `SP` gives s (E along y) / p; it stops if the direction, the 60 deg angle or the spot position
  are off. All other stages read that file (and stop if it is missing).
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
  - JCM's own accuracy estimates: `est_error_FarField` / `est_error_NearField` per refinement
    level and `pml_quality` (per boundary compartment, with the PML thickness level);
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
| `beamcheck` | 0 (incident beam only) | beam direction, s / p assignment, spot on the focus; writes `results/beamcheck.json` |
| `linescan_h5` | 31 | exploratory: raw (not demodulated) signal across the interface at a fixed 5 nm gap, fine mesh, 1 refinement step (~3 % mesh noise expected) |
| `linescan_h101` | 31 | same positions at 101 nm (top of the tapping range); `plot_linescan.py diff` shows E(5 nm) - E(101 nm), which cancels the height-independent far-field drift |
| `converge` | 6 | gaps 1 - 6 nm with 3 HAdaptive refinement steps (coarse start), saves field slices: does the mesh-to-mesh noise of the 1-step runs go away? |
| `test` | 1 | does it run (coarse mesh), cost per solve, far-field sampling (stops if < 50 directions in the cone) |
| `zsweep` | 35 | dense height sweep at the interface: are the 14 heights enough for S_n? |
| `coarse_check` | 14 | same position on the coarse mesh: mesh convergence |
| `noise` | 42 | interface 1 um away, moved by 3 nm: remeshing noise compared with the edge contrast |
| `scan` | 434 | 31 positions (5 nm steps within +-50 nm, out to +-300 nm) x 14 heights at 6.1 um |
| `scan_5.5um` | 434 | the same scan at 5.5 um (water contrast from n only, k small) |

**Next run:** `sbatch submit.sbatch linescan_h101` (on `bigmem`, ~11 h).

What the Gaussian-beam runs showed so far:
- `beamcheck`: `ThetaPhi` 180 travels +x, `SP [1 0]` = s, `[0 1]` = p; spot within 150 nm of the focus.
- `converge` (gaps 1 - 5 nm, 3 refinement steps): |Ep| rises smoothly by ~1e-4 per nm, no
  mesh zigzag; JCM's error estimate still ~10 - 20 % at the last level (looks systematic).
- `linescan_h5` (31 positions, 1 step): point-to-point noise ~1e-4 (amplitude), ~0.1 mrad (phase).
  Amplitude and phase drift almost linearly over +-300 nm, for p and for s (which has no
  near-field hot spot): far-field change as the oil block under the ~10 um beam footprint grows.
  A near-field step is not resolvable on top of it (phase hint of ~ -0.13 mrad near -40 nm).
  Hence `linescan_h101` and the E(5) - E(101) difference.

What the plane-wave runs showed (results in `results/old_planewave/`):
- 1 refinement step (`zsweep`): ~3 % scatter between neighbouring heights; JCM's own far-field
  error estimate ~1.9 % for every solve, +X PML stuck at thickness level 0 (quality ~0.22).
  S_2 was only ~5x above that noise, S_3 at the noise floor.
- 3 refinement steps (`converge`, gap 1 nm): 5.7 M unknowns, 156 GB, 39 min, but the error
  estimate went 3.9 % -> 17.6 % -> 12.7 % while the PML was thickened: the solution was not
  converged and was dominated by the exterior / PML treatment. The plane wave lit the whole
  13 um tip, whose 15 um wide top sits only ~0.5 um from the boundaries; the focused beam is
  meant to remove most of that.
- Field slices (gap 1 nm): p-incidence gives a ~84x enhanced, confined hot spot under the apex
  reaching ~100 - 200 nm through the SiN into the liquid; s-incidence gives no hot spot.

Settings are at the top of `run_linescan.py` (`STAGES`, `HEIGHTS`, `X_SCAN`, `THETA`, `NA`,
`TAP_AMPLITUDE`, `MIN_GAP`, `MATERIAL_FILES`, `GEOMETRY`, `MESH`).

```
python plot_linescan.py test | zsweep | coarse_check | noise | scan | converge | linescan_h5 | diff   # analysis per stage
python plot_fields.py results/fields/converge_x+0_g1.npz [s|p] [abs|Ex|Ey|Ez]  # field slices
python run_linescan.py --jcm [--coarse]                              # write .jcm for JCMcontrol
```

## Field slices and logs

- `project.jcmpt` (template; `jcmwave.solve` turns it into `project.jcmp`) exports two vertical
  slices through the tip axis after every solve: `slice_yz` (x = 0, parallel to the interface)
  and `slice_xz` (y = 0, perpendicular to it), +-600 nm laterally, z = -305 ... 1000 nm,
  2 nm spacing around the apex / gap / SiN and 10 nm further out.
- Stages with `save_fields=True` (`converge`, `test`) keep them in `results/fields/` as
  compressed npz (~2.3 MB per solve, both polarizations).
- `results/jcm_<stage>.log` holds JCM's full console output of every solve; `run_log.txt`
  has one line per solve including the far-field error estimate and the +X PML quality.
- `MaxNumberSteps` is set per mesh preset (`MESH[...]['max_steps']`).
- A stage refuses to continue a results file made with a different geometry, mesh preset,
  wavelength or materials (move the old file away first).

## Cost notes

- Every solve changes the geometry, so JCMgeo remeshes every time
  (about 1 minute for the fine mesh, plus the 3D solve; the `test` stage measures the real cost).
- On SLURM the job uses the allocated cores, and with `--mem` set JCM is told 90 % of it, so a
  too-large job aborts with an error in the log instead of being killed silently.
- Requires the `JCMROOT` environment variable; `jcmwave` is imported from the installation.
