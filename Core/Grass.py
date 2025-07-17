# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
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
#     7 jun 2019, JH, PBL
#           - temporary folder path changed to Y-disk
#           - distance modified, changed datatype for distance calculations to int to limit output size
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - excludeVector added.
#           16 nov 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - init modified, because of Y:\.
#           30 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - distance_V1 added because of backwardcompatibility.
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
import GlobioModel.Common.Utils as Utils

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Grass(object):
  quiet = True
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    self.quiet = True

  #-------------------------------------------------------------------------------
  def init(self):

    Log.dbg("Initialising GRASS...")

    # Set initial names.
    locationName = "globio4ws"
    mapsetName = "PERMANENT"

    # Get the user temp dir.
    userTempDir = Utils.getUserTempDir()
    # Make sure the server (in our case Azure VM) has a large scratch-drive.

    # Set grass temp dir.
    grassTempDir = os.path.join(userTempDir,"Grass")

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

    # Update the GISRC environment var.    
    Log.dbg("- Setting GISRC environment variable...")
    os.environ["GISRC"] = rcFileName

    # Get GISBASE dir.
    gisbaseDir = os.environ["GISBASE"]
    Log.dbg("- Using GISBASE: %s" % gisbaseDir)

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
    grInRasterName = Utils.getUniqueName("r%s") 
    grOutRasterName = Utils.getUniqueName("r%s")  
    
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
  def createGISRC(self,fileName,dbaseDir,locationName,mapsetName):
    lines = []
    lines.append("GISDBASE: "+dbaseDir)
    lines.append("LOCATION_NAME: "+locationName)
    lines.append("MAPSET: "+mapsetName)
    lines.append("GUI: wxpython")
    lines.append("PID: 2948")
    Utils.fileWrite(fileName,lines)
  
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
  def distance_V1(self,extent,cellSize,inRasterName,outRasterName,
                  dataType=np.float32,compress=True):

    # Set grass raster names.
    grInRasterName = Utils.getUniqueName("r%s") 
    grOutRasterName = Utils.getUniqueName("r%s")  

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
  def distance(self,extent,cellSize,inRasterName,outRasterName,maskRasterName,
               dataType=np.uint32,compress=True):
    
    # Set grass raster names.
    grInRasterName = Utils.getUniqueName("r%s")
    Log.info(grInRasterName) 
    grOutRasterName = Utils.getUniqueName("r%s")
    Log.info(grOutRasterName)
    grMaskRasterName = Utils.getUniqueName("r%s")
    Log.info(grMaskRasterName)
    
    # Set region.
    gscript.run_command("g.region",
                         w=extent[0],s=extent[1],e=extent[2],n=extent[3],
                         res=cellSize,quiet=self.quiet)
    
    # Reading input raster.
    Force = False
    if Force:
      r.in_gdal(input=inRasterName,output=grInRasterName,l=True,overwrite=True,quiet=self.quiet)
      r.in_gdal(input=maskRasterName,output=grMaskRasterName,l=True,overwrite=True,quiet=self.quiet)
    else:
      r.in_gdal(input=inRasterName,output=grInRasterName,overwrite=True,quiet=self.quiet)
      r.in_gdal(input=maskRasterName,output=grMaskRasterName,overwrite=True,quiet=self.quiet)
    
    # JM addition
    # Set a mask for the distance analysis
    # https://grass.osgeo.org/grass76/manuals/r.mask.html
    Log.info("Set the mask for the distance analysis")
    gscript.run_command("r.mask",raster=grMaskRasterName)
        
    # Calculate distance.
    # https://grass.osgeo.org/grass64/manuals/r.grow.distance.html
    gscript.run_command("r.grow.distance",flags="m",input=grInRasterName,distance=grOutRasterName,
                        metric="geodesic",overwrite=True,quiet=self.quiet)
        
    # Compress?
    createOption="BIGTIFF=YES"
    if compress:
      createOption+=",COMPRESS=LZW"
    
    # Get datatype string.
    dataTypeStr = self.dataTypeNumpyToString(dataType)
    #dataTypeStr = self.dataTypeNumpyToString(np.uint32)
    #Log.info(dataTypeStr)
    
    # Writing output raster.
    r.out_gdal(input=grOutRasterName,output=outRasterName,
               type=dataTypeStr,format="GTiff",createopt=createOption,
               f=True,c=True,quiet=self.quiet) 
    
    # Turn off the mask
    gscript.run_command("r.mask",flags="r")
    
    # Clean up.
    g.remove(type="raster",name=grInRasterName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grOutRasterName,f=True,quiet=self.quiet)
    g.remove(type="raster",name=grMaskRasterName,f=True,quiet=self.quiet)
  
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
  # Excludes areas from from a vector.
  #
  # Remarks:
  #   - The areas of exclude vector are removed from the input vector.
  #   - The exclude vector must be a have polygons.
  #   - The input vector can have lines or polygons.
  #
  #   - When running "ERROR 6:..." messages are shown. They can be ignored.
  #
  # Usage:
  #     gr = Grass()
  #     gr.init()
  #     gr.excludeVector(inVectorName,exclVectorName,outVectorName)
  #     gr = None
  #
  def excludeVector(self,inVectorName,excludeVectorName,outVectorName):

    # Set grass raster names.
    grInVectorName = Utils.getUniqueName("v%s") 
    grExcludeVectorName = Utils.getUniqueName("v%s") 
    grOutVectorName = Utils.getUniqueName("v%s")  

    # Reading input vector.
    v.in_ogr(input=inVectorName,output=grInVectorName,
             overwrite=True,quiet=self.quiet) 

    # Reading exclude vector.
    v.in_ogr(input=excludeVectorName,output=grExcludeVectorName,
             overwrite=True,quiet=self.quiet) 

    # Calculate overlay.
    # https://grass.osgeo.org/grass76/manuals/v.overlay.html
    gscript.run_command("v.overlay",
                        ainput=grInVectorName,
                        atype="auto",
                        binput=grExcludeVectorName,
                        btype="area",
                        operator="not",
                        output=grOutVectorName,
                        overwrite=True,quiet=self.quiet)
      
    # Writing output vector.
    v.out_ogr(input=grOutVectorName,output=outVectorName,
              format="ESRI_Shapefile",
              quiet=self.quiet)       

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
    grInVectorName = Utils.getUniqueName("v%s") 
    grOutRasterName = Utils.getUniqueName("r%s")  
    
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
    availMemGB = Utils.memPhysicalAvailableGB()
    
    # Set max memory to use.
    maxMemMB = Utils.trunc(availMemGB * 0.75 * 1000)
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
