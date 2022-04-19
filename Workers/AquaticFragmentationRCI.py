# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
#
#  RCI = sum(Li**2 / L**2) * 100
#  
#  Where Li is the length of the river segment i and L is the total length
#  of the river network in the catchment.
# 
#  When RCI = 100 there is no fragmentation.
#
# Modified: 24 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           19 dec 2018, ES, ARIS B.V.
#           - run aangepast ivm. VU.shpPolygonFromBounds.
#           11 feb 2019, ES, ARIS B.V.
#           - speedups.enable() added.
#           - box() replaced with Polygon().
#           - No use of getLock().
#           - calculate_length added.
#           - calculate_rasterize added.
#           25 feb 2019, ES, ARIS B.V.
#           - calculate modified, now using np.float32 to prevent bad
#             allocation error.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#           8 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - Use of sharedDataSH etc. added.
#-------------------------------------------------------------------------------

import multiprocessing as mp
import numpy as np

from shapely import speedups
from shapely.geometry import Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Core.VectorUtils as VU
#from GlobioModel.Core.WorkerBase import SharedRaster
from GlobioModel.Core.WorkerBase import RasterSH
from GlobioModel.Core.WorkerBase import SharedData
from GlobioModel.Core.WorkerBase import WorkerBase
from GlobioModel.Core.WorkerBase import WorkerProgress

# Enable shapely speedup.
speedups.enable()

# Shared data for multiprocessing.
# TODO: Initialize with None???
sharedDataSH: SharedData

# # Multiprocessing shared raster.
# catchRasterSH = None
#
# # Multiprocessing shared dict.
# catchRCIDictSH = None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Fragment(object):
  fragId = None
  line = None
  lengthKM = None
  #-------------------------------------------------------------------------------
  def __init__(self,fragmentLine):
    self.fragId = fragmentLine.fragId
    self.line = fragmentLine
    self.lengthKM = fragmentLine.lengthKM

#-------------------------------------------------------------------------------
# Helper function.
# Creates a global variable to share data between pool subprocesses.
def initPool(sharedData):
  global sharedDataSH
  sharedDataSH = sharedData

#-------------------------------------------------------------------------------
# Helper function.
def calculate_length(arg,**kwarg):
  return AquaticFragmentationRCI.calculate_length(*arg,**kwarg)    

