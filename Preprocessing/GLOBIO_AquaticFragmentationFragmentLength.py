# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Argument NumberOfCores added.
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

# Import after shapely.
#import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

#import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticFragmentationFragmentLength import AquaticFragmentationFragmentLength
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticFragmentationFragmentLength(CalculationBase):
  """
  Calculates the river fragment length as an indicator for river fragmentation.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR RiverFragments
    IN INTEGER NumberOfCores
    OUT RASTER RiverFragmentLength
    """

    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inRivShapeFileName = args[2]
    nrOfCores = args[3]
    outRasterName = args[4]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inRivShapeFileName)
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

    # Get connected lines with RivId.
    multiLines = []
    for feat in inVector.layer:
      mline = loads(feat.GetGeometryRef().ExportToWkb())
      mline.rivId = feat.RivId
      mline.fragId = feat.FragId
      mline.lengthKM = feat.LengthKM
      multiLines.append(mline)      

    Log.info("Total number of river fragments found: %s" % len(multiLines))    

    # Clean up.
    inVector.close()
    inVector = None

    #-----------------------------------------------------------------------------
    # Calculate the fragment length raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating fragment length raster...")    

    # Create worker.
    w = AquaticFragmentationFragmentLength(nrOfCores)
    w.debug = self.debugPrint
    w.showProgress = True
    nrOfChunks = w.nrOfCores * 16
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    fragRaster = w.run(extent,cellSize,multiLines,nrOfChunks)

    # Clean up.
    multiLines = None

    #-----------------------------------------------------------------------------
    # Writing raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing fragment length raster...")

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
  pass
#  try:
#    GLOB.monitorEnabled = True
#    GLOB.SHOW_TRACEBACK_ERRORS = True
#    
#    pCalc = GLOBIO_AquaticFragmentationFragmentLength_A()
#    pCalc.debugPrint = False
#    pCalc.debugPrint = True
#    
#    extentName = "wrld"
#    #extentName = "eu"
#    #extentName = "nl"
#    cellSizeName = "30sec"
#
#    ext = GLOB.constants[extentName].value
#    cs = GLOB.constants[cellSizeName].value
#
#    inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
#    if extentName == "eu":
#      inShp = "frag_river_fragments_%s.shp" % "wrld"
#    else:
#      inShp = "frag_river_fragments_%s.shp" % extentName
#    
#    outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20181123" % (cellSizeName,extentName)
#    out = "frag_fragment_length.tif"
#
#    if os.path.isdir("/root"):
#      inDir = UT.toLinux(inDir)
#      outDir = UT.toLinux(outDir)
#
#    # Create outdir.
#    if not os.path.isdir(outDir):
#      os.makedirs(outDir)
#
#    # Set input/output data.
#    inShp = os.path.join(inDir,inShp)
#    out = os.path.join(outDir,out)
#
#    # Remove output data.
#    RU.rasterDelete(out)
#
#    # Run.
#    pCalc.run(ext,cs,inShp,out)
#  except:
#    MON.cleanup()
#    Log.err()
  
