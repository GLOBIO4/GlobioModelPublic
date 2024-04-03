# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#--------------------------------------------------------------------------------------
# Script to obtain histograms of the input values of the pressures: JH, PBL
#--------------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Common.Utils as Utils

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_Histogram(CalculationBase):
  """
  Creates a raster with total terrestrial MSA.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER HumanEncroachmentMSA
    IN RASTER NDepositionMSA
    IN RASTER InfraDisturbanceMSA
    IN RASTER InfraFragmentationMSA
    OUT FILE HistHE 
    OUT FILE HistNdep
    OUT FILE HistID
    OUT FILE HistIF
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=9:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    humanEncMSAName = args[2]
    nDepMSAName = args[3]
    infraDistMSAName = args[4]
    infraFragMSAName = args[5]
    outHistHE = args[6]
    outHistND = args[7]
    outHistID = args[8]
    outHistIF = args[9]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(humanEncMSAName,optional=True)
    self.checkRaster(nDepMSAName,optional=True)
    self.checkRaster(infraDistMSAName,optional=True)
    self.checkRaster(infraFragMSAName,optional=True)
    self.checkFile(outHistHE,asOutput=True,optional=True)
    self.checkFile(outHistND,asOutput=True,optional=True)
    self.checkFile(outHistID,asOutput=True,optional=True)
    self.checkFile(outHistIF,asOutput=True,optional=True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outHistHE)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Create a list with all msa rasters.
    msaRasterNames = [humanEncMSAName,
                      nDepMSAName,
                      infraDistMSAName,infraFragMSAName]  
    msaDescriptions = ["human encroachment",
                       "N-deposition",
                       "infrastructure disturbance","infrastructure fragmentation"]  
    msaOutFileNames = [outHistHE,outHistND,outHistID,outHistIF]
    
    # Calculate total MSA.
    Log.info("Calculating histogram...")
    for i in range(len(msaRasterNames)):
      msaRasterName = msaRasterNames[i]
      msaDescription = msaDescriptions[i]
      msaOutFileName = msaOutFileNames[i]

      if (not self.isValueSet(msaRasterName)):
          continue
      else:
          
          #-----------------------------------------------------------------------------
          # Read the MSA raster and prepare.
          #-----------------------------------------------------------------------------
    
          # Reads the raster and resizes to extent and resamples to cellsize.
          msaRaster = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,msaDescription)
      
          # Calculate msa where no nodata.      
          Log.info("- Calculating...")

          if i==0:
              mask = (msaRaster.r > 0)
              hist, bin_edges = np.histogram(np.log10(msaRaster.r[mask]+0.1), bins = 100)
          if i==1:
              mask = (msaRaster.r > 0)
              hist, bin_edges = np.histogram(np.log10(msaRaster.r[mask]+0.01), bins = 100)                    
          if i==2:
              mask = (msaRaster.r > 0)
              hist, bin_edges = np.histogram(np.log10(msaRaster.r[mask]+0.1), bins = 100)
          if i==3:
              mask = (msaRaster.r > 0)
              hist, bin_edges = np.histogram(np.log10(np.unique(msaRaster.r[mask])+1), bins = 100)              
          
          # Combine regions and areas in an array of region/area tuples.
          regionAreas = zip(hist,bin_edges)
          hist = None
          bin_edges = None
          mask = None
    
          # Close and free rasters.   
          msaRaster.close()
          msaRaster = None
    
          # Create file content.
          lines = []
          lines.append("value;bin_edge")
          for regionArea in regionAreas:
              lines.append("{};{}".format(*regionArea))
        
          # Write to file.
          Utils.fileWrite(msaOutFileName,lines)
          # Free areas and lines.
          regionAreas = None
          lines = None 
      
          # Clear mask.
          mask = None
          
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
