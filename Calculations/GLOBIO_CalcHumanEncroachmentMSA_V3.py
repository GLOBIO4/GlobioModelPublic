# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
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
#           5 dec 2017, ES, ARIS B.V.
#           - Version 4.0.11
#           - New formula.
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
import GlobioModel.Common.Utils as UT

from GlobioModel.Calculations.GLOBIO_CalcSettlementDistance import GLOBIO_CalcSettlementDistance

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcHumanEncroachmentMSA_V3(CalculationBase):
  """
  Calculates a raster with the MSA of human encroachment.
  """
  
  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()    
    super(GLOBIO_CalcHumanEncroachmentMSA_V3,self).__init__()

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
  # v09: Nu met een nieuwe formule.
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER SettlementDistance
    IN DIR SettlementsDir
    IN RASTER TravelTime
    IN INTEGER MinimumTravelTimeMIN
    IN INTEGER MaximumTravelTimeMIN
    IN RASTER Landcover
    IN STRING LandcoverCodes
    IN FLOAT LandcoverBufferDistanceKM
    IN FLOAT MaximumDistanceKM
    IN STRING MammalRegressionCoefficients
    IN STRING BirdRegressionCoefficients
    OUT RASTER HumanEncroachmentMSA
    """
    
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=12:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    settDistanceRasterName = args[1]
    settlementsDir = args[2]
    travelTimeRasterName = args[3]
    minTravelTimeMIN = args[4]
    maxTravelTimeMIN = args[5]
    landcoverRasterName = args[6]
    landcoverCodesStr= args[7]
    landcoverBufferKM = args[8]
    maxDistanceKM = args[9]
    mammalRegressionCoeffsStr = args[10]
    birdRegressionCoeffsStr = args[11]
    outRasterName = args[12]

    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(settDistanceRasterName,optional=True)
    # A settlement distance raster specified?
    if self.isValueSet(settDistanceRasterName):
      # Set the flag.
      calcSettlementDistance = False
    else:
      # Set the flag.
      calcSettlementDistance = True
      # The next parameters are needed and must be valid.
      self.checkDirectory(settlementsDir)
      self.checkRaster(travelTimeRasterName)
      self.checkInteger(minTravelTimeMIN,0,99999999)
      self.checkInteger(maxTravelTimeMIN,0,99999999)
      self.checkRaster(landcoverRasterName)
      self.checkIntegerList(landcoverCodesStr)
      self.checkFloat(landcoverBufferKM,0,99999)
      self.checkFloat(maxDistanceKM,0,99999)
    self.checkFloatList(mammalRegressionCoeffsStr,needCnt=3)
    self.checkFloatList(birdRegressionCoeffsStr,needCnt=3)
    self.checkRaster(outRasterName,asOutput=True)

    # Convert code and names to arrays.
    mammalRegressionCoeffs = self.splitFloatList(mammalRegressionCoeffsStr)
    birdRegressionCoeffs = self.splitFloatList(birdRegressionCoeffsStr)

    # Get the minimum cellsize for the output raster.
    if calcSettlementDistance:
      inRasterNames = [travelTimeRasterName,landcoverRasterName]
    else:
      inRasterNames = [settDistanceRasterName]
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
    tmpMammalMSARasterName = os.path.join(self.outDir,"tmp_mammalmsa.tif")
    tmpBirdMSARasterName = os.path.join(self.outDir,"tmp_birdmsa.tif")

    # Remove temporary data.
    if RU.rasterExists(tmpMammalMSARasterName):
      RU.rasterDelete(tmpMammalMSARasterName)
    if RU.rasterExists(tmpBirdMSARasterName):
      RU.rasterDelete(tmpBirdMSARasterName)

    # Need to calculate settlement distances?
    if calcSettlementDistance:
      
      # Calculate the distances (km) to the nearest settlements.
      pCalc = GLOBIO_CalcSettlementDistance()
      distanceRaster = pCalc.calcDistance(extent,cellSize,
                settlementsDir,travelTimeRasterName,
                minTravelTimeMIN,maxTravelTimeMIN,
                landcoverRasterName,landcoverCodesStr,landcoverBufferKM,
                maxDistanceKM,self.outDir)
      pCalc = None

    else:
      Log.info("Reading settlement distances...")
      
      # Read settlement distance raster.
      distanceRaster = Raster(settDistanceRasterName)
      distanceRaster.read()

    # Select valid distance values.
    noDataValue = distanceRaster.noDataValue
    distMask = (distanceRaster.r > 0.0) & (distanceRaster.r != noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate mammal MSA. 
    #-----------------------------------------------------------------------------

    Log.info("Calculating mammal MSA...")

    # Create raster with default MSA value 1.
    outMammalMSARaster = Raster()
    outMammalMSARaster.initRaster(extent,cellSize,np.float32,255,1)

    # Set regression coefficients.
    b0 = mammalRegressionCoeffs[0]
    b1 = mammalRegressionCoeffs[1]
    b2 = mammalRegressionCoeffs[2]

    # Calculate MSA for the valid cells.
    # 
#    # MSA = e ^ (b0 + b1*ln(d) + b2*(ln(d)^2))
#    #
#    outMammalMSARaster.r[distMask] = np.exp(b0 + b1 * np.log(distanceRaster.r[distMask]) + b2 * np.power(np.log(distanceRaster.r[distMask]),2))
#
#    # Set all other cells to 0.
#    outMammalMSARaster.r[~distMask] = 0.0
#    
#    # Set all cells with values >=1 to 1.
#    mask = (outMammalMSARaster.r >= 1.0)
#    outMammalMSARaster.r[mask] = 1.0

    
    # Modified 20171205
    # MSA = if(b0+b1*log(distance)+b2*(log(distance))^2<0,
    #          0,
    #          if(b0+b1*log(distance)+b2*(log(distance))^2<1,
    #             b0+b1*log(distance)+b2*(log(distance))^2,
    #             1))
    outMammalMSARaster.r[distMask] = b0 + b1 * np.log10(distanceRaster.r[distMask]) + b2 * np.power(np.log10(distanceRaster.r[distMask]),2)

    # Set all other cells to 0.0.
    outMammalMSARaster.r[~distMask] = 0.0
    
    # Set all cells with values <0 to 0.0.
    mask = (outMammalMSARaster.r < 0.0)
    outMammalMSARaster.r[mask] = 0.0

    # Set all cells with values >1 to 1.0.
    mask = (outMammalMSARaster.r > 1.0)
    outMammalMSARaster.r[mask] = 1.0

    # Cleanup mask.
    mask = None

    # Save tmp files?
    if GLOB.saveTmpData:
      # Save mammal MSA.
      outMammalMSARaster.writeAs(tmpMammalMSARasterName)

    #-----------------------------------------------------------------------------
    # Calculate bird MSA. 
    #-----------------------------------------------------------------------------
 
    Log.info("Calculating bird MSA...")
 
    # Create raster with default MSA value 1.
    outBirdMSARaster = Raster()
    outBirdMSARaster.initRaster(extent,cellSize,np.float32,255,1)

    # Set regression coefficients.
    b0 = birdRegressionCoeffs[0]
    b1 = birdRegressionCoeffs[1]
    b2 = birdRegressionCoeffs[2]
 
    # Calculate MSA for the valid cells.
    #         
    # MSA = e ^ (b0 + b1*ln(d) + b2*(ln(d)^2))
    #
    outBirdMSARaster.r[distMask] = np.exp(b0 + b1 * np.log(distanceRaster.r[distMask]) + b2 * np.power(np.log(distanceRaster.r[distMask]),2))

    # Set all other cells to 0.
    outBirdMSARaster.r[~distMask] = 0.0
     
    # Set all cells with values >=1 to 1.
    mask = (outBirdMSARaster.r >= 1.0)
    outBirdMSARaster.r[mask] = 1.0

    # Cleanup mask.
    mask = None
    distMask = None
 
    # Save tmp files?
    if GLOB.saveTmpData:
      # Save brid MSA.
      outBirdMSARaster.writeAs(tmpBirdMSARasterName)

    # Close and free the distance raster.
    distanceRaster.close()
    distanceRaster = None

    #-----------------------------------------------------------------------------
    # Calculate final MSA.
    #
    # Encroachment MSA = ((Mammal MSA + Bird MSA) / 2 * 2/6) + 4/6
    #
    # For the overall MSA, we need to add 4/6. This is because we assume that
    # for the other four taxonomic groups, there is no hunting impact (MSA = 1).
    # The overall impact is in fact MSA-mammals*1/6 + MSA-birds*1/6 + 
    # MSA-amphibians*1/6 + MSA-reptiles* 1/6 + MSA-invertebrates*1/6 + 
    # MSA-plants*1/6, where MSA=1 for the groups other than mammals and birds. 
    # So then we have 1/6*(MSA-mammals + MSA-birds) + 4/6.
    #-----------------------------------------------------------------------------

    # Assign mammal MSA to outRaster (as a referrence).
    outRaster = outMammalMSARaster
    
    outRaster.r += outBirdMSARaster.r

    factor = 1.0/2.0 * 2.0/6.0
    outRaster.r *= factor

    factor = 4.0/6.0
    outRaster.r += factor

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------

    Log.info("Writing %s..." % outRasterName)

    # Save final MSA.
    outRaster.writeAs(outRasterName)

    # Close and free the output raster.
    outBirdMSARaster.close()
    outBirdMSARaster = None
    outRaster.close()
    outRaster = None

    # Cleanup temporary files.
    if not GLOB.saveTmpData:
      if RU.rasterExists(tmpMammalMSARasterName):
        RU.rasterDelete(tmpMammalMSARasterName)
      if RU.rasterExists(tmpBirdMSARasterName):
        RU.rasterDelete(tmpBirdMSARasterName)

    # Show used memory and disk space.
    MON.showMemDiskUsage()
    
    self.showEndMsg()
    
  #-------------------------------------------------------------------------------
  def doTest(self):

    if not self.test:
      self.debug = False
      
    #self.debug = True
    GLOB.saveTmpData = True

    if self.debug:
      GLOB.SHOW_TRACEBACK_ERRORS = True

    #-----------------------------------------------------------------------------
    # SETTINGS.
    #-----------------------------------------------------------------------------

    linux = True

    # Bij 10sec wordt de oorspronkelijke esa tif gebruikt
    # en de 30sec region tif.
    landcoverRefVersion = "20170116"
    travelTimeRefVersion = "20170116"

    extentName = "wrld"
    cellSizeName = "30sec"
    #cellSizeName = "10sec"

    # Multipoint shapefile.
    inSettlementsDir = r"G:\Data\Globio4LA\data\luh_20170907\Settlements"
    inTravelTimeDir = r"G:\Data\Globio4LA\data\referentie\v405\30sec_wrld\in_%s" % (travelTimeRefVersion)
    inLandcoverDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\in_%s" % (cellSizeName,extentName,landcoverRefVersion)
    outVersion = "20170911"
    outDir = r"G:\Data\Globio4LA\data\referentie\v409\%s_wrld\globio_%s" % (cellSizeName,outVersion)

    # Use 1 settlements shapefile.
    #self.test = True
    self.test = False
    
    # Set extent and cellsize.
    extent = GLOB.constants[extentName].value
    #extent = [1.154,6.310,3.250,7.871]          # Benin
    #extent = [0.0,10,15,21]                     # Western Africa
    cellSize = GLOB.constants[cellSizeName].value
    extent = RU.alignExtent(extent,cellSize)

    travelTimeRasterName = "acc_50k.tif"
    landcoverRasterName = "esa_lc_2010.tif"
    outRasterName = "HumanEncroachmentMSA.tif"

    if cellSizeName == "10sec":
      # Gebruik originele esa landcover.
      inLandcoverDir = r"G:\Data\Globio4LA\data\web_20161104\esa"
      landcoverRasterName = "ESACCI-LC-L4-LCCS-Map-300m-P5Y-2010-v1.6.1.tif"

    minTravelTimeMin = 5
    maxTravelTimeMin = 5270
    
    # Linux?
    if linux:
      print("Linux")
      inSettlementsDir = UT.toLinux(inSettlementsDir)
      inTravelTimeDir = UT.toLinux(inTravelTimeDir)
      inLandcoverDir = UT.toLinux(inLandcoverDir)
      outDir = UT.toLinux(outDir)
    
    # Add paths.
    travelTimeRasterName = os.path.join(inTravelTimeDir,travelTimeRasterName)
    landcoverRasterName = os.path.join(inLandcoverDir,landcoverRasterName)
    outRasterName = os.path.join(outDir,outRasterName)
    
    # Create directory.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)
    
    if RU.rasterExists(outRasterName):
      RU.rasterDelete(outRasterName)
    
    landcoverCodes = "190"
    landcoverBufferKM = 1
    #maxDistanceKM = 40
    maxDistanceKM = 150
    mammalRegressionCoeffs = "-2.3633|0.1012|0.1498"
    birdRegressionCoeffs = "-2.0005|1.216|-0.1234"
    
    self.run(extent,
             inSettlementsDir,
             travelTimeRasterName,minTravelTimeMin,maxTravelTimeMin,
             landcoverRasterName,landcoverCodes,landcoverBufferKM,
             maxDistanceKM,
             mammalRegressionCoeffs,birdRegressionCoeffs,
             outRasterName)
      
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  try:
    pCalc = GLOBIO_CalcHumanEncroachmentMSA_V3()
    pCalc.doTest()
  except:
    Log.err()
