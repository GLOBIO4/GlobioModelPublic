# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: 2 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2.
#           - init - userTempDir = os.environ["TEMP"] changed to 
#               Utils.getUserTempDir(). 
#           - init - additional gsetup.init() added for use on Linux.
#           20 apr 2017, ES, ARIS B.V.
#           - Version 4.0.6.
#           - distance added.
#           - vectorToRaster added.
#           - buffer modified, now using compression.
#           - distance modified, now using float32 and compression.
#           - buffer and buffer modified, now using BIGTIFF.
#-------------------------------------------------------------------------------

import os

import numpy as np

import grass.script as gscript 
from grass.script import setup as gsetup
from grass.script import core as gcore

from grass.pygrass.modules.shortcuts import general as g
from grass.pygrass.modules.shortcuts import raster as r
from grass.pygrass.modules.shortcuts import vector as v
from grass.pygrass.modules import Module

import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Grass(object):
  quiet = True
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    self.quiet = True

  #-------------------------------------------------------------------------------
  def init(self,batchNumber):

    Log.dbg("Initialising GRASS...")

    # Set initial names.
    locationName = "globio4ws"
    mapsetName = "PERMANENT"

    # Get the user temp dir.
    #userTempDir = Utils.getUserTempDir()
    userTempDir = "D:\\Grass"

    # Set grass temp dir.
    grassTempDir = os.path.join(userTempDir,("Grass"+str(batchNumber)))

    # Create user base dir if not exist.
    if not os.path.isdir(grassTempDir):
      Log.dbg("- Creating temp directory: %s" % grassTempDir)
      os.mkdir(grassTempDir)

    # Set the dbase dir. 
    dbaseDir = grassTempDir

    # Set the loction dir.
    locationDir = os.path.join(dbaseDir,locationName)

    # Set GISRC filename.    
    rcFileName = os.path.join(grassTempDir,"globio4.rc")

    # Create GISRC file with custom settings.
    # The directory will be by exmaple:
    #   <user>\Temp\Grass\globio4ws\PERMANENT
    Log.dbg("- Creating gisrc file...")
    Log.dbg("    Using dbasedir : %s" % dbaseDir)
    Log.dbg("    Using location : %s" % locationName)
    Log.dbg("    Using mapset : %s" % mapsetName)
    self.createGISRC(rcFileName,dbaseDir,locationName,mapsetName)
    
    print(rcFileName)
    
    # Update the GISRC environment var.    
    Log.dbg("- Setting GISRC environment variable...")
    os.environ["GISRC"] = rcFileName

    # Get GISBASE dir.
    gisbaseDir = os.environ["GISBASE"]
    Log.dbg("- Using GISBASE: %s" % gisbaseDir)
    
    print(gisbaseDir,dbaseDir,locationName)
    	
    # Setup GRASS environment.      
    Log.dbg("- Setting up GRASS environment...")
    gsetup.init(gisbaseDir,dbaseDir,locationName)

    # Create location directory.
    if not os.path.isdir(locationDir):
      # Create GRASS workspace.
      Log.dbg("- Creating GRASS workspace: %s" % dbaseDir)
      gcore.create_location(dbaseDir,locationName,epsg=GLOB.epsgWGS84)

    # Check GRASS workspace.
    fullDir = os.path.join(dbaseDir,locationName,mapsetName)
    if not os.path.isdir(fullDir):
      Log.dbg("Globio4 GRASS workspace not found.")
      return

    # Setup GRASS environment.      
    Log.dbg("- Setting up GRASS environment...")
    gsetup.init(gisbaseDir,dbaseDir,locationName,mapsetName)

    #Log.dbg("- Current GRASS environment: %s" % gscript.gisenv())

    # Define GRASS alias names.
    r.in_gdal = Module("r.in.gdal")
    r.out_gdal = Module("r.out.gdal")
  
  #-------------------------------------------------------------------------------
  # Buffers all values except nodata!
  # Input gets value 1, buffer gets value 2.
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.buffer(extent,cellSize,tmpSettlementsRasterName,tmpSettlementsBufRasterName,
  #               bufferDistanceKM,"kilometers")
  #     gr = None
  def buffer(self,extent,cellSize,inRasterName,outRasterName,distance,units,
             compress=True):

    # Set grass raster names.
    grInRasterName = UT.getUniqueName("r%s") 
    grOutRasterName = UT.getUniqueName("r%s")  

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)
         
    # Reading input raster.
    Force = False
    if Force:
      r.in_gdal(input=inRasterName,output=grInRasterName,l=True,overwrite=True,quiet=self.quiet)
    else:
      r.in_gdal(input=inRasterName,output=grInRasterName,overwrite=True,quiet=self.quiet) 

    # Create buffer.
    # Input gets value 1, buffer gets value 2.
    r.buffer(input=grInRasterName,output=grOutRasterName,
             distances=distance,units=units,overwrite=True,quiet=self.quiet)
  
    # Compress?
    createOption="BIGTIFF=YES"
    if compress:
      createOption+=",COMPRESS=LZW"
  
    # Writing output raster.
    r.out_gdal(input=grOutRasterName,output=outRasterName,
               format="GTiff",createopt=createOption,
               c=True,quiet=self.quiet) 

    # Clean up.
    g.remove(type="raster",name=grInRasterName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grOutRasterName,f=True,quiet=self.quiet)

  #-------------------------------------------------------------------------------
  # Recategorizes a raster by grouping cells that form physically discrete areas into unique categories
  #  
  # Remarks:
  #   dataType:       numpy datatype
  #   diagonal:       setting to include diagonal connections (True) or only connect neighbouring cells (False)
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.clump(extent,cellSize,tmpSpeciesBufClumpRasterName,tmpSpeciesESHClumpRasterName,diagonal)
  #     gr = None
  def clump(self,extent,cellSize,inRasterName,outRasterName,dataType=np.uint32,diagonal=False,compress=True):

    # Set grass raster names.
    grInRasterName = UT.getUniqueName("r%s") 
    grOutRasterName = UT.getUniqueName("r%s")     

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)

    # Reading input raster.
    Force = False
    if Force:
      r.in_gdal(input=inRasterName,output=grInRasterName,l=True,overwrite=True,quiet=self.quiet)
    else:
      r.in_gdal(input=inRasterName,output=grInRasterName,overwrite=True,quiet=self.quiet) 
    
    if diagonal:
      gscript.run_command("r.clump",input=grInRasterName,output=grOutRasterName,
                          flags='d',overwrite=True,quiet=self.quiet)
    else:
      gscript.run_command("r.clump",input=grInRasterName,output=grOutRasterName,
                          overwrite=True,quiet=self.quiet)   

    # Get datatype string.
    dataTypeStr = self.dataTypeNumpyToString(dataType)
    
    # Compress?
    createOption="BIGTIFF=YES"
    if compress:
      createOption+=",COMPRESS=LZW"
    createOption+=",PROFILE=GeoTIFF"  
  
    # Writing output raster.
    r.out_gdal(input=grOutRasterName,output=outRasterName,
               type=dataTypeStr,format="GTiff",createopt=createOption,
               f=True,c=True,quiet=self.quiet) 

    # Clean up.
    g.remove(type="raster",name=grInRasterName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grOutRasterName,f=True,quiet=self.quiet)
    
  #-------------------------------------------------------------------------------
  def createGISRC(self,fileName,dbaseDir,locationName,mapsetName):
    lines = []
    lines.append("GISDBASE: "+dbaseDir)
    lines.append("LOCATION_NAME: "+locationName)
    lines.append("MAPSET: "+mapsetName)
    lines.append("GUI: wxpython")
    lines.append("PID: 2948")
    UT.fileWrite(fileName,lines)

  #-------------------------------------------------------------------------------
  # Calculate distances to the nearest feature.
  # When using WGS84 the distance is in meters.
  #  
  # Remarks:
  #   dataType:       numpy datatype
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.distance(extent,cellSize,tmpSettlementsRasterName,tmpDistanceRasterName)
  #     gr = None
  def distance(self,extent,cellSize,inRasterName,outRasterName,
               dataType=np.float32,compress=True):

    # Set grass raster names.
    grInRasterName = UT.getUniqueName("r%s") 
    grOutRasterName = UT.getUniqueName("r%s")  

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)

    # Reading input raster.
    Force = False
    if Force:
      r.in_gdal(input=inRasterName,output=grInRasterName,l=True,overwrite=True,quiet=self.quiet)
    else:
      r.in_gdal(input=inRasterName,output=grInRasterName,overwrite=True,quiet=self.quiet) 

    # Calculate distance.
    # https://grass.osgeo.org/grass64/manuals/r.grow.distance.html
    gscript.run_command("r.grow.distance",input=grInRasterName,distance=grOutRasterName,
                        metric="geodesic",overwrite=True,quiet=self.quiet)
  
    # Compress?
    createOption="BIGTIFF=YES"
    if compress:
      createOption+=",COMPRESS=LZW"

    # Get datatype string.
    dataTypeStr = self.dataTypeNumpyToString(dataType)
  
    # Writing output raster.
    r.out_gdal(input=grOutRasterName,output=outRasterName,
               type=dataTypeStr,format="GTiff",createopt=createOption,
               f=True,c=True,quiet=self.quiet) 

    # Clean up.
    g.remove(type="raster",name=grInRasterName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grOutRasterName,f=True,quiet=self.quiet)

  #-------------------------------------------------------------------------------
  # Converts Numpy datatype to GRASS/GDAL datatype string.
  #   Byte,Int16,UInt16,Int32,UInt32,Float32,Float64,CInt16,CInt32,CFloat32,CFloat64
  def dataTypeNumpyToString(self,dataType):
    if dataType==np.int16:
      return "Int16"
    elif dataType==np.int32:
      return "Int32"
    elif dataType==np.byte:
      return "Byte"
    elif dataType==np.uint8:
      return "Byte"
    elif dataType==np.uint16:
      return "UInt16"
    elif dataType==np.uint32:
      return "UInt32"
    elif dataType==np.float32:
      return "Float32"
    elif dataType==np.float64:
      return "Float64"
    else:
      return "unknown"

  #-------------------------------------------------------------------------------
  # Creates a minimum convex hull polygon around vector input
  #  
  # Remarks:
  #   geometryType:   point,line,polygon
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.hull(extent,cellSize,tmpRangesShapeFileName,tmpEOOShapeFileName,"polygon")
  #     gr = None
  def hull(self,extent,cellSize,inVectorName,outVectorName,geometryType):

    if not RU.vectorExists(inVectorName):
      Err.raiseGlobioError(Err.VectorNotFound1,inVectorName)

    # Set grass raster names.
    grInVectorName = UT.getUniqueName("v%s") 
    grOutVectorName = UT.getUniqueName("v%s")    

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)

    # Reading input vector.
    Force = False
    if Force:
      v.in_ogr(input=inVectorName,output=grInVectorName,l=True,overwrite=True,quiet=self.quiet)
    else:
      v.in_ogr(input=inVectorName,output=grInVectorName,overwrite=True,quiet=self.quiet) 

    # Set geometry type.
    geometryType = geometryType.lower()
    if geometryType.lower() == "polygon":
      geometryType = "area"
    
    gscript.run_command("v.hull",input=grInVectorName,output=grOutVectorName,
                        overwrite=True,quiet=self.quiet)

    # Writing output vector.
    v.out.ogr(input=grOutVectorName,output=outVectorName,
              type=geometryType,format="ESRI_Shapefile",overwrite=True,quiet=self.quiet) 

    # Clean up.
    g.remove(type="vector",name=grInVectorName,f=True,quiet=self.quiet)
    g.remove(type="vector",name=grOutVectorName,f=True,quiet=self.quiet)

  #-------------------------------------------------------------------------------
  # Creates a mask based on a shapefile to limit grass calculations to a specific area
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.mask(extent,cellSize,tmpEOOShapeFileName)
  #     gr = None
  def mask(self,extent,cellSize,inVectorName):

    if not RU.vectorExists(inVectorName):
      Err.raiseGlobioError(Err.VectorNotFound1,inVectorName)

    # Set grass vector names.
    grInVectorName = UT.getUniqueName("v%s")  
    grOutVectorName = UT.getUniqueName("v%s")  
    
    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)

    # Reading input vector.
    Force = False
    if Force:
      v.in_ogr(input=inVectorName,output=grInVectorName,l=True,overwrite=True,quiet=self.quiet)
    else:
      v.in_ogr(input=inVectorName,output=grInVectorName,overwrite=True,quiet=self.quiet) 
    
    # Set region.
    gscript.run_command("g.region",
                         vector=grInVectorName,quiet=self.quiet)

    # Create vector from extent.
    gscript.run_command("v.in.region",
                         output=grOutVectorName,quiet=self.quiet)

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)
                         
    gscript.run_command("r.mask",vector=grOutVectorName,
                        overwrite=True,quiet=self.quiet)

    # Clean up.
    g.remove(type="vector",name=grInVectorName,f=True,quiet=self.quiet)
    g.remove(type="vector",name=grOutVectorName,f=True,quiet=self.quiet)

  #-------------------------------------------------------------------------------
  # Removes the mask 
  def remove_mask(self):
    g.remove(type="raster",name="MASK",f=True,quiet=self.quiet)

  #-------------------------------------------------------------------------------
  # Rasterizes a vector dataset.
  #
  # Remarks:
  #   geometryType:   point,line,polygon
  #   dataType:       numpy datatype
  #   Specify fieldName or value.
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.vectorToRaster(extent,cellSize,inVectorName,outRasterName,
  #                       "point",np.uint8,"BIOME")
  #     gr = None
  def vectorToRaster(self,extent,cellSize,inVectorName,outRasterName,
                     geometryType,dataType,
                     fieldName=None,value=None,compress=True):

    if not RU.vectorExists(inVectorName):
      Err.raiseGlobioError(Err.VectorNotFound1,inVectorName)

    if RU.rasterExists(outRasterName):
      RU.rasterDelete(outRasterName)

    if (fieldName is None) and (value is None):
      raise Exception("VectorToRaster - No fieldname of value specified.")

    # Set grass raster names.
    grInVectorName = UT.getUniqueName("v%s") 
    grOutRasterName = UT.getUniqueName("r%s")  

    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)

    # Reading input raster.
    Force = False
    if Force:
      v.in_ogr(input=inVectorName,output=grInVectorName,l=True,overwrite=True,quiet=self.quiet)
    else:
      v.in_ogr(input=inVectorName,output=grInVectorName,overwrite=True,quiet=self.quiet) 

    # Set geometry type.
    geometryType = geometryType.lower()
    if geometryType.lower() == "polygon":
      geometryType = "area"
      
    # Get available memory.
    availMemGB = UT.memPhysicalAvailableGB()

    # Set max memory to use.
    maxMemMB = UT.trunc(availMemGB * 0.75 * 1000)
    if maxMemMB == 0:
      maxMemMB = 1

    #print "Cache size: %s MB" % maxMemMB
    
    # Rasterize.
    if not fieldName is None:
      gscript.run_command("v.to.rast",input=grInVectorName,output=grOutRasterName,
                          type=geometryType,use="attr",attribute_column=fieldName,
                          memory=maxMemMB,overwrite=True,quiet=self.quiet)
    else:
      gscript.run_command("v.to.rast",input=grInVectorName,output=grOutRasterName,
                          type=geometryType,use="val",value=value,
                          memory=maxMemMB,overwrite=True,quiet=self.quiet)

    # Compress?
    createOption="BIGTIFF=YES"
    if compress:
      createOption+=",COMPRESS=LZW"

    # Get datatype string.
    dataTypeStr = self.dataTypeNumpyToString(dataType)
    
    # Writing output raster.
    r.out_gdal(input=grOutRasterName,output=outRasterName,
               type=dataTypeStr,format="GTiff",createopt=createOption,
               f=True,c=True,quiet=self.quiet) 

    # Clean up.
    g.remove(type="vector",name=grInVectorName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grOutRasterName,f=True,quiet=self.quiet)
