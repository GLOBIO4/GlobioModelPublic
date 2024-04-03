# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
#           8 nov 2018, JH, PBL
#           -Removed the dominant land use calculation
#           18 mar 2019, JH, PBL
#           -Include the possibility to calculate overall MSA with limited 
#            number of pressures if raster names equal ""
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcTerrestrialMSA(CalculationBase):
  """
  Creates a raster with total terrestrial MSA.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER LanduseMSA
    IN RASTER HumanEncroachmentMSA
    IN RASTER NDepositionMSA
    IN RASTER ClimateChangeMSA
    IN RASTER InfraDisturbanceMSA
    IN RASTER InfraFragmentationMSA
    OUT RASTER TerrestrialMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    landuseMSAName = args[2]
    humanEncMSAName = args[3]
    nDepMSAName = args[4]
    climChangeMSAName = args[5]
    infraDistMSAName = args[6]
    infraFragMSAName = args[7]
    outRasterName = args[8]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(landuseMSAName,optional=True)
    self.checkRaster(humanEncMSAName,optional=True)
    self.checkRaster(nDepMSAName,optional=True)
    self.checkRaster(climChangeMSAName,optional=True)
    self.checkRaster(infraDistMSAName,optional=True)
    self.checkRaster(infraFragMSAName,optional=True)
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Create a list with all msa rasters.
    msaRasterNames = [landuseMSAName,humanEncMSAName,
                      nDepMSAName,climChangeMSAName,
                      infraDistMSAName,infraFragMSAName]  
    msaDescriptions = ["landuse","human encroachment",
                       "N-deposition","climate change",
                       "infrastructure disturbance","infrastructure fragmentation"]  
    
    # Create terrestrial MSA raster.
    Log.info("Creating terrestrial MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate total MSA.
    Log.info("Calculating terrestrial MSA raster...")
    for i in range(len(msaRasterNames)):
      msaRasterName = msaRasterNames[i]
      msaDescription = msaDescriptions[i]

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
      
          if i == 0:
              outRaster.r = msaRaster.r
          else:
              mask = (outRaster.r != outRaster.noDataValue) & (msaRaster.r != msaRaster.noDataValue)
              outRaster.r[mask] *= msaRaster.r[mask]
      
          # Clear mask.
          mask = None

          # Close and free the msa raster.
          msaRaster.close()
          msaRaster = None 
        
    # Save the terrestrial MSA raster.
    Log.info("Writing terrestrial MSA raster...")
    outRaster.write()

    # Cleanup.
    outRaster.close()
    outRaster = None
          
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    mapDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\geodata\GlobalTifs\res_10sec"
    lookupDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\LookupGlobal"
    outDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    if not os.path.isdir(outDir):
      outDir = r"S:\hilbersj"

    pCalc = GLOBIO_CalcTerrestrialMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec    
    lu = os.path.join(inDir,"LanduseMSA_test.tif")
    he = os.path.join(inDir,"HumanEncroachmentMSA_test.tif")
    nd = os.path.join(inDir,"NDepositionMSA_test.tif")
    cc = os.path.join(inDir,"ClimateChangeMSA_test.tif")
    di = os.path.join(inDir,"InfraDisturbanceMSA_test.tif")
    fr = os.path.join(inDir,"InfraFragmentationMSA_test.tif")
    out = os.path.join(outDir,"TerrestrialMSA_test.tif")
    
    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,lu,he,nd,cc,di,fr,out)
  except:
    Log.err()
