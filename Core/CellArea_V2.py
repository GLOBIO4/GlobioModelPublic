# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# This version uses a new algorithm to calculate the geodetic area.
#
# The results are more accurate, but run much slower (50x to 100x!!) than
# the first version.
#
# Modified: 22 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - Module created.
#           17 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - createCellAreaList modified, trunc added to avoid NaN values.
#-------------------------------------------------------------------------------

import numpy as np

import GlobioModel.Common.Utils as UT

import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
# Creates a raster column (WGS84) with per cell the area in km2.
# Because of broadcasting a complete raster is not needed.
# The raster column is a 2d raster/array with dimension (1,nrRows).
# DataType is numpy data type (default float32).
def createCellAreaColumn(extent,cellSize,dataType=None):

  # Check datatype.
  if dataType is None:
    dataType = np.float32

  # Calculate number of cols/rows.
  _,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
  # Create a list of cell areas in km2.
  lst = createCellAreaList(extent,cellSize,nrRows,dataType)
  
  # Fill raster with 1 column.
  column = np.repeat(lst,1).reshape(nrRows,1)         

  return column

#-------------------------------------------------------------------------------
# Creates a list of cell areas in km2 (WGS84).
# DataType is numpy data type (default float32).
def createCellAreaList(extent,cellSize,nrRows,dataType=None):

  # Check datatype.
  if dataType is None:
    dataType = np.float32
      
  # Create a list with the area in km2 of all cells in a column.
  lon1 = 0.0
  lon2 = cellSize
  lat2 = extent[3]
  lat1 = lat2 - cellSize
  lst = []
  # Trunc lon.
  tlon1 = UT.trunc(lon1,9)
  tlon2 = UT.trunc(lon2,9)
  # Loop rows.
  for _ in range(nrRows):
    # Trunc lat.
    tlat1 = UT.trunc(lat1,9)
    tlat2 = UT.trunc(lat2,9)
    # Use trunced coords to avoid NaN at the poles.
    lst.append(dataType(RU.degreeToKM2([(tlon1,tlat1),(tlon1,tlat2),
                                        (tlon2,tlat2),(tlon2,tlat1)])))
    lat1 -= cellSize
    lat2 -= cellSize

  return lst

#-------------------------------------------------------------------------------
# Creates a list of cell area ratio.
# DataType is numpy data type (default float32).
def createCellAreaRatioList(extent,cellSize,nrRows,dataType=None):

  # Check datatype.
  if dataType is None:
    dataType = np.float32
      
  # Calculate half cellsize.
  halfCellSize = cellSize / 2.0

  # Calculate the vertical cellsize in km.
  # The vertical cellsize doesn't vary on the vertical axis.
  lon1 = 0.0
  lat1 = halfCellSize
  lon2 = lon1 + cellSize
  lat2 = halfCellSize
  sizeVertical = RU.degreeToKM_v2(lon1,lat1,lon2,lat2)

  # Create a list of all cells in a column.
  lon1 = 0.0
  lon2 = lon1 + cellSize
  lat = extent[3] - halfCellSize
  lst = []
  for _ in range(nrRows):
    # Calculate horizontal size.
    sizeHorizontal = RU.degreeToKM_v2(lon1,lat,lon2,lat)
    # Calculate ratio.
    ratio = (sizeHorizontal / sizeVertical)
    lst.append(dataType(ratio))
    lat -= cellSize

  return lst

#-------------------------------------------------------------------------------
# Creates a raster (WGS84) with per cell the area in km2.
# The raster is a 2d array with dimension (nrCols,nrRows).
# DataType is numpy data type (default float32).
#
# Caution: When calculating the sum of areas always use
#   np.sum(ras,dtype=np.float64) to prevent overflow.
#
# Use Raster.initRasterCellAreas() to create a Raster() object.
#
def createCellAreaRaster(extent,cellSize,dataType=None):

  # Check datatype.
  if dataType is None:
    dataType = np.float32

  # Calculate number of cols/rows.
  nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
  # Create a list of cell areas in km2.
  lst = createCellAreaList(extent,cellSize,nrRows,dataType)
  
  # Fill raster with repeated columns.
  ras = np.repeat(lst,nrCols).reshape(nrRows,nrCols)         

  return ras

#-------------------------------------------------------------------------------
# Creates a raster (WGS84) with per cell the area ratio.
#
# The mean area factor can be used to correct a wgs84 area without
# calculating the real geodetic area.
# To correct for disturbances at high/low lattitude the area ratio is
# calculated as the ratio of horizontal width / vertical hight.
#
# The raster is a 2d array with dimension (nrCols,nrRows).
# DataType is numpy data type (default float32).
def createCellAreaRatioRaster(extent,cellSize,dataType=None):

  # Check datatype.
  if dataType is None:
    dataType = np.float32

  # Calculate number of cols/rows.
  nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
  # Create a list of cell ratio's.
  lst = createCellAreaRatioList(extent,cellSize,nrRows,dataType)
  
  # Fill raster with repeated columns.
  ras = np.repeat(lst,nrCols).reshape(nrRows,nrCols)         

  return ras

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-----------------------------------------------------------------------------
  def test():
    import GlobioModel.Common.Utils as UT

    print("-OLD------------------")

    import GlobioModel.Core.CellArea as CA
    
    cellSize = 1.0
    extent = [-180.0,-90.0,180.0,90.0] 
    _,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    a = CA.createCellAreaList(extent,cellSize,nrRows)
    a = np.array(a)
    print(a)
    tot = np.sum(a)
    print("Total: %.8f " % tot)

    print("-NEW------------------")
    
    cellSize = 1.0
    extent = [-180.0,-90.0,180.0,90.0] 
    _,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    a = createCellAreaList(extent,cellSize,nrRows)
    a = np.array(a)
    #UT.printArray("",a)
    print(a)
    tot = np.sum(a)
    print("Total: %.8f " % tot)
    
  #-----------------------------------------------------------------------------
  # QGIS area: 83.060 km2
  def test_nl():
    import GlobioModel.Common.Utils as UT

    print("-NL------------------")
    tot = 83060
    print("Total: %.8f " % tot)

    print("-OLD------------------")

    import GlobioModel.Core.CellArea as CA
    
    #cellSize = 1.0
    cellSize =  0.00833333333333   # 30sec
    extent = [-3.326,50.739,7.247,53.524] 
    
    _,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    a = CA.createCellAreaList(extent,cellSize,nrRows)
    a = np.array(a)
    #print a
    tot = np.sum(a)
    print("Total: %.8f " % tot)

    print("-NEW------------------")
    
    _,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    a = createCellAreaList(extent,cellSize,nrRows)
    a = np.array(a)
    #UT.printArray("",a)
    #print a
    tot = np.sum(a)
    print("Total: %.8f " % tot)
    
    
  #-----------------------------------------------------------------------------
  #-----------------------------------------------------------------------------
  #test()
  test_nl()
