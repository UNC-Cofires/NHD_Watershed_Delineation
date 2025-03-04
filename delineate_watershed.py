import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon
import matplotlib.pyplot as plt
import networkx as nx
import os

### *** HELPER FUNCTIONS *** ###

def get_watershed_boundaries(source_comid,G,catchments):
    """
    param: source_comid: comid of source NHD flowline
    param: G: NetworkX DiGraph object encoding flow network
    param: catchments: pandas geodataframe of NHD catchment polygons
    
    returns: watershed_polygon: polygon describing area upstream of source comid
    returns: proportion_matched: float describing the share of flow network members found in catchments geodataframe
                                 (should ideally be close to 1.0, otherwise we're missing parts of the watershed) 
    """
    upstream_comids = list(nx.ancestors(G,source_comid))
    watershed_comids = [source_comid] + upstream_comids
    proportion_matched = pd.Series(watershed_comids).isin(catchments['COMID']).mean()
    watershed_polygon = catchments[catchments['COMID'].isin(watershed_comids)]['geometry'].union_all()
    return(watershed_polygon,proportion_matched)

def write_geodatabase(gdf,filepath,layer_name,polygons_as_points=False):
    """
    param: gdf: pandas geodataframe
    param: filepath: filepath to geodatabase
    param: layer_name: name of layer in geodatabase to save file to
    param: polygons_as_points: if true, convert polygon geometries to points based on centroid
    """
    
    # If geodataframe contains mix of polygons and multipolygons,
    # upcast polygons to multipolygons

    geom_types = list(gdf['geometry'].geom_type.unique())
    geom_types.sort()

    if polygons_as_points:
        if any(x in geom_types for x in ['Polygon','MultiPolygon']):
            gdf['geometry'] = gdf['geometry'].centroid

    elif len(geom_types) > 1:
        print('warning: multiple geometry types in geodataframe')
        if geom_types == ['MultiPolygon','Polygon']:
            print('upcasting polygons to multipolygons to achieve consistency')
            gdf['geometry'] = [MultiPolygon([feature]) if feature.geom_type == 'Polygon' else feature for feature in gdf['geometry']]

    gdf.to_file(filepath,layer=layer_name,driver='OpenFileGDB')

    return(None)

### *** INITIAL SETUP *** ###

# Get current working directory 
pwd = os.getcwd()

# Specify desired coordinate reference system
crs = 'EPSG:4269'

# Specify path to NHDPlusV2 medium-resolution dataset
# Available at: https://www.epa.gov/waterdata/nhdplus-national-data
NHD_path = '/proj/characklab/projects/kieranf/flood_damage_index/data/NHDPlusMRData/NHDPlusNationalData/NHDPlusV21_National_Seamless_Flattened_Lower48.gdb'

# Specify path to enhanced NHDPlusV2 flow network dataset
# (This dataset more accurately models connectivity between flowlines than original release)
# Available at: https://doi.org/10.5066/P13IRYTB
ENHD_path = '/proj/characklab/projects/kieranf/flood_damage_index/data/ENHDPlusV2/enhd_nhdplusatts.parquet'

# Specify path to 2-digit HUC region shapefile
huc_regions_path = '/proj/characklab/projects/kieranf/flood_damage_index/data/watersheds/CONUS_WBD_HU2'

# Specify path to dataset of stream gage station points that includes latitude/longitude
station_path = os.path.join(pwd,'site_info.csv')

### *** LOAD INPUT DATA *** ### 

## Define which HUC regions to include

# Options are: 
#    01: New England Region
#    02: Mid Atlantic Region
#    03: South Atlantic-Gulf Region
#    04: Great Lakes Region
#    05: Ohio Region
#    06: Tennessee Region
#    07: Upper Mississippi Region
#    08: Lower Mississippi Region
#    09: Souris-Red-Rainy Region
#    10: Missouri Region
#    11: Arkansas-White-Red Region
#    12: Texas-Gulf Region
#    13: Rio Grande Region
#    14: Upper Colorado Region
#    15: Lower Colorado Region
#    16: Great Basin Region
#    17: Pacific Northwest Region
#    18: California Region

# Note that you might want to list more than just one (e.g., ['14','15'] for upper and lower colorado) 
included_hucs = ['18']
huc_regions = gpd.read_file(huc_regions_path).to_crs(crs)
study_area_mask = huc_regions[huc_regions['huc2'].isin(included_hucs)].dissolve()['geometry'].values[0]

## Read in NHD flowlines and catchment polygons

# This step can take a long time if you are reading in the entire CONUS
# To improve speed, use the "mask" argument to filter out data that falling outside study area
flowlines = gpd.read_file(NHD_path,layer='NHDFlowline_Network',mask=study_area_mask).to_crs(crs)
catchments = gpd.read_file(NHD_path,layer='Catchment',mask=study_area_mask).to_crs(crs)
catchments = catchments.rename(columns={'FEATUREID':'COMID'})

## Read in ENHD flowtable 
flowtable = pd.read_parquet(ENHD_path)
flowtable[['comid','tocomid']] = flowtable[['comid','tocomid']].astype(int)

### REPRESENT FLOW NETWORK AS DIRECTED GRAPH ###

# Initialize directed graph object
G = nx.DiGraph()

# Add nodes
G.add_nodes_from(flowtable['comid'])

# Add edges
terminal_flows = (flowtable['tocomid']==0) # Want to exclude terminal flows 
edges = [tuple(x) for x in flowtable[~terminal_flows][['comid','tocomid']].to_numpy()]
G.add_edges_from(edges)

### READ IN DATA ON GAGE LOCATIONS ###

stations = pd.read_csv(station_path)

# Create points from latitude/longitude data

stations = gpd.GeoDataFrame(stations,geometry=gpd.points_from_xy(stations['dec_long_va'],stations['dec_lat_va'],crs=crs))

# Spatially join station points to NHD catchment polygons 
stations = gpd.sjoin(stations,catchments[['COMID','geometry']],how='inner').drop(columns='index_right')

# Create separate geodataframe that we'll use to keep track of watershed geometry 
watersheds = stations.copy()

### GET AREA UPSTREAM OF EACH GAGE ###

watersheds['proportion_matched'] = np.nan

for i in watersheds.index.values:
    source_comid = watersheds.loc[i,'COMID']
    watersheds.loc[i,'geometry'],watersheds.loc[i,'proportion_matched'] = get_watershed_boundaries(source_comid,G,catchments)
    
    site_no = watersheds.loc[i,'site_no']
    match_rate = np.round(100*watersheds.loc[i,'proportion_matched'],1)
    
    print(f'site_no: {site_no} match_rate: {match_rate}%',flush=True)
    
# Create figure to verify that things are working as intended
fig,ax = plt.subplots(figsize=(6,6))

gpd.GeoSeries(study_area_mask).plot(ax=ax,facecolor='none',edgecolor='k')

watersheds.plot(ax=ax,facecolor='C0',alpha=0.4)
stations.plot(ax=ax,color='C3',markersize=10)

ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.grid('on')

fig.savefig('streamgage_contributing_area.png',dpi=300)
fig.show()

### SAVE OUTPUT AS GEODATABASE ###  

output_gdb = os.path.join(pwd,'streamgage_contributing_area.gdb')
write_geodatabase(stations,output_gdb,'stations')
write_geodatabase(watersheds,output_gdb,'watersheds')