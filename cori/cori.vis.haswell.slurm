#!/bin/bash
#
# Number of nodes:
#SBATCH --nodes=1
#
#################
# Haswell nodes
#################
#
# Requests Cori Haswell nodes:
#SBATCH --constraint=haswell
#
# Haswell: Assign 1 MPI task to each socket (2 sockets/node)
#SBATCH --tasks-per-node=32
#
# Haswell: each socket has 32 CPUs (with hyperthreading)
#SBATCH --cpus-per-task=1
#
#################
# Queue & Job
#################
#
# Which queue to run in: debug, regular, premium, etc. ...
#SBATCH --qos=debug
#
# Run for this much walltime: hh:mm:ss
#SBATCH --time=00:30:00
#
# Use this job name:
#SBATCH -J emu_vis
#
# Send notification emails here:
#SBATCH --mail-user=eugene.willcox@gmail.com
#SBATCH --mail-type=ALL
#
# Which allocation to use:
#SBATCH -A m3761

module load julia/1.6.0

export PYTHONPATH="/global/u2/d/dwillcox/dev-emu/Emu_scripts/data_reduction:$PYTHONPATH"

# On the compute node, change to the directory we submitted from
cd $SLURM_SUBMIT_DIR

julia distributed_tasks.jl "python3 emu_phase_volume_render.py {entry} -lo 0 0 0 -hi 8 8 8 -f all -o $SLURM_SUBMIT_DIR/volume_rendering_jl" --entries $(ls -d plt[0-9]*5) --nprocs 32
