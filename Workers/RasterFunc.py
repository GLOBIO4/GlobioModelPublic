# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 9 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - RasterFunc.__init__ modified.
#           4 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - SharedDataSH added.
#           - initPool added.
#           - Several methods modified, because shared global vars doesn't
#             work anymore.
#-------------------------------------------------------------------------------

import numpy as np
import multiprocessing as mp

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
from GlobioModel.Core.WorkerBase import RasterSH
from GlobioModel.Core.WorkerBase import SharedData

# Shared data for multiprocessing.
# TODO: Initialize with None???
sharedDataSH: SharedData

#-------------------------------------------------------------------------------
# Helper function.
# Creates a global variable to share data between pool subprocesses.
def initPool(sharedData):
  global sharedDataSH
  sharedDataSH = sharedData

#-------------------------------------------------------------------------------
# Helper function.
def calculate_Label(arg,**kwarg):
  return RasterFunc.calculate_Label(*arg,**kwarg)    

#-------------------------------------------------------------------------------
# Helper function.
def calculate_ZonalSumArea(arg,**kwarg):
  return RasterFunc.calculate_ZonalSumArea(*arg,**kwarg)    

#-------------------------------------------------------------------------------
# Helper function.
def calculate_ZonalMean(arg,**kwarg):
  return RasterFunc.calculate_ZonalMean(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class RasterFunc(WorkerBase):
  """
  Miscellaneous multiprocessing raster functions.
  """

  # 20201207
  # func = None
  # zoneRasF = None
  # valueRasF = None
  # areaRasF = None
  # noDataValue = None

  #-------------------------------------------------------------------------------
  # nrOfCores: The number of cores to be used. 
  #  >=1 = This number of cores will be used.
  #  0   = All number of available cores will be used.
  #  <0  = All number of available cores will be used minus the specified number.
  def __init__(self,nrOfCores):
    super(RasterFunc,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  # Create a raster (chunk) by replacing the id's of the label raster with the 
  # values/labels in the labelDict.
  # When an id is not found in the labelDict the noDataValue is set.
  def calculate_Label(self,args):
    global sharedDataSH
                
    # Get arguments.
    # 20201118
    #coreId = args[0]
    offset = args[1]
    size = args[2]
    nrCols = args[3]
    dataType = args[4]
    noDataValue = args[5]
    labelDict = args[6]

    # 20201207
    # Get shared rasters.
    labelRas = sharedDataSH.labelRaster.r

    # Create a chunk raster for the label values.
    outRas = np.full((size,nrCols),noDataValue,dataType)
    
    # Loop rows and cols.
    for r in range(size):
      for c in range(nrCols):
        # Get label id in the full extent label raster.
        lid = labelRas[offset+r,c]
        # Found?
        if lid in labelDict:
          # Set label value in the chunk raster.
          outRas[r,c] = labelDict[lid]

    return (outRas,)

  #-----------------------------------------------------------------------------
  # Returns a tupe of dicts (sumDict,sumAreaDict) with the sum of 
  # values per zone and the total area per zone.
  # NoData values in the zone and value raster are skipped.
  def calculate_ZonalSumArea(self,args):
    global sharedDataSH

    # Get arguments.
    # 20201118
    #coreId = args[0]
    offset = args[1]
    size = args[2]
    nrCols = args[3]

    # 20201207
    # Get shared rasters.
    zoneRas = sharedDataSH.zoneRaster.r
    valueRas = sharedDataSH.valueRaster.r
    areaRas = sharedDataSH.areaRaster.r

    # 20201207
    # Get nodata values.
    zoneNoDataValue = sharedDataSH.zoneRaster.noDataValue
    valueNoDataValue = sharedDataSH.valueRaster.noDataValue

    # Initialize dicts.
    sumDict = dict()
    sumAreaDict = dict()
    
    # Loop rows and cols in chunks of the full extent rasters.
    for i in range(size):
      # Set chunck row.
      r = offset+i
      for c in range(nrCols):

        # Get zone id.
        zid = zoneRas[r,c]
        # Zone id is nodata?
        if zid == zoneNoDataValue:
          # Skip.
          continue

        # Get area.
        area = areaRas[r,c]
        # Get value.
        v = valueRas[r,c]
                
        # Set sum and area.
        if not zid in sumDict:
          # Value is not nodata?
          # 20201118
          #if v <> valueNoDataValue:
          if v != valueNoDataValue:
            sumDict[zid] = v
          sumAreaDict[zid] = area
        else:
          # Value is not nodata?
          # 20201118
          #if v <> valueNoDataValue:
          if v != valueNoDataValue:
            sumDict[zid] += v
          sumAreaDict[zid] += area

    return (sumDict,sumAreaDict)

  #-----------------------------------------------------------------------------
  # Returns a tupe of dicts (countDict,sumDict) with the number of 
  # values and the total sum of the values per zone.
  # NoData values in the zone and value raster are skipped.
  def calculate_ZonalMean(self,args):
    global sharedDataSH

    # Get arguments.
    # 20201118
    #coreId = args[0]
    offset = args[1]
    size = args[2]
    nrCols = args[3]

    # 20201207
    # Get shared rasters.
    zoneRas = sharedDataSH.zoneRaster.r
    valueRas = sharedDataSH.valueRaster.r

    # 20201207
    # Get nodata values.
    zoneNoDataValue = sharedDataSH.zoneRaster.noDataValue
    valueNoDataValue = sharedDataSH.valueRaster.noDataValue

    # Initialize dicts.
    countDict = dict()
    sumDict = dict()
    
    # Loop rows and cols in chunks of the full extent rasters.
    for i in range(size):
      # Set chunck row.
      r = offset+i
      for c in range(nrCols):
        # Get value.
        v = valueRas[r,c]
        # Value is nodata?
        if (v == valueNoDataValue):
          # Skip.
          continue
        # Get zone id.
        zid = zoneRas[r,c]
        # Zone id is nodata?
        if (zid == zoneNoDataValue):
          # Skip.
          continue
        # Set count and area.
        if not zid in countDict:
          countDict[zid] = 1
          sumDict[zid] = v
        else:
          countDict[zid] += 1
          sumDict[zid] += v

    return (countDict,sumDict)

  #-----------------------------------------------------------------------------
  # Labels the inRaster by replacing the id's with the values/labels in the
  # labelDict.
  # When an id is not found in the labelDict the noDataValue is set.
  def label(self,extent,cellSize,inRaster,labelDict,
            dataType,noDataValue=None,nrOfChunks=0):
    pool = None
    try:
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores

      # Check noDataValue.
      if noDataValue is None:
        noDataValue = RU.getNoDataValue(dataType)

      # Get number of cols and rows.
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
      self.dbgPrint("nrCols,nrRows: %s %s" % (nrCols,nrRows))
  
      # Split the data in chunks to be handled by the cores.
      offsets,sizes = self.getOffsetsAndSizes(nrRows,nrOfChunks)
      self.dbgPrint(offsets)
      self.dbgPrint(sizes)

      # Create the input list with tuples of (coreId,offset,size,nrCols).
      args = []
      for i in range(len(offsets)):
        args.append([i,offsets[i],sizes[i],nrCols,dataType,noDataValue,labelDict])

      ### TODO???
      ## Shared object: labelDict

      # 20201207
      # Set shared raster.
      sharedData = SharedData()
      sharedData.labelRaster = RasterSH(inRaster)

      # 20201207
      # Create the pool.
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate_Label,zip([self]*len(args),args))

      # Get the result chunks.
      rasterChunks = [r[0] for r in results]
      
      # Sum the chunk counts per zone id.
      ras = self.joinRasterChunks(extent,cellSize,rasterChunks)
      
      # Create output raster.
      outRaster = Raster()
      outRaster.initRasterEmpty(extent,cellSize,dataType,noDataValue)
      outRaster.r = ras.astype(dataType)
      
      return outRaster
    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        # noinspection PyUnusedLocal
        pool = None
      return None

  #-----------------------------------------------------------------------------
  # Returns a tupe of dicts (densDict,countDict,areaDict) with the density
  # (i.e. the number of values per area), the number of values and the areas
  # per zone.
  # NoData values in the zone and value raster are skipped.
  def zonalCountDensity(self,extent,cellSize,
                        zoneRaster,valueRaster,areaRaster,
                        nrOfChunks=0):
    pool = None
    try:
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores
      
      # Get number of cols and rows.
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
      self.dbgPrint("nrCols,nrRows: %s %s" % (nrCols,nrRows))
  
      # Split the data in chunks to be handled by the cores.
      offsets,sizes = self.getOffsetsAndSizes(nrRows,nrOfChunks)
      self.dbgPrint(offsets)
      self.dbgPrint(sizes)

      # Create the input list with tuples of (coreId,offset,size,nrCols).
      args = []
      for i in range(len(offsets)):
        args.append([i,offsets[i],sizes[i],nrCols])

      # 20201207
      # Set shared rasters.
      sharedData = SharedData()
      sharedData.zoneRaster = RasterSH(zoneRaster)
      sharedData.valueRaster = RasterSH(valueRaster)
      sharedData.areaRaster = RasterSH(areaRaster)

      # 20201207
      # Create the pool.
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate_ZonalSumArea,zip([self]*len(args),args))

      # Get the result chunks.
      sumDicts = [r[0] for r in results]
      areaDicts = [r[1] for r in results]

      # Sum the chunk sums and areas per zone id.
      sumDict = self.joinDictChunksSum(sumDicts)
      areaDict = self.joinDictChunksSum(areaDicts)
      #self.dbgPrint(sumDict)
      #self.dbgPrint(areaDict)
      
      # Copy count dict.
      densDict = dict(sumDict)
      # Calculate density (i.e. sum/area) per zone id. 
      # 20201118
      #for key,sum in sumDict.iteritems():
      # noinspection PyShadowingBuiltins
      for key,sum in sumDict.items():
        if key in areaDict:
          densDict[key] = sum / areaDict[key]

      return (densDict,sumDict,areaDict)
    
    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
      return (None,None,None)

  #-----------------------------------------------------------------------------
  # Returns a tupe of dicts (meanDict,countDict,sumDict) with the mean of 
  # the values, the number of values and the sum of the values per zone.
  # NoData values in the zone and value raster are skipped.
  def zonalMean(self,extent,cellSize,
                zoneRaster,valueRaster,
                nrOfChunks=0):
    pool = None
    try:
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores
      
      # Get number of cols and rows.
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
      self.dbgPrint("nrCols,nrRows: %s %s" % (nrCols,nrRows))
  
      # Split the data in chunks to be handled by the cores.
      offsets,sizes = self.getOffsetsAndSizes(nrRows,nrOfChunks)
      self.dbgPrint(offsets)
      self.dbgPrint(sizes)

      # Create the input list with tuples of (coreId,offset,size,nrCols).
      args = []
      for i in range(len(offsets)):
        args.append([i,offsets[i],sizes[i],nrCols])

      # 20201207
      # Set shared rasters.
      sharedData = SharedData()
      sharedData.zoneRaster = RasterSH(zoneRaster)
      sharedData.valueRaster = RasterSH(valueRaster)

      # 20201207
      # Create the pool.
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate_ZonalMean,zip([self]*len(args),args))

      # Get the result chunks.
      countDicts = [r[0] for r in results]
      sumDicts = [r[1] for r in results]

      # Sum the chunk counts and areas per zone id.
      countDict = self.joinDictChunksSum(countDicts)
      sumDict = self.joinDictChunksSum(sumDicts)
      #self.dbgPrint(countDict)
      #self.dbgPrint(sumDict)
      
      # Copy count dict.
      meanDict = dict(countDict)
      # Calculate mean (i.e. sum/cnt) per zone id. 
      # 20201118
      #for key,cnt in countDict.iteritems():
      for key,cnt in countDict.items():
        if key in sumDict:
          meanDict[key] = sumDict[key] / cnt

      return (meanDict,countDict,sumDict)
    
    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
      return (None,None,None)

