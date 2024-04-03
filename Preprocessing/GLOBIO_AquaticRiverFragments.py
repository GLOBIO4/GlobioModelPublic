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
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - run modified, because of shapeFileWriteFeatures.
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

# Import after shapely.
import osgeo.ogr as ogr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticRiverFragments import AquaticRiverFragments
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticRiverFragments(CalculationBase):
  """
  Creates river fragments (i.e. parts separated by dams) from river segments.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Rivers
    IN VECTOR Dams
    IN INTEGER NumberOfCores
    OUT VECTOR RiverFragments
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inRivShapeFileName = args[2]
    inDamShapeFileName = args[3]
    nrOfCores = args[4]
    outShapeFileName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inRivShapeFileName)
    self.checkVector(inDamShapeFileName)
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

    Log.info("Reading dams...")

    # Read shapefile.
    inVector = Vector(inDamShapeFileName)
    inVector.read()

    # Get points.
    points = []
    for feat in inVector.layer:
      point = loads(feat.GetGeometryRef().ExportToWkb())
      # Connected to a river?
      if feat.Connected == 1:
        # Add to list.
        points.append(point)      

    Log.info("Total number of dams connected to rivers found: %s" % len(points))    

    # Clean up.
    inVector.close()
    inVector = None

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading rivers...")

    # Read shapefile.
    inVector = Vector(inRivShapeFileName)
    inVector.read()

    # Get connected lines with RivId.
    multiLines = []
    for feat in inVector.layer:
      mline = loads(feat.GetGeometryRef().ExportToWkb())
      mline.rivId = feat.RivId
      multiLines.append(mline)      

    Log.info("Total number of connected rivers found: %s" % len(multiLines))    

    # Clean up.
    inVector.close()
    inVector = None

    #-----------------------------------------------------------------------------
    # Calculate the river fragments.
    #-----------------------------------------------------------------------------

    Log.info("Calculating river fragments...")    

    # Create worker.
    w = AquaticRiverFragments(nrOfCores)
    w.debug = self.debugPrint
    #nrOfChunks = w.nrOfCores * 1
    nrOfChunks = w.nrOfCores * 4
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    fragmentLines = w.run(extent,cellSize,points,multiLines,nrOfChunks)

    Log.info("River fragments found: %s" % len(fragmentLines))    

    # Clean up.
    points = None
    multiLines = None

    #-----------------------------------------------------------------------------
    # Writing river fragments.
    #-----------------------------------------------------------------------------

    Log.info("Writing river fragments shapefile...")

    # Write output shapefile.
    VU.shapeFileWriteFeatures(outShapeFileName,fragmentLines,
                              ["RivId","FragId","LengthKM"],
                              [ogr.OFTInteger,ogr.OFTInteger,ogr.OFTReal])

    # Cleanup.
    fragmentLines = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True
    
    pCalc = GLOBIO_AquaticRiverFragments()
    pCalc.debugPrint = False
    pCalc.debugPrint = True
    
    extentName = "wrld"
    #extentName = "eu"
    #extentName = "nl"
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
    if extentName == "eu":
      riv = "frag_rivers_connected_%s.shp" % "wrld"
      dam = "frag_dams_%s.shp" % "wrld"
    else:
      riv = "frag_rivers_connected_%s.shp" % extentName
      dam = "frag_dams_%s.shp" % extentName
    
    outDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
    out = "frag_river_fragments_%s.shp" % extentName

    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Create outdir.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    # Set input/output data.
    riv = os.path.join(inDir,riv)
    dam = os.path.join(inDir,dam)
    out = os.path.join(outDir,out)

    # Remove output data.
    RU.vectorDelete(out)    

    # Run.
    pCalc.run(ext,cs,riv,dam,out)
  except:
    MON.cleanup()
    Log.err()
 
