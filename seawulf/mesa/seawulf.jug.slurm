#!/bin/bash
#SBATCH --job-name=mesa_cauchy_grid
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=40
#SBATCH --cpus-per-task=1
#SBATCH --time=48:00:00
#SBATCH --output=mesa_cauchy_grid.txt
#SBATCH --error=mesa_cauchy_grid_error.txt
#SBATCH -p long-40core

module load shared
module load maui
module load slurm/17.11.12
module load mvapich2/gcc/64/2.2rc1
module load gcc
module load anaconda/3

source /gpfs/home/dwillcox/codes/mesa-for-UQ/revision-8118/setup_mesa.sh

export PATH="/gpfs/home/dwillcox/job-run-scripts:$PATH"
export PATH="/gpfs/home/dwillcox/.local/bin:$PATH"

export OMP_NUM_THREADS=1

cd $SLURM_SUBMIT_DIR

# May need to delete multitask_.jugdata/ before running
rm -rf multitask_.jugdata

mpiexec jug execute multitask_jug
