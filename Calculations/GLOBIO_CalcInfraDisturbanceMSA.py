# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
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
  #   When InfrastructureDistance is specified the following parameters are
  #   not needed:
  #   - Infrastructure
  #   - MaximumDistanceKM
  #   - Landuse
  #   - WaterLookupFile
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN STRING INFRADIST_LandcoverExclCodes
    IN RASTERLIST InfraDistances
    IN RASTERLIST Infrastructures
    IN FLOAT INFRADIST_MaximumDistanceKM
    IN STRING INFRADIST_WbVertRegressionCoefficients
    IN FLOAT INFRADIST_WeightFactor
    OUT RASTER InfraDisturbanceMSA
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args) != 9:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    landcoverExclCodesStr= args[2]
    infraDistanceRasterNames = args[3]
    infraRasterNames = args[4]
    maxDistanceKM = args[5]
    wbvertRegressionCoeffsStr = args[6]
    weightFactor = args[7]
    outRasterName = args[8]

    # Check arguments.
    self.checkExtent(extent)
    self.checkRasterList(infraDistanceRasterNames, optional=True)
    if self.isValueSet(infraDistanceRasterNames):
      infraDistanceRasterNames = self.splitStringList(infraDistanceRasterNames)
    else:
      infraDistanceRasterNames = []
    self.checkRaster(landuseRasterName)
    self.checkIntegerList(landcoverExclCodesStr)
    self.checkRasterList(infraRasterNames, optional=True)
    if self.isValueSet(infraRasterNames):
      # maxDistanceKM is required when passing a raster
      self.checkFloat(maxDistanceKM,0,99999)
      infraRasterNames = self.splitStringList(infraRasterNames)
    else:
      infraRasterNames = []
    self.checkFloatList(wbvertRegressionCoeffsStr,needCnt=2)
    self.checkFloat(weightFactor,0.0,1.0)
    self.checkRaster(outRasterName,True)

    if len(infraDistanceRasterNames) == 0 and len(infraRasterNames) == 0:
      Err.raiseGlobioError(Err.UserDefined1, "Either 'InfraDistances' or 'Infrastructures' argument should contain at least one raster")
    
    # Convert code and names to arrays.
    landcoverExclCodes = self.splitIntegerList(landcoverExclCodesStr)
    wbvertRegressionCoeffs = self.splitFloatList(wbvertRegressionCoeffsStr)

    # Get the minimum cellsize for the output raster.
    inRasterNames = infraDistanceRasterNames + infraRasterNames + [landuseRasterName]
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
   
    tmpCombInfraDistanceRasterName = os.path.join(self.outDir,"tmp_combinfradistance.tif")
    if RU.rasterExists(tmpCombInfraDistanceRasterName):
      Log.info("Delete %s" % tmpCombInfraDistanceRasterName)
      RU.rasterDelete(tmpCombInfraDistanceRasterName)

    noDataValue = -999.0
    combinedInfraDistanceRaster = Raster(tmpCombInfraDistanceRasterName)
    combinedInfraDistanceRaster.initRaster(extent, cellSize, np.float32, noDataValue)

    # First use the provided distance rasters to calculate a raster with minimum distances
    firstDistanceRaster = True
    for i, infraDistanceRasterName in enumerate(infraDistanceRasterNames):

      if not self.isValueSet(infraDistanceRasterName):
        continue

      Log.info(f"Reading infra distance raster {infraDistanceRasterName}")
      infraDistanceRaster = self.readAndPrepareInRaster(extent, cellSize, infraDistanceRasterName, f"distance {i}")
      self.fuseDistanceRasters(combinedInfraDistanceRaster, infraDistanceRaster, existingIsEmpty=firstDistanceRaster)
      if firstDistanceRaster:
        firstDistanceRaster = False

    # Second, go over the non-distance rasters to first calculate distance and then fuse
    for i, infraRasterName in enumerate(infraRasterNames):

      if not self.isValueSet(infraRasterName):
        continue

      tmpInfraRasterName = os.path.join(self.outDir, f"tmp_infra_{i}.tif")
      tmpInfraDistanceRasterName = os.path.join(self.outDir, f"tmp_infradistance_{i}.tif")

      # Read the infra raster
      Log.info(f"Reading infra raster {infraRasterName}")
      # Reads the raster and resizes to extent and resamples to cellsize.
      tmpInfraRaster = self.readAndPrepareInRaster(extent,cellSize,infraRasterName,f"infra {i}")

      # Replace 0 with nodata for buffering.
      tmpInfraRaster.r[tmpInfraRaster.r==0] = tmpInfraRaster.noDataValue

      # Check the temporary infra raster.
      if RU.rasterExists(tmpInfraRasterName):
        Log.info("Delete %s" % tmpInfraRasterName)
        RU.rasterDelete(tmpInfraRasterName)

      # Save the temporary infra raster.
      Log.info("Writing %s..." % tmpInfraRasterName)
      tmpInfraRaster.writeAs(tmpInfraRasterName)

      # Close and free the temporary raster.
      tmpInfraRaster.close()
      tmpInfraRaster = None

      Log.info(f"Calculating nearest distance to infrastructure {i}...")

      # Check the temporary distance raster.
      if RU.rasterExists(tmpInfraDistanceRasterName):
        Log.info("Delete %s" % tmpInfraDistanceRasterName)
        RU.rasterDelete(tmpInfraDistanceRasterName)
        
      # Calculate nearest distance to infrastructure. 
      gr = Grass()
      gr.init()
      gr.distance_V1(extent,cellSize,tmpInfraRasterName,tmpInfraDistanceRasterName)
      gr = None
          
      # Read distance raster.
      Log.info(f"Reading infra distance raster {tmpInfraDistanceRasterName}...")
      distanceRaster = Raster(tmpInfraDistanceRasterName)
      distanceRaster.read()
    
      # Limit distance to maximum value.
      maxDistanceM = maxDistanceKM * 1000.0
      maxDistMask = (distanceRaster.r >= maxDistanceM)
      distanceRaster.r[maxDistMask] = maxDistanceM
      del maxDistMask
    
      # Convert distance meters to kilometers.
      distMask = (distanceRaster.r > 0.0) & (distanceRaster.r != distanceRaster.noDataValue)
      distanceRaster.r[distMask] /= 1000.0

      if not GLOB.saveTmpData:
        if RU.rasterExists(tmpInfraRasterName):
          RU.rasterDelete(tmpInfraRasterName)
        if RU.rasterExists(tmpInfraDistanceRasterName):
          RU.rasterDelete(tmpInfraDistanceRasterName)

      self.fuseDistanceRasters(combinedInfraDistanceRaster, distanceRaster, existingIsEmpty=firstDistanceRaster)
      # Clear flag if not already cleared
      if firstDistanceRaster:
        firstDistanceRaster = False

      Log.info(f"Writing {tmpInfraDistanceRasterName}...")
      distanceRaster.write()
      distanceRaster.close()
      del distanceRaster

    # check if anything was processed
    if firstDistanceRaster:
      Err.raiseGlobioError(Err.UserDefined1, "No distance raster could be calculated")

    Log.info("Adapting distance raster based on landcover exclude codes...")

    # Reads the landuse raster and resizes to extent and resamples to cellsize.
    landuseRaster = self.readAndPrepareInRaster(extent,cellSize,landuseRasterName,"landuse")
    # Reclassify LC exclusion pixels to noDataValue 
    for landcoverExclCode in landcoverExclCodes:
      mask = (landuseRaster.r == landcoverExclCode)
      combinedInfraDistanceRaster.r[mask] = combinedInfraDistanceRaster.noDataValue
    del mask
    # Close and free the landuse raster.
    landuseRaster.close()
    del landuseRaster

    # Select valid distance values.
    distMask = (combinedInfraDistanceRaster.r > 0.0) & (combinedInfraDistanceRaster.r != combinedInfraDistanceRaster.noDataValue)
    zerodistMask = (combinedInfraDistanceRaster.r == 0.0) & (combinedInfraDistanceRaster.r != combinedInfraDistanceRaster.noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate mammal MSA.
    #-----------------------------------------------------------------------------

    Log.info("Calculating warm-blooded vert. MSA...")

    # Create raster with default MSA value 1.
    msaNoDataValue = -999.0
    outWbvertMSARaster = Raster()
    outWbvertMSARaster.initRaster(extent,cellSize,np.float32,msaNoDataValue)

    # Set regression coefficients.
    b0 = wbvertRegressionCoeffs[0]
    b1 = wbvertRegressionCoeffs[1]
       
    outWbvertMSARaster.r[distMask] = 1/(1+np.exp(-b0 - b1 * np.log10(combinedInfraDistanceRaster.r[distMask]) - 3 * b1))

    # Set cells to 0 where distance = 0.0.
    outWbvertMSARaster.r[zerodistMask] = 0.0

    # Set all cells with values <0 to 0.0.
    mask = (outWbvertMSARaster.r != msaNoDataValue) & (outWbvertMSARaster.r < 0.0)
    outWbvertMSARaster.r[mask] = 0.0

    # Set all cells with values >1 to 1.0.
    mask = (outWbvertMSARaster.r != msaNoDataValue) & (outWbvertMSARaster.r > 1.0)
    outWbvertMSARaster.r[mask] = 1.0

    # Cleanup mask.
    del mask
    del distMask
    del zerodistMask
    
    # Close and free the distance raster.
    Log.info("Writing input raster....")
    if GLOB.saveTmpData:
      combinedInfraDistanceRaster.write()
    combinedInfraDistanceRaster.close()
    del combinedInfraDistanceRaster

    if not GLOB.saveTmpData:
      Log.info("Delete %s" % tmpCombInfraDistanceRasterName)
      RU.rasterDelete(tmpCombInfraDistanceRasterName)

    # Write away taxonomic group - MSA output
    Log.info("Writing taxonomic group - MSA rasters....")
    outWbvertMSARaster.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
    
    #-----------------------------------------------------------------------------
    # Calculate final MSA.
    #
    # Disturbance MSA = (Warm-blooded Vert. MSA * 1/N) + (N-1)/N
    #
    # For the overall MSA, we need to correct. This is because we assume that
    # for the other N-1 taxonomic groups, there is no disturbance impact (MSA = 1).
    #-----------------------------------------------------------------------------

    Log.info("Creating the overall disturbance by infrastructure MSA raster...")
    
    # Assign warm-blooded vert. MSA to outRaster (as a referrence).
    outRaster = outWbvertMSARaster
    mask = (outRaster.r != noDataValue)

    complWeightFactor = 1.0 - weightFactor
    outRaster.r[mask] *= weightFactor
    outRaster.r[mask] += complWeightFactor
    
    # Clear mask.
    del mask

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------

    # Save the disturbance by infrastructure MSA raster.
    Log.info("Writing overall MSA of disturbance by infrastructure raster...")
    # Save final MSA.
    outRaster.writeAs(outRasterName)

    # Cleanup.
    outWbvertMSARaster.close()
    outWbvertMSARaster = None
    outRaster.close()
    del outRaster
        
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

  def fuseDistanceRasters(self, existingRaster : Raster, newRaster : Raster, existingIsEmpty : bool = False):
    Log.info("Fusing distance raster...")
    newNoDataMask = newRaster.getNoDataMask()
    existingNoDataMask = existingRaster.getNoDataMask()
    # if read raster has different nodataval, replace it first
    if newRaster.noDataValue != existingRaster.noDataValue:
      newRaster.r[newNoDataMask] = existingRaster.noDataValue
    if existingIsEmpty:
      # copy the initial distance raster
      existingRaster.r = newRaster.r
    else:
      # take the element-wise minimum, and take the union of the nodata masks
      existingRaster.r = np.minimum(existingRaster.r, newRaster.r)
      existingRaster.r[existingNoDataMask] = existingRaster.noDataValue
      existingRaster.r[newNoDataMask] = existingRaster.noDataValue

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r""
    mapDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcInfraDisturbanceMSA()

    ext = GLOB.extent_NL
    infra = os.path.join(mapDir,"GRIP4_5types_10sec.tif")
    dist = os.path.join(mapDir,"GRIP4_distance_km_10sec.tif")
    maxdist = 150
    lu = os.path.join(mapDir,"ESACCI_LC_1992_v207.tif")
    lookup = os.path.join(lookupDir,"LanduseNDepFactor_Globio4.csv")
    wbvertRegressionCoeffs = "1.06|0.36"
    wf = 0.33333333
    msa = os.path.join(outDir,"InfraDisturbanceMSA.tif")

    if RU.rasterExists(msa):
      RU.rasterDelete(msa)

    pCalc.run(ext,dist,infra,maxdist,lu,lookup,wbvertRegressionCoeffs,wf,msa)

  except:
    Log.err()
