# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           14 dec 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - "frag_" added.
#           18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Argument NumberOfCores added.
#-------------------------------------------------------------------------------

import os
import numpy as np

from shapely.wkb import loads

# NA shapely.
#import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Core.CellArea as CA
#import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.RasterFunc import RasterFunc
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticFragmentationDamDensity(CalculationBase):
  """
  Calculates the damdensity as an indicator for river fragmentation.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Dams
    IN RASTER Catchments
    IN INTEGER NumberOfCores
    OUT RASTER DamDensity
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    damShapeFileName = args[2]
    catchmentRasterName = args[3]
    nrOfCores = args[4]
    outRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(damShapeFileName)
    self.checkRaster(catchmentRasterName)
    self.checkInteger(nrOfCores,-9999,9999)    
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading dams...")

    # Read shapefile.
    inVector = Vector(damShapeFileName)
    inVector.read()

    # Get points.
    points = [loads(feat.GetGeometryRef().ExportToWkb()) for feat in inVector.layer]
    
    Log.info("Total number of features found: %s" % len(points))    

    # Clean up.
    inVector.close()
    inVector = None

    #-----------------------------------------------------------------------------
    # Create dam raster.
    #-----------------------------------------------------------------------------

    # Initialize with 0.0.
    Log.info("Creating dam raster...")
    dataType = np.uint16
    noDataValue = RU.getNoDataValue(dataType)
    damRaster = Raster(outRasterName)
    damRaster.initRaster(extent,cellSize,dataType,noDataValue)

    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)

    Log.info("Rasterizing dams...")

    # Rasterize points with number of dams per cell.
    for point in points:
      # Get col/row of raster.
      col,row = RU.calcColRowFromXY(point.x,point.y,extent,cellSize)
      # Inside the working extent?
      if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
        # Set raster cell value.
        if damRaster.r[row,col] == damRaster.noDataValue:
          damRaster.r[row,col] = 1
        else:
          damRaster.r[row,col] += 1

    mask = damRaster.getDataMask()
    self.dbgPrint("damRaster sum mask %s" % np.sum(damRaster.r[mask]))
    mask = np.logical_and(mask,damRaster.r>1)
    self.dbgPrint("damRaster sum mask+>1 %s" % np.sum(damRaster.r[mask]))
    self.dbgPrint("damRaster where %s" % (np.argwhere(damRaster.r ==1)))
    
    # Clean up.
    points = None

    #-----------------------------------------------------------------------------
    # Read the catchment raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    catchmentRaster = self.readAndPrepareInRaster(extent,cellSize,catchmentRasterName,"catchment")

    # TODO: Ignore warning.
    self.dbgPrint("catchmentRaster ids %s" % (np.unique(catchmentRaster.r)))

    #-----------------------------------------------------------------------------
    # Calculate areas.
    #-----------------------------------------------------------------------------

    Log.info("Calculating areas...")

    # Calculate areas.
    areaRaster = Raster()
    areaRaster.initRasterEmpty(extent,cellSize,np.float32)
    areaRaster.r = CA.createCellAreaRaster(extent,cellSize,np.float32)
    
    #-----------------------------------------------------------------------------
    # Calculate dam density.
    #
    # Using scipy.ndimage.labeled_comprehension() is very slow (>58h) for 30sec
    # rasters (under linux).
    #-----------------------------------------------------------------------------

    Log.info("Calculating dam density...")

    # Create raster worker.
    rw = RasterFunc(nrOfCores)
    rw.debug = self.debugPrint
    
    Log.info("  Using: %s cores" % (rw.nrOfCores))

    # Calculate dam density per catchment.
    densDict,sumDict,areaDict = rw.zonalCountDensity(
                                    extent,cellSize,
                                    catchmentRaster,damRaster,areaRaster)
    
    # Clean up.
    damRaster.close()
    damRaster = None
    areaRaster.close()
    areaRaster = None

    #-----------------------------------------------------------------------------
    # Create dam density raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating dam density raster...")

    # Label the catchments with the density values.
    outRaster = rw.label(extent,cellSize,catchmentRaster,densDict,np.float32)

    self.dbgPrint("outRaster sum %s" % np.sum(outRaster.r))

    # Save temporary data?
    if GLOB.saveTmpData:
      # Label the catchments with the count values.
      tmpRaster = rw.label(extent,cellSize,catchmentRaster,sumDict,np.uint16)
      # Save the counts per zone.
      tmpName = "tmp_frag_catchment_dam_sum.tif"
      Log.info("- Writing sum per zone: "+tmpName)
      self.writeTmpRaster(tmpRaster,tmpName)

      # Label the catchments with the total area.
      tmpRaster = rw.label(extent,cellSize,catchmentRaster,areaDict,np.float32)
      # Save the counts per zone.
      tmpName = "tmp_frag_catchment_total_area.tif"
      Log.info("- Writing total area per zone: "+tmpName)
      self.writeTmpRaster(tmpRaster,tmpName)
      
      # Clean up.
      tmpRaster.close()
      tmpRaster = None

    # Clean up.
    catchmentRaster.close()
    catchmentRaster = None
    densDict = None
    sumDict = None
    areaDict = None

    #-----------------------------------------------------------------------------
    # Writing dam density raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing dam density raster...")

    # Write fragmentation.
    outRaster.writeAs(outRasterName)

    # Clean up.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
 