#-------------------------------------------------------------------------------
# Helper function.
def calculate_rasterize(arg,**kwarg):
  return AquaticFragmentationRCI.calculate_rasterize(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticFragmentationRCI(WorkerBase):
  """
  Calculates the River Connectivity Index (RCI) as an indicator for river fragmentation.
  """

  #-----------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticFragmentationRCI,self).__init__(nrOfCores)

  #-----------------------------------------------------------------------------
  # Calculates the length per fragId and catchment using geodetic lengths.
  # Collects the total geodetic length fragId/catchment and per catchment.
  def calculate_length(self,args):
    # 20201208
    #global catchRasterSH
    global sharedDataSH

    # Get arguments.
    lock = args[0]
    coreId = args[1]
    cellSize = args[2]
    fragmentObjects = args[3]

    #self.dbgPrint("  %s - calculate_rci" % (coreId))
    #self.dbgPrint("  %s - Nr. of fragmentObjects: %s" % (coreId,len(fragmentObjects)))

    #---------------------------------------------------------------------------
    # Get nrCols/nrRows from catchment raster.
    #---------------------------------------------------------------------------

    # 20201208
    # Get shared raster.
    catchRaster = sharedDataSH.catchRaster

    # 20201208
    # # Get nrCols and nrRows.
    # nrCols = catchRasterSH.nrCols
    # nrRows = catchRasterSH.nrRows

    # 20201208
    # Get nrCols and nrRows from shared raster.
    nrCols = catchRaster.nrCols
    nrRows = catchRaster.nrRows

    #---------------------------------------------------------------------------
    # Collect geodetic lengths per fragId and catchment.
    #---------------------------------------------------------------------------

    # Create dict for lists of lengths.
    catchLengthDict = dict()
    fragCatchLengthDict = dict()

    # Create a small offset for the cell origin.
    d = cellSize / 10.0

    #self.dbgPrint("  Calculating lengths...")

    # Init progress.
    if self.showProgress:
      wp = WorkerProgress(lock,coreId,len(fragmentObjects),resolution=1)
    
    # Loop fragments.
    for fragmentObject in fragmentObjects:

      # Show progress.
      if self.showProgress:
        wp.progress()
      
      # Get fragment properties.
      fragmentLine = fragmentObject.line
      fragId = fragmentObject.fragId
      
      #self.dbgPrint("  %s - Processing fragId: %s %s" % (coreId,fragId))
      
      # Get prepared fragment line.
      prepFragmentLine = prep(fragmentLine)
      
      # Calculate coordinates of origin and the number of cols and rows of 
      # the fragment line boundingbox.
      minx,miny,cols,rows = VU.shpLineCalcOriginNrColsRows(fragmentLine,cellSize)
      
      # Create a grid fishnet over the fragments and calculate length per cell.
      y1 = miny
      y2 = y1 + cellSize
      # Loop rows.
      for _ in range(rows):
        x1 = minx
        x2 = x1 + cellSize
        # Loop cols.
        for _ in range(cols):

          # Create the cell polygon.
          cell = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)])

          # Does fragment line intersects cell?
          if prepFragmentLine.intersects(cell):
          
            # Get col/row of the catchment cell.
            # 20201208
            # catchCol,catchRow = RU.calcColRowFromXY(x1+d,y1+d,
            #                                         catchRasterSH.extent,
            #                                         catchRasterSH.cellSize)
            catchCol,catchRow = RU.calcColRowFromXY(x1+d,y1+d,
                                                    catchRaster.extent,
                                                    catchRaster.cellSize)

            # Inside the catchment extent?
            if (catchCol>=0) and (catchRow>=0) and \
               (catchCol<nrCols) and (catchRow<nrRows):

              # 20201208
              # Get catchment id from catchment raster.
              # catchId = catchRasterSH.r[catchRow,catchCol]
              catchId = catchRaster.r[catchRow,catchCol]

              # No nodata?
              # 20201118
              #if catchId <> catchRasterSH.noDataValue:
              # 20201208
              # if catchId != catchRasterSH.noDataValue:
              if catchId != catchRaster.noDataValue:

                # Get fragment intersections with the cell.
                intersections = fragmentLine.intersection(cell)
                if intersections.is_empty:
                  # Set length.
                  lengthKM = 0.0
                else:
                  # Calculate geodetic length.
                  lengthKM = 0.0
                  intersections = VU.shpMultiLineToLines(intersections)
                  for intersection in intersections:
                    lengthKM += VU.shpCalcGeodeticLineLengthKM(intersection)
                  
                # Add length to catch dict.
                try:
                  catchLengthDict[catchId]+=lengthKM
                except KeyError:
                  catchLengthDict[catchId]=lengthKM

                # Add length to frag/catch dict.
                try:
                  fragCatchLengthDict[(fragId,catchId)]+=lengthKM
                except KeyError:
                  fragCatchLengthDict[(fragId,catchId)]=lengthKM                  

          # Set next column.
          x1 += cellSize
          x2 += cellSize
          
        # Set next row.
        y1 += cellSize
        y2 += cellSize
   
    return (catchLengthDict,fragCatchLengthDict)

  #-----------------------------------------------------------------------------
  def calculate_rasterize(self,args):            
    # 20201208
    #global catchRasterSH,catchRCIDictSH
    global sharedDataSH

    # Get arguments.
    lock = args[0]
    coreId = args[1]
    extent = args[2]             # i.e. workextent 
    cellSize = args[3]
    fragmentObjects = args[4]    # i.e. fragmentObjects in workextent

    # 20201208
    # Get shared raster and dict.
    catchRaster = sharedDataSH.catchRaster
    catchRCIDict = sharedDataSH.catchRCIDict

    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)

    # Create a small offset for the cell origin.
    d = cellSize / 10.0

    # Create an array for the output RCI.
    ras = np.zeros((nrRows,nrCols),np.float32)

    # Init progress.
    if self.showProgress:
      wp = WorkerProgress(lock,coreId,len(fragmentObjects),resolution=1)

    # Loop fragments.
    for fragmentObject in fragmentObjects:
      
      # Show progress.
      if self.showProgress:
        wp.progress()

      # Get fragment properties.
      fragmentLine = fragmentObject.line
      
      # Get prepared fragment line.
      prepFragmentLine = prep(fragmentLine)
      
      # Calculate coordinates of origin and the number of cols and rows of 
      # the fragment line boundingbox.
      minx,miny,cols,rows = VU.shpLineCalcOriginNrColsRows(fragmentLine,cellSize)
      
      # Create a grid fishnet over the fragments and calculate length per cell.
      y1 = miny
      y2 = y1 + cellSize
      # Loop rows.
      for _ in range(rows):
        x1 = minx
        x2 = x1 + cellSize
        # Loop cols.
        for _ in range(cols):
          
          # Get col/row of the cell in work raster.
          col,row = RU.calcColRowFromXY(x1+d,y1+d,extent,cellSize)
          
          # Inside the working extent?
          if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
            
            # Create the cell polygon.
            cell = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)])
            
            # Does fragment line intersects cell?
            if prepFragmentLine.intersects(cell):
            
              # Get catchment id from shared raster.
              # 20201208
              # catchCol,catchRow = RU.calcColRowFromXY(x1+d,y1+d,
              #                                         catchRasterSH.extent,
              #                                         catchRasterSH.cellSize)
              catchCol,catchRow = RU.calcColRowFromXY(x1+d,y1+d,
                                                      catchRaster.extent,
                                                      catchRaster.cellSize)
              # 20201208
              #catchId = catchRasterSH.r[catchRow,catchCol]
              catchId = catchRaster.r[catchRow,catchCol]

              # No nodata?
              # 20201118
              #if catchId <> catchRasterSH.noDataValue:
              # 20201208
              # if catchId != catchRasterSH.noDataValue:
              if catchId != catchRaster.noDataValue:
                # Set raster rci value.
                # 20201208
                #ras[row,col] = catchRCIDictSH[(catchId)]
                ras[row,col] = catchRCIDict[(catchId)]

          # Set next column.
          x1 += cellSize
          x2 += cellSize
        # Set next row.
        y1 += cellSize
        y2 += cellSize

    return (ras,)

  #-----------------------------------------------------------------------------
  # nrOfChunks: number of parts in with the data is devided.
  #             If 0 then nrOfChunks is the same as the nrOfCores.
  # Arguments:
  #   fragmentLines: multilines with fragId,lengthKM.
  #   catchRasters: Raster object with catchments.
  #
  # Returns: outRaster
  #
  def run(self,extent,cellSize,fragmentLines,catchRaster,nrOfChunks=0):
    # 20201208
    #global catchRasterSH,catchRCIDictSH
    global sharedDataSH
    pool = None
    try:
    
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores

      #-------------------------------------------------------------------------
      # Prepare calculating RCI.
      #-------------------------------------------------------------------------

      Log.info("  Preparing calculation of RCI...")

      # Create shared raster.
      # 20201208
      #catchRasterSH = SharedRaster(catchRaster)
      sharedData = SharedData()
      sharedData.catchRaster = RasterSH(catchRaster)

      # Create tree and get fragment lines within extent.
      fragmentLinesTree = STRtree(fragmentLines)
      fragmentLines = fragmentLinesTree.query(VU.shpPolygonFromBounds(extent))
      
      # Convert the fragment lines to Fragment objects.
      fragmentObjects = []
      for fragmentLine in fragmentLines:
        fragmentObjects.append(Fragment(fragmentLine))
        
      # Split the list of fragment objects in work sets.
      workFragmentObjects = self.getWorkFragmentSubLists(fragmentObjects,nrOfChunks)

      # Create the input list with tuples of (coreId,cellSize,fragmentObjects).
      args = []
      for i in range(len(workFragmentObjects)):
        args.append([None,i,cellSize,workFragmentObjects[i]])

      #-------------------------------------------------------------------------
      # Calculate fragment length and total fragment length.
      #-------------------------------------------------------------------------
      
      Log.info("  Calculating fragment length...")

      # Use multiprocessing.
      useMultiprocessing = True
      if useMultiprocessing:
        # Create the pool.
        # 20201208
        # pool = mp.Pool(processes=self.nrOfCores)
        pool = mp.Pool(processes=self.nrOfCores,
                       initializer=initPool, initargs=(sharedData,))
        results = pool.map(calculate_length,zip([self]*len(args),args))
        
        #-------------------------------------------------------------------------
        # Process fragment length results. 
        #-------------------------------------------------------------------------

        # The results are a list of (catchLengthDict,fragCatchLengthDict)
        # tuples. Get the separate results.
        catchLengthDict = [r[0] for r in results]
        fragCatchLengthDict = [r[1] for r in results]

        # Combine dict chunks. Catchments lengths can be calculated
        # by different processes, so sum lengths.
        catchTotLengthDict = self.joinDictChunksSum(catchLengthDict)

        # Combine dict chunks.Fragment/catchments lengths are 
        # calculated by one process, so no summing is needed.
        fragCatchLengthDict = self.joinDictChunksSum(fragCatchLengthDict)
        
      else:
        # Don't use multiprocessing.
        results = self.calculate_length([None,0,cellSize,fragmentObjects])
        catchTotLengthDict = results[0]
        fragCatchLengthDict =  results[1]
        
      Log.info("  Catchments total lengths found: %s" % len(catchTotLengthDict))
      Log.info("  Fragment/catchments lengths found: %s" % len(fragCatchLengthDict))

      #-------------------------------------------------------------------------
      # Calculate RCI per catchment.
      #
      # Per catchment:
      #   RCI = ( sum( sqr(fragm length) / sqr(catchm length) ) ) * 100 
      #-------------------------------------------------------------------------

      Log.info("Calculating RCI...")

      Log.info("  Calculating square total length...")

      # Square the catchment total lengths.
      # 20201204
      #catchSqrLengthDict = {key: length*length for key,length in catchTotLengthDict.iteritems()}
      catchSqrLengthDict = {key: length*length for key,length in catchTotLengthDict.items()}

      # Create sum dict.
      catchSumDict = dict()

      Log.info("  Calculating fragment/catchment sum...")

      # Loop fragment/catchment length dict.
      # 20201204
      #for fragCatchKey,lengthKM in fragCatchLengthDict.iteritems():
      for fragCatchKey,lengthKM in fragCatchLengthDict.items():
        # Sum sqr(fragm length) / sqr(catchm length)
        catchId = (fragCatchKey[1])
        try:
          catchSumDict[catchId]+=lengthKM * lengthKM / float(catchSqrLengthDict[catchId])
        except KeyError:
          catchSumDict[catchId]=lengthKM * lengthKM / float(catchSqrLengthDict[catchId])

      Log.info("  Calculating final rci...")

      # Calculate RCI and set shared dict.
      # 20201118
      #catchRCIDictSH = {key: length * 100 for key,length in catchSumDict.iteritems()}
      # 20201208
      #catchRCIDictSH = {key: length * 100 for key,length in catchSumDict.items()}
      # TODO: Is dit nodig? Is al een keer gemaakt. DENK HET WEL!
      sharedData = SharedData()
      sharedData.catchRaster = RasterSH(catchRaster)
      sharedData.catchRCIDict = {key: length * 100 for key,length in catchSumDict.items()}

      #-------------------------------------------------------------------------
      # Prepare rasterizing RCI.
      #-------------------------------------------------------------------------
      
      Log.info("  Preparing rasterization of RCI...")
      
      # Create list of work extents.
      workExtents = self.getWorkExtents(extent,cellSize,nrOfChunks)

      # Create tree and get fragment lines within working extents.
      fragmentLinesTree = STRtree(fragmentLines)

      # Loop workExtents.
      workFragmentObjectsList = []
      for workExtent in workExtents:
        # Get fragment lines. 
        workFragmentLines = fragmentLinesTree.query(VU.shpPolygonFromBounds(workExtent))
        # Convert to fragment objects.
        fragmentObjs = []
        for fragLine in workFragmentLines:
          fragmentObjs.append(Fragment(fragLine))
        workFragmentObjectsList.append(fragmentObjs)

      # Create the input list with tuples of (coreId,extent,cellSize,fragments).
      args = []
      for i in range(len(workExtents)):
        args.append([None,i,workExtents[i],cellSize,workFragmentObjectsList[i]])
 
      #-------------------------------------------------------------------------
      # Rasterize RCI.
      #-------------------------------------------------------------------------
      
      Log.info("  Rasterizing RCI...")

      # 20201208
      # Create the pool.
      #pool = mp.Pool(processes=self.nrOfCores)
      # TODO: Is dit nodig? Is al een keer gemaakt. DENK HET WEL!
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate_rasterize,zip([self]*len(args),args))
 
      #-------------------------------------------------------------------------
      # Process rasterize results. 
      #-------------------------------------------------------------------------
 
      # The results are a list of (rasterChunks) tuples. Get separate results.
      rasterChunks = [r[0] for r in results]
 
      # Combine raster chunks.
      ras = self.joinRasterChunks(extent,cellSize,rasterChunks,True)

      #-------------------------------------------------------------------------
      # Create fragment length raster. 
      #-------------------------------------------------------------------------
        
      Log.info("  Creating fragmention RCI raster...")
    
      # Create raster.
      outRaster = Raster()
      outRaster.initRasterEmpty(extent,cellSize,np.float32)
      outRaster.r = ras

      # Setting nodata.
      mask = (outRaster.r <= 0.0)
      outRaster.r[mask] = outRaster.noDataValue

      return outRaster

    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        #pool = None
        del pool
      return None
