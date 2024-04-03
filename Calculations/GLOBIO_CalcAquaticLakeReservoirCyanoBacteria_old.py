# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
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
# Step 14
class GLOBIO_CalcAquaticLakeReservoirCyanoBacteria(CalculationBase):
  """
  Creates a raster with the concentration cyano bacteria in lakes and reservoirs.
  """
  
  #-------------------------------------------------------------------------------
  # DepthThreshold is a positive number.
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER ConcN
    IN RASTER ConcP
    IN RASTER WaterTemperature
    IN RASTER LakeShallowFractions
    IN RASTER LakeDeepFractions
    IN RASTER ReservoirShallowFractions
    IN RASTER ReservoirDeepFractions
    IN FLOAT TemperatureThreshold
    IN FLOAT FTNTP_FACTOR_A
    IN FLOAT FT_FACTOR_A
    IN FLOAT FT_FACTOR_B
    IN FLOAT FT_FACTOR_C
    IN FLOAT FT_FACTOR_D
    IN FLOAT FT_FACTOR_E
    IN FLOAT FT_FACTOR_F
    IN FLOAT CB_FACTOR_A
    IN FLOAT CB_FACTOR_B
    IN FLOAT CB_FACTOR_C
    IN FLOAT CB_FACTOR_D
    IN FLOAT CB_FACTOR_E
    IN FLOAT CB_FACTOR_F
    OUT RASTER LakeReservoirCyanoBacteria
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=23:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    concNRasterName = args[2]
    concPRasterName = args[3]
    waterTempRasterName = args[4]
    lakeShallowFractionsRasterName = args[5]
    lakeDeepFractionsRasterName = args[6]
    reseShallowFractionsRasterName = args[7]
    reseDeepFractionsRasterName = args[8]
    tempThreshold = args[9]
    FTNTP_FACTOR_A = args[10]
    FT_FACTOR_A = args[11]
    FT_FACTOR_B = args[12]
    FT_FACTOR_C = args[13]
    FT_FACTOR_D = args[14]
    FT_FACTOR_E = args[15]
    FT_FACTOR_F = args[16]
    CB_FACTOR_A = args[17]
    CB_FACTOR_B = args[18]
    CB_FACTOR_C = args[19]
    CB_FACTOR_D = args[20]
    CB_FACTOR_E = args[21]
    CB_FACTOR_F = args[22]
    outRasterName = args[23]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(concNRasterName)
    self.checkRaster(concPRasterName)
    self.checkRaster(waterTempRasterName)
    self.checkRaster(lakeShallowFractionsRasterName)
    self.checkRaster(lakeDeepFractionsRasterName)
    self.checkRaster(reseShallowFractionsRasterName)
    self.checkRaster(reseDeepFractionsRasterName)
    self.checkFloat(tempThreshold,-100.0,100.0)
    self.checkFloat(FTNTP_FACTOR_A,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_A,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_B,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_C,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_D,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_E,-100.0,9999.0)
    self.checkFloat(FT_FACTOR_F,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_A,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_B,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_C,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_D,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_E,-100.0,9999.0)
    self.checkFloat(CB_FACTOR_F,-100.0,9999.0)
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
    # Read the fractions rasters, prepare and select.
    #-----------------------------------------------------------------------------

    fracNames = ["shallow lake fractions","deep lake fractions",
                 "shallow reservoir fractions","deep reservoir fractions"]
    fracRasterNames = [lakeShallowFractionsRasterName,lakeDeepFractionsRasterName,
                       reseShallowFractionsRasterName,reseDeepFractionsRasterName]
    fracMask = None
    for i in range(len(fracNames)):
      fracName = fracNames[i]
      fracRasterName = fracRasterNames[i]

      # Reads the raster and resizes to extent and resamples to cellsize.
      fracRaster = self.readAndPrepareInRaster(extent,cellSize,fracRasterName,fracName)

      # Create or extend maskfrac.
      if fracMask is None:
        fracMask = (fracRaster.r > 0.0)
      else:
        fracMask = np.logical_or(fracMask,(fracRaster.r > 0.0))

      # Close and free the fractions raster.
      fracRaster.close()
      fracRaster = None

    #-----------------------------------------------------------------------------
    # Read the water temperature raster, prepare and select.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    waterTempRaster = self.readAndPrepareInRaster(extent,cellSize,waterTempRasterName,"water temperature")

    # Get data mask.
    wtDataMask = waterTempRaster.getDataMask()
  
    # Combine masks.
    wtDataMask = np.logical_and(fracMask,wtDataMask)

    #-----------------------------------------------------------------------------
    # Calculate FT.
    #-----------------------------------------------------------------------------

    Log.info("Calculating FT...")

    # Create raster with FT.
    # Initialize with NoData.
    noDataValue = -999.0
    ftRaster = Raster()
    ftRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Select water temperature >= TempThreshold.
    dataMask = np.logical_and(wtDataMask,(waterTempRaster.r >= tempThreshold))

    # Calculate.
    # FT = a + b  * (power(T / TempThreshold,c) - 1.0) 
    ftRaster.r[dataMask] = waterTempRaster.r[dataMask] / tempThreshold
    ftRaster.r[dataMask] = np.power(ftRaster.r[dataMask],FT_FACTOR_C)
    ftRaster.r[dataMask] -= 1.0
    ftRaster.r[dataMask] *= FT_FACTOR_B
    ftRaster.r[dataMask] += FT_FACTOR_A

    # Select water temperature < TempThreshold.
    dataMask = np.logical_and(wtDataMask,(waterTempRaster.r < tempThreshold))

    # Calculate.
    # FT = d + e  * (power(T / TempThreshold,f) - 1.0) 
    ftRaster.r[dataMask] = waterTempRaster.r[dataMask] / tempThreshold
    ftRaster.r[dataMask] = np.power(ftRaster.r[dataMask],FT_FACTOR_F)
    ftRaster.r[dataMask] -= 1.0
    ftRaster.r[dataMask] *= FT_FACTOR_E
    ftRaster.r[dataMask] += FT_FACTOR_D

    # Cleanup masks.
    wtDataMask = None
    dataMask = None
    
    # Cleanup raster.
    waterTempRaster.close()
    waterTempRaster = None
        
    #-----------------------------------------------------------------------------
    # Read the N-concentration raster, prepare and select.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    concNRaster = self.readAndPrepareInRaster(extent,cellSize,concNRasterName,"N concentration")

    # Get data mask.
    nDataMask = concNRaster.getDataMask()
  
    # Combine masks.
    nDataMask = np.logical_and(fracMask,nDataMask)

    #-----------------------------------------------------------------------------
    # Read the P-concentration raster, prepare and select.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    concPRaster = self.readAndPrepareInRaster(extent,cellSize,concPRasterName,"P concentration")

    # Get data mask.
    pDataMask = concPRaster.getDataMask()
  
    # Combine masks.
    pDataMask = np.logical_and(fracMask,pDataMask)

    #-----------------------------------------------------------------------------
    # Calculate FTNTP.
    #-----------------------------------------------------------------------------

    Log.info("Calculating FTNTP...")

    # Create raster with FTNTP.
    # Initialize with NoData.
    noDataValue = -999.0
    ftntpRaster = Raster()
    ftntpRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Select where there is valid n and p data. Combine masks.
    npDataMask = np.logical_and(pDataMask,nDataMask)

    # Initialize FTNTP with 1.0.
    ftntpRaster.r[npDataMask] = 1.0
    
    # And select where p > 0.0. Refine mask.
    dataMask = np.logical_and(npDataMask,concPRaster.r > 0.0)

    # Create tmp raster.
    # Initialize with NoData.
    noDataValue = -999.0
    tmpRaster = Raster()
    tmpRaster.initRaster(extent,cellSize,np.float32,noDataValue)
    
    # Select n/p <= TempThreshold. Refine masks.
    tmpRaster.r[dataMask] = concNRaster.r[dataMask] / concPRaster.r[dataMask]
    ftntpMask = tmpRaster.getDataMask() 
    ftntpMask = np.logical_and(ftntpMask,(tmpRaster.r <= tempThreshold)) 

    # Cleanup.
    tmpRaster.close()
    tmpRaster = None

    # Calculate.
    # FTNTP = 1.0 - a * (TN / (TP * TempThreshold) - 1.0)
    ftntpRaster.r[ftntpMask] = concNRaster.r[ftntpMask]
    ftntpRaster.r[ftntpMask] /= (concPRaster.r[ftntpMask] * tempThreshold)
    ftntpRaster.r[ftntpMask] -= 1.0
    ftntpRaster.r[ftntpMask] *= FTNTP_FACTOR_A
    ftntpRaster.r[ftntpMask] *= -1.0    # (a * -1.0) + 1.0 == 1.0 - a  
    ftntpRaster.r[ftntpMask] += 1.0
    
    # Cleanup masks.
    nDataMask = None
    npDataMask = None
    ftntpMask = None
    dataMask = None
    
    # Cleanup raster.
    concNRaster.close()
    concNRaster = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the output raster.
    # Initialize with NoData.
    Log.info("Creating raster with concentration of cyano bacteria...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate CB.
    #-----------------------------------------------------------------------------

    Log.info("Calculating concentration of cyano bacteria...")
    
    # Create mask with valid data. 
    dataMask = pDataMask
    dataMask = np.logical_and(dataMask,ftRaster.getDataMask())
    dataMask = np.logical_and(dataMask,ftntpRaster.getDataMask())

    # Calculate CB.
    # CB = a * power(b * log10(c * max(P,d)) - e,f) * FTNTP * FT
    outRaster.r[dataMask] = np.maximum(concPRaster.r[dataMask],CB_FACTOR_D)
    outRaster.r[dataMask] *= CB_FACTOR_C
    outRaster.r[dataMask] = np.log10(outRaster.r[dataMask])
    outRaster.r[dataMask] *= CB_FACTOR_B
    outRaster.r[dataMask] -= CB_FACTOR_E
    outRaster.r[dataMask] = np.power(outRaster.r[dataMask],CB_FACTOR_F)
    outRaster.r[dataMask] *= ftntpRaster.r[dataMask]
    outRaster.r[dataMask] *= ftRaster.r[dataMask]
    outRaster.r[dataMask] *= CB_FACTOR_A
 
    # Cleanup mask.
    pDataMask = None
    dataMask = None

    # Cleanup.
    concPRaster.close()
    concPRaster = None
 
    # Save the output raster.
    Log.info("Writing raster with concentration of cyano bacteria ...")
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

    pCalc = GLOBIO_CalcAquaticLakeReservoirCyanoBacteria()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec

    n = os.path.join(inDir,"n_conc.tif")
    p = os.path.join(inDir,"p_conc.tif")
    wt = os.path.join(inDir,"temperature_growseason.tif")
    lsfrac = os.path.join(inDir,"lakeshallow_fractions.tif")
    ldfrac = os.path.join(inDir,"lakedeep_fractions.tif")
    rsfrac = os.path.join(inDir,"reservoirshallow_fractions.tif")
    rdfrac = os.path.join(inDir,"reservoirdeep_fractions.tif")
    thresh = 15.0
    FTNTP_A = 3.0
    FT_A = 0.86
    FT_B = 0.63
    FT_C = 1.5
    FT_D = 1.0
    FT_E = 1.0
    FT_F = 3.0
    CB_A = 0.001
    CB_B = 5.85
    CB_C = 1000.0
    CB_D = 0.005
    CB_E = 4.01
    CB_F = 4.0
    out = os.path.join(outDir,"cyanobact_lakereservoir.tif")
   
    RU.rasterDelete(out)
    
    pCalc.run(ext,cs,n,p,wt,lsfrac,ldfrac,rsfrac,rdfrac,
              thresh,FTNTP_A,
              FT_A,FT_B,FT_C,FT_D,FT_E,FT_F,
              CB_A,CB_B,CB_C,CB_D,CB_E,CB_F,out)
  except:
    MON.cleanup()
    Log.err()
