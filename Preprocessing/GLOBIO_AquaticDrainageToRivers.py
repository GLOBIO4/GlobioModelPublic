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
#           - Argument NumberOfCores added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - run modified, because of shapeFileWriteFeatures.
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticDrainageToRivers import AquaticDrainageToRivers
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticDrainageToRivers(CalculationBase):
  """
  Extracts riversegments based on a discharge threshold.
  """

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Drainage
    IN RASTER RiverDischarge
    IN FLOAT DischargeThreshold
    IN INTEGER NumberOfCores
    OUT VECTOR Rivers
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inShapeFileName = args[2]
    inRasterName = args[3]
    dischargeThreshold = args[4]
    nrOfCores = args[5]
    outShapeFileName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inShapeFileName)
    self.checkRaster(inRasterName)
    self.checkFloat(dischargeThreshold,0.0,9999.0)
    self.checkInteger(nrOfCores,-9999,9999)    
    self.checkVector(outShapeFileName,True)

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
    # Read discharge raster.
    #-------------------------------------------------------------------------------
 
    Log.info("Reading raster...")
    
    # Read the raster.
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

  #-----------------------------------------------------------------------------
  def main_20200908():
    try:
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticDrainageToRivers()
      pCalc.debugPrint = False

      extentName = "wrld"
      #extentName = "nl"
      #extentName = "eu"
      cellSizeName = "30sec"

      ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "nl":
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20181109"
        inShp = "drainage_lines24.shp"
      else:
        inShpDir = r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\flo1k_hydrography"
        inShp = "drainage_lines24.shp"

      inRasDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
      inRas = "flo1k_qav_2015.tif"

      outDir = r"G:\data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      outShp = "rivers_%s.shp" % extentName

      th = 0.0

      if os.path.isdir("/root"):
        inShpDir = UT.toLinux(inShpDir)
        inRasDir = UT.toLinux(inRasDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      inShp = os.path.join(inShpDir,inShp)
      inRas = os.path.join(inRasDir,inRas)
      outShp = os.path.join(outDir,outShp)

      # Remove output data.
      VU.vectorDelete(outShp)

      # Run.
      pCalc.run(ext,cs,inShp,inRas,th,outShp)
    except:
      MON.cleanup()
      Log.err()
  
  #-----------------------------------------------------------------------------
  def main():
    try:
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticDrainageToRivers()
      pCalc.debugPrint = False

      extentName = "wrld"
      #extentName = "nl"
      #extentName = "eu"
      cellSizeName = "30sec"

      ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "nl":
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20181109"
        inShp = "drainage_lines24.shp"
      else:
        inShpDir = r"G:\data\Globio4LA\data\pbl_20181023\VBarbarossa\flo1k_hydrography"
        inShp = "drainage_lines24.shp"

      inRasDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
      inRas = "flo1k_qav_2015.tif"

      outDir = r"G:\data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      outShp = "rivers_%s.shp" % extentName

      th = 0.0

      if os.path.isdir("/root"):
        inShpDir = UT.toLinux(inShpDir)
        inRasDir = UT.toLinux(inRasDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      inShp = os.path.join(inShpDir,inShp)
      inRas = os.path.join(inRasDir,inRas)
      outShp = os.path.join(outDir,outShp)

      # Remove output data.
      VU.vectorDelete(outShp)

      # Run.
      pCalc.run(ext,cs,inShp,inRas,th,outShp)
    except:
      MON.cleanup()
      Log.err()

  #-------------------------------------------------------------------------------
  main()

