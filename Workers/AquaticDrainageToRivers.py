# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 9 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#-------------------------------------------------------------------------------

import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticDrainageToRivers(WorkerBase):
  """
  Extracts riversegments based on a discharge threshold.
  """

  extent = None
  cellSize = None
  nrCols = None
  nrRows = None
  lines = None
  dischargeRas = None
  dischargeThreshold = None
  
  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticDrainageToRivers,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  def run_nopool(self,extent,cellSize,lines,dischargeRas,dischargeThreshold):

    try:
      # Get number of cols and rows of full extent.    
      nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
      
      # Loop lines.
      outLines = []
      for i in range(len(lines)):
        # Get line.
        line = lines[i]
        
        # Set flag.
        isRiver = False
        
        # Calculate line origin coords and number of cols and rows of the
        # boundingbox of the line.
        minx,miny,bndNrCols,bndNrRows = VU.shpLineCalcOriginNrColsRows(line,cellSize)
  
        self.dbgPrint("Line boundingbox minx,miny: %s %s " % (minx,miny))
        self.dbgPrint("Line boundingbox nrCols,nrRows: %s %s " % (bndNrCols,bndNrRows))
        
        # Loop boundingbox rows.
        y1 = miny
        for _ in range(bndNrRows):
          x1 = minx
          # Loop boundingbox cols.
          for _ in range(bndNrCols):
            # Get raster col and row. 
            col,row = RU.calcColRowFromXY(x1,y1,extent,cellSize)
            # Inside the working extent?
            if (col>=0) and (row>=0) and (col<nrCols) and (row<nrRows):
              # Get raster value.
              value = dischargeRas[row,col]
              # Is it a river?
              if value > dischargeThreshold:
                isRiver = True
                break
            x1 += cellSize
          # River found?
          if isRiver:
            # No need to look further.
            break
          y1 += cellSize
  
        # River found?
        if isRiver:
          self.dbgPrint("Line isRiver: %s " % (isRiver))
          # Add line.
          outLines.append(line)

      return outLines

    except KeyboardInterrupt:
      return None

