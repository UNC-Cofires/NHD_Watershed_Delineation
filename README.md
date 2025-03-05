# Watershed Delineation with NHDPlusV2
This project allows you to determine the area that contributes flow to an arbitrary point on a river or 
stream within the contiguous United States (CONUS) based on the enhanced NHDPlus Version 2 medium-resolution river 
network dataset.
## Setup
These instructions assume you are conducting the analysis on UNC's Longleaf HPC cluster. Additional 
documentation on using Longleaf can be found at: https://help.rc.unc.edu/
### Python environment
To create a conda environment that contains all required dependencies, run the following commands from within 
a command-line session on Longleaf:

```
module purge
module load anaconda
conda create --name=nhd_env_v1 python=3.12 
conda activate nhd_env_v1 
pip install -r requirements.txt
python -m ipykernel install --user --name=nhd_env_v1
```
Note that the final command is optional, and is only necessary if you would like to be 
able to use the environment within an interactive Jupyter notebook session in [Open 
OnDemand](https://ondemand.rc.unc.edu/).
### Input data sources
The analysis scripts in this project rely on the following sources of input data, which you will need to have 
downloaded on Longleaf:
- NHDPlusV2 medium-resolution dataset 
([link](https://www.epa.gov/waterdata/nhdplus-national-data)) 
- Enhanced NHDPlusV2 flow network dataset 
([link](https://doi.org/10.5066/P13IRYTB)) 
- A shapefile describing the boundaries of each 2-digit hydrologic 
unit code (HUC) region in the CONUS. This repository contains a shapefile named `CONUS_WBD_HU2` that will 
serve this purpose, but you can also create your own file using the U.S. Geological Survey (USGS) Watershed 
Boundary Dataset 
([link](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Hydrography/WBD/HU2/GDB/)).

Note that you will need to explicitly specify the paths to these files in the `delineate_watersheds.py` file.
### User-supplied points
In addition to the data sources listed above, the script also takes as input a CSV file containing the 
spatial coordinates (i.e., latitude/longitude) of points on a river network for which you would like to 
delineate the areas that contribute flow (i.e., the upstream watershed). This file should be structured in a 
similar manner to the `site_info.csv` file, which contains the coordinates of ten USGS stream gages in 
California as an example. The only columns that are required to be in this file are `dec_lat_va` and 
`dec_long_va` which (respectively) correspond to the latitude and longitude of stream gage locations.
### Job submission
If you are applying this script to a large number of points, it is recommended to submit a batch job that 
will run it on a compute node. An example job submission script is included in the `delineate_watersheds.sh` 
file. This job can be submitted to the queue by running the following command on Longleaf: 
```
sbatch < delineate_watersheds.sh
``` 
For more information on job submission, please see the following article: 
https://help.rc.unc.edu/longleaf-slurm-examples/
