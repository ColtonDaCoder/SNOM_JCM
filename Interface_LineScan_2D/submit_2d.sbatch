#!/bin/bash
#SBATCH -J LineScan_2D
#SBATCH -A ----ALLOCATION----
#SBATCH -p single
#SBATCH -N 1
#SBATCH --ntasks-per-node 8
#SBATCH -t 72:00:00
#SBATCH -o results/slurm-%j.out

# Usage (from inside Interface_LineScan_2D; -A on the command line overrides the line above):
#   sbatch -A <allocation> submit_2d.sbatch                         # beamcheck test converge_fine converge_veryfine
#   sbatch -A <allocation> submit_2d.sbatch scan_h5 scan_wide       # any list of stages from run_2d.py
#   sbatch -A <allocation> submit_2d.sbatch "scan_demod_sin20 --part 1/2" # one part of a split stage (quote it; only 2 JCM licenses)
# Every stage / part solves in its own work/<stage> folder, so several jobs can run at once
# (also next to the 3D jobs).  Stages are resumable.  Afterwards commit and push results/.

STAGES=${@:-beamcheck test converge_fine converge_veryfine}

cd "$SLURM_SUBMIT_DIR"
echo "job $SLURM_JOB_ID on $(hostname), $(nproc) cores, stages: $STAGES"
echo "JCMROOT=$JCMROOT"
if [ $# -eq 0 ]; then set -- beamcheck test converge_fine converge_veryfine; fi
for s in "$@"; do
    python run_2d.py --stage $s || { echo "stage $s failed, stopping"; exit 1; }
done
