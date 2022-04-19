# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
#           5 sep 2019, JH
#           -Script to calculate an overall MSA raster based on the raster outputs from
#            wb vertebrates and plants
#           December 2021
#           - adding MSA class-categories and high msa outputs (for GBW project)
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcOverallTerrestrialMSA(CalculationBase):
  """
  Creates a raster with total terrestrial MSA.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER TerrestrialMSA_wbvert
    IN RASTER TerrestrialMSA_plants
    IN RASTER AreaRaster
    OUT RASTER TerrestrialMSA
    OUT RASTER TerrestrialMSA_area
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    wbvertRasterName = args[2]
    plantRasterName = args[3]
    AreaRasterName = args[4]
    outRasterName = args[5]
    outRasterNameArea = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(wbvertRasterName)
    self.checkRaster(plantRasterName)
    self.checkRaster(AreaRasterName)
    self.checkRaster(outRasterName,True)
    self.checkRaster(outRasterNameArea,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)
    
    # Create terrestrial MSA raster.
    Log.info("Creating terrestrial MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Reads the wb vert and plant rasters and resizes to extent and resamples to cellsize.
    msaRaster_wbvert = self.readAndPrepareInRaster(extent,cellSize,wbvertRasterName,"wbvert")
    msaRaster_plants = self.readAndPrepareInRaster(extent,cellSize,plantRasterName,"plants")
    AreaRaster = self.readAndPrepareInRaster(extent,cellSize,AreaRasterName,"AreaRaster")

    # Calculate total MSA.
    Log.info("Calculating terrestrial MSA raster...")

    mask = (msaRaster_wbvert.r != msaRaster_wbvert.noDataValue) & (msaRaster_plants.r != msaRaster_plants.noDataValue)
    outRaster.r[mask] = (msaRaster_wbvert.r[mask] + msaRaster_plants.r[mask]) / 2.0
    
    # Calculate total MSA area.
    Log.info("Calculating terrestrial MSA area raster...")
    
    outRasterArea = Raster(outRasterNameArea)
    outRasterArea.initRaster(extent,cellSize,np.float32,noDataValue)
    outRasterArea.r[mask] = (outRaster.r[mask] * AreaRaster.r[mask])

    # Close and free the msa raster (for memory purposes moved up here).
    msaRaster_wbvert.close()
    msaRaster_wbvert = None 
    msaRaster_plants.close()
    msaRaster_plants = None
    AreaRaster.close()
    AreaRaster = None

    # Reclass the MSA values in 10 equal 0.1 classes
    Log.info("Reclassifying terrestrial MSA raster in 10 equal 0.1 classes...")
    outRasterCatName = outRasterName.replace(".tif","_10classes.tif")
    outRasterCat = Raster(outRasterCatName)
    outRasterCat.initRaster(extent,cellSize,np.int16,noDataValue)

    msaClassValue = 1
    lowerBoundary = 0.0

    while msaClassValue < 11:
      upperBoundary = lowerBoundary + 0.1
      #Log.info("Reclass info class " + str(msaClassValue) + ": boundaries are: " + str(lowerBoundary) + " - " + str(upperBoundary))
      mask = (outRaster.r != outRaster.noDataValue) & (outRaster.r >= lowerBoundary) & (outRaster.r < upperBoundary)
      outRasterCat.r[mask] = msaClassValue
      msaClassValue = msaClassValue + 1
      lowerBoundary = lowerBoundary + 0.1

    # Reclass the high MSA (>= 0.8) values in value 1
    Log.info("Reclassifying high terrestrial MSA values (>=0.8) in single value (1) raster...")
    outRasterHighName = outRasterName.replace(".tif","_high80.tif")
    outRasterHigh = Raster(outRasterHighName)
    outRasterHigh.initRaster(extent,cellSize,np.int16,noDataValue)
    mask = (outRasterCat.r >= 9)
    outRasterHigh.r[mask] = 1
    
    # Clear mask.
    mask = None
    
    # Save the terrestrial MSA raster.
    Log.info("Writing terrestrial MSA, MSA classes, high MSA and MSA-area rasters...")
    outRaster.write()
    outRasterArea.write()
    outRasterCat.write()
    outRasterHigh.write()
    
    # Cleanup.
    outRaster.close()
    outRaster = None
    outRasterArea.close()
    outRasterArea = None
    outRasterCat.close()
    outRasterCat = None
    outRasterHigh.close()
    outRasterHigh = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    mapDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\geodata\GlobalTifs\res_10sec"
    lookupDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\LookupGlobal"
    outDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    if not os.path.isdir(outDir):
      outDir = r"S:\hilbersj"

    pCalc = GLOBIO_CalcOverallTerrestrialMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec    
    lu = os.path.join(inDir,"LanduseMSA_test.tif")
    he = os.path.join(inDir,"HumanEncroachmentMSA_test.tif")
    nd = os.path.join(inDir,"NDepositionMSA_test.tif")
    cc = os.path.join(inDir,"ClimateChangeMSA_test.tif")
    di = os.path.join(inDir,"InfraDisturbanceMSA_test.tif")
    fr = os.path.join(inDir,"InfraFragmentationMSA_test.tif")
    out = os.path.join(outDir,"TerrestrialMSA_test.tif")
    
    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,lu,he,nd,cc,di,fr,out)
  except:
    Log.err()
