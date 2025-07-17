# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RegionUtils as RegUt 

HA_PER_KM2 = 100.0

class GLOBIO_AggregateNdeposition(CalculationBase):
  """Aggregates Nitrogen deposition raster to region-level.
  """

  #-------------------------------------------------------------------------------
  def run(self, *args):
    """
    IN EXTENT extent
    IN CELLSIZE cellsize
    IN RASTER nitrogen_deposition_raster
    IN RASTER area_raster
    IN RASTER region_raster
    OUT FILE region_ndep_table
    """

    # Check number of arguments.
    if len(args) != 6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2, len(args), self.name)

    extent = args[0]
    cellsize = args[1]
    nitrogen_deposition_raster_file = args[2]
    area_raster_file = args[3]
    region_raster_file = args[4]
    region_ndep_table_file = args[5]

    self.checkExtent(extent)
    if cellsize > 0:
      self.checkCellSize(cellsize)
    self.checkRaster(nitrogen_deposition_raster_file)
    self.checkRaster(area_raster_file)
    self.checkRaster(region_raster_file)
    self.checkFile(region_ndep_table_file, asOutput=True)

    if cellsize <= 0:
      cellsize = self.getMinimalCellSize([region_raster_file, area_raster_file])
      Log.info("Using cellsize: %s" % cellsize)

    # Align extent.
    extent = RU.alignExtent(extent, cellsize)

    # read rasters
    ndep_raster = self.readAndPrepareInRaster(extent, cellsize, nitrogen_deposition_raster_file, "ndep")
    region_raster = self.readAndPrepareInRaster(extent, cellsize, region_raster_file, "region")
    area_raster = self.readAndPrepareInRaster(extent, cellsize, area_raster_file, "area")

    # calculate deposition per cell by mulplying deposition density by cell area
    # set nodata values to zero such as not to interfere with sum
    nodata_mask = (ndep_raster.r == ndep_raster.noDataValue) | np.isnan(ndep_raster.r)
    ndep_raster.r[nodata_mask] = 0
    del nodata_mask

    ndeparea_raster = Raster()
    ndeparea_raster.initRaster(extent, cellsize, np.float64, 0)
    ndeparea_raster.r = ndep_raster.r * area_raster.r * HA_PER_KM2
    del ndep_raster
    del area_raster

    # calculate unique regions
    region_list = RegUt.createRegionListFromRegionRaster(region_raster, includeNoDataValue=False)

    # calculate the areas per region
    Log.info("Aggregating nitrogen deposition per region...")

    RegUt.writeRegionAreas(
      region_raster,
      ndeparea_raster,
      region_list,
      ["ISO3#", "deposition_kg"],
      region_ndep_table_file
    )

    Log.info(f"Wrote region aggregations to {region_ndep_table_file}")
