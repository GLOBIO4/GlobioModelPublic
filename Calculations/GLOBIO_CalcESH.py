# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# Script to calculate the extent of suitable habitat per species
#
# Required input:   - Land use map
#                   - List of species with dispersal + density estimates + habitat and altitude preferences
#                   - Species range maps (shapefile)
#                   - Matrix to transform habitat preferences to land use map
#
# Output:           - Extent of suitable habitat at resolution of land use maps
#                   - AOO at 2x2 km as required for Red List assessment
#                   - Patch sizes at resolution of environmental variables
#
# Modified: 29 jul 2019, JH, PBL
#
#-------------------------------------------------------------------------------

import os
import numpy as np
import pandas as pd 
import scipy.ndimage
import glob

import osgeo.ogr as ogr
from osgeo import gdal

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Grass_adj import Grass
from GlobioModel.Core.Raster import Raster
from GlobioModel.Core.Vector import Vector

import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcESH(CalculationBase):
  """
  Calculates a file with the extent of suitable habitat for species.
  """

  nrCols = 0
  nrRows = 0
  debug = False

  #-------------------------------------------------------------------------------
  # Calculates the AOO at a 2 km resolution required by IUCN
  def calcSpeciesAOO(self,species,inRasterName,outRasterName):

      Log.info("Reprojecting and resizing...")

      inRaster = gdal.Open(inRasterName)
      # 20201130
      # outRaster = gdal.Warp(outRasterName,inRaster,dstNodata = 0,
      #                       dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs',
      #                       xRes=2000,yRes=2000,resampleAlg = gdal.GRA_Average,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
      gdal.Warp(outRasterName,inRaster,dstNodata = 0,
                dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs',
                xRes=2000,yRes=2000,resampleAlg = gdal.GRA_Average,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
      
      #outRaster = gdal.Warp(outRasterName,inRaster,cutlineDSName=clipShapefileName,cropToCutline=True,dstNodata = 0,
      #                      dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs',
      #                      xRes=2000,yRes=2000,resampleAlg = gdal.GRA_Average,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
      
      Log.info("Calculating AOO...")

      # Read buffered ESH raster.
      SpeciesRaster = Raster(outRasterName)
      SpeciesRaster.read()

      AOOmask = (SpeciesRaster.r > 0)
      notAOOmask = np.invert(AOOmask)
      SpeciesRaster.r[AOOmask] = 1  
      SpeciesRaster.r[notAOOmask] = 0      

      #Calculate AOO using number of cells x resolution
      AOOSum = np.sum(SpeciesRaster.r) * 4
      print(AOOSum)
      speciesAOO = [species,AOOSum]

      # Free rasters,masks,areas and lines.
      inRaster = None
      #outRaster = None
      SpeciesRaster.close()
      SpeciesRaster = None
      AOOmask = None
      notAOOmask = None
      AOOSum = None

      return speciesAOO

#-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN FILE SpeciesData
    IN FILE TransformationMatrix
    IN FILE ElevationData
    IN FILE HabitatData    
    IN DIR RangesDir
    IN STRING SpeciesIDs
    IN STRING SuitabilityStr
    IN STRING PresenceCodes
    IN STRING OriginCodes
    IN STRING SeasonalityCodes
    IN BOOLEAN addMCPflag 
    IN RASTER LandUse
    IN RASTER AreaRaster
    IN RASTER ElevationRaster
    OUT FILE OutESHFileName
    OUT FILE OutAOOFileName
    OUT FILE OutESHPatchesFileName
    IN INTEGER BatchNumber  
    """
    
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=18:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    speciesdataFileName = args[1]
    transmatrixFileName = args[2]
    eledataFileName = args[3]
    habitatFileName = args[4]
    rangesDir = args[5]
    speciesIDsStr= args[6]
    suitabilityStr= args[7]
    presenceCodesStr= args[8]
    originCodesStr= args[9]
    seasonalityCodesStr= args[10]
    addMCP = args[11]
    landuseRasterName = args[12]
    areaRasterName = args[13]
    eleRasterName = args[14]
    outESHsFileName = args[15]
    outAOOsFileName = args[16]
    outESHsPatchesFileName = args[17]
    batchNumber = args[18]

    # Check arguments.
    self.checkExtent(extent)
    self.checkFile(speciesdataFileName)
    self.checkFile(transmatrixFileName)
    self.checkFile(eledataFileName)
    self.checkFile(habitatFileName)
    self.checkDirectory(rangesDir)
    self.checkIntegerList(speciesIDsStr)
#    self.checkListCount(suitabilityStr,suitabilityCodesStr,"suitabilities")     
    self.checkIntegerList(presenceCodesStr)
    self.checkIntegerList(originCodesStr)    
    self.checkIntegerList(seasonalityCodesStr)
    self.checkBoolean(addMCP)    
    self.checkRaster(landuseRasterName)
    self.checkRaster(areaRasterName)
    self.checkRaster(eleRasterName)
    self.checkFile(outESHsFileName,asOutput=True)
    self.checkFile(outAOOsFileName,asOutput=True)
    self.checkFile(outESHsPatchesFileName,asOutput=True)
    self.checkInteger(batchNumber,0,99999999)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [landuseRasterName,areaRasterName,eleRasterName]
    cellSize = self.getMinimalCellSize(inRasterNames)
    Log.info("Using cellsize: %s" % cellSize)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)
    
    # Convert code and names to arrays.
    speciesIDs = self.splitIntegerList(speciesIDsStr)
    suitabilityCodes = self.splitStringList(suitabilityStr)
    presenceCodes = self.splitIntegerList(presenceCodesStr)
    originCodes = self.splitIntegerList(originCodesStr)
    seasonalityCodes = self.splitIntegerList(seasonalityCodesStr)
    
    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.nrCols,self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    self.outDir = os.path.dirname(os.path.dirname(outESHsFileName))

    # Set temporary vector/raster names.
    tmpRangesShapeFileName = os.path.join(self.outDir,("tmp_range_"+str(batchNumber)+".shp"))
    tmpEOOShapeFileName = os.path.join(self.outDir,("tmp_EOO_"+str(batchNumber)+".shp"))
    #tmpExtentEOOShapeFileName = os.path.join(self.outDir,("tmp_Extent_EOO_"+str(batchNumber)+".shp"))
    tmpSpeciesRasterName = os.path.join(self.outDir,("tmp_species_"+str(batchNumber)+".tif"))
    tmpSpeciesESHRasterName = os.path.join(self.outDir,("tmp_ESH_species_"+str(batchNumber)+".tif"))
    tmpSpeciesAOORasterName = os.path.join(self.outDir,("tmp_AOO_species_"+str(batchNumber)+".tif"))
    tmpSpeciesESHBufRasterName = os.path.join(self.outDir,("tmp_ESH_species_buf_"+str(batchNumber)+".tif"))
    tmpSpeciesBufClumpRasterName = os.path.join(self.outDir,("tmp_ESH_species_buf_clump_"+str(batchNumber)+".tif"))
    tmpSpeciesESHClumpRasterName = os.path.join(self.outDir,("tmp_ESH_species_clump_"+str(batchNumber)+".tif"))
    tmpSpeciesESHPatchesRasterName = os.path.join(self.outDir,("tmp_ESH_species_patches_"+str(batchNumber)+".tif"))

    tmpSpeciesAreaRasterName = os.path.join(self.outDir,("tmp_species_area_"+str(batchNumber)+".tif"))
    tmpSpeciesLURasterName = os.path.join(self.outDir,("tmp_species_lu_"+str(batchNumber)+".tif"))
    tmpSpeciesEleRasterName = os.path.join(self.outDir,("tmp_species_ele_"+str(batchNumber)+".tif"))

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the dispersal + density data of the species.
    #-----------------------------------------------------------------------------

    speciesMatrix = pd.read_csv(speciesdataFileName,dtype={'species_id':int,'dispersal':float,'density':float})
    
    #-----------------------------------------------------------------------------
    # Read the elevation data of the species.
    #-----------------------------------------------------------------------------

    eleMatrix = pd.read_csv(eledataFileName,dtype={'taxid':int,'elevation_lower':float,'elevation_upper':float})
    
    #-----------------------------------------------------------------------------
    # Read the transformation matrix.
    #-----------------------------------------------------------------------------

    transMatrix = pd.read_csv(transmatrixFileName,dtype={'iucn_code':object})

    #-----------------------------------------------------------------------------
    # Read the habitat file.
    #-----------------------------------------------------------------------------

    Log.info("Getting habitat files...")
    habMatrix = pd.read_csv(habitatFileName,dtype={'code':object,'suitability':object,'season':object,'majorimportance':object,'species_id':int})
    
    # Get all species filenames in the directory and subdirectries.
    # habitatFileNames = []
    # for (dirPath, _, fileNames) in os.walk(habitatDir):
    #   for fileName in fileNames:
    #     #if UT.hasFileNameExtension(fileName,".csv"):
    #       fileName = os.path.join(dirPath,fileName)
    #       habitatFileNames.append(fileName)
    #       # Subset the list for only those files with a species ID number
    #       habitatFileNames = [x for x in habitatFileNames if re.search("\d", x)]    

    # Need to filter species?
    # if self.isValueSet(speciesIDs):
    #   Log.info("Filtering species...")
    #   habitatFileNamesIDs=[]
    #   for habitatFileName in habitatFileNames:
    #     habitatFileName = os.path.split(habitatFileName)[1]
    #     habitatFileNamesIDs+=([int(s) for s in re.findall(r'\d+', habitatFileName)])
    #   habitatFileNamesIDs = np.array(habitatFileNamesIDs)
    #   habitatFileNames_reduced = np.array(habitatFileNames)[np.nonzero(np.array(speciesIDs)[:, None] == habitatFileNamesIDs)[1]].tolist() 

    #-----------------------------------------------------------------------------
    # Read and merge settlement shapefiles.
    #-----------------------------------------------------------------------------
    
    #Log.info("Getting range maps...")
    
    # Get all shapefile names in the directory and subdirectries.
    #shapeFileNames = []
    #for (dirPath, _, fileNames) in os.walk(rangesDir):
    #  for fileName in fileNames:
    #    if UT.hasFileNameExtension(fileName,".shp"):
    #      fileName = os.path.join(dirPath,fileName)
    #      shapeFileNames.append(fileName)
    
    #Log.info("- %s shapefiles found." % len(shapeFileNames))

    # Need to filter species?
    #if self.isValueSet(speciesIDs):
    #  Log.info("Filtering species...")
    #  shapeFileNamesIDs=[]
    #  for shapeFileName in shapeFileNames:
    #    shapeFileName = os.path.split(shapeFileName)[1]
    #    shapeFileNamesIDs+=([int(s) for s in re.findall(r'\d+', shapeFileName)])
    #  shapeFileNamesIDs = np.array(shapeFileNamesIDs)
    #  shapeFileNames_reduced = np.array(shapeFileNames)[np.nonzero(np.array(speciesIDs)[:, None] == shapeFileNamesIDs)[1]].tolist() 

    #Log.info("- %s shapefiles used." % len(shapeFileNames_reduced))
    
    for species in speciesIDs:
    
      # Remove temporary data.
      if RU.vectorExists(tmpRangesShapeFileName):
        RU.vectorDelete(tmpRangesShapeFileName)
      if RU.vectorExists(tmpEOOShapeFileName):
        RU.vectorDelete(tmpEOOShapeFileName)
      #if RU.vectorExists(tmpExtentEOOShapeFileName):
      #  RU.vectorDelete(tmpExtentEOOShapeFileName)
      if RU.rasterExists(tmpSpeciesRasterName):
        RU.rasterDelete(tmpSpeciesRasterName)
      if RU.rasterExists(tmpSpeciesESHRasterName):
        RU.rasterDelete(tmpSpeciesESHRasterName)
      if RU.rasterExists(tmpSpeciesAOORasterName):
        RU.rasterDelete(tmpSpeciesAOORasterName)   
      if RU.rasterExists(tmpSpeciesESHBufRasterName):
        RU.rasterDelete(tmpSpeciesESHBufRasterName)
      if RU.rasterExists(tmpSpeciesBufClumpRasterName):
        RU.rasterDelete(tmpSpeciesBufClumpRasterName)
      if RU.rasterExists(tmpSpeciesESHClumpRasterName):
        RU.rasterDelete(tmpSpeciesESHClumpRasterName)
      if RU.rasterExists(tmpSpeciesESHPatchesRasterName):
        RU.rasterDelete(tmpSpeciesESHPatchesRasterName)    
      if RU.rasterExists(tmpSpeciesAreaRasterName):
        RU.rasterDelete(tmpSpeciesAreaRasterName)
      if RU.rasterExists(tmpSpeciesLURasterName):
        RU.rasterDelete(tmpSpeciesLURasterName)
      if RU.rasterExists(tmpSpeciesEleRasterName):
        RU.rasterDelete(tmpSpeciesEleRasterName)
        
      Log.info("- Processing species with ID=%s..." % species)

      # If species output already exists go to the next species.
      if os.path.isfile(outESHsPatchesFileName.replace(".csv",("_"+str(species)+".csv"))):       
        Log.info("- Output exists for species with ID=%s..." % species)
        continue
      
      # Set output.
      linesESH = []
      linesESH.append("species;esh")
      linesAOO = []
      linesAOO.append("species;aoo")
      linesESH_patches = []
      linesESH_patches.append("species;patch;area;pop")
    
      # Obtain dispersal + density estimates
      speciesFile = speciesMatrix[speciesMatrix['species_id']==species]
      if speciesFile.empty:
        Log.info("- No dispersal + density data for species with ID=%s..." % species)
        continue
      if np.isnan(speciesFile.iloc[0]['dispersal']):
        Log.info("- No dispersal data for species with ID=%s..." % species)
        continue
      if np.isnan(speciesFile.iloc[0]['density']):
        Log.info("- No density data for species with ID=%s..." % species)
        continue
      speciesDisp = speciesFile.iloc[0]['dispersal']
      speciesDens = speciesFile.iloc[0]['density']
      
      # Obtain habitat preferences
      habitatFile = habMatrix[habMatrix['species_id']==species]
      if habitatFile.empty:
        Log.info("- No habitat data for species with ID=%s..." % species)
        continue
      
      # Obtain elevation preferences
      eleSpecies = eleMatrix[eleMatrix['taxid']==species]
      if eleSpecies.empty:
        Log.info("- No elevation data for species with ID=%s..." % species)
        continue

      #shapeFileName = np.array(shapeFileNames)[np.where(species == shapeFileNamesIDs)][0].tostring()
      Log.info("Getting range map...")
      shapeFileName = glob.glob(rangesDir+"\\"+'EO_'+str(species)+'.shp')

      # Read shapefile.
      if len(shapeFileName)==0:       
        Log.info("- No range maps for species with ID=%s..." % species)
        continue

      # Create temporary species shapefile with all selected ranges.
      outPolygonVector = Vector()
      outPolygonVector.create(tmpRangesShapeFileName,ogr.wkbPolygon)

      # Create extent geometry for testing invalid polygons.
      ring = ogr.Geometry(ogr.wkbLinearRing)
      ring.AddPoint(extent[0],extent[1])
      ring.AddPoint(extent[0],extent[3])
      ring.AddPoint(extent[2],extent[3])
      ring.AddPoint(extent[2],extent[1])
      ring.AddPoint(extent[0],extent[1])
      extentGeom = ogr.Geometry(ogr.wkbPolygon)
      extentGeom.AddGeometry(ring)
      
      # Read species shapefile
      inPolygonVector = Vector(shapeFileName[0])
      inPolygonVector.read()
      
      # Get geometry type.
      geomType = inPolygonVector.getGeometryType()

      # Get number of polygons found.
      featureCnt = len(inPolygonVector.layer)
      if featureCnt > 0:
        Log.info("- %s initial polygons found." % featureCnt)

      # Filter the user-defined presense codes
      inPolygonVector.layer.SetAttributeFilter('presence in (' + ','.join(map(str, presenceCodes)) + ') and origin in (' + ','.join(map(str, originCodes)) + ') and seasonal in (' + ','.join(map(str, seasonalityCodes)) + ')')
      featureCnt = len(inPolygonVector.layer)
      Log.info("- %s polygons left after presence + origin + seasonality filters." % featureCnt)

      # No polygons found?
      if featureCnt == 0:
        Log.info("No polygons found or left for %s..." % shapeFileName[0])
        continue    
      
      # Checking the geometries

      # No polygon vector?
      if (geomType != ogr.wkbPolygon) and \
         (geomType != ogr.wkbMultiPolygon) and \
         (geomType != ogr.wkbPolygon25D):
        Log.info("  - Skipping (type %s,%s)..." % (RU.geometryTypeToStr(geomType),geomType))
        # Cleanup.
        inPolygonVector.close()
        inPolygonVector = None
        continue

      # Polygon or MultiPolygon geometry?
      if (geomType == ogr.wkbPolygon):
        # Loop polygons.
        for plgFeat in inPolygonVector.layer:
          inGeom = plgFeat.GetGeometryRef()
          # Invalid polygon?
          if not extentGeom.Intersects(inGeom):
            #print "Skipping geometry..."
            continue
          outPolygonVector.addPointGeometry(inGeom)
      else:
        # Loop multi polygons.
        for plgFeat in inPolygonVector.layer:
          inGeom = plgFeat.GetGeometryRef()
          for i in range(inGeom.GetGeometryCount()):
            inGeom2 = inGeom.GetGeometryRef(i)
            # Invalid polygon?
            if not extentGeom.Intersects(inGeom):
              #print "Skipping geometry..."
              continue
            outPolygonVector.addPointGeometry(inGeom2)
      
      # No polygons found?
      featureCnt = len(outPolygonVector.layer)
      if featureCnt == 0:
        Log.info("No polygons found or left for %s..." % shapeFileName)
        continue
      if featureCnt > 0:
        Log.info("- %s polygons found." % featureCnt)

      # Need to create a convex hull polygon around the species ranges?
      if addMCP:
        Log.info("Create minimum convex polygon...")
        hullPolygonVector = Vector()
        hullPolygonVector.create(tmpEOOShapeFileName,ogr.wkbPolygon)

        # If breeding and non-breeding areas exist, only use the minimum of the convex hull around either areas
        seasonality_values = [feature.GetField("seasonal") for feature in inPolygonVector.layer]
        inPolygonVector.layer.ResetReading()
        if all(x in seasonality_values for x in [2,3]):
          
          inPolygonVector.layer.SetAttributeFilter("(seasonal != 2)")
          hullPolygon_3 = ogr.Geometry(ogr.wkbGeometryCollection)
          for feature in inPolygonVector.layer:
            hullPolygon_3.AddGeometry(feature.GetGeometryRef())
          convexhull_3 = hullPolygon_3.ConvexHull()
          area_3 = convexhull_3.GetArea()
          inPolygonVector.layer.ResetReading()

          inPolygonVector.layer.SetAttributeFilter("(seasonal != 3)")
          hullPolygon_2 = ogr.Geometry(ogr.wkbGeometryCollection)
          for feature in inPolygonVector.layer:
            hullPolygon_2.AddGeometry(feature.GetGeometryRef())
          convexhull_2 = hullPolygon_2.ConvexHull()
          area_2 = convexhull_2.GetArea()
          inPolygonVector.layer.ResetReading()
          
          if area_2 > area_3:
            convexhull = convexhull_3
          else:
            convexhull = convexhull_2

        # If not both breeding and non-breeding areas, take the convex hull around all polygons
        else:
          hullPolygon = ogr.Geometry(ogr.wkbGeometryCollection)
          for feature in outPolygonVector.layer:
              hullPolygon.AddGeometry(feature.GetGeometryRef())
          convexhull = hullPolygon.ConvexHull()

        hullPolygonVector.addPointGeometry(convexhull)
        hullPolygonVector.close()
        hullPolygonVector = None

      else:
        tmpEOOShapeFileName = tmpRangesShapeFileName
       
      # Cleanup input polygon vector.
      inPolygonVector.close()
      inPolygonVector = None
      
      # Write and cleanup output point vector.
      outPolygonVector.close()
      outPolygonVector = None
  
      #-----------------------------------------------------------------------------
      # Get extent of species shapefile.
      #-----------------------------------------------------------------------------

      inPolygonVectorShpF = Vector(tmpEOOShapeFileName)
      inPolygonVectorShpF.read()
      extentShapefile = inPolygonVectorShpF.layer.GetExtent()
      extentShapefile=(max((round(extentShapefile[0],0)-1),-180),
                       max((round(extentShapefile[2],0)-1),-90),
                       min((round(extentShapefile[1],0)+1),180),
                       min((round(extentShapefile[3],0)+1),90))  
      Log.info("Extent of the shapefile is %s..." % str(extentShapefile))
      inPolygonVectorShpF.close()
      inPolygonVectorShpF = None

      # Create polygon from the extent.
      #extentPolygonVector = Vector()
      #extentPolygonVector.create(tmpExtentEOOShapeFileName,ogr.wkbPolygon)
      #ringExtemt = ogr.Geometry(ogr.wkbLinearRing)
      #ringExtemt.AddPoint(extentShapefile[0],extentShapefile[1])
      #ringExtemt.AddPoint(extentShapefile[0],extentShapefile[3])
      #ringExtemt.AddPoint(extentShapefile[2],extentShapefile[3])
      #ringExtemt.AddPoint(extentShapefile[2],extentShapefile[1])
      #ringExtemt.AddPoint(extentShapefile[0],extentShapefile[1])
      #sfextentGeom = ogr.Geometry(ogr.wkbPolygon)
      #sfextentGeom.AddGeometry(ringExtemt)
      #extentPolygonVector.addPointGeometry(sfextentGeom)
      #extentPolygonVector.close()
      #extentPolygonVector = None
      
      #-----------------------------------------------------------------------------
      # Convert species shapefile to raster.
      #-----------------------------------------------------------------------------

      Log.info("Converting species polygon(s) to raster...")
     
      # Convert species polygons to raster.
      gr = Grass()
      #np.random.seed(seed=batchNumber)
      gr.init(batchNumber)
      gr.vectorToRaster(extentShapefile,cellSize,
                        tmpEOOShapeFileName,tmpSpeciesRasterName,
                        "polygon",np.uint8,None,1)
      gr = None

      #-----------------------------------------------------------------------------
      # Read species raster. 
      #-----------------------------------------------------------------------------

      # Read the species raster.
      speciesRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesRasterName,"tmp_species")  

      #-----------------------------------------------------------------------------
      # Read or create the area raster.
      #-----------------------------------------------------------------------------

      # Need to create a area raster?
      if not self.isValueSet(areaRasterName):
        # Create the cell area raster.
        Log.info("Calculating cell area's...")
        areaRaster = Raster()
        areaRaster.initRasterCellAreas(extentShapefile,cellSize)
        return areaRaster
      else:
        # Read the cell area raster.
        cropAreaRaster = gdal.Warp(tmpSpeciesAreaRasterName,areaRasterName,
                                   outputBounds=extentShapefile,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
        cropAreaRaster = None
        areaRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesAreaRasterName,"areas")
      
      #-----------------------------------------------------------------------------
      # Read the elevation raster and resizes to extent and resamples to cellsize.
      #-----------------------------------------------------------------------------
    
      cropEleRaster = gdal.Warp(tmpSpeciesEleRasterName,eleRasterName,
                                outputBounds=extentShapefile,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
      cropEleRaster = None
      eleRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesEleRasterName,"elevation")
    
      #-----------------------------------------------------------------------------
      # Read the landuse raster and resizes to extent and resamples to cellsize.
      #-----------------------------------------------------------------------------
    
      cropLURaster = gdal.Warp(tmpSpeciesLURasterName,landuseRasterName,
                               outputBounds=extentShapefile,format="GTiff",creationOptions=["BIGTIFF=YES","COMPRESS=LZW"])
      cropLURaster = None
      landuseRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesLURasterName,"landuse")
      
      #-----------------------------------------------------------------------------
      # Reclass species raster. 
      #-----------------------------------------------------------------------------

      # habitatFileName = np.array(habitatFileNames)[np.where(species == habitatFileNamesIDs)][0]
      # habitatFile = pd.read_csv(habitatFileName,dtype={'code':object})

      # Merge species habitat suitability with transformation matrix
      habitatFile = pd.merge(habitatFile,transMatrix,how='left',left_on='code',right_on='iucn_code')
      
      # Subset based on user defined suitability codes
      habitatFile = habitatFile[habitatFile['suitability'].isin(suitabilityCodes)]
      if habitatFile.empty:
        Log.info("- No habitat data for specified suitability filter for species with ID=%s..." % species)
        continue

      # Create empty raster.
      noDataValue = -999
      SpeciesESHRaster = Raster()
      SpeciesESHRaster.initRaster(extentShapefile,cellSize,np.int16,noDataValue)
      
      mask = None
      for i in range(len(habitatFile)):
        if mask is None:
          mask = (landuseRaster.r == habitatFile.iloc[i]['globio_code'])
        else:
          mask = np.logical_or(mask,(landuseRaster.r == habitatFile.iloc[i]['globio_code']))        
      speciesmask = (speciesRaster.r == 1)
      mask = (speciesmask & mask)
      SpeciesESHRaster.r[mask] = 1
      
      # Free raster and masks
      speciesRaster.close()
      speciesRaster = None
      landuseRaster.close()
      landuseRaster = None
      speciesmask = None
      mask = None
      notmask = None

      # Subset elevation range
      if np.isnan(eleSpecies.iloc[0]['elevation_lower']):
        if np.isnan(eleSpecies.iloc[0]['elevation_upper']):
          elemask = (eleRaster.r != eleRaster.noDataValue)
        else:
          elemask = (eleRaster.r <= eleSpecies.iloc[0]['elevation_upper'])
      else:
        if np.isnan(eleSpecies.iloc[0]['elevation_upper']):
          elemask = (eleRaster.r >= eleSpecies.iloc[0]['elevation_lower'])
        else:
          elemask = ((eleRaster.r >= eleSpecies.iloc[0]['elevation_lower']) & (eleRaster.r <= eleSpecies.iloc[0]['elevation_upper']))

      mask = (elemask & (SpeciesESHRaster.r == 1))
      SpeciesESHRaster.r[mask] = 1
      notmask = np.invert(mask)
      SpeciesESHRaster.r[notmask] = SpeciesESHRaster.noDataValue

      # Free raster and mask
      elemask = None
      eleRaster.close()
      eleRaster = None

      # Save species ESH raster
      SpeciesESHRaster.writeAs(tmpSpeciesESHRasterName)
      
      # Calculate total ESH of the species at resolution of the land use map
      Log.info("Calculating ESH...")

      # Make new raster object using float as datatype
      noDataValue = -999.0
      SpeciesESHAreaRaster = Raster()
      SpeciesESHAreaRaster.initRaster(extentShapefile,cellSize,np.float32,noDataValue)
      SpeciesESHAreaRaster.r = SpeciesESHRaster.r

      # Free np.int raster
      SpeciesESHRaster.close()
      SpeciesESHRaster = None

      # Calculate ESH
      SpeciesESHAreaRaster.r[notmask] = 0        
      SpeciesESHAreaRaster.r = SpeciesESHAreaRaster.r * areaRaster.r
      areaSum = np.sum(SpeciesESHAreaRaster.r)
      print(areaSum)
      speciesAreas = [species,areaSum]
      linesESH.append("{};{}".format(*speciesAreas))

      # Free rasters and masks
      mask = None
      notmask = None
      SpeciesESHAreaRaster.close()
      SpeciesESHAreaRaster = None
      speciesAreas = None

      # Calculate ESH at 2 km resolution as in the IUCN guidelines
      Log.info("Calculating AOO at 2 km resolution...")
      SpeciesAOO = self.calcSpeciesAOO(species,tmpSpeciesESHRasterName,tmpSpeciesAOORasterName)     
      #SpeciesAOO = self.calcSpeciesAOO(species,tmpSpeciesESHRasterName,tmpSpeciesAOORasterName,tmpEOOShapeFileName)
      linesAOO.append("{};{}".format(*SpeciesAOO))
      SpeciesAOO = None

      #-----------------------------------------------------------------------------
      # Fragmentation effects
      #-----------------------------------------------------------------------------
    
      Log.info("Fragmentation: Buffering ESH areas with half dispersal distance...")

      halfspeciesDisp = speciesDisp / 2.0
    
      # Buffer ESH areas.
      gr = Grass()
      #np.random.seed(seed=batchNumber)
      gr.init(batchNumber)
      gr.buffer(extentShapefile,cellSize,tmpSpeciesESHRasterName,tmpSpeciesESHBufRasterName,
                halfspeciesDisp,"kilometers")
      gr = None

      # Reclass buffer values (i.e., 2) to species values (i.e., 1)
      Log.info("Reclassing...")
      
      # Read buffered ESH raster.
      SpeciesESHBufRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesESHBufRasterName,"tmp_species_buf")

      # Select all values and reclass to 1.
      buffermask = (SpeciesESHBufRaster.r == 2)
      mask = SpeciesESHBufRaster.getDataMask()
      SpeciesESHBufRaster.r[mask] = 1
      mask = None
      
      # Save species ESH buffer raster
      SpeciesESHBufRaster.writeAs(tmpSpeciesBufClumpRasterName)

      # Close and free the raster.
      SpeciesESHBufRaster.close()
      SpeciesESHBufRaster = None

      # Clump connected areas.
      Log.info("Clumping connected areas...")

      diagonal = True

      gr = Grass()
      #np.random.seed(seed=batchNumber)
      gr.init(batchNumber)
      gr.clump(extentShapefile,cellSize,tmpSpeciesBufClumpRasterName,tmpSpeciesESHClumpRasterName,np.uint32,diagonal)
      gr = None

      # Read clumped ESH raster.
      SpeciesESHClumpedRaster = self.readAndPrepareInRaster(extentShapefile,cellSize,tmpSpeciesESHClumpRasterName,"tmp_species_clump")

      # Remove buffer cells from patches by setting to noData.
      SpeciesESHClumpedRaster.r[buffermask] = SpeciesESHClumpedRaster.noDataValue
      buffermask = None

      # Save final species ESH patches raster
      SpeciesESHClumpedRaster.writeAs(tmpSpeciesESHPatchesRasterName)

      # Creates a list of patches from the clumped raster.
      patchList = np.unique(SpeciesESHClumpedRaster.r)
      
      # Get valid patches.
      patchList = patchList[(patchList!=SpeciesESHClumpedRaster.noDataValue)]
      patchList = patchList[~np.isnan(patchList)]
      print(patchList)

      if patchList.size == 0:
        areaSum = np.asarray([0.0])
        patchList = np.asarray([0])
      else:
        areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r,SpeciesESHClumpedRaster.r,patchList,np.sum,np.float64,0)
      print(areaSum)
    
      # Close and free the rasters.
      SpeciesESHClumpedRaster.close()
      SpeciesESHClumpedRaster = None
      areaRaster.close()
      areaRaster = None

      # Calculate population sizes based on species density
      popSum = areaSum * speciesDens

      # Combine patches, areas and populations in an array of patch/area/pop tuples.
      patchAreas = zip(([species]*len(patchList)),patchList,areaSum,popSum)
      areaSum = None
      patchList = None
      popSum = None
   
      # Create file content.

      for patchArea in patchAreas:
        linesESH_patches.append("{};{};{};{}".format(*patchArea))

      patchAreas = None

      # Write to file.
      UT.fileWrite(outESHsFileName.replace(".csv",("_"+str(species)+".csv")),linesESH)
      UT.fileWrite(outAOOsFileName.replace(".csv",("_"+str(species)+".csv")),linesAOO)
      UT.fileWrite(outESHsPatchesFileName.replace(".csv",("_"+str(species)+".csv")),linesESH_patches)

      # Free lines.
      linesESH = None
      linesAOO = None
      linesESH_patches = None 

      # Remove temporary data.
      if RU.vectorExists(tmpRangesShapeFileName):
        RU.vectorDelete(tmpRangesShapeFileName)
      if RU.vectorExists(tmpEOOShapeFileName):
        RU.vectorDelete(tmpEOOShapeFileName)
      #if RU.vectorExists(tmpExtentEOOShapeFileName):
      #  RU.vectorDelete(tmpExtentEOOShapeFileName)
      if RU.rasterExists(tmpSpeciesRasterName):
        RU.rasterDelete(tmpSpeciesRasterName)
      if RU.rasterExists(tmpSpeciesESHRasterName):
        RU.rasterDelete(tmpSpeciesESHRasterName)
      if RU.rasterExists(tmpSpeciesAOORasterName):
        RU.rasterDelete(tmpSpeciesAOORasterName)   
      if RU.rasterExists(tmpSpeciesESHBufRasterName):
        RU.rasterDelete(tmpSpeciesESHBufRasterName)
      if RU.rasterExists(tmpSpeciesBufClumpRasterName):
        RU.rasterDelete(tmpSpeciesBufClumpRasterName)
      if RU.rasterExists(tmpSpeciesESHClumpRasterName):
        RU.rasterDelete(tmpSpeciesESHClumpRasterName)
      if RU.rasterExists(tmpSpeciesESHPatchesRasterName):
        RU.rasterDelete(tmpSpeciesESHPatchesRasterName)    
      if RU.rasterExists(tmpSpeciesAreaRasterName):
        RU.rasterDelete(tmpSpeciesAreaRasterName)
      if RU.rasterExists(tmpSpeciesLURasterName):
        RU.rasterDelete(tmpSpeciesLURasterName)
      if RU.rasterExists(tmpSpeciesEleRasterName):
        RU.rasterDelete(tmpSpeciesEleRasterName) 
    
    # Show used memory and disk space.
    MON.showMemDiskUsage()
    
    self.showEndMsg()

  #-------------------------------------------------------------------------------
  def test(self):

    #if not self.test:
    #  self.debug = False
      
    self.debug = True
    GLOB.saveTmpData = True

    if self.debug:
      GLOB.SHOW_TRACEBACK_ERRORS = True

    #-----------------------------------------------------------------------------
    # SETTINGS.
    #-----------------------------------------------------------------------------
    #extent=[-180,-90,180,90]
    #cellSize=0.027778
    #tmpEOOShapeFileName = r"C:\Y\ESH\Range_maps\Split\EO_10004.shp"
    #linux = False

    extentName = "wrld"
    extent = GLOB.constants[extentName].value
    speciesdata = r"C:\Y\ESH\Species_data\Species_data.csv"
    transmatrix = r"C:\Y\ESH\TransformationMatrix.csv"
    elematrix = r"C:\Y\ESH\Elevation_data_mammals.csv"
    habitatdir = r"C:\Y\ESH\Habitat_data\Habitat_suitability_mammals.csv"
    rangesdir = r"C:\Y\ESH\Range_maps\Split"
    speciesids = "13451"
    suitabilitiesstr = "Suitable"
    presencecodes = "1"
    origincodes = "1|2|6"
    seasonalitycodes = "1|2|3"
    landuse = r"C:\Y\ESH\Input_rasters\Globio4_landuse_10sec_2015_World_agri_int.tif"
    arearaster = r"C:\Y\ESH\Input_rasters\areakm2_10sec.tif"
    elevationraster = r"C:\Y\ESH\Input_rasters\Elevation_meter_10sec.tif"
    batchnumber=1
    addmcpflag = True
    
    outVersion = speciesids
    outeshfilename = r"C:\Y\ESH\testesh_%s" % (outVersion)
    outaoofilename = r"C:\Y\ESH\testaoo_%s" % (outVersion)
    outeshpatchesfilename = r"C:\Y\ESH\testeshpatches_%s" % (outVersion)
    
    # Check output area files.
    # for fileName in [outeshfilename]:
    #   if (fileName != "") and (os.path.isfile(fileName)):
    #     os.remove(fileName)
    # for fileName in [outaoofilename]:
    #   if (fileName != "") and (os.path.isfile(fileName)):
    #     os.remove(fileName)
    # for fileName in [outeshpatchesfilename]:
    #   if (fileName != "") and (os.path.isfile(fileName)):
    #     os.remove(fileName)        
    
    # self.run(extent,speciesdata,transmatrix,elematrix,
    #          habitatdir,rangesdir,speciesids,suitabilitiesstr,
    #          presencecodes,origincodes,seasonalitycodes,addmcpflag,landuse,
    #          arearaster,elevationraster,
    #          outeshfilename,outaoofilename,outeshpatchesfilename,batchnumber)

    species = 13451
    inRasterName = r"C:\Y\ESH\tmp_species_1.tif"
    outRasterName = r"C:\Y\ESH\tmp_aoo_check_1.tif"
    clipShapefileName = r"C:\Y\ESH\tmp_EOO_1.shp"
    self.calcSpeciesAOO(species,inRasterName,outRasterName,clipShapefileName)             
      
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  try:
    pCalc = GLOBIO_CalcESH()
    pCalc.test()
  except:
    Log.err()
