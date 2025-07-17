# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# Remarks : During a run the GRASS distance function can take a lot of
#           diskspace for temporary use, in case of 10sec runs more than
#           200GB.
#
# Modified: 4 sep 2017, ES, ARIS B.V.
#           - Version 4.0.8
#           - New version with settlement shapefiles.
#           11 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - Use of wwf ecoregions removed.
#           - run() modified, check on ogr.wkbPoint25D added.
#           - run() modified, tmpDistanceKMRasterName added.
#           - run() modified, enableLogToFile removed.
#           - run() modified, check on number of settlements added.
#           27 sep 2017, ES, ARIS B.V.
#           - Version 4.0.10
#           - Separate module created for distance calculation.
#           2 june 2019, JH, PBL
#           - Limit the MSA calculations to the tropical biome
#           30 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - Commented out because of serious PyLint error.
#            Dec 2021
#           - Issues checked and calculation run, results OK
#-------------------------------------------------------------------------------

import os
import numpy as np

import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Grass import Grass
from GlobioModel.Core.Raster import Raster
from GlobioModel.Core.Vector import Vector

#import Convert as CO
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Common.Utils as UT

# 20201202
#from GlobioModel.Calculations.GLOBIO_CalcSettlementDistance_V2 import GLOBIO_CalcSettlementDistance_V2
from GlobioModel.Calculations.GLOBIO_CalcSettlementDistance import GLOBIO_CalcSettlementDistance

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcHumanEncroachmentMSA_V2b(CalculationBase):
  """
  Calculates a raster with the MSA of human encroachment.
  """

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcHumanEncroachmentMSA_V2b,self).__init__()

    #-------------------------------------------------------------------------------
    # Set internal settings.
    #-------------------------------------------------------------------------------

    self.mtimer = None

    self.debug = False
    #self.debug = True

    #self.showProgress = False
    self.showProgress = True

    self.test = False

  #-------------------------------------------------------------------------------
  # Remarks:
  #   When SettlementDistance is specified the following parameters are
  #   not needed:
  #   - SettlementsDir
  #   - TravelTime
  #   - MinimumTravelTimeMIN
  #   - MaximumTravelTimeMIN
  #   - Landcover
  #   - LandcoverCodes
  #   - LandcoverBufferDistanceKM
  #   - MaximumDistanceKM.
  #
  # v03: Nu met een begrenzing bij het berekenen van de distance.
  # v04: Bij mammal en bird MSA wordt nu de settlement cellen op 0.0 gezet.
  #      Nu met gebruik saveTmpFiles.
  # v05: Gebruikt nu gr.vectorToRaster.
  #      Nu met uitfilteren ongeldige settlement punten.
  #      Gebruikt nu maxDistKM ivm. BridMSA.
  # v06: Nu met maxDistanceKM parameter.
  #      Nu met monitor.
  # v07: Nu zonder de wwf ecoregions.
  # v08: Nu met setllement distance.
  # v09: Vergelijking MSA berekening aangepast ivm update Radboud (JM/ES)
  # Adding the global LU mask exclusion code (water/210) for distance calc mask
  #
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN STRING HUMANENC_LandcoverExlCodes
    IN FILE WaterLookupFile    
    IN RASTER SettlementDistance
    IN DIR SettlementsDir
    IN RASTER TropBiome
    IN STRING LandcoverCodes
    IN FLOAT HUMANENC_LandcoverBufferDistanceKM
    IN STRING HUMANENC_WbVertRegressionCoefficients
    IN FLOAT HUMANENC_WeightFactor
    IN STRING MASK_Global_LU_ExlCode
    IN RASTER SettlementRaster
    OUT RASTER HumanEncroachmentMSA
    """

    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=12:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    landcoverExlCodesStr= args[2]
    lookupFileName = args[3]
    settDistanceRasterName = args[4]
    settlementsDir = args[5]
    tropBiomeRasterName = args[6]
    landcoverCodesStr= args[7]
    landcoverBufferKM = args[8]
    wbvertRegressionCoeffsStr = args[9]
    weightFactor = args[10]
    maskGlobalLuExlCodeStr = args[11]
    SettlementRasterName = args[12]
    outRasterName = args[13]

    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(settDistanceRasterName,optional=True)
    self.checkRaster(landuseRasterName)
    self.checkIntegerList(landcoverExlCodesStr)
    self.checkLookup(lookupFileName)
    # JH: check tropical biome raster
    self.checkRaster(tropBiomeRasterName)
    # A settlement distance raster specified?
    if self.isValueSet(settDistanceRasterName):
      # Set the flag.
      calcSettlementDistance = False
    else:
      # Set the flag.
      calcSettlementDistance = True
      if self.isValueSet(SettlementRasterName):
        useSettlementRaster = True
        # The next parameters are needed and must be valid.
        self.checkRaster(SettlementRasterName,optional=True)
      else:
        useSettlementRaster = False
        # The next parameters are needed and must be valid.
        self.checkDirectory(settlementsDir)
      # The next parameters are needed and must be valid.
      self.checkIntegerList(landcoverCodesStr)
      self.checkFloat(landcoverBufferKM,0,99999)
      self.checkIntegerList(maskGlobalLuExlCodeStr)
    self.checkFloatList(wbvertRegressionCoeffsStr,needCnt=2)
    self.checkFloat(weightFactor,0.0,1.0)
    self.checkRaster(outRasterName,asOutput=True)

    # Convert code and names to arrays.
    landcoverExlCodes = self.splitIntegerList(landcoverExlCodesStr)
    wbvertRegressionCoeffs = self.splitFloatList(wbvertRegressionCoeffsStr)

    # Get the minimum cellsize for the output raster.
    if calcSettlementDistance:
      inRasterNames = [tropBiomeRasterName,landuseRasterName,SettlementRasterName]
    else:
      inRasterNames = [settDistanceRasterName,landuseRasterName,tropBiomeRasterName]
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

    # Set temporary vector/raster names.
    tmpWbVertMSARasterName = os.path.join(self.outDir,"tmp_wbvertmsa.tif")

    # Remove temporary data.
    if RU.rasterExists(tmpWbVertMSARasterName):
      RU.rasterDelete(tmpWbVertMSARasterName)

    # Need to calculate settlement distances?
    if calcSettlementDistance:

      # Calculate the distances (km) to the nearest settlements.
      # Check if settlementsraster is already provided
      if useSettlementRaster:
        pCalc = GLOBIO_CalcSettlementDistance_V2()
        distanceRaster = pCalc.calcDistance(extent,cellSize,
                  settlementsDir,tropBiomeRasterName,
                  landuseRasterName,landcoverCodesStr,landcoverBufferKM,maskGlobalLuExlCodeStr,
                  self.outDir,SettlementRasterName)
        pCalc = None
      else:
        pCalc = GLOBIO_CalcSettlementDistance_V2()
        
        # 20201130 - Python2 -> 3
        Err.raiseGlobioError(Err.UserDefined1,"Python2->3 - Invalid Call, please correct code.")

        # distanceRaster = pCalc.calcDistance(extent,cellSize,
        #           settlementsDir,tropBiomeRasterName,
        #           landuseRasterName,landcoverCodesStr,landcoverBufferKM,maskGlobalLuExlCodeStr,
        #           self.outDir)
        pCalc = None
    
    else:
      Log.info("Reading settlement distances...")
      #-------------------------------------------------------------------------------------
      # If provided, read the preprocessed settlement distance raster and prepare, and save.
      #-------------------------------------------------------------------------------------
      # Reads the raster and resizes to extent and resamples to cellsize.
      distanceRaster = self.readAndPrepareInRaster(extent,cellSize,settDistanceRasterName,"settlement distances")
    
    # JH: Limit distance to tropical biome.
    
    # Reads the biome raster and resizes to extent and resamples to cellsize.
    tropBiomeRaster = self.readAndPrepareInRaster(extent,cellSize,tropBiomeRasterName,"tropical biome")

    Log.info("Selecting tropical biome...")

    mask = ((tropBiomeRaster.r == tropBiomeRaster.noDataValue) | (tropBiomeRaster.r == 0))
    noDataValue = distanceRaster.noDataValue
    distanceRaster.r[mask] = noDataValue
    
    # Cleanup mask.
    mask = None

    # Select valid distance values.
    distMask = (distanceRaster.r > 0.0)

    # Convert distance meters to kilometers.
    #distanceRaster.r[distMask] /= 1000.0
      
    # END update JH

    # Select valid distance values.
    noDataValue = distanceRaster.noDataValue
    distMask = (distanceRaster.r > 0.0) & (distanceRaster.r != noDataValue)
    zerodistMask = (distanceRaster.r == 0.0) & (distanceRaster.r != noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate warm-blooded vert. MSA.
    #-----------------------------------------------------------------------------

    Log.info("Calculating warm-blooded vert. MSA...")

    # Create raster with default MSA value 1.
    noDataValue = -999.0
    outWbVertMSARaster = Raster()
    outWbVertMSARaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Set regression coefficients.
    b0 = wbvertRegressionCoeffs[0]
    b1 = wbvertRegressionCoeffs[1]

    outWbVertMSARaster.r[distMask] = 1/(1+np.exp(-b0 - b1 * np.log10(distanceRaster.r[distMask])))

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
    # END UPDATE
    
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
    # JM: moved to here to enable set nodata MSA factor for areas beyond 150km
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
    # Encroachment MSA = (Warm-blooded Vert. MSA * 1/3) + 2/3
    #
    # For the overall MSA, we need to add 2/3. This is because we assume that
    # for the other 2 taxonomic groups, there is no hunting impact (MSA = 1).
    #
    #-----------------------------------------------------------------------------
    Log.info("Creating the encroachment MSA raster...")
    
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

    Log.info("Writing %s..." % outRasterName)

    # Save final MSA.
    outRaster.writeAs(outRasterName)

    # Close and free the output raster.
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
    inDir = r""
    mapDir = r""
    lookupDir = r""
    inSettlementsDir = r""  
    inTravelTimeDir = r""  
    outDir = r""

    pCalc = GLOBIO_CalcHumanEncroachmentMSA_V2b()
 
    ext =  [-180,-57,-26,84] #GLOB.constants["world"].value
    dist = os.path.join(mapDir,"SettlementDistanceCurrentKM.tif")
    setdir = inSettlementsDir
    trraster = os.path.join(inTravelTimeDir,"acc_50k.tif")
    mintr = 5
    maxtr = 5270
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    lucode = 190
    lubuf = 1
    maxdi = 150
    wbvertRegressionCoeffs = "0.33|0.37"
    wf = 0.33333333
    msa = os.path.join(outDir,"InfraDisturbanceMSA.tif")

    if RU.rasterExists(msa):
      RU.rasterDelete(msa)

    pCalc.run(ext,dist,setdir,trraster,mintr,maxtr,lu,lucode,lubuf,maxdi,wbvertRegressionCoeffs,wf,msa)

  except:
    Log.err()
