# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 1 dec 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - esriGridToTif, now with compression.
#           7 dec 2016, ES, ARIS B.V.
#           - Version 4.0.3
#           - esriGridToTif, now with cellSize.
#           15 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - normalize added.
#           22 jun 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - vectorToRaster modified.
#           29 oct 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - netCDFToTif added.
#-------------------------------------------------------------------------------

import os

import osgeo.gdal as gd

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
def esriGridToTif(esriGridName,tifFileName,dataType,noDataValue=None,
                  cellSize=None,checkAlignExtent=False,Compress=False):

  if not RU.rasterExists(esriGridName):
    Err.raiseGlobioError(Err.RasterNotFound1,esriGridName)

  if RU.rasterExists(tifFileName):
    RU.rasterDelete(tifFileName)

  # Read the esri grid.
  Log.info("Reading esri grid: "+esriGridName)
  inRaster = Raster(esriGridName)
  inRaster.read()

  # Show grid info.
  Log.info("Input:")
  Log.info("  CellSize: %s" % inRaster.cellSize)
  Log.info("  Extent: %s %s %s %s" % (inRaster.extent[0],inRaster.extent[1],inRaster.extent[2],inRaster.extent[3]))
  Log.info("  NrCols/NrRows: %s %s" % (inRaster.nrCols,inRaster.nrRows))
  Log.info("  NoDataValue: %s" % RU.rasterValueToString(inRaster.noDataValue,inRaster.dataType,3))
  Log.info("  DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))
  Log.info("  Min: %s" % inRaster.min())
  Log.info("  Max: %s" % inRaster.max())
  
  if checkAlignExtent:
    # Check extent alignment.
    if not RU.isExtentAligned(inRaster.extent,inRaster.cellSize):
      inRaster.extent = RU.alignExtent(inRaster.extent,inRaster.cellSize)
      Log.info("Aligning extent to: %s" % inRaster.extent)

  if not cellSize is None:
    Log.info("Using cellsize: %s" % cellSize)
    
  # Convert the data.
  outRaster = inRaster.convert(dataType,noDataValue)

  # Close and free the esri grid.
  inRaster.close()
  inRaster = None

  # Write the tif.
  Log.info("Writing tif: "+tifFileName)
  outRaster.writeAs(tifFileName,Compress)

  # Close and free the output.
  outRaster.close()
  outRaster = None

#-------------------------------------------------------------------------------
# BandNr is from 1 to NrOfBands.
# SubdatasetNr is from 1 to NrOfSubdatasets.
def netCDFToTif(ncFileName,tifFileName,bandNr,
                extent,cellSize,dataType,noDataValue=None,
                netCDFNoDataValue=None,subDatasetNr=None,
                flipOrigin=True,
                Compress=False):

  if not os.path.isfile(ncFileName):
    Err.raiseGlobioError(Err.RasterNotFound1,ncFileName)
 
  if RU.rasterExists(tifFileName):
    RU.rasterDelete(tifFileName)
 
  # Read the NetCDF grid.
  dataset = gd.Open(ncFileName,gd.GA_ReadOnly)

  # Do we need to read a subdataset?
  if not subDatasetNr is None:
    # Get the subdatasets.
    subDatasets = dataset.GetSubDatasets()
    # Not found.
    if subDatasets is None:
      Err.raiseGlobioError(Err.UserDefined1,"No subdatasets found.")
    # Check subdataset nr.
    if (subDatasetNr < 1) or (subDatasetNr>len(subDatasets)):      
      Err.raiseGlobioError(Err.UserDefined1,"Invalid subdataset number.")
    # Get subdataset name.
    subDatasetName = subDatasets[subDatasetNr-1][0]
    # Close current dataset.
    gd.Dataset.__swig_destroy__(dataset)
    dataset = None
    # Open the subdataset.
    dataset = gd.Open(subDatasetName,gd.GA_ReadOnly)

  inNrCols = dataset.RasterXSize
  inNrRows = dataset.RasterYSize
  nrBands = dataset.RasterCount

  # Get the output nr of columns and rows and check.     
  outNrCols,OutNrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  # 20201118
  #if (outNrCols<>inNrCols) and (OutNrRows<>inNrRows):
  if (outNrCols!=inNrCols) and (OutNrRows!=inNrRows):
    Err.raiseGlobioError(Err.UserDefined1,"Invalid extent and cellsize.")

  # Check bandnr.
  if (bandNr < 1) or (bandNr>nrBands):      
    Err.raiseGlobioError(Err.UserDefined1,"Invalid band number.")
  
  # Get band.
  band = dataset.GetRasterBand(bandNr)
  
  # Get datatype.
  inDataType = RU.dataTypeGdalToNumpy(band.DataType)
  
  # No NetCDF nodatavalue specified? 
  if netCDFNoDataValue is None:
    # Get from band.
    inNoDataValue = band.GetNoDataValue()
  else:
    # Use specified value.
    inNoDataValue = netCDFNoDataValue
     
  # Show grid info.
  Log.info("Input:")
  Log.info("  NrCols/NrRows: %s %s" % (inNrCols,inNrRows))
  Log.info("  NrBands: %s" % nrBands)
  Log.info("  DataType: %s" % RU.dataTypeNumpyToString(inDataType))
  Log.info("  NoDataValue: %s" % inNoDataValue)

  if not cellSize is None:
    Log.info("Using cellsize: %s" % cellSize)
    
  Log.info("Converting band: %s" % bandNr)

  # Create the output tif.
  outRaster = Raster(tifFileName)
  outRaster.initRasterEmpty(extent,cellSize,dataType,noDataValue)

  # Get the input data.
  inData = band.ReadAsArray().astype(dataType)
  
  # Process nodata if available.
  if not inNoDataValue is None:
    Log.info("Processing nodata...")
    delta = abs(inNoDataValue / float(1000))
    #print delta
    if inNoDataValue > 0:
      mask = (inData > (inNoDataValue-delta))
    else:
      mask = (inData < (inNoDataValue+delta))
    inData[mask] = noDataValue 

  # Close and free the NetCDF grid.
  band = None
  if not dataset is None:
    gd.Dataset.__swig_destroy__(dataset)
  dataset = None

  # Set the data.
  outRaster.r = inData

  # Flip the grid origin.
  if flipOrigin: 
    Log.info("Flipping grid origin...")
    outRaster.flip()

  # Write the tif.
  Log.info("Writing tif: "+tifFileName)
  outRaster.write()
 
  # Close and free the output.
  outRaster.close()
  outRaster = None

#-------------------------------------------------------------------------------
# Invert - inverts the values
def normalize(inRasterName,outRasterName,
              dataType=None,noDataReplaceValue=None,invert=False):

  if RU.rasterExists(outRasterName):
    RU.rasterDelete(outRasterName)

  # Read raster.
  Log.info("Reading raster: "+inRasterName)
  inRaster = Raster(inRasterName)
  inRaster.read()

  # Get min/max value.
  minValue = inRaster.min()
  maxValue = inRaster.max()

  # Show raster info.
  Log.info("Extent: %s" % inRaster.extent)
  Log.info("CellSize: %s" % inRaster.cellSize)
  Log.info("DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))
  Log.info("NoData: %s" % inRaster.noDataValue)
  Log.info("Min: %s" % minValue)
  Log.info("Max: %s" % maxValue)

  # Get datatype.
  if dataType is None:
    dataType = inRaster.dataType
    noDataValue = inRaster.noDataValue
  else:
    noDataValue = RU.getNoDataValue(dataType)
    
  # Create out raster.
  Log.info("Creating raster...")
  outRaster = Raster(outRasterName)
  outRaster.initRaster(inRaster.extent,inRaster.cellSize,dataType,noDataValue)

  # Select data cells.
  mask = inRaster.getDataMask()

  # Copy values.
  outRaster.r[mask] = inRaster.r[mask]  

  # Close and free the input raster.
  inRaster.close()
  inRaster = None
  
  # Correct the data origin.
  # 20201118
  #if minValue <> 0.0:
  if minValue != 0.0:
    outRaster.r[mask] -= minValue  

  # Recalculate max value.
  maxValue = maxValue - minValue
  
  # Normalize.
  if maxValue > 0.0:
    outRaster.r[mask] /= maxValue
  
  # Invert?
  if invert:
    # Actualy inv = 1.0 - norm
    outRaster.r[mask] *= -1.0
    outRaster.r[mask] += 1.0
    
  # Replace nodata with an other value.
  if not noDataReplaceValue is None:
    # Set replace value.
    outRaster.r[~mask] = noDataReplaceValue

  # Write the tif.
  Log.info("Writing tif: "+outRasterName)
  outRaster.write()

  # Get min/max value.
  minValue = outRaster.min()
  maxValue = outRaster.max()

  # Show raster info.
  Log.info("Extent: %s" % outRaster.extent)
  Log.info("CellSize: %s" % outRaster.cellSize)
  Log.info("DataType: %s" % RU.dataTypeNumpyToString(outRaster.dataType))
  Log.info("NoData: %s" % outRaster.noDataValue)
  Log.info("Min: %s" % minValue)
  Log.info("Max: %s" % maxValue)

  # Close and free the output.
  outRaster.close()
  outRaster = None
          
#-------------------------------------------------------------------------------
def rasterResize(inRasterName,outRasterName,toExtent,noDataValue=None):

  if RU.rasterExists(outRasterName):
    RU.rasterDelete(outRasterName)

  # Read raster.
  Log.info("Reading raster: "+inRasterName)
  inRaster = Raster(inRasterName)
  inRaster.read()

  # Show raster info.
  Log.info("Extent: %s" % inRaster.extent)
  Log.info("CellSize: %s" % inRaster.cellSize)
  Log.info("DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))
  Log.info("NoData: %s" % inRaster.noDataValue)
  Log.info("Min: %s" % inRaster.min())
  Log.info("Max: %s" % inRaster.max())

  # Check extent alignment.
  if not RU.isExtentAligned(inRaster.extent,inRaster.cellSize):
    inRaster.extent = RU.alignExtent(inRaster.extent,inRaster.cellSize)
    Log.info("Aligning extent to: %s" % inRaster.extent)

  # Convert the data.
  outRaster = inRaster.resize(toExtent,noDataValue)

  # Close and free the esri grid.
  inRaster.close()
  inRaster = None

  # Write the tif.
  Log.info("Writing tif: "+outRasterName)
  outRaster.writeAs(outRasterName,True)

  # Close and free the output.
  outRaster.close()
  outRaster = None

#-------------------------------------------------------------------------------
# Specify fieldName or value.
def vectorToRaster(shpFileName,rasterName,extent,cellSize,dataType,
                   fieldName=None,value=None,noDataValue=None,
                   quiet=True,compress=True):

  Log.info("WARNING: Obsolete, use GRASS vectorToRaster instead.")
  
  if not RU.vectorExists(shpFileName):
    Err.raiseGlobioError(Err.VectorNotFound1,shpFileName)

  if RU.rasterExists(rasterName):
    RU.rasterDelete(rasterName)

  if (fieldName is None) and (value is None):
    raise Exception("VectorToRaster - No fieldname of value specified.")
    # 20201118
    #noDataValue = RU.getNoDataValue(dataType)

  if noDataValue is None:
    noDataValue = RU.getNoDataValue(dataType)
     
  # Read vector.
  if not quiet:
    Log.info("Reading vector...")
  vector = Vector(shpFileName)
  vector.read()
  
  # Initialize raster with nodata 255.
  if not quiet:
    Log.info("Creating raster...")
  raster = Raster(rasterName)
  raster.initRaster(extent,cellSize,dataType,noDataValue)

  # Compress?
  options = []
  if compress:
    options.append("COMPRESS=LZW")

  if not quiet:
    Log.info("Converting vector to raster...")
  if not fieldName is None:
    options.append("ATTRIBUTE="+fieldName)
    gd.RasterizeLayer(raster.dataset,[1],vector.layer,options=options)
  else:
    gd.RasterizeLayer(raster.dataset,[1],vector.layer,burn_values=[value],options=options)
    
  # Close and free shapefile and raster.
  if not vector is None:
    vector.close()
    vector = None     
  if not raster is None:
    raster.close()     
    raster = None
