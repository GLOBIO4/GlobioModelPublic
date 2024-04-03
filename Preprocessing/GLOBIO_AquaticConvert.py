# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Usage:
#   ./run.sh GLOBIO_AquaticConvert.py
#
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - convertDams_20181129 modified, because of because of open(,newline="").
#-------------------------------------------------------------------------------

import os
import csv
import shutil
import numpy as np

import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.Convert as Convert
import GlobioModel.Core.Globals as GLOB
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticConvert(CalculationBase):
  """
  Performs several conversion actions.
  """
  
  #-------------------------------------------------------------------------------
  # Werkt alleen voor tifs.
  # Werkt alleen voor kopieren naar andere dir.
  def tifCopyToDir(self,inRasterName,outRasterName):
    
    if not RU.geoTifExists(inRasterName):
      Err.raiseGlobioError(Err.RasterNotFound1,inRasterName)
  
    if RU.geoTifExists(outRasterName):
      Err.raiseGlobioError(Err.UserDefined1,"Raster %s already exists." % outRasterName)
  
    shutil.copy(inRasterName,outRasterName)

  #-------------------------------------------------------------------------------
  def resample(self,inName,outName,toCellSize,noDataValue,floatSkipNoData):

    if RU.rasterExists(outName):
      RU.rasterDelete(outName)

    # Read the esri grid.
    Log.info("Reading input: "+inName)
    inRaster = Raster(inName)
    inRaster.read()

    # Show grid info.
    Log.info("Extent: %s" % inRaster.extent)
    Log.info("CellSize: %s" % inRaster.cellSize)
    Log.info("DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))
    Log.info("NoData: %s" % inRaster.noDataValue)
    Log.info("Min: %s" % inRaster.min())
    Log.info("Max: %s" % inRaster.max())

    # Resample.
    Log.info("Resampling input...")
    outRaster = inRaster.resample(toCellSize,noDataValue,floatSkipNoData)

    # Close and free the input.
    inRaster.close()
    inRaster = None

    # Save the output raster.
    Log.info("Writing output: "+outName)
    outRaster.writeAs(outName)
    
    # Close and free the output.
    outRaster.close()
    outRaster = None

  #-------------------------------------------------------------------------------
  def resize(self,inName,outName,toExtent,noDataValue):

    if RU.rasterExists(outName):
      RU.rasterDelete(outName)

    # Read the esri grid.
    Log.info("Reading input: "+inName)
    inRaster = Raster(inName)
    inRaster.read()

    # Show grid info.
    Log.info("Extent: %s" % inRaster.extent)
    Log.info("CellSize: %s" % inRaster.cellSize)
    Log.info("DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))
    Log.info("NoData: %s" % inRaster.noDataValue)
    Log.info("Min: %s" % inRaster.min())
    Log.info("Max: %s" % inRaster.max())

    # Resample.
    Log.info("Resizing input...")
    outRaster = inRaster.resize(toExtent,noDataValue)

    # Close and free the input.
    inRaster.close()
    inRaster = None

    # Save the output raster.
    Log.info("Writing output: "+outName)
    outRaster.writeAs(outName)
    
    # Close and free the output.
    outRaster.close()
    outRaster = None

  #-------------------------------------------------------------------------------
  def lakesVectorToRaster_20181029(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    extentName = "world"
    cellSizeName = "30sec"

    # Set extent and cellSize.
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    Log.info("Extent: %s" % extent)
    Log.info("CellSize: %s" % cellSize)

    inDir = r"G:\data\Globio4LA\data\pbl_20181023\HydroLakes\shapefile"
    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"

    vectors = [("HydroLAKES_polys_v10",
                "lake_depth",
                np.float32,0.0,1.0,"Depth_avg")]

    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
 
    # Create directory.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)
   
    for vector in vectors:
      try:
        inName = vector[0]
        outName = vector[1]
        dataType = vector[2]
        value = vector[3]
        nodata = vector[4]
        #fieldName = None
        fieldName = vector[5]
        inName = os.path.join(inDir,inName+".shp")
        outName = os.path.join(outDir,outName+".tif")
        if os.path.isfile(outName):
          os.remove(outName)
        Log.info("Using: '%s'" % inName)
        Log.info("Creating '%s'..." % outName)
        Convert.vectorToRaster(inName,outName,extent,cellSize,dataType,fieldName,value,nodata,True)
        Log.info("")
      except:
        Log.err()

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Toont raster info.
  def showRasterInfo_20181029(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    inDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"

    rasters = [("GLWD","glwd"),("Lake depth","lake_depth")]
               
    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)

    for raster in rasters:
      rasterName = raster[0]
      inRasterFileName = raster[1]

      Log.info("Reading '%s'..." % rasterName)

      if not inRasterFileName.endswith(".tif"):
        inRasterFileName += ".tif"
              
      inRasterFileName = os.path.join(inDir,inRasterFileName)

      pInfo = RU.rasterGetInfo(inRasterFileName)
      
      print(pInfo)
      print("")
      
    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert from esri grid to tif.
  # Nu met compressie
  def convertGLWDToTif_20181029(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    #Log.info("Running: convertGridToTif_20161202")
    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    rasters = [("GLWD",
                r"G:\data\Globio4LA\data\pbl_20181023\GLWD\GLWD-level3",
                "glwd_3",
                "glwd",
                np.uint8,True)]

    # Convert settings.
    outCellSizeName = "30sec"
    outCellSize = GLOB.constants[outCellSizeName].value
    outCheckAlignExtent=True

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      rasterName = raster[0]
      inDir = raster[1]
      inRasterFileName = raster[2]
      outRasterFileName = raster[3]
      outDataType = raster[4]
      outCompress = raster[5]

      Log.info("Converting '%s'..." % rasterName)

      if outRasterFileName is None:
        outRasterFileName = inRasterFileName
      if not outRasterFileName.endswith(".tif"):
        outRasterFileName += ".tif"
              
      inRasterFileName = os.path.join(inDir,inRasterFileName)
      outRasterFileName = os.path.join(outDir,outRasterFileName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      noDataValue = RU.getNoDataValue(outDataType)
      Convert.esriGridToTif(inRasterFileName,
                            outRasterFileName,outDataType,noDataValue,
                            outCellSize,outCheckAlignExtent,outCompress)

      rasInfo = RU.rasterGetInfo(outRasterFileName)
      rasInfo.show("Output:")

      Log.info("")

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert from NetCDF to tif.
  def convertNetCDFToTif_20181029(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    rasters = [("FLO1K qav",
                r"G:\data\Globio4LA\data\pbl_20181023\FLO1K\FLO1K_upscaled_5min",
                "FLO1K.5min.ts.1960.2015.qav.nc",
                "flo1k_qav_5min",
                np.float32,True,33)]

    # Convert settings.
    outExtentName = "world"
    outExtent = GLOB.constants[outExtentName].value
    outCellSizeName = "5min"
    outCellSize = GLOB.constants[outCellSizeName].value
    
    outDir = r"G:\Data\Globio4LA\data\kanweg"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      rasterName = raster[0]
      inDir = raster[1]
      inRasterFileName = raster[2]
      outRasterFileName = raster[3]
      outDataType = raster[4]
      outCompress = raster[5]
      outBandNr = raster[6]

      Log.info("Converting '%s'..." % rasterName)

      if outRasterFileName is None:
        outRasterFileName = inRasterFileName
      if not outRasterFileName.endswith(".tif"):
        outRasterFileName += ".tif"
              
      inRasterFileName = os.path.join(inDir,inRasterFileName)
      outRasterFileName = os.path.join(outDir,outRasterFileName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      noDataValue = RU.getNoDataValue(outDataType)
      Convert.netCDFToTif(inRasterFileName,
                            outRasterFileName,
                            outBandNr,
                            outExtent,outCellSize,
                            outDataType,noDataValue,
                            outCompress)

      rasInfo = RU.rasterGetInfo(outRasterFileName)
      rasInfo.show("Output:")

      Log.info("")

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  def riverVectorToRaster_20181107(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    extentName = "world"
    cellSizeName = "30sec"

    # Set extent and cellSize.
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    Log.info("Extent: %s" % extent)
    Log.info("CellSize: %s" % cellSize)

    inDir = r"P:\Project\Globio4LA\data\pbl_20181023\VBarbarossa\flo1k_hydrography"
    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"

    vectors = [("drainage_lines24",
                "rivers",
                np.uint8,1,255,None)]

    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
 
    # Create directory.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)
   
    for vector in vectors:
      try:
        inName = vector[0]
        outName = vector[1]
        dataType = vector[2]
        value = vector[3]
        nodata = vector[4]
        fieldName = vector[5]
        inName = os.path.join(inDir,inName+".shp")
        outName = os.path.join(outDir,outName+".tif")
        if os.path.isfile(outName):
          os.remove(outName)
        Log.info("Using: '%s'" % inName)
        Log.info("Creating '%s'..." % outName)
        Convert.vectorToRaster(inName,outName,extent,cellSize,dataType,fieldName,value,nodata,True)
        Log.info("")
      except:
        Log.err()

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Creates 1 deg, 5 min en 30sec fishnet shapefiles.
  def createFishNets_20181108(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    extentName = "world"
    cellSizeNames = ["1deg","5min","30sec"]
    
    for cellSizeName in cellSizeNames:

      # Set extent and cellSize.
      extent = GLOB.constants[extentName].value
      cellSize = GLOB.constants[cellSizeName].value
  
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
      Log.info("Extent: %s" % extent)
      Log.info("CellSize: %s" % cellSize)
      Log.info("NrCols/NrRows: %s %s" % (nrCols,nrRows))
      Log.info("NrCells: %s " % (nrCols*nrRows))
  
      outDir = r"G:\Data\Globio4LA\data\referentie\v4012\%s_wrld\in_20181026\shp" % cellSizeName

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)

      # Set members.
      self.outDir = outDir

      # Enable logging to a file.
      self.enableLogToFile(self.outDir)
 
      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)
   
      outName = os.path.join(outDir,"fishnet.shp")
      try:
        Log.info("Creating '%s'..." % outName)
        VU.createFishNetShapeFile(outName,extent,cellSize)
        Log.info("")
      except:
        Log.err()

    self.showEndMsg()

  #------------------------------------------------------------------------------
  # Creates dummy rasters.
  def createWaterTemperatureMonths_20181119(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    extentName = "world"
    cellSizeNames = ["5min"]
    cellSizeNames = ["30sec"]
    
    for cellSizeName in cellSizeNames:

      # Set extent and cellSize.
      extent = GLOB.constants[extentName].value
      cellSize = GLOB.constants[cellSizeName].value
  
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
      Log.info("Extent: %s" % extent)
      Log.info("CellSize: %s" % cellSize)
      Log.info("NrCols/NrRows: %s %s" % (nrCols,nrRows))
      Log.info("NrCells: %s " % (nrCols*nrRows))
  
      outDir = r"G:\Data\Globio4LA\data\referentie\v4012\%s_wrld\test_20181119" % cellSizeName

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)

      # Set members.
      self.outDir = outDir
 
      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      try:
        for i in range(1,13):
          rasterName = os.path.join(outDir,"watertemperature_%s.tif" % i)
          Log.info("Creating '%s'..." % rasterName)
          raster = Raster(rasterName)
          noDataValue = -999.0
          value = 8.5 + i * 0.1
          raster.initRaster(extent, cellSize, np.float32, noDataValue, value)
          raster.write()
          raster.close()
          raster = None
        Log.info("")
      except:
        Log.err()

    self.showEndMsg()

  #------------------------------------------------------------------------------
  # Creates dummy rasters.
  def createFractions_20181119(self,*args):
    
    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    extentName = "world"
    #cellSizeNames = ["5min"]
    cellSizeNames = ["30sec"]
    
    for cellSizeName in cellSizeNames:

      # Set extent and cellSize.
      extent = GLOB.constants[extentName].value
      cellSize = GLOB.constants[cellSizeName].value
  
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
      Log.info("Extent: %s" % extent)
      Log.info("CellSize: %s" % cellSize)
      Log.info("NrCols/NrRows: %s %s" % (nrCols,nrRows))
      Log.info("NrCells: %s " % (nrCols*nrRows))
  
      outDir = r"G:\Data\Globio4LA\data\referentie\v4012\%s_wrld\test_20181119" % cellSizeName

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)

      # Set members.
      self.outDir = outDir
 
      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      try:
        fractionRasterNames = ["lakeshallow_fractions","lakedeep_fractions",
                               "reservoirshallow_fractions","reservoirdeep_fractions",
                               "river_fractions","floodplain_fractions",
                               "wetland_fractions"]
        for rasterName in fractionRasterNames:
          rasterName = os.path.join(outDir,rasterName+".tif")
          Log.info("Creating '%s'..." % rasterName)
          raster = Raster(rasterName)
          noDataValue = -999.0
          value = 0.1
          raster.initRaster(extent, cellSize, np.float32, noDataValue, value)
          raster.write()
          raster.close()
          raster = None
        Log.info("")
      except:
        Log.err()

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert de FLO1K nc bestanden naar tifs.
  def convertFLO1KToTif_20181119(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # rasterName,inDir,inRasterFileName,outRasterFileName,
    # outDataType,netCDFNoDataValue,subDatasetNr,outCompress,outBandNr
    rasters = [("FLO1K qav",
                r"G:\data\Globio4LA\data\pbl_20181023\FLO1K",
                "FLO1K.ts.1960.2015.qav.nc",
                "flo1k_qav_2015",
                np.float32,-1,None,True,56),
               ("FLO1K qma",
                r"G:\data\Globio4LA\data\pbl_20181023\FLO1K",
                "FLO1K.ts.1960.2015.qma.nc",
                "flo1k_qma_2015",
                np.float32,-1,None,True,56),
               ("FLO1K qmi",
                r"G:\data\Globio4LA\data\pbl_20181023\FLO1K",
                "FLO1K.ts.1960.2015.qmi.nc",
                "flo1k_qmi_2015",
                np.float32,-1,None,True,56)]

    # Convert settings.
    outExtentName = "world"
    outCellSizeName = "30sec"
    
    outExtent = GLOB.constants[outExtentName].value
    outCellSize = GLOB.constants[outCellSizeName].value
    
    outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
    
    if os.path.isdir("/root"):
      outDir = UT.toLinux(outDir)
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      rasterName = raster[0]
      inDir = raster[1]
      inRasterFileName = raster[2]
      outRasterFileName = raster[3]
      outDataType = raster[4]
      netCDFNoDataValue = raster[5]
      subDatasetNr = raster[6]
      outCompress = raster[7]
      outBandNr = raster[8]

      Log.info("Converting '%s'..." % rasterName)

      if outRasterFileName is None:
        outRasterFileName = inRasterFileName
      if not outRasterFileName.endswith(".tif"):
        outRasterFileName += ".tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inRasterFileName = os.path.join(inDir,inRasterFileName)
      outRasterFileName = os.path.join(outDir,outRasterFileName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      noDataValue = RU.getNoDataValue(outDataType)
      flipOrigin = True
      Convert.netCDFToTif(inRasterFileName,
                          outRasterFileName,
                          outBandNr,
                          outExtent,outCellSize,
                          outDataType,noDataValue,
                          netCDFNoDataValue,
                          subDatasetNr,
                          flipOrigin,
                          outCompress)

      rasInfo = RU.rasterGetInfo(outRasterFileName)
      rasInfo.show("Output:")
      raster = Raster(outRasterFileName)
      raster.read()
#       print np.max(raster.r)
#       print np.min(raster.r)
#       Log.info("  Min: %s" % raster.min())
#       Log.info("  Max: %s" % raster.max())
      raster.close()
      raster = None

      Log.info("")

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert de PCRGLOBWB nc bestanden naar 5min tifs. 
  def convertPCRGLOBWBToTif_20181119(self,*args):

    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # rasterName,inDir,inRasterFileName,outRasterFileName,
    # outDataType,netCDFNoDataValue,subDatasetNr,outCompress,outBandNr
    rasters = [("PCR-GLOBWB qav",
                r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\pcrglobwb_discharge",
                "qav_longTerm_1960_2015.nc",
                "pcrglobwb_qav_2015",
                np.float32,1e+20,1,True,1),
               ("PCR-GLOBWB qma",
                r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\pcrglobwb_discharge",
                "qma_longTerm_1960_2015.nc",
                "pcrglobwb_qma_2015",
                np.float32,1e+20,1,True,1),
               ("PCR-GLOBWB qmi",
                r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\pcrglobwb_discharge",
                "qmi_longTerm_1960_2015.nc",
                "pcrglobwb_qmi_2015",
                np.float32,1e+20,1,True,1)]
    
    # Convert settings.
    outExtentName = "world"
    outCellSizeName = "5min"
    
    outExtent = GLOB.constants[outExtentName].value
    outCellSize = GLOB.constants[outCellSizeName].value
    
    outDir = r"G:\data\Globio4LA\data\referentie\v4012\5min_wrld\in_20181026"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      rasterName = raster[0]
      inDir = raster[1]
      inRasterFileName = raster[2]
      outRasterFileName = raster[3]
      outDataType = raster[4]
      netCDFNoDataValue = raster[5]
      subDatasetNr = raster[6]
      outCompress = raster[7]
      outBandNr = raster[8]

      Log.info("Converting '%s'..." % rasterName)

      if outRasterFileName is None:
        outRasterFileName = inRasterFileName
      if not outRasterFileName.endswith(".tif"):
        outRasterFileName += ".tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inRasterFileName = os.path.join(inDir,inRasterFileName)
      outRasterFileName = os.path.join(outDir,outRasterFileName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      noDataValue = RU.getNoDataValue(outDataType)
      flipOrigin = False
      Convert.netCDFToTif(inRasterFileName,
                          outRasterFileName,
                          outBandNr,
                          outExtent,outCellSize,
                          outDataType,noDataValue,
                          netCDFNoDataValue,
                          subDatasetNr,
                          flipOrigin,
                          outCompress)

      rasInfo = RU.rasterGetInfo(outRasterFileName)
      rasInfo.show("Output:")
      raster = Raster(outRasterFileName)
      raster.read()
      raster.close()
      raster = None

      Log.info("")

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert from tif to tif.
  def convertCatchments_20181128(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    #Log.info("Running: convertGridToTif_20161202")
    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    rasters = [("Basins",
                r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\flo1k_hydrography",
                "basins.tif",
                "catchments",
                np.uint32,True)]

    # Convert settings.
    outExtentName = "wrld"
    outCellSizeName = "30sec"
    
    extent = GLOB.constants[outExtentName].value
    cellSize = GLOB.constants[outCellSizeName].value

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      rasterName = raster[0]
      inDir = raster[1]
      inRasterName = raster[2]
      outRasterName = raster[3]
      # 20201118
      # outDataType = raster[4]
      # outCompress = raster[5]

      Log.info("Converting '%s'..." % rasterName)

      if outRasterName is None:
        outRasterName = inRasterName
      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inRasterName = os.path.join(inDir,inRasterName)
      outRasterName = os.path.join(outDir,outRasterName)

      Log.info("Using input    : %s" % inRasterName)
      Log.info("Creating output: %s" % outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      rasInfo = RU.rasterGetInfo(inRasterName)
      rasInfo.show("Input:")

      # Reads the raster and resizes to extent and resamples to cellsize.
      catchRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,"catchments")

      Log.info("writing catchments raster...")

      catchRaster.writeAs(outRasterName)

      rasInfo = RU.rasterGetInfo(outRasterName)
      rasInfo.show("Output:")

      Log.info("")

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Convert from csv to tif.
  # There are dams which are not near a river, i.e. Oosterdschelde kering.
  # So dams with "NA" coords are skipped.
  def convertDams_20181129(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    #Log.info("Running: convertGridToTif_20161202")
    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    rasters = [("dams",
                r"G:\data\Globio4LA\data\pbl_20181023\GRAND",
                "GRanD_reallocated.csv",
                "dams_wrld")]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      name = raster[0]
      inDir = raster[1]
      inFileName = raster[2]
      outShapeFileName = raster[3]

      Log.info("Converting '%s'..." % name)

      if not outShapeFileName.endswith(".shp"):
        outShapeFileName += ".shp"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inFileName = os.path.join(inDir,inFileName)
      outShapeFileName = os.path.join(outDir,outShapeFileName)

      Log.info("Using input    : %s" % inFileName)
      Log.info("Creating output: %s" % outShapeFileName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Create output vector.
      outVector = Vector()
      outVector.create(outShapeFileName,ogr.wkbPoint)
     
      # Set default 'virtual' fieldnames.
      fieldNames = ["GRAND_ID","RES_NAME","DAM_NAME","ALT_NAME","RIVER",
                    "ALT_RIVER","MAIN_BASIN","SUB_BASIN","NEAR_CITY","ALT_CITY",
                    "ADMIN_UNIT","SEC_ADMIN","COUNTRY","SEC_CNTRY","YEAR",
                    "ALT_YEAR","DAM_HGT_M","ALT_HGT_M","DAM_LEN_M","ALT_LEN_M",
                    "AREA_SKM","AREA_POLY","AREA_REP","AREA_MAX","AREA_MIN",
                    "CAP_MCM","CAP_MAX","CAP_REP","CAP_MIN","DEPTH_M",
                    "DIS_AVG_LS","DOR_PC","ELEV_MASL","area","CATCH_REP",
                    "DATA_INFO","USE_IRRI","USE_ELEC","USE_SUPP","USE_FCON",
                    "USE_RECR","USE_NAVI","USE_FISH","USE_PCON","USE_LIVE",
                    "USE_OTHR","MAIN_USE","LAKE_CTRL","MULTI_DAMS",
                    "TIMELINE","COMMENTS","URL","QUALITY","EDITOR",
                    "long","lat","new_lon","new_lat",
                    "new_area","area_diff_perc","quality"]
    
      skippedCnt = 0
      # 20201202
      #with open(inFileName,"rb") as f:
      with open(inFileName,newline="") as f:
        dialect = csv.Sniffer().sniff(f.read(1024),delimiters=",")
        f.seek(0)
        reader = csv.DictReader(f,fieldNames,dialect=dialect)
        # 20201118
        #fieldNames = reader.next()
        fieldNames = next(reader)
        for row in reader:
          # Get id and coords.
          lon = row["new_lon"]
          lat = row["new_lat"]
          # No valid coords?
          if (lon == "NA") or (lat == "NA"):
            # Skip.
            skippedCnt += 1
          else:
            # Add dam.
            outVector.addPoint(lon,lat)

      # Are there skipped dams.
      if skippedCnt > 0:
        Log.info("Skipped dams: %s" % skippedCnt)

      Log.info("Writing dams shapefile...")

      outVector.write()

      Log.info("")

    self.showEndMsg()

  #-----------------------------------------------------------------------------
  # Checks the extent and cellsize.
  def copyFlowDirection_20181220(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    #Log.info("Running: convertGridToTif_20161202")
    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # Convert settings.
    extentName = "wrld"
    cellSizeName = "30sec"
    
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    rasters = [("flowdirection",
                r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\Flowdirection",
                "dir30sec_d8taudem.tif",
                "river_flowdirection.tif")]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      name = raster[0]
      inDir = raster[1]
      inRasterName = raster[2]
      outRasterName = raster[3]

      Log.info("Converting '%s'..." % name)

      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inRasterName = os.path.join(inDir,inRasterName)
      outRasterName = os.path.join(outDir,outRasterName)

      Log.info("Using input    : %s" % inRasterName)
      Log.info("Creating output: %s" % outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      rasInfo = RU.rasterGetInfo(inRasterName)
      rasInfo.show("Input:")

      # Reads the raster and resizes to extent and resamples to cellsize.
      outRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,name)

      Log.info("writing output raster...")

      outRaster.writeAs(outRasterName)

      rasInfo = RU.rasterGetInfo(outRasterName)
      rasInfo.show("Output:")

      Log.info("")

    self.showEndMsg()

  #-----------------------------------------------------------------------------
  # Checks the extent and cellsize.
  def copyNConc_PConc_WaterTemp_20181220(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # Convert settings.
    extentName = "wrld"
    cellSizeName = "30min"
    
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    rasters = [("nconc_2015",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "nconc_2015.tif",
                "nconc_2015.tif"),
               ("nconc_2050",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "nconc_2050.tif",
                "nconc_2050.tif"),
               ("pconc_2015",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "pconc_2015.tif",
                "pconc_2015.tif"),
               ("pconc_2050",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "pconc_2050.tif",
                "pconc_2050.tif"),
               ("AvgTemp_2015",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "AvgTemp_2015.tif",
                "avgtemp_2015.tif"),
               ("AvgTemp_2050",
                r"G:\data\Globio4LA\data\pbl_20181023\Johan",
                "AvgTemp_2050.tif",
                "avgtemp_2050.tif")
    ]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30min_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      name = raster[0]
      inDir = raster[1]
      inRasterName = raster[2]
      outRasterName = raster[3]

      Log.info("Converting '%s'..." % name)

      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)
              
      inRasterName = os.path.join(inDir,inRasterName)
      outRasterName = os.path.join(outDir,outRasterName)

      Log.info("Using input    : %s" % inRasterName)
      Log.info("Creating output: %s" % outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      rasInfo = RU.rasterGetInfo(inRasterName)
      rasInfo.show("Input:")

      # Reads the raster and resizes to extent and resamples to cellsize.
      outRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,name)

      Log.info("writing output raster...")

      outRaster.writeAs(outRasterName)
      outRaster.close()
      outRaster = None

      rasInfo = RU.rasterGetInfo(outRasterName)
      rasInfo.show("Output:")
      
      raster = Raster(outRasterName)
      raster.read()
      minValue = raster.min()
      maxValue = raster.max()
      Log.info("  Minimum: %s" % minValue) 
      Log.info("  Maximum: %s" % maxValue) 
      raster.close()
      raster = None

    self.showEndMsg()

  #-----------------------------------------------------------------------------
  # Creates dummy rasters.
  def createDummyMonthDischarge_20181220(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # Convert settings.
    extentName = "wrld"
    cellSizeName = "30sec"
    
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    # RasterName,Value
    rasters = [("dummy_streamflow_scen_1.tif",
                1.1),
                ("dummy_streamflow_scen_2.tif",
                1.2),               
                ("dummy_streamflow_ref_1.tif",
                1.0),
                ("dummy_streamflow_ref_2.tif",
                1.1),               
                ("dummy_streamflow_ref_mean_1.tif",
                0.8),
                ("dummy_streamflow_ref_mean_2.tif",
                0.9)               
    ]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      outRasterName = raster[0]
      value = raster[1]

      Log.info("Creating '%s'..." % outRasterName)

      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)
              
      outRasterName = os.path.join(outDir,outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Reads the raster and resizes to extent and resamples to cellsize.
      outRaster = Raster(outRasterName)
      noDataValue = -999.0
      outRaster.initRaster(extent,cellSize,np.float32,noDataValue,value)

      Log.info("writing output raster...")

      outRaster.write()
      outRaster.close()
      outRaster = None

    self.showEndMsg()

  #-----------------------------------------------------------------------------
  # Creates dummy rasters.
  def createDummyMonthWatertemperature_20181220(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # Convert settings.
    extentName = "wrld"
    cellSizeName = "30sec"
    
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    # RasterName,Value
    rasters = [("dummy_watertemperature_1.tif",
                16.5),
               ("dummy_watertemperature_2.tif",
                17.1)
    ]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      outRasterName = raster[0]
      value = raster[1]

      Log.info("Creating '%s'..." % outRasterName)

      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)
              
      outRasterName = os.path.join(outDir,outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Reads the raster and resizes to extent and resamples to cellsize.
      outRaster = Raster(outRasterName)
      noDataValue = -999.0
      outRaster.initRaster(extent,cellSize,np.float32,noDataValue,value)

      Log.info("writing output raster...")

      outRaster.write()
      outRaster.close()
      outRaster = None

    self.showEndMsg()

  #-----------------------------------------------------------------------------
  # Creates dummy rasters.
  def createDummyFragmentation_20181220(self,*args):

    self.showHeaderMsg()
    self.showStartMsg(args)

    Log.info("")
    Log.info("Running: " + UT.getMethodName())
    Log.info("")

    # Convert settings.
    extentName = "wrld"
    cellSizeName = "30sec"
    
    extent = GLOB.constants[extentName].value
    cellSize = GLOB.constants[cellSizeName].value

    # RasterName,Value
    rasters = [
               ("dummy_frag_downstream_distance.tif",
                2.0),
               ("dummy_frag_upstream_distance.tif",
                2.0),
               ("dummy_frag_fragment_length.tif",
                2.0),
               ("dummy_frag_rci.tif",
                0.9)
    ]

    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    
    # Set members.
    self.outDir = outDir

    # Enable logging to a file.
    self.enableLogToFile(self.outDir)
    
    for raster in rasters:
      outRasterName = raster[0]
      value = raster[1]

      Log.info("Creating '%s'..." % outRasterName)

      if not outRasterName.endswith(".tif"):
        outRasterName += ".tif"

      if os.path.isdir("/root"):
        outDir = UT.toLinux(outDir)
              
      outRasterName = os.path.join(outDir,outRasterName)

      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Reads the raster and resizes to extent and resamples to cellsize.
      outRaster = Raster(outRasterName)
      noDataValue = -999.0
      outRaster.initRaster(extent,cellSize,np.float32,noDataValue,value)

      Log.info("writing output raster...")

      outRaster.write()
      outRaster.close()
      outRaster = None

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.SHOW_TRACEBACK_ERRORS = True
  
    pCalc = GLOBIO_AquaticConvert()
    #pCalc.lakesVectorToRaster_20181029()
    #pCalc.showRasterInfo_20181029()
    #pCalc.convertGLWDToTif_20181029()   # Met compress etc.
    #pCalc.convertNetCDFToTif_20181029()  # Test 5min
    #pCalc.riverVectorToRaster_20181107()
    #pCalc.createFishNets_20181108()
    #pCalc.extentCatchments_20181115()
    #pCalc.createWaterTemperatureMonths_20181119()
    #pCalc.createFractions_20181119()
    #pCalc.convertFLO1KToTif_20181119()
    #pCalc.convertPCRGLOBWBToTif_20181128()
    #pCalc.convertCatchments_20181128()
    #pCalc.convertDams_20181129()
    #pCalc.copyFlowDirection_20181220()
    #pCalc.copyNConc_PConc_WaterTemp_20181220()
    #pCalc.createDummyMonthDischarge_20181220()
    #pCalc.createDummyMonthWatertemperature_20181220()
    pCalc.createDummyFragmentation_20181220()
  except:
    print("----error---")
    Log.err()
  
  
