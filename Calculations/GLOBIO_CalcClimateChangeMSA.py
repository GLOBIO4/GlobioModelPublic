# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 1 feb 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - Added nodata argument when calling reclassUniqueValues.
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
class GLOBIO_CalcClimateChangeMSA(CalculationBase):
  """
  Calculates a raster with the MSA of climate change.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN FILE WaterLookupFile
    IN FLOAT TemperatureChange
    IN STRING CLIMCH_WbVertRegressionCoefficients
    IN STRING CLIMCH_PlantRegressionCoefficients   
    OUT RASTER ClimateChangeMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    lookupFileName = args[2]
    temperatureChange = args[3]
    wbvertRegressionCoeffsStr = args[4]
    plantRegressionCoeffsStr = args[5]
    outRasterName = args[6]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(landuseRasterName)
    self.checkLookup(lookupFileName)
    self.checkFloat(temperatureChange,-99999,99999)
    self.checkFloatList(wbvertRegressionCoeffsStr,needCnt=2)
    self.checkFloatList(plantRegressionCoeffsStr,needCnt=2)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [landuseRasterName]
    cellSize = self.getMinimalCellSize(inRasterNames)
    Log.info("Using cellsize: %s" % cellSize)

    # Convert code and names to arrays.
    wbvertRegressionCoeffs = self.splitFloatList(wbvertRegressionCoeffsStr)
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
    # Read the biomes raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    #biomesRaster = self.readAndPrepareInRaster(extent,cellSize,biomesRasterName,"biomes")
    
    # Create a list of unique biomes from the biome raster.
    #biomeList = np.unique(biomesRaster.r)
    #biomeList = biomeList[(biomeList!=biomesRaster.noDataValue)].tolist()
    
    #-----------------------------------------------------------------------------
    # Read the temperature change raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    #temperatureRaster = self.readAndPrepareInRaster(extent,cellSize,temperatureRasterName,"temperature change")

    # Combine msa loss nodata mask with temperature nodata.
    #zeroMask = (temperatureRaster.r == 0.0)
    
    #-----------------------------------------------------------------------------
    # Calculate MSA.
    #-----------------------------------------------------------------------------

    Log.info("Calculating climate change MSA raster...")
    
    # Create raster with default MSA value 1.
    noDataValue = -999.0
    outWbVertMSARaster = Raster()
    outWbVertMSARaster.initRaster(extent,cellSize,np.float32,noDataValue)

    outPlantMSARaster = Raster()
    outPlantMSARaster.initRaster(extent,cellSize,np.float32,noDataValue)
    
    #Loop over biomes
    # for biome in biomeList:
        
    #     # Show progress.
    #     Log.info("- Processing biome %s..." % biome)
        
    #     # Select the cells in the current biome.
    #     currSuitMask = (biomesRaster.r == biome)
        
    #     # Check biomes.
    #     if np.sum(currSuitMask) == 0:
    #       Log.info("    No biome cells found.")
    #       continue
        
    #     #########################
    #     #Warm-blooded vertebrates
        
    #     # Set regression coefficients.
    #     b0 = wbvertRegressionCoeffs[(biome-1)]
    #     b1 = wbvertRegressionCoeffs[((biome-1)+3)]
        
    #     Log.info("- Using wb coefficients %s and %s..." % (b0,b1))
        
    #     outWbVertMSARaster.r[currSuitMask] = 1/(1+np.exp(-b0-b1 * temperatureChange))
    
    #     # Set cells to 1 where temp change = 0.0.
    #     #outWbVertMSARaster.r[zeroMask] = 1.0
    
    #     # Set all cells with values <0 to 0.0.
    #     mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r < 0.0)
    #     outWbVertMSARaster.r[mask] = 0.0
    
    #     # Set all cells with values >1 to 1.0.
    #     mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r > 1.0)
    #     outWbVertMSARaster.r[mask] = 1.0
    
    #     # Free mask.
    #     mask = None
    
    #     #########################
    #     #Plants
    
    #     # Set regression coefficients.
    #     b0 = plantRegressionCoeffs[(biome-1)]
    #     b1 = plantRegressionCoeffs[((biome-1)+3)]
        
    #     Log.info("- Using plant coefficients %s and %s..." % (b0,b1))
        
    #     outPlantMSARaster.r[currSuitMask] = 1/(1+np.exp(-b0-b1 * temperatureChange))
    
    #     # Set cells to 1 where temp change = 0.0.
    #     #outPlantMSARaster.r[zeroMask] = 1.0
    
    #     # Set all cells with values <0 to 0.0.
    #     mask = (outPlantMSARaster.r != noDataValue) & (outPlantMSARaster.r < 0.0)
    #     outPlantMSARaster.r[mask] = 0.0
    
    #     # Set all cells with values >1 to 1.0.
    #     mask = (outPlantMSARaster.r != noDataValue) & (outPlantMSARaster.r > 1.0)
    #     outPlantMSARaster.r[mask] = 1.0
    
    #     # Free mask.
    #     mask = None
    #     #zeroMask = None
             
    #########################
    #Warm-blooded vertebrates
        
    # Set regression coefficients.
    b0 = wbvertRegressionCoeffs[0]
    b1 = wbvertRegressionCoeffs[1]
        
    Log.info("- Using wb coefficients %s and %s..." % (b0,b1))
   
    outWbVertMSARaster.r[:] = 1/(1+np.exp(-b0-b1 * temperatureChange))
    
    # Set all cells with values <0 to 0.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r < 0.0)
    outWbVertMSARaster.r[mask] = 0.0
    
    # Set all cells with values >1 to 1.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r > 1.0)
    outWbVertMSARaster.r[mask] = 1.0
    
    # Free mask.
    mask = None
    
    #########################
    #Plants
    
    # Set regression coefficients.
    b0 = plantRegressionCoeffs[0]
    b1 = plantRegressionCoeffs[1]
        
    Log.info("- Using plant coefficients %s and %s..." % (b0,b1))
        
    outPlantMSARaster.r[:] = 1/(1+np.exp(-b0-b1 * temperatureChange))
    
    # Set all cells with values <0 to 0.0.
    mask = (outPlantMSARaster.r != noDataValue) & (outPlantMSARaster.r < 0.0)
    outPlantMSARaster.r[mask] = 0.0
    
    # Set all cells with values >1 to 1.0.
    mask = (outPlantMSARaster.r != noDataValue) & (outPlantMSARaster.r > 1.0)
    outPlantMSARaster.r[mask] = 1.0
    
    # Free mask.
    mask = None
    
    #-----------------------------------------------------------------------------
    # Read the landuse raster and prepare.
    #-----------------------------------------------------------------------------
    
    Log.info("Filter out water areas...")
    
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
    outWbVertMSARaster.r[mask] = noDataValue
    outPlantMSARaster.r[mask] = noDataValue
    #temperatureRaster.r[mask] = noDataValue
    mask = None
        
    # Write, close and free the temperature change raster.
    #Log.info("Writing input raster....")
    #temperatureRaster.writeAs(outRasterName.replace(".tif","_finalinput.tif"))
    #temperatureRaster.close()
    #temperatureRaster = None
    
    # Close and free the landuse raster.
    landuseRaster.close()
    landuseRaster = None

    # Create the climate change MSA raster.
    Log.info("Creating the climate change MSA raster...")
           
    # Write, close and free the MSA loss raster.
    Log.info("Writing taxonomic group - MSA rasters....")
    outWbVertMSARaster.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
    outPlantMSARaster.writeAs(outRasterName.replace(".tif","_plants.tif"))
    
    # Save the climate change MSA raster.
    Log.info("Writing climate change MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    mask = (outWbVertMSARaster.r != outWbVertMSARaster.noDataValue)
    
    outRaster.r[mask] = (outWbVertMSARaster.r[mask]+ outPlantMSARaster.r[mask])/2

    # Save temporary data?
    if GLOB.saveTmpData:
      # Save the N-deposition factor.
      tmpName = "tmp_lu_factor.tif"
      Log.info("- Writing Land use factor: "+tmpName)
      self.writeTmpRaster(tmpLUFactorRaster,tmpName)

    # Close and free the NDepFactor raster.
    tmpLUFactorRaster.close()
    tmpLUFactorRaster = None
    
    #Write final raster
    #Log.info("Writing %s..." % outRasterName)
    #outRaster.write()

    # Cleanup.
    outRaster.close()
    outRaster = None
    outWbVertMSARaster.close()
    outWbVertMSARaster = None   
    outPlantMSARaster.close()
    outPlantMSARaster = None
    
    # Show used memory and disk space.
    MON.showMemDiskUsage()
    
    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r"C:\Globio4"
    lookupDir = r"C:\Globio4"
    outDir = r"C:\Globio4"
    luDir = r"C:\Y\ESH\Input_rasters"
    if not os.path.isdir(outDir):
      outDir = r"S:\hilbersj"

    pCalc = GLOBIO_CalcClimateChangeMSA()

    ext = GLOB.extent_NL
    lu = os.path.join(luDir,"Globio4_landuse_10sec_2015_cropint_pasint.tif")
    tc = 2.58446979
    wlf = os.path.join(lookupDir,"WaterAreasFilter.csv")
    msa = os.path.join(outDir,"ClimateChangeMSA.tif")
    wbrc= "3.213|-0.362"
    plrc = "2.867|-0.467" 

    if RU.rasterExists(msa):
      RU.rasterDelete(msa)
      
    pCalc.run(ext,lu,wlf,tc,wbrc,plrc,msa)
    
  except:
    Log.err()
