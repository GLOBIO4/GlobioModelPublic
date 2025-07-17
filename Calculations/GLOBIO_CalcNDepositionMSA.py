# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 28 apr 2016, ES, ARIS B.V.
#           - Weighting formula modified.
#           9 aug 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - Now using uniform names for temporary files.
#           30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
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
class GLOBIO_CalcNDepositionMSA(CalculationBase):
  """
  Calculates a raster with the MSA of N-deposition.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN STRING NDEP_LandcoverExlCodes
    IN FILE WaterLookupFile
    IN RASTER NDep
    IN STRING NDEP_PlantRegressionCoefficients
    IN FLOAT NDEP_WeightFactor
    OUT RASTER NDepositionMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=7:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    landcoverExlCodesStr= args[2]
    lookupFileName = args[3]
    ndepRasterName = args[4]
    plantRegressionCoeffsStr = args[5]
    weightFactor = args[6]
    outRasterName = args[7]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(landuseRasterName)
    self.checkIntegerList(landcoverExlCodesStr)
    self.checkLookup(lookupFileName)
    self.checkRaster(ndepRasterName)
    self.checkFloatList(plantRegressionCoeffsStr,needCnt=2)
    self.checkFloat(weightFactor,0.0,1.0)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [landuseRasterName,ndepRasterName]
    cellSize = self.getMinimalCellSize(inRasterNames)
    Log.info("Using cellsize: %s" % cellSize)

    # Convert code and names to arrays.
    landcoverExlCodes = self.splitIntegerList(landcoverExlCodesStr)
    plantRegressionCoeffs = self.splitFloatList(plantRegressionCoeffsStr)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the N-exceed raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the landuse raster and resizes to extent and resamples to cellsize.
    ndepRaster = self.readAndPrepareInRaster(extent,cellSize,ndepRasterName,"N-dep")

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the N-deposition MSA raster.
    # Initialize raster with MSA 1.0.
    Log.info("Creating the N-deposition MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)
    
    # Set regression coefficients.
    b0 = plantRegressionCoeffs[0]
    b1 = plantRegressionCoeffs[1]

    #-----------------------------------------------------------------------------
    # Calculate ln.
    #-----------------------------------------------------------------------------

    # Create data mask.
    Log.info("Creating N-dep data mask...")
    dataMask = (ndepRaster.r != ndepRaster.noDataValue)
    
    # Create mask ndep = 0.0 where MSA = 1. 
    ndepzeroMask = (dataMask) & (ndepRaster.r == 0.0)
    outRaster.r[ndepzeroMask] = 1.0
    
    # Free mask.
    ndepzeroMask = None
    
    # Create mask ndep > 0.0.
    # Because: ndep <= 0.0 results in a MSA of -Inf. 
    ndepMask = (dataMask) & (ndepRaster.r > 0.0)

    # Free data mask.
    dataMask = None
    
    Log.info("Calculating log10...")
    outRaster.r[ndepMask] = 1/(1+np.exp(-b0 - b1 * np.log10(ndepRaster.r[ndepMask])))

    # Free mask.
    ndepMask = None
     
    #-----------------------------------------------------------------------------
    # Read the landuse raster and prepare.
    #-----------------------------------------------------------------------------
    
    Log.info("Filter out land uses and water areas...")
    
    # Reads the landuse raster and resizes to extent and resamples to cellsize.
    landuseRaster = self.readAndPrepareInRaster(extent,cellSize,landuseRasterName,"landuse")
       
    # Filter out water areas
    lookupFieldTypes = ["I","F"]
    tmpLUFactorRaster = self.reclassUniqueValues(landuseRaster,
                                                 lookupFileName,lookupFieldTypes,
                                                 np.float32)

    #Reclassify water areas to NoData
    noDataValue = -999.0
    mask = (tmpLUFactorRaster.r == noDataValue)
    outRaster.r[mask] = noDataValue
    ndepRaster.r[mask] = ndepRaster.noDataValue
    mask = None
    
    # Select specified landcover types (selected = 1).
    for landcoverExlCode in landcoverExlCodes:
      mask = (outRaster.r != noDataValue) & (landuseRaster.r == landcoverExlCode)
      outRaster.r[mask] = noDataValue
      ndepRaster.r[mask] = ndepRaster.noDataValue

    # Cleanup mask.
    mask = None
    
    # Write, close and free the N-dep raster.
    Log.info("Writing input raster....")
    ndepRaster.writeAs(outRasterName.replace(".tif","_finalinput.tif"))
    ndepRaster.close()
    ndepRaster = None
    
    # Close and free the landuse raster.
    landuseRaster.close()
    landuseRaster = None

    # Save temporary data?
    if GLOB.saveTmpData:
      # Save the N-deposition factor.
      tmpName = "tmp_lu_factor.tif"
      Log.info("- Writing Land use factor: "+tmpName)
      self.writeTmpRaster(tmpLUFactorRaster,tmpName)

    # Close and free the NDepFactor raster.
    tmpLUFactorRaster.close()
    tmpLUFactorRaster = None

    # Calculate weighted MSA.
    Log.info("Calculating...")
    
     # Set all cells with values <0 to 0.0.
    Negmask = (outRaster.r != noDataValue) & (outRaster.r < 0.0)
    outRaster.r[Negmask] = 0.0
    
    # Clear negative MSA mask
    Negmask = None

    # Set all cells with values >1 to 1.0.
    Posmask = (outRaster.r != noDataValue) & (outRaster.r > 1.0)
    outRaster.r[Posmask] = 1.0
    
    # Clear greater than 1 MSA mask
    Posmask = None
    
    # Write away taxonomic group - MSA output
    Log.info("Writing taxonomic group - MSA rasters....")
    outRaster.writeAs(outRasterName.replace(".tif","_plants.tif"))
    
    # Calculate weighted MSA.
    Log.info("Calculating N-deposition MSA...")
    # Is: MSA + (1 - MSA) * (1 - W)
    # Is: MSA + CW - CW * MSA           for CW = 1-W
    # Is: (1 - CW) * MSA + CW           for CW = 1-W
    # Or: 
    #   MSA *= (1 - CW)
    #   MSA += CW
    # Or: 
    #   MSA *= W
    #   MSA += CW
    
    outMask = (outRaster.r != outRaster.noDataValue)
    
    complWeightFactor = 1.0 - weightFactor
    outRaster.r[outMask] *= weightFactor
    outRaster.r[outMask] += complWeightFactor
    
    # Clear N-exceed mask.
    outMask = None    

    # Save the N-deposition MSA raster.
    Log.info("Writing N-deposition MSA raster...")
    outRaster.writeAs(outRasterName)

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
    inDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcNDepositionMSA()

    ext = GLOB.extent_World
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    ndep = os.path.join(inDir,"Ndep.tif")
    lut = os.path.join(lookupDir,"WaterAreasFilter.csv")
    coef = "0.86|-0.097"
    wf = 1.0/3.0
    msa = os.path.join(outDir,"NDepositionMSA.tif")
    
    if RU.rasterExists(msa):
      RU.rasterDelete(msa)
      
    pCalc.run(ext,lu,lut,ndep,coef,wf,msa)
    
  except:
    Log.err()
