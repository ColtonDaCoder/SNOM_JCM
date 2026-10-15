#!/bin/bash
#SBATCH -J Interface_LineScan_3D
#SBATCH -A ----ALLOCATION----
#SBATCH -p single
#SBATCH -N 1
#SBATCH --ntasks-per-node 8
#SBATCH -t 150:00:00
#SBATCH -o results/slurm-%j.out
##SBATCH --mem=64G        # uncomment / adjust if the partition does not give enough memory by default

# Usage (from inside Interface_LineScan_3D):
#   sbatch submit.sbatch                  # stages: test zsweep coarse_check noise scan
#   sbatch submit.sbatch scan_5.5um       # any list of stages from run_linescan.py
# Stages are resumable, so resubmitting continues where the last job stopped.
# Afterwards commit and push the whole results/ folder (pkl files, run_log.txt, slurm-*.out).

# JCMROOT must point to the JCMsuite installation (run_linescan.py imports jcmwave from it)
# export JCMROOT=/path/to/JCMsuite

STAGES=${@:-test zsweep coarse_check noise scan}

cd "$SLURM_SUBMIT_DIR"
echo "job $SLURM_JOB_ID on $(hostname), $(nproc) cores, stages: $STAGES"
echo "JCMROOT=$JCMROOT"
for s in $STAGES; do
    python run_linescan.py --stage "$s" || { echo "stage $s failed, stopping"; exit 1; }
done
