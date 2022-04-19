# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************

import os
from typing import Optional
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
class GLOBIO_CalcAquaticLakeShallowMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for shallow lakes.
  """
  
  #-------------------------------------------------------------------------------
  # DepthThreshold is a positive number.
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER ConcentrationN
    IN RASTER ConcentrationP
    IN RASTER ShallowLakeFractions
    IN FLOAT N_FACTOR_A
    IN FLOAT N_FACTOR_B
    IN FLOAT N_FACTOR_C
    IN FLOAT P_FACTOR_A
    IN FLOAT P_FACTOR_B
    IN FLOAT P_FACTOR_C
    OUT RASTER LakeShallowMSA
    OUT RASTER LakeShallowMSA_N
    OUT RASTER LakeShallowMSA_P
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=13:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    concNRasterName = args[2]
    concPRasterName = args[3]
    lakeShallowRasterName = args[4]
    N_FACTOR_A = args[5]
    N_FACTOR_B = args[6]
    N_FACTOR_C = args[7]
    P_FACTOR_A = args[8]
    P_FACTOR_B = args[9]
    P_FACTOR_C = args[10]
    outRasterName = args[11]
    outRasterNameN = args[12]
    outRasterNameP = args[13]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(concNRasterName)
    self.checkRaster(concPRasterName)
    self.checkRaster(lakeShallowRasterName)
    self.checkFloat(N_FACTOR_A,-100.0,100.0)
    self.checkFloat(N_FACTOR_B,-100.0,100.0)
    self.checkFloat(N_FACTOR_C,-100.0,100.0)
    self.checkFloat(P_FACTOR_A,-100.0,100.0)
    self.checkFloat(P_FACTOR_B,-100.0,100.0)
    self.checkFloat(P_FACTOR_C,-100.0,100.0)
    self.checkRaster(outRasterName,True)
    # Check if optional output of Nitrogen and Phosphorous MSA maps must be saved
    self.checkRaster(outRasterNameN,asOutput=True,optional=True)
    self.checkRaster(outRasterNameP,asOutput=True,optional=True)

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
    lakeShallowRaster = self.readAndPrepareInRaster(extent,cellSize,lakeShallowRasterName,"shallow lake fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting lake fractions...")
    fracMask = (lakeShallowRaster.r > 0.0)

    # Close and free the fractions raster.
    lakeShallowRaster.close()
    lakeShallowRaster = None

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
    if self.isValueSet(outRasterNameN):
      nMSA = Raster(outRasterNameN)
    else:
      nMSA = Raster()
    nMSA.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate.
    #
    # N_MSA = exp(a + b * log(NCONC+c))/(1.0 + exp(a + b * log(NCONC+c)))
    #
    Log.info("Calculating MSA for N concentration...")
    nMSA.r[nDataMask] = concNRaster.r[nDataMask]
    nMSA.r[nDataMask] += N_FACTOR_C
    nMSA.r[nDataMask] = np.log(nMSA.r[nDataMask])
    nMSA.r[nDataMask] *= N_FACTOR_B
    nMSA.r[nDataMask] += N_FACTOR_A
    nMSA.r[nDataMask] = np.exp(nMSA.r[nDataMask])

    nTmp= Raster()
    noDataValue = -999.0
    nTmp.initRaster(extent,cellSize,np.float32,noDataValue)

    nTmp.r[nDataMask] = nMSA.r[nDataMask]
    nTmp.r[nDataMask] += 1.0
    
    nMSA.r[nDataMask] /= nTmp.r[nDataMask]

    # Cleanup.
    nTmp.close()
    nTmp = None
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
    pDataMask = np.logical_and(pDataMask,(concPRaster.r > 0.0))

    # Combine masks.
    pDataMask = np.logical_and(pDataMask,fracMask)

    # Create raster with MSA for P.
    # Initialize with NoData.
    Log.info("Creating MSA for P concentration raster...")
    noDataValue = -999.0
    if self.isValueSet(outRasterNameP):
      pMSA = Raster(outRasterNameP)
    else:
      pMSA = Raster()
    pMSA.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate.
    #
    # P_MSA = exp(a + b * log(PCONC+c))/(1.0 + exp(a + b * log(PCONC+c)))
    #
    Log.info("Calculating MSA for P concentration...")
    pMSA.r[pDataMask] = concPRaster.r[pDataMask]
    pMSA.r[pDataMask] += P_FACTOR_C
    pMSA.r[pDataMask] = np.log(pMSA.r[pDataMask])
    pMSA.r[pDataMask] *= P_FACTOR_B
    pMSA.r[pDataMask] += P_FACTOR_A
    pMSA.r[pDataMask] = np.exp(pMSA.r[pDataMask])
    
    pTmp= Raster()
    noDataValue = -999.0
    pTmp.initRaster(extent,cellSize,np.float32,noDataValue)

    pTmp.r[pDataMask] = pMSA.r[pDataMask]
    pTmp.r[pDataMask] += 1.0
    
    pMSA.r[pDataMask] /= pTmp.r[pDataMask]

    # Cleanup.
    pTmp.close()
    pTmp = None
    concPRaster.close()
    concPRaster = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the output raster.
    # Initialize with NoData.
    Log.info("Creating MSA for shallow lakes raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate the final MSA for shallow lakes.
    #-----------------------------------------------------------------------------

    Log.info("- Calculating MSA for shallow lakes...")

    # Select where both n and p has data - set maximum value.
    dataMask = np.logical_and(nDataMask,pDataMask)
    outRaster.r[dataMask] = np.maximum(nMSA.r[dataMask],pMSA.r[dataMask]) 

    # Select where n has data and p not - set n value.
    dataMask = np.logical_and(nDataMask,~pDataMask)
    outRaster.r[dataMask] = nMSA.r[dataMask] 

    # Select where p has data and n not - set p value.
    dataMask = np.logical_and(pDataMask,~nDataMask)
    outRaster.r[dataMask] = pMSA.r[dataMask] 

    # Cleanup masks.
    fracMask = None
    nDataMask = None
    pDataMask = None
    dataMask = None
 
    # Save the MSA raster for shallow lakes.
    Log.info("Writing MSA for shallow lakes raster...")
    outRaster.write()
    if self.isValueSet(outRasterNameN):
      nMSA.write()
    if self.isValueSet(outRasterNameP):
      pMSA.write()

    # Cleanup rasters.
    nMSA.close()
    nMSA = None
    pMSA.close()
    pMSA = None
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

    pCalc = GLOBIO_CalcAquaticLakeShallowMSA()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec
    n = os.path.join(inDir,"n_conc.tif")
    p = os.path.join(inDir,"p_conc.tif")
    frac = os.path.join(inDir,"shallow_lake_fractions.tif")
    N_A = 0.264
    N_B = -0.998
    N_C = 0.01
    P_A = -2.089
    P_B = -1.048
    P_C = 0.001
    out = os.path.join(outDir,"shallow_lake_msa.tif")
   
#     ### ZETTEN DUMMIES
#     Log.info("USING DUMMY RASTERS!!!")
#     testDir = r"G:\data\Globio4LA\data\referentie\v405\30sec_wrld\suit_20170315"
#     n = os.path.join(testDir,"suit_crop.tif")
#     p = os.path.join(testDir,"suit_crop.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,n,p,frac,N_A,N_B,N_C,P_A,P_B,P_C,out)
  except:
    MON.cleanup()
    Log.err()
