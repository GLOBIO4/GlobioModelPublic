# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - degreeToKM_v2 replaced with degreeToKM.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#-------------------------------------------------------------------------------

import multiprocessing as mp
import numpy as np

from shapely.geometry import Polygon,box
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return AquaticRiverFractions.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticRiverFractions(WorkerBase):
  """
  Calculates fractions for rivers.
  """

  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticRiverFractions,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  def calculate(self,args):            

    # Get arguments.
    # 20201118
    #coreId = args[0]
    extent = args[1]
    cellSize = args[2]
    lines = args[3]
    
    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    
    # Create an array for the length.
    ras = np.zeros((nrRows,nrCols),np.float16)

    # Create a small offset for the cell origin.
    d = cellSize / 10.0

    # Loop lines.
    for line in lines:
      
      #self.dbgPrint(line.wkt)
      
      # Calculate origin coords and number of cols and rows of the line boundingbox.
      minx,miny,cols,rows = VU.shpLineCalcOriginNrColsRows(line,cellSize)
      # Create a grid fishnet over the line and calculate length per cell.
      y1 = miny
      y2 = y1 + cellSize
      # Loop rows.
      for _ in range(rows):
        x1 = minx
        x2 = x1 + cellSize
        # Loop cols.
        for _ in range(cols):
          # Get col/row of raster.
          col,row = RU.calcColRowFromXY(x1+d,y1+d,extent,cellSize)
          # Inside the working extent?
          if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
            # Create the cell polygon.
            cell = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)])
            # Get line intersection with the cell.
            intersections = line.intersection(cell)
            # Not empty?
            if not intersections.is_empty:
              # Calculate intersection polygon area.
              lengthKM = VU.shpCalcGeodeticLineLengthKM(intersections)
              
              #self.dbgPrint("row,col,lengthKM: %s %s %s" % (row,col,lengthKM))

              # Update length of raster cell.
              ras[row,col] += lengthKM
              
          # Set next column.
          x1 += cellSize
          x2 += cellSize
          
        # Set next row.
        y1 += cellSize
        y2 += cellSize
   
    return (ras,)


  #-------------------------------------------------------------------------------
  # nrOfChunks: number of parts in with the data is devided.
  #             If 0 then nrOfChunks is the same as the nrOfCores.  
  def run(self,extent,cellSize,lines,nrOfChunks=0):
    
    pool = None
    try:
    
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores

      #---------------------------------------------------------------------------
      # Split full extent in parts to divide over the cores. 
      #---------------------------------------------------------------------------
      
      # Get number of cols and rows.
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
      self.dbgPrint("nrCols,nrRows: %s %s" % (nrCols,nrRows))
  
      # Split the data in chunks to be handled by the cores.
      offsets,sizes = self.getOffsetsAndSizes(nrRows,nrOfChunks)
      self.dbgPrint("Using input:")
      self.dbgPrint(offsets)
      self.dbgPrint(sizes)

      # Create list of working extents.
      yMin = extent[1]
      workExtents = []
      for size in sizes:
        yMax = yMin + size * cellSize
        workExtent = [extent[0],yMin,extent[2],yMax]
        workExtents.append(workExtent)
        yMin = yMax

      #---------------------------------------------------------------------------
      # Prepare pool data. 
      #---------------------------------------------------------------------------
      
      Log.info("Creating spatial index...")
          
      # Create feature tree.
      featureTree = STRtree(lines)
  
      Log.info("Preparing calculation...")
      
      # Get features within working extents.
      workFeatures = [featureTree.query(box(x1,y1,x2,y2)) for x1,y1,x2,y2 in workExtents]
  
      # Create the input list with tuples of (id,extent,cellSize,lines).
      args = []
      for i in range(len(offsets)):
        args.append([i,workExtents[i],cellSize,workFeatures[i]])

      #---------------------------------------------------------------------------
      # Calculate. 
      #---------------------------------------------------------------------------
  
      Log.info("Starting calculation...")
    
      # Create the pool.
      pool = mp.Pool(processes=self.nrOfCores)
      results = pool.map(calculate,zip([self]*len(args),args))

      #---------------------------------------------------------------------------
      # Process results. 
      #---------------------------------------------------------------------------

      # The results are a list of (rasterChunks) tuples. Get separate results.
      rasterChunks = [r[0] for r in results]

      # The first one contains the results from the lowest extent, so reverse.
      rasterChunks.reverse()

      # Combine raster chunks and reshape.
      ras = np.concatenate(rasterChunks)
      ras.reshape(nrRows,nrCols)
      #self.dbgPrint(ras.shape)

      #---------------------------------------------------------------------------
      # Create watertype length raster. 
      #---------------------------------------------------------------------------
       
      Log.info("Creating watertype length raster...")
   
      # Create raster.
      outRaster = Raster()
      outRaster.initRasterEmpty(extent,cellSize,np.float32,-999)
      outRaster.r = ras.astype(np.float32)

      return outRaster

    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        pool = None
      return None
