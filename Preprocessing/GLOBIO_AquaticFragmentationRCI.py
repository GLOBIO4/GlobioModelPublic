# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           25 feb 2019, ES, ARIS B.V.
#           - nrOfChunks *16 added.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Argument NumberOfCores added.
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

# Import after shapely.
#import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticFragmentationRCI import AquaticFragmentationRCI
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticFragmentationRCI(CalculationBase):
  """
  Calculates the River Connectivity Index (RCI) as an indicator for river
  fragmentation.
  
  RCI = sum(Li**2 / L**2) * 100
  
  Where Li is the length of the river segment i and L is the total length of the
  river network in the catchment.

  When RCI = 100 there is no fragmentation.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR RiverFragments
    IN RASTER Catchments
    IN INTEGER NumberOfCores
    OUT RASTER RCI
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inRivShapeFileName = args[2]
    inCatchRasterName = args[3]
    nrOfCores = args[4]
    outRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inRivShapeFileName)
    self.checkRaster(inCatchRasterName)
    self.checkInteger(nrOfCores,-9999,9999)
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading river fragments...")

    # Read shapefile.
    inVector = Vector(inRivShapeFileName)
    inVector.read()

    # Get connected lines.
    multiLines = []
    for feat in inVector.layer:
      mline = loads(feat.GetGeometryRef().ExportToWkb())
      mline.fragId = feat.FragId
      mline.lengthKM = feat.LengthKM
      multiLines.append(mline)      

    Log.info("Total number of river fragments found: %s" % len(multiLines))    

    # Clean up.
    inVector.close()
    inVector = None

    #-------------------------------------------------------------------------------
    # Read raster.
    #-------------------------------------------------------------------------------
 
    # Read the raster.
    catchRaster = self.readAndPrepareInRaster(extent,cellSize,inCatchRasterName,"catchments")

    #-----------------------------------------------------------------------------
    # Calculate raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating fragment RCI raster...")    

    # Create worker.
    w = AquaticFragmentationRCI(nrOfCores)
    w.debug = self.debugPrint
    w.showProgress = True
    nrOfChunks = w.nrOfCores * 16
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    fragRaster = w.run(extent,cellSize,multiLines,catchRaster,nrOfChunks)

    # Clean up.
    multiLines = None
    catchRaster.close()
    catchRaster = None

    #-----------------------------------------------------------------------------
    # Writing raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing fragmentation RCI raster...")

    # Write fragmentation.
    fragRaster.writeAs(outRasterName)

    # Clean up.
    fragRaster.close()
    fragRaster = None

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

      pCalc = GLOBIO_AquaticFragmentationRCI()
      pCalc.debugPrint = False
      #pCalc.debugPrint = True

      extentName = "wrld"
      extentName = "eu"
      #extentName = "nl"
      #extentName = "sp"
      cellSizeName = "30sec"

      if extentName == "sp":
        ext = [-4.68,42.40,-2.55,43.67]
      else:
        ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "sp":
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20190210"
      else:
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      if extentName == "eu":
        riv = "frag_river_fragments_%s.shp" % "wrld"
      else:
        riv = "frag_river_fragments_%s.shp" % extentName

      inRasDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
      catch = "catchments.tif"

      if extentName == "sp":
        outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20190206" % (cellSizeName,"nl")
      else:
        outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20190206" % (cellSizeName,extentName)
      out = "frag_rci.tif"

      if os.path.isdir("/root"):
        inShpDir = UT.toLinux(inShpDir)
        inRasDir = UT.toLinux(inRasDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      riv = os.path.join(inShpDir,riv)
      catch = os.path.join(inRasDir,catch)
      out = os.path.join(outDir,out)

      # Remove output data.
      RU.rasterDelete(out)

      # Run.
      pCalc.run(ext,cs,riv,catch,out)
    except:
      MON.cleanup()
      Log.err()

  #-----------------------------------------------------------------------------
  def main():
    try:
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticFragmentationRCI()
      pCalc.debugPrint = False
      #pCalc.debugPrint = True

      #extentName = "wrld"
      extentName = "eu"
      #extentName = "nl"
      #extentName = "sp"
      cellSizeName = "30sec"

      if extentName == "sp":
        ext = [-4.68,42.40,-2.55,43.67]
      else:
        ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "sp":
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20190210"
      else:
        inShpDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
      if extentName == "eu":
        riv = "frag_river_fragments_%s.shp" % "wrld"
      else:
        riv = "frag_river_fragments_%s.shp" % extentName

      # 20200908
      #inRasDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
      # P:\Project\Globio4LA\data\pbl_20200806\xGlobio-aqua\flo1k_hydrography
      inRasDir = r"G:\data\Globio4LA\data\pbl_20200806\xGlobio-aqua\flo1k_hydrography"
      #catch = "catchments.tif"
      catch = "basins.tif"

      if extentName == "sp":
        #outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20190206" % (cellSizeName,"nl")
        outDir = r"G:\data\Globio4LA\data\referentie\v4015\%s_%s\in_20200909" % (cellSizeName,"nl")
      else:
        #outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20190206" % (cellSizeName,extentName)
        outDir = r"G:\data\Globio4LA\data\referentie\v4015\%s_%s\in_20200909" % (cellSizeName,extentName)
      out = "frag_rci.tif"

      if os.path.isdir("/root"):
        inShpDir = UT.toLinux(inShpDir)
        inRasDir = UT.toLinux(inRasDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      riv = os.path.join(inShpDir,riv)
      catch = os.path.join(inRasDir,catch)
      out = os.path.join(outDir,out)

      # Remove output data.
      RU.rasterDelete(out)

      # Run.
      pCalc.run(ext,cs,riv,catch,out)
    except:
      MON.cleanup()
      Log.err()
  
  #-------------------------------------------------------------------------------
  doProfile = False
  if doProfile:
    import cProfile
    cProfile.run("main()")
  else:
    main()
  
