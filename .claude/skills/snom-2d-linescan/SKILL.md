---
name: snom-2d-linescan
description: Workflow for the JCMsuite 2D s-SNOM model in Interface_LineScan_2D (Pt tip over layered / water-oil samples) - adding stages to run_2d.py, giving the cluster sbatch command, pulling results, demodulating S1-S4 and plotting. Use when the user asks to set up, run, pull, analyse or plot 2D SNOM simulations (line scans, window comparisons, depth maps, uniform stacks, near-field maps).
---

# 2D s-SNOM simulations (Interface_LineScan_2D)

## The model
- JCMsuite 6.0.10, 2D Cartesian (x lateral, y height, invariant along z). y = 0 is the sample top surface.
- Pt tip: 75 nm apex radius, 30.14 deg half-angle, length 12.94 um. In 2D it is a ridge, so the numbers are qualitative relative to a 3D cone.
- Illumination: p-polarised at 60 deg, backscatter collected in NA 0.4. Tapping is h = 1 + 50(1 + cos wt) nm.
- Heights: `HEIGHTS` (14 values, 1-101 nm) plus 5 nm, giving 15 gaps per position.
- Mesh preset `fine` is the production mesh. `veryfine` is only for convergence checks.
- Domain IDs:

  | ID | Material | Data file |
  |---|---|---|
  | 1 | air | |
  | 2 | water | Hale & Querry |
  | 3 | Pt | Rakic BB |
  | 7 | window / Si3N4 | Kischkat, or the stage's window file |
  | 9 | oil / OTS | n-octane, Myers |
  | 10 | window above the oil | equivalent-layer stages |
  | 11 | Si | Li 1980, `optical_data/Si_Li1980.csv` |

- Files:
  - `layout.jcmt`, `materials.jcmt`, `sources.jcmt`, `project.jcmpt`: templates.
  - `run_2d.py`: the stage definitions (`STAGES`) and the runner.
  - `plot_2d.py`: plots, run as `python plot_2d.py <keyword>`.
  - `depthmap.py`: depth-sensitivity maps.
  - `stack_diagram.py`: schematic of the uniform stacks.
- Results go in `results/<stage>.pkl` and `results/run_log.txt`. Field maps go in `results/fields/<stage>_x+0_g<gap>.npz`, which holds X, Y and E[source, ix, iy, xyz], with source 1 = p.

## Adding a stage
Add an entry to `STAGES` in `run_2d.py`, before `MIN_DIRECTIONS`:
`dict(mesh='fine', wvl=<um>, x=[...], gaps=sorted(HEIGHTS + [5]), geom={...}, ...)`

Options:
- `geom`: overrides `GEOMETRY`, for example `{'t_SiN': 20}`.
- `window='<file>.csv'`: the material for domain 7.
- `eqlayer=dict(...)`: an equivalent layer for monolayers. A 0.33 nm layer cannot be meshed (it gives 551k triangles).
- Uniform stacks: `geom={'t_SiN': total, 'stack': [[DomainId, thickness_nm], ...], 'stack_substrate': DomainId}`. Layers are listed from the top down.
- `extra_materials={'Si': 'Si_Li1980.csv'}`: needed when the stack uses domain 11.
- `field_map=True`: near-field map, x +-250 nm and y -60 to gap+150 nm, 5 nm grid. Keep it to one gap. `field_map='depth'` exports the field inside the liquid instead.

Also:
- Update the module docstring.
- Check the geometry locally (JCMgeo, no licence needed) before committing: `python run_2d.py --stage meshcheck`, or render the `.jcm` files with `--jcm`.

## Running on the cluster
The cluster is LSU SuperMIC, repo at `/ddnA/work/coltonb/SNOM_JCM`. The user runs the jobs. Commit and push the new stages (only when asked), then give the command:
```bash
cd /ddnA/work/coltonb/SNOM_JCM/Interface_LineScan_2D
git pull
sbatch -A <allocation> submit_2d.sbatch <stage1> <stage2> ...
```
- Give one plain sbatch line. No dependency chains or `$j1` variables.
- **Only one JCM licence is usable**, out of 2 shared with the 3D jobs. Never suggest concurrent jobs unless the user says a second licence is free.
- Stages are resumable: finished points are skipped. A stage stops after 3 consecutive failures. The job limit is 72 h.
- A `fine` solve takes about 6-7 min, so 15 heights is about 1.5-2 h per position.
- The cluster pushes `results/` and you `git pull` locally to get them.
- Do not edit the 3D `submit.sbatch`.

## Analysis
- Demodulation: spline E_p (backscattered p far field) over the heights, sample one tapping cycle, take the n-th Fourier coefficient to get S_n, a complex value.
  - `plot_2d.demodulate` and `plot_2d.demod_rows(set_name)` do this. `N_HEIGHTS = 14` means one failed height is tolerated as long as 1-101 nm is still covered.
- Edge metrics for a line scan: normalise S_n between the oil plateau (x <= -500) and the water plateau (x >= 500). Report the 10-90% and 20-80% widths and the FWHM of the line spread function. S2/S3 is the cleanest signal.
- Depth maps: demodulate E.E at each point. The in-phase part is p_n = Re(w_n e^{-i arg W}). The 50% and 90% contours enclose the smallest regions holding that share of the signal.
- When the user wants values: print tables of |S_n|, arg S_n, ratios between cases, and convergence (JCM error estimate). Save the raw numbers to `results/*.csv` when asked.

## Preferences (standing)
- Never lower simulation accuracy to save resources. Failing is better than a degraded mesh, blended layers or approximations the user did not ask for.
- Keep 2D exports minimal. JCM point export costs about 4 s per point. Check post-processing timings first if runs are slow.
- Ask for approval before setting up any new sweep or stage the user did not request.
- Plots for the PI: simple, lines between points, no notes, annotations or fits unless asked.
- Often the user wants **values, not plots**. Give numbers first.
- Commit and push only when asked. End commit messages with the attribution line from the session's system instructions.
- Graphene/hBN window stages (`win_graphene_*`, `win_hBN_*`) are on hold until the user resumes them.
