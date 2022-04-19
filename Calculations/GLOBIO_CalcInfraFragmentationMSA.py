# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 26 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - Comment modified. 
#           - createCellAreaColumn removed, now using from CellArea module. 
#           - createCellAreaRaster removed, now using from CellArea module. 
#           9 aug 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - Now using uniform names for temporary files.
#           30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
#-------------------------------------------------------------------------------

import os
import numpy as np
import scipy.ndimage

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.CellArea as CellArea
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcInfraFragmentationMSA(CalculationBase):
  """
  Calculates a raster with the MSA of fragmentation by infrastructure.
  """
  
  #-------------------------------------------------------------------------------
  def getFilterFootprint(self):
    fp = np.array([[1,1,1],
                   [1,1,1],
                   [1,1,1]])
    return fp
    
  #-------------------------------------------------------------------------------
  def getFilterPatterns(self):
    p1 = np.array([[0,0,1],
                   [0,0,1],
                   [1,1,0]]).flatten()
    p2 = np.array([[1,1,0],
                   [0,0,1],
                   [0,0,1]]).flatten()
    p3 = np.array([[0,1,1],
                   [1,0,0],
                   [1,0,0]]).flatten()
    p4 = np.array([[1,0,0],
                   [1,0,0],
                   [0,1,1]]).flatten()
    return (p1,p2,p3,p4)

  #-------------------------------------------------------------------------------
  # Find natural regions.
  def createRegions(self,roadsRas,natRas,closeRoadConnections):

    if closeRoadConnections:
      # Shifting down roads to close diagonal connections.      
      Log.info("- Closing road connections...")
      # Roll all rows 1 row down.
      roadsSRas = np.roll(roadsRas,roadsRas.shape[1])
      # Blank out first row to 0.
      roadsSRas[:1] = 0
      # Add original roads.
      roadsSRas[(roadsRas==1)] = 1
    else:
      roadsSRas = roadsRas
      
    # Free roads.
    roadsRas = None
  
    # Blank out natural landuse on road locations.
    Log.info("- Removing natural landuse on roads locations...")
    natRas[roadsSRas > 0] = 0
 
    # Free shifted roads.
    roadsSRas = None
    
    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_infrafragmentation_nat_noroads.tif"
      Log.info("- Writing natural landuse: "+tmpName)
      self.writeTmpRaster(natRas,tmpName)
    
    # Find natural landuse regions with diagonal connections.
    Log.info("- Finding natural landuse regions...")
    struc = np.array([[1,1,1],
                      [1,1,1],
                      [1,1,1]])
    natRegionsRas,nrRegions = scipy.ndimage.label(natRas,structure=struc)

    # Show found number of regions.
    Log.info("- Number of regions found: %s" % nrRegions)

    # Free natural landuse.
    natRas = None

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_infrafragmentation_nat_regions.tif"
      Log.info("- Writing natural regions: "+tmpName)
      self.writeTmpRaster(natRegionsRas,tmpName)

    # Return natural landuse regions/patches and number of regions.
    return (natRegionsRas,nrRegions)
     
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN FILE WaterLookupFile
    IN RASTER Roads
    IN RASTER NaturalLanduse
    IN STRING INFRAG_WbVertRegressionCoefficients
    IN FLOAT INFRAG_WeightFactor
    IN BOOLEAN CloseRoadConnections
    OUT RASTER InfraFragmentationMSA
    """

    self.showStartMsg(args)
     
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
     
    # Get arguments.
    extent = args[0]
    landuseRasterName = args[1]
    lookupFileName = args[2]
    roadsRasterName = args[3]
    naturalLanduseRasterName = args[4]
    wbvertRegressionCoeffsStr = args[5]
    weightFactor = args[6]
    closeRoadConnections = args[7]
    outRasterName = args[8]
   
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(landuseRasterName)
    self.checkLookup(lookupFileName)
    self.checkRaster(roadsRasterName)
    self.checkRaster(naturalLanduseRasterName)
    self.checkFloatList(wbvertRegressionCoeffsStr,needCnt=2)
    self.checkFloat(weightFactor,0.0,1.0)
    self.checkBoolean(closeRoadConnections)
    self.checkRaster(outRasterName,True)
 
    # Convert code and names to arrays.
    wbvertRegressionCoeffs = self.splitFloatList(wbvertRegressionCoeffsStr)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [roadsRasterName,naturalLanduseRasterName]
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
      
    #-----------------------------------------------------------------------------
    # Set datatype.
    #-----------------------------------------------------------------------------

    #if cellSize==GLOB.constants["10sec"].value:
    if cellSize==GLOB.cellSize_10sec:
      Log.info("# Using float16 datatypes!!!")
      # Reduce precision for more memory.
      dataType = np.float16
    else:
      dataType = np.float32
      
    #-----------------------------------------------------------------------------
    # Read the roads raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    roadsRaster = self.readAndPrepareInRaster(extent,cellSize,roadsRasterName,"roads")
    
    # Select roadtype > 3, update with 0.
    Log.info("Removing unused roadtypes...")
    roadsRaster.r[(roadsRaster.r > 3)] = 0

    # Set references to the raster.
    roadsRas = roadsRaster.r
 
    # Close and free the roads raster.
    roadsRaster.close()
    roadsRaster = None

    #-----------------------------------------------------------------------------
    # Read the natural landuse and prepare.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    naturalLanduseRaster = self.readAndPrepareInRaster(extent,cellSize,naturalLanduseRasterName,"natural landuse")

    # Replace nodata with 0.
    Log.info("Replacing natural landuse nodata...")
    naturalLanduseRaster.r[(naturalLanduseRaster.r == naturalLanduseRaster.noDataValue)] = 0

    # Set references to the raster.
    natRas = naturalLanduseRaster.r
 
    # Close and free the natural landuse raster.
    naturalLanduseRaster.close()
    naturalLanduseRaster = None
    
    #-----------------------------------------------------------------------------
    # Find natural regions.
    #-----------------------------------------------------------------------------
 
    Log.info("Finding natural regions...")
    natRegionsRas,nrRegions = self.createRegions(roadsRas,natRas,closeRoadConnections)
  
    # Free roads.
    roadsRas = None
  
    #-------------------------------------------------------------------------------
    # Calculate CellArea in km2.
    #-------------------------------------------------------------------------------

    # Create column with cellarea in km2.
    Log.info("Creating cell area in km2...")
    areaRas = CellArea.createCellAreaColumn(extent,cellSize,dataType)

#     # For checking.    
#     # Create raster with cellarea in km2.
#     Log.info("Creating cell area in km2...")
#     areaRas = CellArea.createCellAreaRaster(extent,cellSize)
#     # Save temp raster?
#     if GLOB.saveTmpData:
#       tmpName = "tmp_infrafragmentation_cellarea_km.tif"
#       Log.info("- Writing cell area raster: "+tmpName)
#       self.writeTmpRaster(areaRas,tmpName) 

    # Calculate natural landuse cell area in km2 (by broadcasting).
    Log.info("Calculating natural landuse area in km2...")
    natAreaRas = np.zeros_like(natRegionsRas,dtype=dataType) 
    natAreaRas[natRegionsRas>0] = 1.0
    natAreaRas *= areaRas

    # Free cellarea raster.
    areaRas = None

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_infrafragmentation_nat_area.tif"
      Log.info("- Writing natural landuse cell area raster: "+tmpName)
      self.writeTmpRaster(natAreaRas,tmpName)
 
    # Calculate natural landuse cell area in km2.
    Log.info("Summarizing area of landuse regions...")
    regionIds = np.arange(0,nrRegions+1)
    regionAreaRas = scipy.ndimage.labeled_comprehension(natAreaRas,natRegionsRas,regionIds,np.sum,dataType,0)

    # Replace region ids by region areas.
    Log.info("Updating landuse regions...")
    natRegionAreaIds = np.empty(nrRegions+1,dtype=dataType)
    natRegionAreaIds[regionIds] = regionAreaRas
    natRegionAreaSumRas = natRegionAreaIds[natRegionsRas.flatten()].reshape(natRegionsRas.shape)

    # Free rasters and lists.
    natRegionsRas = None
    regionAreaRas = None
    natRegionAreaIds = None

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_infrafragmentation_region_areasum.tif"
      Log.info("- Writing natural landuse region area sum raster: "+tmpName)
      self.writeTmpRaster(natRegionAreaSumRas,tmpName)

    # Create the region area sum raster.
    noDataValue = -999.0
    regionAreaSumRaster = Raster()
    regionAreaSumRaster.initRasterEmpty(extent,cellSize,np.float32,noDataValue)
    regionAreaSumRaster.r = natRegionAreaSumRas
    
    # Free raster.
    natRegionAreaSumRas = None
    
    #Create masks
    noDataValue = regionAreaSumRaster.noDataValue
    mask = (regionAreaSumRaster.r > 0.0) & (regionAreaSumRaster.r != noDataValue)
      
    #-----------------------------------------------------------------------------
    # Calculate warm-blooded vertebrate MSA.
    #-----------------------------------------------------------------------------

    Log.info("Calculating warm-blooded vert. MSA...")

    outWbVertMSARaster = Raster()
    outWbVertMSARaster.initRaster(extent,cellSize,np.float32,noDataValue)
    
    # Set regression coefficients.
    b0 = wbvertRegressionCoeffs[0]
    b1 = wbvertRegressionCoeffs[1]
    
    #Original regression using ha so last term (2 * b1) is needed to convert the relationship
    #to km2
    outWbVertMSARaster.r[mask] = 1/(1+np.exp(-b0 - b1 * np.log10(regionAreaSumRaster.r[mask]) - 2 * b1))
   
    # Set cells to 1 where there is no natural area.
    outWbVertMSARaster.r[outWbVertMSARaster.r == outWbVertMSARaster.noDataValue] = 1.0
       
    # Set all cells with values <0 to 0.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r < 0.0)
    outWbVertMSARaster.r[mask] = 0.0

    # Set all cells with values >1 to 1.0.
    mask = (outWbVertMSARaster.r != noDataValue) & (outWbVertMSARaster.r > 1.0)
    outWbVertMSARaster.r[mask] = 1.0
    
    # Cleanup mask.
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
    regionAreaSumRaster.r[mask] = noDataValue
    mask = None
    
    # Close and free the landuse raster.
    landuseRaster.close()
    landuseRaster = None
    
    # Write, close and free the region area sum raster.
    Log.info("Writing input raster....")
    regionAreaSumRaster.writeAs(outRasterName.replace(".tif","_finalinput.tif"))
    regionAreaSumRaster.close()
    regionAreaSumRaster = None
    
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
    Log.info("Creating the final fragmentation MSA raster...")
    
    # Assign warm-blooded vert. MSA to outRaster (as a referrence).
    outRaster = outWbVertMSARaster
    mask = (outRaster.r != noDataValue)

    complWeightFactor = 1.0 - weightFactor
    outRaster.r[mask] *= weightFactor
    outRaster.r[mask] += complWeightFactor
    
    # Clear mask.
    mask = None

    #-----------------------------------------------------------------------------
    # Save output raster.
    #-----------------------------------------------------------------------------
      
    # Save the output raster.
    #Log.info("Writing fragmentation by infrastructure MSA...")
    #outRaster.writeAs(outRasterName)
           
    # Close and free the output raster.
    outWbVertMSARaster.close()
    outWbVertMSARaster = None
    outRaster.close()
    outRaster = None
 
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

    pCalc = GLOBIO_CalcInfraFragmentationMSA()
 
    ext = GLOB.extent_World
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    lut = os.path.join(lookupDir,"WaterAreasFilter.csv")
    roads = os.path.join(mapDir,"GRIP4_5types_10sec.tif")
    nlu = os.path.join(inDir,"NaturalLanduse_test.tif")
    coef = "0.38|0.13"
    wf = 1.0/3.0
    crc = False
    msa = os.path.join(outDir,"InfraFragmentationMSA.tif")

    if RU.rasterExists(msa):
      RU.rasterDelete(msa)

    pCalc.run(ext,lu,lut,roads,nlu,coef,wf,crc,msa)

  except:
    Log.err()
