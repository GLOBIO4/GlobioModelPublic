# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#-------------------------------------------------------------------------------

import os
import numpy as np

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Core.CellArea as CA
import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticRiverFractions import AquaticRiverFractions
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticRiverFractions(CalculationBase):
  """
  Calculates fractions for rivers.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Rivers
    IN FLOAT RiverWidthKM
    OUT RASTER RiverFractions
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    rivShapeFileName = args[2]
    rivWidthKM = args[3]
    outRasterName = args[4]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(rivShapeFileName)
    self.checkFloat(rivWidthKM,0.0,9999.0)
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

    Log.info("Reading shapefile...")

    # Read shapefile.
    inVector = Vector(rivShapeFileName)
    inVector.read()

    # Get lines.
    lines = [loads(feat.GetGeometryRef().ExportToWkb()) for feat in inVector.layer]

    Log.info("Total number of features found: %s" % len(lines))    

    # Clean up.
    inVector.close()
    inVector = None

    #-----------------------------------------------------------------------------
    # Calculate the watertype length raster.
    #-----------------------------------------------------------------------------

    # Create worker.
    # 20201118
    #w = AquaticRiverFractions()
    w = AquaticRiverFractions(-1)
    nrOfChunks = w.nrOfCores * 4

    # Calculate watertype length raster.
    w.debug = self.debugPrint
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    wtLenRaster = w.run(extent,cellSize,lines,nrOfChunks)

    # Save temporary data?
    if GLOB.saveTmpData:
      Log.info("Writing watertype length raster...")
      # Create tmp raster name.
      tmpRasterName = os.path.join(self.outDir,"tmp_"+os.path.basename(outRasterName))
      # Remove tmp data.
      RU.rasterDelete(tmpRasterName)
      # Write watertype area.
      wtLenRaster.writeAs(tmpRasterName)

    # Clean up.
    lines = None

    #-----------------------------------------------------------------------------
    # Create the river fraction raster.
    #-----------------------------------------------------------------------------
    Log.info("Creating watertype fraction raster...")

    # Create fraction raster.
    outRaster = Raster(outRasterName)
    noDataValue = -999.0
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate the river length.
    #-----------------------------------------------------------------------------

    # Select valid watertype cells.
    mask = (wtLenRaster.r > 0.0)
      
    Log.info("Calculating river area...")

    # Calculate area.
    outRaster.r[mask] = wtLenRaster.r[mask] * rivWidthKM

    # Clean up.
    wtLenRaster.close()
    wtLenRaster = None

    #-----------------------------------------------------------------------------
    # Correct the river area for high/low lattitude.
    #-----------------------------------------------------------------------------

    Log.info("Correcting river area...")

    # Create the cell area ratio raster array.
    ratioRas = CA.createCellAreaRatioRaster(extent,cellSize)

    # Correct the area.
    outRaster.r[mask] *= ratioRas[mask]

    # Clean up.
    ratioRas = None

    #-----------------------------------------------------------------------------
    # Create the cell area raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating cell area raster...")
    
    # Create the cell area raster array.
    areaRas = CA.createCellAreaRaster(extent,cellSize)

    #-----------------------------------------------------------------------------
    # Calculate the watertype fraction raster.
    #-----------------------------------------------------------------------------
       
    Log.info("Calculating fraction...")

    # Calculate fraction.
    outRaster.r[mask] /= areaRas[mask]

    # Clean up.
    areaRas = None

    # Correct fractions (not greater than 1.0).
    corrMask = np.logical_and(mask,(outRaster.r > 1.0))
    outRaster.r[corrMask] = 1.0

    # Cleanup.
    mask = None
    corrMask = None

    #-----------------------------------------------------------------------------
    # Write fraction raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing watertype fraction raster...")

    # Write watertype fraction.
    outRaster.write()

    # Cleanup.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.saveTmpData = False
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True

    pCalc = GLOBIO_AquaticRiverFractions()
    pCalc.debugPrint = False
    
    extentName = "wrld"
    #extentName = "nl"
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    if extentName == "nl":
      inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      inShp = "rivers_nl.shp"
    else:
      inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      inShp = "rivers_%s.shp" % extentName
    
    outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20181123" % (cellSizeName,extentName)
    out = "river_fractions.tif"

    #riverWidthKM = 1.0       # Is 30sec cellsize!!!
    riverWidthKM = 0.1
    
    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Create outdir.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    # Set input/output data.
    inShp = os.path.join(inDir,inShp)
    out = os.path.join(outDir,out)

    # Remove output data.
    RU.rasterDelete(out)    
    
    # Run.
    pCalc.run(ext,cs,inShp,riverWidthKM,out)
  except:
    MON.cleanup()
    Log.err()
  
