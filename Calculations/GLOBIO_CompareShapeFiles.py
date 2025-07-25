# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 4 jan 2021, ES, ARIS B.V.
#           - Version 4.1.0
#-------------------------------------------------------------------------------

import os

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CompareShapeFiles(CalculationBase):
  """
  Compares two shapefiles and calculates the differences.

  This script can be used to compare a shapefile to its reference to check
  if changes in the code has no effect on the results.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN VECTOR InputShapeFile
    IN VECTOR ReferenceShapeFile
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=1:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    inShapeFileName = args[0]
    refShapeFileName = args[1]
  
    # Check arguments.
    self.checkVector(inShapeFileName)
    self.checkVector(refShapeFileName)

    #-----------------------------------------------------------------------------
    # Read the input shapefile.
    #-----------------------------------------------------------------------------

    # Reads the input shapefile.
    Log.info("Reading input shapefile %s..." % inShapeFileName)
    inVector = Vector(inShapeFileName)
    inVector.read()

    inExtent = inVector.getExtent()

    inLines = []
    for feat in inVector.layer:
      line = loads(feat.GetGeometryRef().ExportToWkb())
      tmpLines = VU.shpMultiLineToLines(line)
      inLines.extend(tmpLines)

    del inVector

    #-----------------------------------------------------------------------------
    # Read the reference shapefile.
    #-----------------------------------------------------------------------------

    # Reads the reference shapefile.
    Log.info("Reading reference shapefile %s..." % refShapeFileName)
    refVector = Vector(refShapeFileName)
    refVector.read()

    refExtent = refVector.getExtent()

    refLines = []
    for feat in refVector.layer:
      line = loads(feat.GetGeometryRef().ExportToWkb())
      tmpLines = VU.shpMultiLineToLines(line)
      refLines.extend(tmpLines)

    del refVector

    #-----------------------------------------------------------------------------
    # Check extent.
    #-----------------------------------------------------------------------------

    Log.info("Checking extent...")

    # Set "virtual" cellsize.
    cellSize = GLOB.cellSize_10sec
    # Check extent.
    if not RU.isEqualExtent(inExtent,refExtent,cellSize):
      Log.info("  The shapefiles have a different extent.")
      Log.info("  - Input shapefile    : %s" % (inExtent,))
      Log.info("  - Reference shapefile: %s" % (refExtent,))
    else:
      Log.info("  The shapefiles have the same extent.")

    #-----------------------------------------------------------------------------
    # Check number of features.
    #-----------------------------------------------------------------------------

    Log.info("Checking nr. of features...")

    # Check extent.
    if not len(inLines) == len(refLines):
      Log.info("  The shapefiles have a different number of features.")
      Log.info("  - Input shapefile          : %s" % len(inLines))
      Log.info("  - Reference shapefile      : %s" % len(refLines))
      Log.info("  - Nr. of different features: %s" % (len(inLines) - len(refLines)))
    else:
      Log.info("  The shapefiles have the same number of features.")

    del inLines
    del refLines

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-----------------------------------------------------------------------------
  def test1():
    try:
      refDir = r""
      inDir = r""

      pCalc = GLOBIO_CompareShapeFiles()
      shapeFileName = "rivers_wrld.shp"
      inShapeFileName = os.path.join(inDir,shapeFileName)
      refShapeFileName = os.path.join(refDir,shapeFileName)

      pCalc.run(inShapeFileName,refShapeFileName)
    except:
      Log.err()

  #-----------------------------------------------------------------------------

  test1()
