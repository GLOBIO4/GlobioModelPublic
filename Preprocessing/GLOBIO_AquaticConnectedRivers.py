# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Finds connected rivers with dams. 
# Writes connected rivers a multilines. 
#
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - run() modified, shpMultiLineToLines added.
#           - Argument NumberOfCores added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - run modified, because of shapeFileWriteFeatures.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - run modified, use of loads added.
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
from GlobioModel.Workers.AquaticConnectedRivers import AquaticConnectedRivers
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticConnectedRivers(CalculationBase):
  """
  Converts connected riversegments to rivers (multi-lines).
  """

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Rivers
    IN INTEGER NumberOfCores
    OUT VECTOR ConnectedRivers
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inShapeFileName = args[2]
    nrOfCores = args[3]
    outShapeFileName = args[4]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inShapeFileName)
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

    Log.info("Reading river shapefile...")

    # Read shapefile.
    inVector = Vector(inShapeFileName)
    inVector.read()

    # 20201209
    # # Get lines.
    # lines = []
    # for line in inVector.layer:
    #   tmpLines = VU.shpMultiLineToLines(line)
    #   for tmpLine in tmpLines:
    #     tmpLine.Connected = line.Connected
    #     lines.append(tmpLine)

    # 20201209
    # Get lines.
    lines = []
    for feat in inVector.layer:
      line = loads(feat.GetGeometryRef().ExportToWkb())
      tmpLines = VU.shpMultiLineToLines(line)
      for tmpLine in tmpLines:
        tmpLine.Connected = feat.Connected
        lines.append(tmpLine)

    Log.info("Total number of rivers found: %s" % len(lines))    

    # Clean up.
    inVector.close()
    #inVector = None
    del inVector

    #-----------------------------------------------------------------------------
    # Calculate connected rivers.
    #-----------------------------------------------------------------------------

    Log.info("Getting connected rivers...")    

    # Create worker.
    w = AquaticConnectedRivers(nrOfCores)
    w.debug = self.debugPrint
    nrOfChunks = w.nrOfCores * 1
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    multiLines = w.run(extent,cellSize,lines,nrOfChunks)

    Log.info("Connected lines found: %s" % len(multiLines))

    #-----------------------------------------------------------------------------
    # Add RivIds.
    #-----------------------------------------------------------------------------

    Log.info("Creating river ids...")

    # Loop multilines.
    rivId = 0
    for multiLine in multiLines:
      multiLine.RivId = rivId 
      rivId += 1
      
    #-----------------------------------------------------------------------------
    # Write output.
    #-----------------------------------------------------------------------------

    Log.info("Writing output...")

    # Write output.
    VU.shapeFileWriteFeatures(outShapeFileName,multiLines,["RivId"],[ogr.OFTInteger])

    # Clean up.
    lines = None
    multiLines = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
        
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True
    
    pCalc = GLOBIO_AquaticConnectedRivers()
    pCalc.debugPrint = True
    
    extentName = "wrld"
    #extentName = "nl"
    #extentName = "eu"
#     #extentName = "neu"
#     #extentName = "nor_b"
#     if extentName == "neu":
#       extent = [-7,49,19,68]
#     elif extentName == "nor_b":
#       extent = [-7,49,19,68]
#     else:
#       extent = GLOB.constants[extentName].value
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    inDir = r"G:\data\Globio4LA\data\referentie\v4012\vector\in_20181123"
    if (extentName == "eu") or extentName == "neu":
      inShp = "frag_rivers_%s.shp" % "wrld"
    else:
      inShp = "frag_rivers_%s.shp" % extentName
    
    outDir = r"G:\data\Globio4LA\data\referentie\v4012\vector\in_20181123"
    outShp = "frag_rivers_connected_%s.shp" % extentName
    
    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Create outdir.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    # Set input/output data.
    inShp = os.path.join(inDir,inShp)
    outShp = os.path.join(outDir,outShp)

    # Remove output data.
    VU.vectorDelete(outShp)

    # Run.
    pCalc.run(ext,cs,inShp,outShp)
  except:
    MON.cleanup()
    Log.err()
  

