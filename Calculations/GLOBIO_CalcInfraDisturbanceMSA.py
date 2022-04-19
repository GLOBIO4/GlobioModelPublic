# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 25 apr 2016, ES, ARIS B.V.
#           - Now uses a lookup file with the MSA. This file should contain
#             1 column and 2 lines with the MSA value on the 2-nd line.
#           28 apr 2016, ES, ARIS B.V.
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
from GlobioModel.Core.Grass import Grass
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcInfraDisturbanceMSA(CalculationBase):
  """
  Calculates a raster with the MSA of disturbance by infrastructure.
  """
  #-------------------------------------------------------------------------------
  # Remark:
  #   When SettlementDistance is specified the following parameters are
  #   not needed:
  #   - Roads
  #   - MaximumDistanceKM
  #   - Landuse
  #   - LookupFile
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN STRING INFRADIST_LandcoverExlCodes
    IN FILE WaterLookupFile
    IN RASTER SettlementDistance
    IN RASTER Roads
    IN FLOAT INFRADIST_MaximumDistanceKM
    IN STRING INFRADIST_WbVertRegressionCoefficients
    IN FLOAT INFRADIST_WeightFactor
    OUT RASTER InfraDisturbanceMSA
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=9:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    landcoverExlCodesStr= args[2]
    lookupFileName = args[3]
    settDistanceRasterName = args[4]
    roadsRasterName = args[5]
    maxDistanceKM = args[6]
    wbvertRegressionCoeffsStr = args[7]
    weightFactor = args[8]
    outRasterName = args[9]

    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(settDistanceRasterName,optional=True)
    self.checkRaster(landuseRasterName)
    self.checkIntegerList(landcoverExlCodesStr)
    self.checkLookup(lookupFileName)
    # A settlement distance raster specified?
    if self.isValueSet(settDistanceRasterName):
      # Set the flag.
      calcSettlementDistance = False
    else:
      # Set the flag.
      calcSettlementDistance = True
      # The next parameters are needed and must be valid.
      self.checkRaster(roadsRasterName)
      self.checkFloat(maxDistanceKM,0,99999)
    self.checkFloatList(wbvertRegressionCoeffsStr,needCnt=2)
    self.checkFloat(weightFactor,0.0,1.0)
    self.checkRaster(outRasterName,True)
    
    # Convert code and names to arrays.
    landcoverExlCodes = self.splitIntegerList(landcoverExlCodesStr)
    wbvertRegressionCoeffs = self.splitFloatList(wbvertRegressionCoeffsStr)

    # Get the minimum cellsize for the output raster.
    if calcSettlementDistance:
      inRasterNames = [roadsRasterName,landuseRasterName]
    else:
      inRasterNames = [settDistanceRasterName,landuseRasterName]
    cellSize = self.getMinimalCellSize(inRasterNames)
    Log.info("Using cellsize: %s" % cellSize)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Set temporary raster names.
    tmpWbVertMSARasterName = os.path.join(self.outDir,"tmp_wbvertmsa.tif")
    
    # Remove temporary data.
    if RU.rasterExists(tmpWbVertMSARasterName):
      RU.rasterDelete(tmpWbVertMSARasterName)
   
    #-----------------------------------------------------------------------------
    # Calculate nearest distance to roads. 
    #-----------------------------------------------------------------------------
   
    # Need to calculate settlement distances?
    if calcSettlementDistance:
    
      # Set temporary raster names.
      tmpRoadsRasterName = os.path.join(self.outDir,"tmp_infradist_roads.tif")
      tmpDistanceRasterName = os.path.join(self.outDir,"tmp_infradist_roadsdist.tif")
      
      #-----------------------------------------------------------------------------
      # Read the roads raster and prepare, and save.
      #-----------------------------------------------------------------------------

      Log.info("Reading roads raster...")
      
      # Reads the raster and resizes to extent and resamples to cellsize.
      tmpRaster = self.readAndPrepareInRaster(extent,cellSize,roadsRasterName,"roads")

      # Replace 0 with nodata for buffering.
      tmpRaster.r[tmpRaster.r==0] = tmpRaster.noDataValue

      # Check the temporary roads raster.
      if RU.rasterExists(tmpRoadsRasterName):
        RU.rasterDelete(tmpRoadsRasterName)

      # Save the temporary roads raster.
      Log.info("Writing %s..." % tmpRoadsRasterName)
      tmpRaster.writeAs(tmpRoadsRasterName)

      # Close and free the temporary raster.
      tmpRaster.close()
      tmpRaster = None
                         
      Log.info("Calculating nearest distance to roads...")
      
      # Check the temporary distance raster.
      if RU.rasterExists(tmpDistanceRasterName):
        RU.rasterDelete(tmpDistanceRasterName)
        
      # Calculate nearest distance to settlements. 
      gr = Grass()
      gr.init()
      gr.distance_V1(extent,cellSize,tmpRoadsRasterName,tmpDistanceRasterName)
      gr = None
          
      # Read distance raster.
      Log.info("Reading roads distance...")
      distanceRaster = Raster(tmpDistanceRasterName)
      distanceRaster.read()
    
      # Limit distance to maximum value.
      maxDistanceM = maxDistanceKM * 1000.0
      mask = (distanceRaster.r >= maxDistanceM)
      distanceRaster.r[mask] = maxDistanceM
        
      # Cleanup mask.
      mask = None
    
      # Select valid distance values.
      noDataValue = distanceRaster.noDataValue
      distMask = (distanceRaster.r > 0.0) & (distanceRaster.r != noDataValue)
      zerodistMask = (distanceRaster.r == 0.0) & (distanceRaster.r != noDataValue)
    
      # Convert distance meters to kilometers.
      distanceRaster.r[distMask] /= 1000.0
      
      # Reads the landuse raster and resizes to extent and resamples to cellsize.
      landuseRaster = self.readAndPrepareInRaster(extent,cellSize,landuseRasterName,"landuse")
      
      # Do lookup to filter out water areas.
      lookupFieldTypes = ["I","F"]
      tmpLUFactorRaster = self.reclassUniqueValues(landuseRaster,
                                                   lookupFileName,lookupFieldTypes,
                                                   np.float32)

      #Reclassify water areas to NoData
      noDataValue = -999.0
      mask = (tmpLUFactorRaster.r == noDataValue)
      distanceRaster.r[mask] = noDataValue
      mask = None
    
      # Close and free the roads distance raster.
      # 20210104
      # tmpRoadsRasterName.close()
      # tmpRoadsRasterName = None
      # tmpDistanceRasterName.close()
      # tmpDistanceRasterName = None
      
      # Close and free the landuse raster.
      landuseRaster.close()
      landuseRaster = None
      tmpLUFactorRaster.close()
      tmpLUFactorRaster = None
      
      #-----------------------------------------------------------------------------
      # Remove temporary rasters.
      #-----------------------------------------------------------------------------
      if not GLOB.saveTmpData:
        if RU.rasterExists(tmpRoadsRasterName):
          RU.rasterDelete(tmpRoadsRasterName)
        if RU.rasterExists(tmpDistanceRasterName):
          RU.rasterDelete(tmpDistanceRasterName)
          
    else:
      Log.info("Reading road distances...")

      #-----------------------------------------------------------------------------
      # Read the roads raster and prepare, and save.
      #-----------------------------------------------------------------------------
      # Reads the raster and resizes to extent and resamples to cellsize.
      distanceRaster = self.readAndPrepareInRaster(extent,cellSize,settDistanceRasterName,"road distances")
      
      # Select valid distance values.
      noDataValue = distanceRaster.noDataValue
      distMask = (distanceRaster.r > 0.0) & (distanceRaster.r != noDataValue)
      zerodistMask = (distanceRaster.r == 0.0) & (distanceRaster.r != noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate mammal MSA.
    #-----------------------------------------------------------------------------

    Log.info("Calculating warm-blooded vert. MSA...")

    # Create raster with default MSA value 1.
    noDataValue = -999.0
    outWbVertMSARaster = Raster()
    outWbVertMSARaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Set regression coefficients.
    b0 = wbvertRegressionCoeffs[0]
    b1 = wbvertRegressionCoeffs[1]
       
    outWbVertMSARaster.r[distMask] = 1/(1+np.exp(-b0 - b1 * np.log10(distanceRaster.r[distMask]) - 3 * b1))

    # Set cells to 0 where distance = 0.0.
    outWbVertMSARaster.r[zerodistMask] = 0.0

    # Set all cells with values <0 to 0.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r < 0.0)
    outWbVertMSARaster.r[mask] = 0.0

    # Set all cells with values >1 to 1.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r > 1.0)
    outWbVertMSARaster.r[mask] = 1.0

    # Cleanup mask.
    mask = None
    distMask = None
    zerodistMask = None
    
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
    outWbVertMSARaster.r[mask] = noDataValue
    mask = None
    
    #JM: previous location of landuseRaster reading in

    # Select specified landcover types (selected = 1).
    for landcoverExlCode in landcoverExlCodes:
      mask = (outWbVertMSARaster.r != noDataValue) & (landuseRaster.r == landcoverExlCode)
      outWbVertMSARaster.r[mask] = noDataValue
      distanceRaster.r[mask] = distanceRaster.noDataValue

    # Cleanup mask.
    mask = None
    
    # Close and free the landuse raster.
    landuseRaster.close()
    landuseRaster = None
    
    # Close and free the distance raster.
    Log.info("Writing input raster....")
    distanceRaster.writeAs(outRasterName.replace(".tif","_finalinput.tif"))
    distanceRaster.close()
    distanceRaster = None

    # Save tmp files?
    if GLOB.saveTmpData:
      # Save mammal MSA.
      outWbVertMSARaster.writeAs(tmpWbVertMSARasterName)

    # Write away taxonomic group - MSA output
    Log.info("Writing taxonomic group - MSA rasters....")
    outWbVertMSARaster.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
    
    #-----------------------------------------------------------------------------
    # Calculate final MSA.
    #
    # Disturbance MSA = (Warm-blooded Vert. MSA * 1/3) + 2/3
    #
    # For the overall MSA, we need to add 2/3. This is because we assume that
    # for the other 2 taxonomic groups, there is no disturbance impact (MSA = 1).
    #-----------------------------------------------------------------------------

    Log.info("Creating the disturbance by infrastructure MSA raster...")
    
    # Assign warm-blooded vert. MSA to outRaster (as a referrence).
    outRaster = outWbVertMSARaster
    mask = (outRaster.r != noDataValue)

    complWeightFactor = 1.0 - weightFactor
    outRaster.r[mask] *= weightFactor
    outRaster.r[mask] += complWeightFactor
    
    # Clear mask.
    mask = None 

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------

    # Save the disturbance by infrastructure MSA raster.
    #Log.info("Writing MSA of disturbance by infrastructure raster...")
    # Save final MSA.
    #outRaster.writeAs(outRasterName)

    # Cleanup.
    outWbVertMSARaster.close()
    outWbVertMSARaster = None
    outRaster.close()
    outRaster = None

    # Cleanup temporary files.
    if not GLOB.saveTmpData:
      if RU.rasterExists(tmpWbVertMSARasterName):
        RU.rasterDelete(tmpWbVertMSARasterName)
        
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

    pCalc = GLOBIO_CalcInfraDisturbanceMSA()

    ext = GLOB.extent_World
    roads = os.path.join(mapDir,"GRIP4_5types_10sec.tif")
    dist = os.path.join(mapDir,"GRIP4_distance_km_10sec.tif")
    maxdist = 150
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    lookup = os.path.join(lookupDir,"LanduseNDepFactor_Globio4.csv")    
    wbvertRegressionCoeffs = "1.06|0.36"
    wf = 0.33333333
    msa = os.path.join(outDir,"InfraDisturbanceMSA.tif")

    if RU.rasterExists(msa):
      RU.rasterDelete(msa)

    pCalc.run(ext,dist,roads,maxdist,lu,lookup,wbvertRegressionCoeffs,wf,msa)

  except:
    Log.err()
