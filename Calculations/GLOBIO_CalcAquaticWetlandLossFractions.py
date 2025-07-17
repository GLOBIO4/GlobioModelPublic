# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.CellArea as CA
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcAquaticWetlandLossFractions(CalculationBase):
  """
  Creates a raster with the fractions of loss and actual wetlands.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER Landuse10sec
    IN RASTER WetlandFractions
    OUT RASTER WetlandLossFractions
    OUT RASTER WetlandActualFractions
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    luRasterName = args[2]
    wetlandRasterName = args[3]
    outLossRasterName = args[4]
    outActualRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(luRasterName)
    self.checkRaster(wetlandRasterName)
    self.checkRaster(outLossRasterName,True)
    self.checkRaster(outActualRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outLossRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Create 10sec area raster for anthropogenic landuse.
    #-----------------------------------------------------------------------------

    Log.info("Creating anthropogenic area raster...")

    # Set 10sec cellsize.
    areaCellSizeName = "10sec"
    areaCellSize = GLOB.constants[areaCellSizeName].value

    # Create area raster.
    anthrAreaRaster = Raster()
    anthrAreaRaster.initRasterEmpty(extent,areaCellSize,np.float32,-999.0)
    anthrAreaRaster.r = CA.createCellAreaRaster(extent,areaCellSize,np.float32)

    #-----------------------------------------------------------------------------
    # Read landuse raster.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    luRaster = self.readAndPrepareInRaster(extent,areaCellSize,luRasterName,"landuse")

    #-----------------------------------------------------------------------------
    # Create mask for anthropogenic landuse.
    #-----------------------------------------------------------------------------

    Log.info("Selecting anthropogenic landuse...")

    # Set the anthropogenic landuse type: urban|crop|pasture.
    luTypes = [1,2,3]
    mask = None
    for luType in luTypes:
      if mask is None:
        mask = (luRaster.r == luType)
      else:
        mask = np.logical_or(mask,(luRaster.r == luType))
        
    # Set areas to 0.0 for all non-anthropogenic cells.
    anthrAreaRaster.r[~mask] = 0.0                     # pylint: disable=invalid-unary-operand-type

    # Cleanup.
    luRaster.close()
    luRaster = None
    
    #-----------------------------------------------------------------------------
    # Calculate anthropogenic area of 30sec cells.
    #-----------------------------------------------------------------------------

    Log.info("Calculating anthropogenic landuse area...")

    # Resample 10sec raster to 30sec and sum areas.
    resAnthrAreaRaster = anthrAreaRaster.resample(cellSize,calcSumDiv=True)
    
    # Cleanup.
    anthrAreaRaster.close()
    anthrAreaRaster = None

    #-----------------------------------------------------------------------------
    # Create 30sec total area raster.
    #-----------------------------------------------------------------------------

    # Create area raster.
    totAreaRaster = Raster()
    totAreaRaster.initRasterEmpty(extent,cellSize,np.float32,-999.0)
    totAreaRaster.r = CA.createCellAreaRaster(extent,cellSize,np.float32)

    #-----------------------------------------------------------------------------
    # Calculate anthropogenic fraction.
    #-----------------------------------------------------------------------------

    Log.info("Calculating anthropogenic fractions...")
    
    # Create anthropogenic fraction raster.
    anthrFracRaster = Raster()
    anthrFracRaster.initRasterEmpty(extent,cellSize,np.float32,-999.0)
    anthrFracRaster.r = resAnthrAreaRaster.r / totAreaRaster.r
    
    # Correct fractions > 1.0.
    mask = (anthrFracRaster.r > 1.0)
    anthrFracRaster.r[mask] = 1.0
    
    # Cleanup.
    mask = None
    resAnthrAreaRaster.close()
    resAnthrAreaRaster = None
    totAreaRaster.close()
    totAreaRaster = None

    #-----------------------------------------------------------------------------
    # Read the fractions raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    wetlandRaster = self.readAndPrepareInRaster(extent,cellSize,wetlandRasterName,"wetland fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting wetland fractions...")
    fracMask = (wetlandRaster.r > 0.0)

    #-----------------------------------------------------------------------------
    # Create output wetland loss raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating wetland loss raster...")

    # Create raster.
    # Initialize with NoData.
    noDataValue = -999.0
    outLossFracRaster = Raster(outLossRasterName)
    outLossFracRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate wetland loss.
    #-----------------------------------------------------------------------------

    Log.info("Calculating wetland loss fractions...")

    outLossFracRaster.r[fracMask] = wetlandRaster.r[fracMask] * anthrFracRaster.r[fracMask]

    #-----------------------------------------------------------------------------
    # Create output actual wetland raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating actual wetland raster...")

    # Create raster.
    # Initialize with NoData.
    noDataValue = -999.0
    outActualFracRaster = Raster(outActualRasterName)
    outActualFracRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate actual wetland.
    #-----------------------------------------------------------------------------

    Log.info("Calculating actual wetland fractions...")

    outActualFracRaster.r[fracMask] = wetlandRaster.r[fracMask] - outLossFracRaster.r[fracMask]

    # Cleanup.
    wetlandRaster.close()
    wetlandRaster = None
   
    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the wetland loss fractions.
    Log.info("Writing wetland loss fractions...")
    outLossFracRaster.write()

    # Cleanup.
    outLossFracRaster.close()
    outLossFracRaster = None

    # Save the wetland loss fractions.
    Log.info("Writing actual wetland fractions...")
    outActualFracRaster.write()

    # Cleanup.
    outActualFracRaster.close()
    outActualFracRaster = None
          
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.SHOW_TRACEBACK_ERRORS = True

    pCalc = GLOBIO_CalcAquaticWetlandLossFractions()
    
    extentName = "wrld"
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    inLuDir = r""
    inFrDir = r""
    outDir = r""

    if os.path.isdir("/root"):
      inLuDir = UT.toLinux(inLuDir)
      inFrDir = UT.toLinux(inFrDir)
      outDir = UT.toLinux(outDir)

    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    lu = os.path.join(inLuDir,"landuse_alloc_v2.tif")
    wfrac = os.path.join(inFrDir,"aq_wetland_fractions.tif")
    outLoss = os.path.join(outDir,"aq_wetland_loss_fractions.tif")
    outAct = os.path.join(outDir,"aq_wetland_actual_fractions.tif")

    RU.rasterDelete(outLoss)
    RU.rasterDelete(outAct)

    pCalc.run(ext,cs,lu,wfrac,outLoss,outAct)
  except:
    Log.err()
