# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

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
class GLOBIO_CalcAquaticWetlandMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for wetlands.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER WetlandFloodplainLanduseMSA
    IN RASTER WetlandLossFractions
    IN RASTER WetlandActualFractions
    IN FLOAT LOSS_MSA
    OUT RASTER WetlandMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    wetFloodLUMSARasterName = args[2]
    wetlandLossFractionsRasterName = args[3]
    wetlandActualFractionsRasterName = args[4]
    LOSS_MSA = args[5]
    outRasterName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(wetFloodLUMSARasterName)
    self.checkRaster(wetlandLossFractionsRasterName)
    self.checkRaster(wetlandActualFractionsRasterName)
    self.checkFloat(LOSS_MSA,0.0,1.0)
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Create temporary raster with loss MSA.
    #-----------------------------------------------------------------------------

    # Set raster name.
    tmpMSARasterName = "tmp_wetland_loss_msa.tif"
    tmpMSARasterName = os.path.join(self.outDir,tmpMSARasterName)
    
    # Delete tmp raster.    
    RU.rasterDelete(tmpMSARasterName)

    # Create the loss MSA raster.
    # Initialize with LOSS_MSA.
    Log.info("Creating wetland loss MSA raster...")
    noDataValue = -999.0
    tmpMSARaster = Raster(tmpMSARasterName)
    tmpMSARaster.initRaster(extent,cellSize,np.float32,noDataValue,LOSS_MSA)

    # Write tmp raster.
    tmpMSARaster.write()
    
    # Cleanup.
    tmpMSARaster.close()
    tmpMSARaster = None
    
    #-----------------------------------------------------------------------------
    # Create weighted wetland MSA.
    #-----------------------------------------------------------------------------

    # Create a lists with all msa and fraction rasters.
    msaRasterNames = [tmpMSARasterName,wetFloodLUMSARasterName]
    msaDescriptions = ["wetland loss","actual wetland"]
    fracRasterNames = [wetlandLossFractionsRasterName,wetlandActualFractionsRasterName]
    fracDescriptions = msaDescriptions[:]

    Log.info("Calculate weighted MSA...")
    
    # Calculate weighte MSA.
    outRaster = self.calcWeightedMSA(extent,cellSize,
                                     msaRasterNames,msaDescriptions,
                                     fracRasterNames,fracDescriptions)

    #-----------------------------------------------------------------------------
    # Write output raster.
    #-----------------------------------------------------------------------------
        
    # Save the wetland MSA raster.
    Log.info("Writing wetland MSA raster...")
    outRaster.writeAs(outRasterName)

    # Cleanup.
    outRaster.close()
    outRaster = None
          
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
