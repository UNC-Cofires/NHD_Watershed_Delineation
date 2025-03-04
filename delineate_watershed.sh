#!/bin/bash

#SBATCH -p general
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --mem=64g
#SBATCH -t 1-00:00:00
#SBATCH --mail-type=all
#SBATCH --job-name=flow_network
#SBATCH --mail-user=kieranf@email.unc.edu
export PYTHONWARNINGS="ignore"
module purge
module load anaconda/2023.03
conda activate /proj/characklab/projects/kieranf/flood_damage_index/fli-env-v1
python3.12 delineate_watershed.py
