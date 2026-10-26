#!/bin/bash
#SBATCH -J NP_NearField
#SBATCH -A ----ALLOCATION----
#SBATCH -p single
#SBATCH -N 1
#SBATCH --ntasks-per-node 8
#SBATCH -t 24:00:00
#SBATCH -o results/slurm-%j.out

# Usage (from inside NP_NearField_Cylindrical; -A on the command line overrides the line above):
#   sbatch -A <allocation> submit_np.sbatch            # all cases: R0 R25 R50 R75 (finished ones are skipped)
#   sbatch -A <allocation> submit_np.sbatch R50        # one case
# Afterwards commit and push results/ (npz maps, start meshes, logs, summary.json).

cd "$SLURM_SUBMIT_DIR"
echo "job $SLURM_JOB_ID on $(hostname), $(nproc) cores, cases: ${@:-all}"
echo "JCMROOT=$JCMROOT"
if [ $# -eq 0 ]; then
    python run_np.py --all
else
    for c in "$@"; do python run_np.py --case "$c" || { echo "case $c failed"; exit 1; }; done
fi
