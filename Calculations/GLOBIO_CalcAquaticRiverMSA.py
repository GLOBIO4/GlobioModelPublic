# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: nov 2018, ES, ARIS B.V.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Run modified, the RiverFragmentationMSA raster is optional now.
#           3 nov 2021, MB, PBL
#           - Fixed error in optional 'RiverFragmentationMSA' code, needed more
#             checks on NONE of fragmentation MSA
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcAquaticRiverMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for rivers.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER RiverFragmentationMSA
    IN RASTER RiverFRHLUMSA
    IN RASTER RiverAAPFDMSA
    IN RASTER RiverFractions
    OUT RASTER RiverMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    riverFragMSARasterName = args[2]
    riverLUMSARasterName = args[3]
    riverAAPFDMSARasterName = args[4]
    riverFractionsRasterName = args[5]
    outRasterName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(riverFragMSARasterName,False,True)
    self.checkRaster(riverLUMSARasterName)
    self.checkRaster(riverAAPFDMSARasterName)
    self.checkRaster(riverFractionsRasterName)
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
    # Read the fractions raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    riverFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,riverFractionsRasterName,"river fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting river fractions...")
    fracMask = (riverFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    riverFractionsRaster.close()
    riverFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the output raster.
    # Initialize with NoData.
    Log.info("Creating river MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Read and process river fragmentation msa raster (optional).
    #-----------------------------------------------------------------------------

    # Need to use the river fragmentation raster?
    if self.isValueSet(riverFragMSARasterName):

      # Reads the raster and resizes to extent and resamples to cellsize.
      riverFragRaster = self.readAndPrepareInRaster(extent,cellSize,riverFragMSARasterName,"river fragmentation msa")

      # Get data mask.
      dataMask = riverFragRaster.getDataMask()
  
      # Combine masks.
      dataMask = np.logical_and(fracMask,dataMask)

      # Calculate.
      Log.info("Processing river fragmentation MSA...")
      outRaster.r[dataMask] = riverFragRaster.r[dataMask]
    
      # Close and free the river fragmentation msa raster.
      riverFragRaster.close()
      riverFragRaster = None

    #-----------------------------------------------------------------------------
    # Read and process river landuse msa raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    riverLURaster = self.readAndPrepareInRaster(extent,cellSize,riverLUMSARasterName,"river landuse msa")

    # Get data mask.
    dataMask = riverLURaster.getDataMask()

    if self.isValueSet(riverFragMSARasterName):
      # Get output data mask.
      outMask = outRaster.getDataMask()
  
      # Combine masks.
      dataMask = np.logical_and(outMask,dataMask)
      dataMask = np.logical_and(fracMask,dataMask)

    # Calculate.
    Log.info("Processing river landuse MSA...")
    if self.isValueSet(riverFragMSARasterName):
      outRaster.r[dataMask] *= riverLURaster.r[dataMask]
    else:
      outRaster.r[dataMask] = riverLURaster.r[dataMask]
    
    # Close and free the river landuse msa raster.
    riverLURaster.close()
    riverLURaster = None

    #-----------------------------------------------------------------------------
    # Read and process river AAPFD msa raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    riverAAPFDRaster = self.readAndPrepareInRaster(extent,cellSize,riverAAPFDMSARasterName,"river AAPFD msa")

    # Get data mask.
    dataMask = riverAAPFDRaster.getDataMask()
  
    # Get output data mask.
    outMask = outRaster.getDataMask()
  
    # Combine masks.
    dataMask = np.logical_and(outMask,dataMask)
    dataMask = np.logical_and(fracMask,dataMask)

    # Calculate.
    Log.info("Processing river AAPFD MSA...")
    outRaster.r[dataMask] *= riverAAPFDRaster.r[dataMask]
    
    # Close and free the river AAPFD msa raster.
    riverAAPFDRaster.close()
    riverAAPFDRaster = None

    #-----------------------------------------------------------------------------
    # Write output raster.
    #-----------------------------------------------------------------------------
        
    # Save the river MSA raster.
    Log.info("Writing river MSA raster...")
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
    
    # Enable the monitor.    
    GLOB.monitorEnabled = True
    
    inDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
    
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\data\Globio4LA\data\kanweg\20181031_v1"

    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    pCalc = GLOBIO_CalcAquaticRiverMSA()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec
    frag = os.path.join(inDir,"river_frag_msa.tif")
    lu = os.path.join(inDir,"river_frhlu_msa.tif")
    aa = os.path.join(inDir,"river_aapfd_msa.tif")
    frac = os.path.join(inDir,"river_fractions.tif")
    out = os.path.join(outDir,"river_msa.tif")
   
#     ### ZETTEN DUMMIES
#     Log.info("USING DUMMY RASTERS!!!")
#     testDir = r"G:\data\Globio4LA\data\referentie\v407\30sec_wrld\globio_20170830"
#     rivFrag = os.path.join(testDir,"InfraFragmentationMSA.tif")
#     rivLU = os.path.join(testDir,"InfraFragmentationMSA.tif")
#     rivAAPFD = os.path.join(testDir,"InfraFragmentationMSA.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,frag,lu,aa,frac,out)
  except:
    MON.cleanup()
    Log.err()
