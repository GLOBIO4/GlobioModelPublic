# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 9 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           10 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - New version, the cellsize parameter is removed. The resolution
#             is based on the resolution of the RiverDischarge raster.
#           - Run modified, use of readAndPrepareInRaster removed.
#           - Argument NumberOfCores added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - run modified, because of shapeFileWriteFeatures.
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
#import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

#import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticDrainageToRivers import AquaticDrainageToRivers
#from GlobioModel.Core.Raster import Raster
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticDrainageToRivers_V2(CalculationBase):
  """
  Extracts riversegments based on a discharge threshold.
  """

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN VECTOR Drainage
    IN RASTER RiverDischarge
    IN FLOAT DischargeThreshold
    IN INTEGER NumberOfCores
    OUT VECTOR Rivers
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    inShapeFileName = args[1]
    inRasterName = args[2]
    dischargeThreshold = args[3]
    nrOfCores = args[4]
    outShapeFileName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkVector(inShapeFileName)
    self.checkRaster(inRasterName)
    self.checkFloat(dischargeThreshold,0.0,9999.0)
    self.checkInteger(nrOfCores,-9999,9999)
    self.checkVector(outShapeFileName,True)

    # Get the raster info from the input raster.
    rasterInfo = RU.rasterGetInfo(inRasterName)

    # Get the cellsize.
    cellSize = rasterInfo.cellSize
    
    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outShapeFileName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading shapefile...")

    # Read the shapefile.
    inVector = Vector(inShapeFileName)
    inVector.read()
    
    # Get the drainage lines.
    lines = [loads(feat.GetGeometryRef().ExportToWkb()) for feat in inVector.layer]

    Log.info("Total number of features found: %s" % len(lines))    
      
    # Clean up.
    inVector.close()
    inVector = None
      
    #-------------------------------------------------------------------------------
    # Read discharge raster and prepare.
    #-------------------------------------------------------------------------------
 
    #Log.info("Reading raster...")
    
    # Reads the raster and resizes to extent.
    dischargeRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,"discharge")
    dischargeRas = dischargeRaster.r
    
    #-----------------------------------------------------------------------------
    # Select rivers.
    #-----------------------------------------------------------------------------

    Log.info("Selecting rivers...")

    # Create worker.
    w = AquaticDrainageToRivers(nrOfCores)
    w.debug = self.debugPrint

    #Log.info("  Using: %s cores" % (w.nrOfCores))

    outLines = w.run_nopool(extent,cellSize,lines,
                            dischargeRas,dischargeThreshold)

    # Do we have not results.
    if outLines is None:
      Log.info("No valid results!")
    else:
      Log.info("Result nr. of rivers: %s" % len(outLines))

      Log.info("Writing rivers...")

      # Write rivers.
      VU.shapeFileWriteFeatures(outShapeFileName,outLines)
    
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
