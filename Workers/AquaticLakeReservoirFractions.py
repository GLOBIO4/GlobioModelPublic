# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 24 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - prepare and lake.contains added.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - calculate modified, because of self-intersecting polygons.
#-------------------------------------------------------------------------------

import multiprocessing as mp
import numpy as np

from shapely.geometry import Polygon,box
from shapely.prepared import prep
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return AquaticLakeReservoirFractions.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticLakeReservoirFractions(WorkerBase):
  """
  Calculates fractions for lakes and reservoirs.
  """

  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticLakeReservoirFractions,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  # Returns a tuple with the raster chunk (float16). 
  def calculate(self,args):            

    # Get arguments.
    # 20201118
    #coreId = args[0]
    extent = args[1]
    cellSize = args[2]
    polys = args[3]

    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    
    # Create an raster for the area.
    ras = np.zeros((nrRows,nrCols),np.float16)

    # Create a small offset for the cell origin.
    d = cellSize / 10.0
    
    # Loop polygons.
    for poly in polys:
      # Create prepared polygon for later use.
      prepPoly = prep(poly)
      # Calculate origin coords and number of cols and rows of the polygon boundingbox.
      minx,miny,cols,rows = VU.shpLineCalcOriginNrColsRows(poly,cellSize)
      # Create a grid fishnet over the polygon and calculate area per cell.
      y1 = miny
      y2 = y1 + cellSize
      # Loop rows.
      for _ in range(rows):
        x1 = minx
        x2 = x1 + cellSize
        # Reset rowCellAreaKM2 (does not vary in one row, i.e. lattitude).
        rowCellAreaKM2 = None
        # Loop cols.
        for _ in range(cols):
          # Get col/row of raster.
          col,row = RU.calcColRowFromXY(x1+d,y1+d,extent,cellSize)
          # Inside the working extent?
          if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
            # Create the cell polygon.
            cell = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)])
            # Does the polygon fully contains the cell?
            areaKM2 = None
            if prepPoly.contains(cell):
              # rowCellAreaKM2 not yet calculated?
              if rowCellAreaKM2 is None:
                rowCellAreaKM2 = VU.shpCalcGeodeticPolygonAreaKM2(cell)
              # Set full area of cell.
              areaKM2 = rowCellAreaKM2
            else:
              # 20201209
              # Check the polygon geometry for self-intersections.
              if not poly.is_valid:
                poly = poly.buffer(0)
              # Get intersection with the cell.
              intersections = poly.intersection(cell)
              # Not empty?
              if not intersections.is_empty:
                # Calculate intersection polygon area.
                areaKM2 = VU.shpCalcGeodeticPolygonAreaKM2(intersections)
            # Valid area?
            if not areaKM2 is None:
              # Update area of raster cell.
              ras[row,col] += areaKM2
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
  def run(self,extent,cellSize,
          polygons,depthThreshold,depthFlag,nrOfChunks=0):
    
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
      featureTree = STRtree(polygons)
  
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
      self.dbgPrint(ras.shape)

      #---------------------------------------------------------------------------
      # Create watertype area raster. 
      #---------------------------------------------------------------------------
       
      Log.info("Creating watertype area raster...")
   
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

    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
