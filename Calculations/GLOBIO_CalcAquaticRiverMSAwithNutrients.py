# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: nov 2018, ES, ARIS B.V.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Run modified, the RiverFragmentationMSA raster is optional now.
#           3 nov 2021, MB, PBL
#           - Added new functions for effects of Nitrogen and Phosphorous on river MSA
#           - Commented out the effect of landuse on MSA, the nutritions N and P replace 
#             the effect of landuse
#           - Fixed the error in optional 'RiverFragmentationMSA' code (noData raster output), 
#             by first creating an output raster for the effects of N and P on MSA (maxOf), 
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
class GLOBIO_CalcAquaticRiverMSAwithNutrients(CalculationBase):
  """
  Creates a raster with the aquatic MSA for rivers.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER ConcN
    IN RASTER ConcP
    IN RASTER RiverFragmentationMSA
    IN RASTER RiverLanduseMSA
    IN RASTER RiverAAPFDMSA
    IN RASTER RiverFractions
    IN FLOAT N_FACTOR_Alpha
    IN FLOAT N_FACTOR_Beta
    IN FLOAT N_FACTOR_C
    IN FLOAT P_FACTOR_Alpha
    IN FLOAT P_FACTOR_Beta
    IN FLOAT P_FACTOR_C
    OUT RASTER RiverMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=14:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    concNRasterName = args[2]
    concPRasterName = args[3]
    riverFragMSARasterName = args[4]
    riverLUMSARasterName = args[5]
    riverAAPFDMSARasterName = args[6]
    riverFractionsRasterName = args[7]
    N_FACTOR_Alpha = args[8]
    N_FACTOR_Beta = args[9]
    N_FACTOR_C = args[10]
    P_FACTOR_Alpha = args[11]
    P_FACTOR_Beta = args[12]
    P_FACTOR_C = args[13]
    outRasterName = args[14]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(concNRasterName)
    self.checkRaster(concPRasterName)
    self.checkRaster(riverFragMSARasterName,False,True)
    self.checkRaster(riverLUMSARasterName)
    self.checkRaster(riverAAPFDMSARasterName)
    self.checkRaster(riverFractionsRasterName)
    self.checkFloat(N_FACTOR_Alpha,-100.0,100.0)
    self.checkFloat(N_FACTOR_Beta,-100.0,100.0)
    self.checkFloat(N_FACTOR_C,-100.0,100.0)
    self.checkFloat(P_FACTOR_Alpha,-100.0,100.0)
    self.checkFloat(P_FACTOR_Beta,-100.0,100.0)
    self.checkFloat(P_FACTOR_C,-100.0,100.0)
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
    # Calculate MSA for N.
    #-----------------------------------------------------------------------------

    # Read the N-concentration raster and prepare.

    # Reads the raster and resizes to extent and resamples to cellsize.
    concNRaster = self.readAndPrepareInRaster(extent,cellSize,concNRasterName,"N concentration")

    # Get data mask.
    nDataMask = concNRaster.getDataMask()
    nDataMask = np.logical_and(nDataMask,(concNRaster.r > 0.0))
  
    # Combine masks.
    nDataMask = np.logical_and(nDataMask,fracMask)

    # Create raster with MSA for N.
    # Initialize with NoData.
    Log.info("Creating MSA for N concentration raster...")
    noDataValue = -999.0
    #if self.isValueSet(outRasterNameN):
    #  nMSA = Raster(outRasterNameN)
    #else:
    nMSA = Raster()
    nMSA.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate.
    #
    # N_MSA = 1.0 / (1.0 + exp(- ( ( log10(NCONC+c)-a)/b) ))
    #
    Log.info("Calculating MSA for N concentration...")
    nMSA.r[nDataMask] = concNRaster.r[nDataMask]
    nMSA.r[nDataMask] += N_FACTOR_C
    nMSA.r[nDataMask] = np.log10(nMSA.r[nDataMask])
    nMSA.r[nDataMask] -= N_FACTOR_Alpha
    nMSA.r[nDataMask] /= N_FACTOR_Beta
    nMSA.r[nDataMask] = np.exp(-nMSA.r[nDataMask])
    nMSA.r[nDataMask] += 1.0
    nMSA.r[nDataMask] = 1.0 / nMSA.r[nDataMask]

    # Cleanup.
    concNRaster.close()
    concNRaster = None

    #-----------------------------------------------------------------------------
    # Calculate MSA for P.
    #-----------------------------------------------------------------------------

    # Read the P-concentration raster and prepare.

    # Reads the raster and resizes to extent and resamples to cellsize.
    concPRaster = self.readAndPrepareInRaster(extent,cellSize,concPRasterName,"P concentration")

    # Get data mask.
    pDataMask = concPRaster.getDataMask()
  
    # Combine masks.
    pDataMask = np.logical_and(fracMask,pDataMask)
    pDataMask = np.logical_and(pDataMask,(concPRaster.r > 0.0))

    # Create raster with MSA for P.
    # Initialize with NoData.
    Log.info("Creating MSA for P concentration raster...")
    noDataValue = -999.0
    #if self.isValueSet(outRasterNameP):
    #  pMSA = Raster(outRasterNameP)
    #else:
    pMSA = Raster()
    pMSA.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate.
    #
    # N_MSA = 1.0 / (1.0 + exp(- ( ( log10(NCONC+c)-a)/b) ))
    #
    Log.info("Calculating MSA for N concentration...")
    pMSA.r[pDataMask] = concPRaster.r[pDataMask]
    pMSA.r[pDataMask] += P_FACTOR_C
    pMSA.r[pDataMask] = np.log10(pMSA.r[pDataMask])
    pMSA.r[pDataMask] -= P_FACTOR_Alpha
    pMSA.r[pDataMask] /= P_FACTOR_Beta
    pMSA.r[pDataMask] = np.exp(-pMSA.r[pDataMask])
    pMSA.r[pDataMask] += 1.0
    pMSA.r[pDataMask] = 1.0 / pMSA.r[pDataMask]

    # Cleanup.
    concPRaster.close()
    concPRaster = None

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
    # Combine N and P raster, use maximum where both N and P.
    #-----------------------------------------------------------------------------

    # Create raster with combined MSA for N and P.
    # Initialize with NoData.
    Log.info("Combina MSA for P and N...")
    
    # Select where both n and p has data - set maximum value.
    dataMask = np.logical_and(nDataMask,pDataMask)
    outRaster.r[dataMask] = np.maximum(nMSA.r[dataMask],pMSA.r[dataMask]) 

    # Select where n has data and p not - set n value.
    dataMask = np.logical_and(nDataMask,~pDataMask)
    outRaster.r[dataMask] = nMSA.r[dataMask] 

    # Select where p has data and n not - set p value.
    dataMask = np.logical_and(pDataMask,~nDataMask)
    outRaster.r[dataMask] = pMSA.r[dataMask] 

    # Cleanup.
    nMSA.close()
    nMSA = None
    pMSA.close()
    pMSA = None

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
      outRaster.r[dataMask] *= riverFragRaster.r[dataMask]
    
      # Close and free the river fragmentation msa raster.
      riverFragRaster.close()
      riverFragRaster = None

    #-----------------------------------------------------------------------------
    # Read and process river landuse msa raster.
    #-----------------------------------------------------------------------------

    """ # Reads the raster and resizes to extent and resamples to cellsize.
    riverLURaster = self.readAndPrepareInRaster(extent,cellSize,riverLUMSARasterName,"river landuse msa")

    # Get data mask.
    dataMask = riverLURaster.getDataMask()

    # Get output data mask.
    outMask = outRaster.getDataMask()
  
    # Combine masks.
    dataMask = np.logical_and(outMask,dataMask)
    dataMask = np.logical_and(fracMask,dataMask)

    # Calculate.
    Log.info("Processing river landuse MSA...")
    outRaster.r[dataMask] = riverLURaster.r[dataMask]
    
    # Close and free the river landuse msa raster.
    riverLURaster.close()
    riverLURaster = None """

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
    
    inDir = r""
    outDir = r""

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

    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,frag,lu,aa,frac,out)
  except:
    MON.cleanup()
    Log.err()
