# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
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
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - calcDistance modified, delete removed.
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

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcSettlementDistance(CalculationBase):
  """
  Calculates a raster with the distances (km) to the nearest settlements.
  """
  
  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()    
    super(GLOBIO_CalcSettlementDistance,self).__init__()

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
  # Collect all shapefile names in the directory and subdirectries.
  def getSettlementShapeFileNames(self,inDir):
    shapeFileNames = []
    for (dirPath, _, fileNames) in os.walk(inDir):
      for fileName in fileNames:
        if UT.hasFileNameExtension(fileName,".shp"):
          fileName = os.path.join(dirPath,fileName)
          shapeFileNames.append(fileName)
    return shapeFileNames

  #-------------------------------------------------------------------------------
  def calcDistance(self,extent,cellSize,
                   settlementsDir,travelTimeRasterName,
                   minTravelTimeMIN,maxTravelTimeMIN,
                   landcoverRasterName,landcoverCodesStr,landcoverBufferKM,
                   maxDistanceKM,
                   outDir):

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkDirectory(settlementsDir)
    self.checkRaster(travelTimeRasterName)
    self.checkInteger(minTravelTimeMIN,0,99999999)
    self.checkInteger(maxTravelTimeMIN,0,99999999)
    self.checkRaster(landcoverRasterName)
    self.checkIntegerList(landcoverCodesStr)
    self.checkFloat(landcoverBufferKM,0,99999)
    self.checkFloat(maxDistanceKM,0,99999)

    # Convert code and names to arrays.
    landcoverCodes = self.splitIntegerList(landcoverCodesStr)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = outDir

    # Set temporary vector/raster names.
    tmpSettlementsShapeFileName = os.path.join(self.outDir,"tmp_settlements.shp")
    tmpSettlementsRasterName = os.path.join(self.outDir,"tmp_settlements.tif")
    tmpSelSettlementsRasterName = os.path.join(self.outDir,"tmp_settlements_sel.tif")
    tmpLandcoverSelRasterName = os.path.join(self.outDir,"tmp_landcover_sel.tif")
    tmpLandcoverBufRasterName = os.path.join(self.outDir,"tmp_landcover_buf.tif")
    tmpDistanceRasterName = os.path.join(self.outDir,"tmp_humenc_distance.tif")

    # Remove temporary data.
    if RU.vectorExists(tmpSettlementsShapeFileName):
      RU.vectorDelete(tmpSettlementsShapeFileName)
    if RU.rasterExists(tmpSettlementsRasterName):
      RU.rasterDelete(tmpSettlementsRasterName)
    if RU.rasterExists(tmpSelSettlementsRasterName):
      RU.rasterDelete(tmpSelSettlementsRasterName)
    if RU.rasterExists(tmpLandcoverSelRasterName):
      RU.rasterDelete(tmpLandcoverSelRasterName)
    if RU.rasterExists(tmpLandcoverBufRasterName):
      RU.rasterDelete(tmpLandcoverBufRasterName)
    if RU.rasterExists(tmpDistanceRasterName):
      RU.rasterDelete(tmpDistanceRasterName)

    #-----------------------------------------------------------------------------
    # Read and merge settlement shapefiles.
    #-----------------------------------------------------------------------------
    
    Log.info("Getting settlement shapefiles...")
    
    # Get all shapefile names in the directory and subdirectries.
    shapeFileNames = self.getSettlementShapeFileNames(settlementsDir)

    Log.info("- %s shapefiles found." % len(shapeFileNames))

    Log.info("Merging settlement shapefiles...")

    # Create temporary settlement shapefile with all settlement points.
    outPointVector = Vector()
    outPointVector.create(tmpSettlementsShapeFileName,ogr.wkbPoint)

    # Create extent geometry for testing invalid points.
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(extent[0],extent[1])
    ring.AddPoint(extent[0],extent[3])
    ring.AddPoint(extent[2],extent[3])
    ring.AddPoint(extent[2],extent[1])
    ring.AddPoint(extent[0],extent[1])
    extentGeom = ogr.Geometry(ogr.wkbPolygon)
    extentGeom.AddGeometry(ring)
    
    # Read all settlement shapefiles.
    for shapeFileName in shapeFileNames:
  
      Log.info("- Processing %s..." % shapeFileName)
      
      # Read shapefile.
      inPointVector = Vector(shapeFileName)
      inPointVector.read()
      
      # Get geometry type.
      geomType = inPointVector.getGeometryType()
      
      # No point vector?
      if (geomType != ogr.wkbPoint) and \
         (geomType != ogr.wkbMultiPoint) and \
         (geomType != ogr.wkbPoint25D):
        Log.info("  - Skipping (type %s,%s)..." % (RU.geometryTypeToStr(geomType),geomType))
        # Cleanup.
        inPointVector.close()
        inPointVector = None
        continue
      
      # Point or MultiPoint geometry?
      if (geomType == ogr.wkbPoint):
        # Loop points.
        for pntFeat in inPointVector.layer:
          inGeom = pntFeat.GetGeometryRef()
          # Invalid point?
          if not extentGeom.Intersects(inGeom):
            #print "Skipping geometry..."
            continue
          outPointVector.addPointGeometry(inGeom)
      else:
        # Loop multi points.
        for pntFeat in inPointVector.layer:
          inGeom = pntFeat.GetGeometryRef()
          for i in range(inGeom.GetGeometryCount()):
            inGeom2 = inGeom.GetGeometryRef(i)
            # Invalid point?
            if not extentGeom.Intersects(inGeom):
              #print "Skipping geometry..."
              continue
            outPointVector.addPointGeometry(inGeom2)
        
      # Cleanup input point vector.
      inPointVector.close()
      inPointVector = None

      # Use 1 shapefile?
      if self.test:
        break
     
    # Get number of points found.
    featureCnt = len(outPointVector.layer)
    if featureCnt > 0:
      Log.info("- %s settlements found." % featureCnt)

    # Write and cleanup output point vector.
    outPointVector.close()
    outPointVector = None
  
    # No settlements found?
    if featureCnt == 0:
      Err.raiseGlobioError(Err.NoSettlementsFound)

    #-----------------------------------------------------------------------------
    # Convert settlement shapefile to raster.
    #-----------------------------------------------------------------------------

    Log.info("Converting settlements to raster...")
     
    # Convert settlement points to raster.
    gr = Grass()
    gr.init()
    gr.vectorToRaster(extent,cellSize,
                      tmpSettlementsShapeFileName,tmpSettlementsRasterName,
                      "point",np.uint8,None,1)
    gr = None

    #-----------------------------------------------------------------------------
    # Read settlements raster. 
    #-----------------------------------------------------------------------------

    # Read the settlements raster.
    settlementsRaster = Raster(tmpSettlementsRasterName)
    settlementsRaster.read()
 
    #-----------------------------------------------------------------------------
    # Remove settlements nearby and far away using travel time.
    #-----------------------------------------------------------------------------

    # Reads the travel time raster and resizes to extent and resamples to cellsize.
    travelTimeRaster = self.readAndPrepareInRaster(extent,cellSize,travelTimeRasterName,"travel time")

    Log.info("Removing settlements nearby and far away from populated areas...")
     
    # Select proper travel time.
    mask = ((travelTimeRaster.r <= minTravelTimeMIN) | (travelTimeRaster.r > maxTravelTimeMIN))

    # Set to nodata.
    noDataValue = settlementsRaster.noDataValue
    settlementsRaster.r[mask] = noDataValue

    # Cleanup mask.
    mask = None
    
    # Close and free the WWF reclass raster.
    travelTimeRaster.close()
    travelTimeRaster = None

    #-----------------------------------------------------------------------------
    # Select (urban) areas from landcover.
    #-----------------------------------------------------------------------------

    # Reads the landcover raster and resizes to extent and resamples to cellsize.
    landcoverRaster = self.readAndPrepareInRaster(extent,cellSize,landcoverRasterName,"landcover")

    Log.info("Selecting landcover types...")

    # Create empty raster.
    landcoverSelRaster = Raster()
    landcoverSelRaster.initRasterLike(landcoverRaster)
    
    # Select specified landcover types (selected = 1).
    for landcoverCode in landcoverCodes:
      mask = ((landcoverSelRaster.r == landcoverSelRaster.noDataValue) & (landcoverRaster.r == landcoverCode))
      landcoverSelRaster.r[mask] = 1

    # Save landcover selection.
    landcoverSelRaster.writeAs(tmpLandcoverSelRasterName)

    # Cleanup mask.
    mask = None

    # Close and free the rasters.
    landcoverRaster.close()
    landcoverRaster = None
    landcoverSelRaster.close()
    landcoverSelRaster = None
    
    #-----------------------------------------------------------------------------
    # Remove settlements within 1 km from a urban cell (190).
    #-----------------------------------------------------------------------------
    
    Log.info("Buffering selected landcover areas...")
    
    # Buffer landcover areas.
    gr = Grass()
    gr.init()
    gr.buffer(extent,cellSize,tmpLandcoverSelRasterName,tmpLandcoverBufRasterName,
              landcoverBufferKM,"kilometers")
    gr = None

    Log.info("Removing settlements nearby selected landcover areas...")

    # Read buffered landcover raster.
    landcoverBufRaster = Raster(tmpLandcoverBufRasterName)
    landcoverBufRaster.read()

    # Select all settlements inside the buffer.
    mask = landcoverBufRaster.getDataMask()

    # And set to nodata.
    noDataValue = settlementsRaster.noDataValue
    settlementsRaster.r[mask] = noDataValue

    # Cleanup mask.
    mask = None

    # Close and free the raster.
    landcoverBufRaster.close()
    landcoverBufRaster = None

    #-----------------------------------------------------------------------------
    # Save the settlements. 
    #-----------------------------------------------------------------------------

    Log.info("Saving settlements...")

    # Save settlements selection.
    settlementsRaster.writeAs(tmpSelSettlementsRasterName)

    # Close and free the raster.
    settlementsRaster.close()
    settlementsRaster = None

    #-----------------------------------------------------------------------------
    # Calculate nearest distance to settlements. 
    #-----------------------------------------------------------------------------
   
    Log.info("Calculating nearest distance to settlements...")
    
    # Calculate nearest distance to settlements. 
    gr = Grass()
    gr.init()
    gr.distance_V1(extent,cellSize,tmpSelSettlementsRasterName,tmpDistanceRasterName)
    gr = None
      
    # Read distance raster.
    distanceRaster = Raster(tmpDistanceRasterName)
    distanceRaster.read()

    # Limit distance to maximum value.
    maxDistanceM = maxDistanceKM * 1000.0
    mask = (distanceRaster.r >= maxDistanceM)
    distanceRaster.r[mask] = maxDistanceM
    
    # Cleanup mask.
    mask = None

    # Select valid distance values.
    distMask = (distanceRaster.r > 0.0)

    # Convert distance meters to kilometers.
    distanceRaster.r[distMask] /= 1000.0

    # Cleanup temporary files.
    if not GLOB.saveTmpData:
      if RU.vectorExists(tmpSettlementsShapeFileName):
        RU.vectorDelete(tmpSettlementsShapeFileName)
      if RU.rasterExists(tmpSettlementsRasterName):
        RU.rasterDelete(tmpSettlementsRasterName)
      if RU.rasterExists(tmpSelSettlementsRasterName):
        RU.rasterDelete(tmpSelSettlementsRasterName)
      if RU.rasterExists(tmpLandcoverSelRasterName):
        RU.rasterDelete(tmpLandcoverSelRasterName)
      if RU.rasterExists(tmpLandcoverBufRasterName):
        RU.rasterDelete(tmpLandcoverBufRasterName)
      # 20201202
      # if RU.rasterExists(tmpDistanceRasterName):
      #   RU.rasterDelete(tmpDistanceRasterName)

    return distanceRaster
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN DIR SettlementsDir
    IN RASTER TravelTime
    IN INTEGER MinimumTravelTimeMIN
    IN INTEGER MaximumTravelTimeMIN
    IN RASTER Landcover
    IN STRING LandcoverCodes
    IN FLOAT LandcoverBufferDistanceKM
    IN FLOAT MaximumDistanceKM
    OUT RASTER SettlementDistance
    """
    
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=9:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    settlementsDir = args[1]
    travelTimeRasterName = args[2]
    minTravelTimeMIN = args[3]
    maxTravelTimeMIN = args[4]
    landcoverRasterName = args[5]
    landcoverCodesStr= args[6]
    landcoverBufferKM = args[7]
    maxDistanceKM = args[8]
    outRasterName = args[9]

    # Check arguments.
    self.checkExtent(extent)
    self.checkDirectory(settlementsDir)
    self.checkRaster(travelTimeRasterName)
    self.checkInteger(minTravelTimeMIN,0,99999999)
    self.checkInteger(maxTravelTimeMIN,0,99999999)
    self.checkRaster(landcoverRasterName)
    self.checkIntegerList(landcoverCodesStr)
    self.checkFloat(landcoverBufferKM,0,99999)
    self.checkFloat(maxDistanceKM,0,99999)
    self.checkRaster(outRasterName,asOutput=True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [travelTimeRasterName,landcoverRasterName]
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

    #-----------------------------------------------------------------------------
    # Calculate the distances (km) to the nearest settlements.
    #-----------------------------------------------------------------------------
    distanceRaster = self.calcDistance(extent,cellSize,
                          settlementsDir,travelTimeRasterName,
                          minTravelTimeMIN,maxTravelTimeMIN,
                          landcoverRasterName,landcoverCodesStr,landcoverBufferKM,
                          maxDistanceKM,self.outDir)

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------

    Log.info("Writing %s..." % outRasterName)

    # Save final MSA.
    distanceRaster.writeAs(outRasterName)

    # Close and free the output raster.
    distanceRaster.close()
    distanceRaster = None

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
    outRasterName = "SettlementDistanceKM.tif"

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
    
    self.run(extent,inSettlementsDir,
             travelTimeRasterName,minTravelTimeMin,maxTravelTimeMin,
             landcoverRasterName,landcoverCodes,landcoverBufferKM,
             maxDistanceKM,
             outRasterName)
      
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  try:
    pCalc = GLOBIO_CalcSettlementDistance()
    pCalc.doTest()
  except:
    Log.err()
