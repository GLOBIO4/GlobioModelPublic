# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 24 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           19 dec 2018, ES, ARIS B.V.
#           - run aangepast ivm. VU.shpPolygonFromBounds.
#           17 jan 2019, ES, ARIS B.V.
#           - run aangepast ivm. noDataValue = -999.0.
#           - calculate aangepast ivm. 
#              lengthDict[key] = np.mean(np.array(value,np.float16)).
#           30 jan 2019, ES, ARIS B.V.
#           - calculate aangepast, nu met col/row/fragId dict.
#           - No use of np.mean (is slow).
#           - Using (col,row) as key.
#           - Using meanDict.
#           21 feb 2019, ES, ARIS B.V.
#           - calculate modified, now using np.float32 because of bad
#             allocation.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#-------------------------------------------------------------------------------

import multiprocessing as mp
import numpy as np

from shapely.geometry import Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
from GlobioModel.Core.WorkerBase import WorkerProgress
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Fragment(object):
  rivId = None
  fragId = None
  line = None
  lengthKM = None
  #-------------------------------------------------------------------------------
  def __init__(self,rivId,fragId,line,lengthKM):
    self.rivId = rivId
    self.fragId = fragId
    self.line = line
    self.lengthKM = lengthKM

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return AquaticFragmentationFragmentLength.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticFragmentationFragmentLength(WorkerBase):
  """
  Calculates the river fragment length as an indicator for river fragmentation.
  """

  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticFragmentationFragmentLength,self).__init__(nrOfCores)
  
  #-----------------------------------------------------------------------------
  def calculate(self,args):            

    # Get arguments.
    lock = args[0]
    coreId = args[1]
    extent = args[2]
    cellSize = args[3]
    fragmentObjects = args[4]
    
    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)

    #---------------------------------------------------------------------------
    # Collect lengths per cell.
    #---------------------------------------------------------------------------

    # Create dict for lists of lengths. Needed for calculating mean length.
    lengthDict = dict()

    # Create a small offset for the cell origin.
    d = cellSize / 10.0

    #self.dbgPrint("  Collecting lengths...")

    # Init progress.
    if self.showProgress:
      wp = WorkerProgress(lock,coreId,len(fragmentObjects))

    # Loop fragments.
    for fragmentObject in fragmentObjects:
      
      # Show progress.
      if self.showProgress:
        wp.progress()
        
      # Get fragment line.
      fragmentLine = fragmentObject.line

      # Get prepared fragment line.
      prepFragmentLine = prep(fragmentLine)
      
      # Calculate origin coords and number of cols and rows of the fragments boundingbox.
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
          # Get col/row of the cell.
          col,row = RU.calcColRowFromXY(x1+d,y1+d,extent,cellSize)
          # Inside the working extent?
          if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
            # Create the cell polygon.
            cell = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)])
            # Does fragment line intersects cell?
            if prepFragmentLine.intersects(cell):
              # Add current fragment length to dict. Per fragment id there is only one
              # length per col/row. Only on junctions a cell can have more than one
              # length of multiple fragment id's.
              key = (col,row)
              if key in lengthDict:
                lengthDict[key].append(fragmentObject.lengthKM)
              else:
                lengthDict[key] = [fragmentObject.lengthKM]
          # Set next column.
          x1 += cellSize
          x2 += cellSize
        # Set next row.
        y1 += cellSize
        y2 += cellSize

    #---------------------------------------------------------------------------
    # Calculate mean length per cell.
    #---------------------------------------------------------------------------

    # Loop length dict.
    meanLengthDict = dict()
    # 20201118
    #for key,value in lengthDict.iteritems():
    for key,value in lengthDict.items():
      # Update value with mean.
      if len(value) == 1:
        meanLengthDict[key] = value[0]
      else:
        meanLengthDict[key] = sum(value) / float(len(value))

    #---------------------------------------------------------------------------
    # Create raster with mean length per cell.
    #---------------------------------------------------------------------------

    # Create an array for the output length.
    # Use float32 and no float16 to prevent bad allocation error!!!
    ras = np.zeros((nrRows,nrCols),np.float32)
    
    # Init progress.
    if self.showProgress:
      wp = WorkerProgress(lock,coreId,len(meanLengthDict))
    
    # Loop mean length dict.
    #for key,value in meanLengthDict.iteritems():
    for key,value in meanLengthDict.items():
      # Show progress.
      if self.showProgress:
        wp.progress()
      # get col/row and update value.
      col,row = key[0],key[1]
      ras[row,col] = value
    
    return (ras,)
  
  #-------------------------------------------------------------------------------
  # nrOfChunks: number of parts in with the data is devided.
  #             If 0 then nrOfChunks is the same as the nrOfCores.
  # Arguments:
  #   fragmentLines: multilines with rivId,fragId,lengthKM.
  # Returns outRaster
  def run(self,extent,cellSize,fragmentLines,nrOfChunks=0):
    # 20201118
    #global damTreeSH
    pool = None
    try:
    
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores
        
      #---------------------------------------------------------------------------
      # Prepare.
      #---------------------------------------------------------------------------

      Log.info("Preparing rasterize...")

      # Create list of work extents.
      workExtents = self.getWorkExtents(extent,cellSize,nrOfChunks)

      # Create tree and get fragment lines within working extents.
      fragmentLinesTree = STRtree(fragmentLines)
      
      # Loop workExtents and get all fragments which overlaps the workextent.
      workFragmentObjectsList = []
      for workExtent in workExtents:
        # Get fragment lines. 
        workFragmentLines = fragmentLinesTree.query(VU.shpPolygonFromBounds(workExtent))
        # Convert to fragment objects.
        fragmentObjs = []
        for fragLine in workFragmentLines:
          fragmentObj = Fragment(fragLine.rivId,fragLine.fragId,fragLine,fragLine.lengthKM)                                            
          fragmentObjs.append(fragmentObj)
        workFragmentObjectsList.append(fragmentObjs)

      # Create the input list with tuples of (lock,id,extent,cellSize,fragments).
      args = []
      for i in range(len(workExtents)):
        args.append([None,i,workExtents[i],cellSize,workFragmentObjectsList[i]])
 
      #---------------------------------------------------------------------------
      # Rasterize fragments.
      #---------------------------------------------------------------------------
      
      Log.info("  Starting rasterize...")

      # Create the pool.
      pool = mp.Pool(processes=self.nrOfCores)
      results = pool.map(calculate,zip([self]*len(args),args))

      # EXTRA I
      # No more tasks, so wrap up current tasks.
      pool.close() 
      pool.join()  

      #---------------------------------------------------------------------------
      # Process rasterize results. 
      #---------------------------------------------------------------------------
 
      # The results are a list of (rasterChunks) tuples. Get separate results.
      rasterChunks = [r[0] for r in results]
 
      # Combine raster chunks.
      ras = self.joinRasterChunks(extent,cellSize,rasterChunks,True)

      #---------------------------------------------------------------------------
      # Create fragment length raster. 
      #---------------------------------------------------------------------------
        
      Log.info("Creating fragment length raster...")
    
      # Create raster.
      outRaster = Raster()
      noDataValue = -999.0
      outRaster.initRasterEmpty(extent,cellSize,np.float32,noDataValue)
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
        pool = None
      return None
