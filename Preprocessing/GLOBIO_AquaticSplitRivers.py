# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           13 dec 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - Setting of property HasDam added.
#           14 dec 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - Setting of property Connected added.
#           - MultiLineToLine added.
#           - "frag_" added.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Modified call to checkFloat in run().
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - run modified, because of shapeFileWriteFeatures.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - run modified, list(filter(..)) added.
#-------------------------------------------------------------------------------

import os

from shapely.strtree import STRtree
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
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticSplitRivers(CalculationBase):
  """
  Splits river segments at (nearby) dams.
  """
    
  #-------------------------------------------------------------------------------
  def calculate(self,args):         
       
    # Get arguments.
    # 20201118
    #cellSize = args[0]
    rivers = args[1]         # all rivers
    dams = args[2]           # all dams
    tolerance = args[3]    

    # Create trees for rivers and splitted rivers.
    riverTree = STRtree(rivers)

    # Create dicts.
    damDict = dict()        # dam.FID - dam
    riverDamsDict = dict()  # river.FID - [dams]
 
    #---------------------------------------------------------------------------
    # Find nearest rivers for dams. 
    #---------------------------------------------------------------------------
    
    Log.info("  Getting nearby rivers...")

    # Create list for rivers, splitted included.
    newRivers = []

    # Create a list for dams, snapped included.
    newDams = []

    # Init progress.
    self.initProgress(len(dams))
    
    # Loop all dams.
    for dam in dams:
      
      # Add dam to dict.
      damDict[dam.FID] = dam
      
      # Get nearest river.
      foundRiver = VU.shpTreeFeaturesGetNearestByPoint(riverTree,dam,tolerance)

      # Found?
      if not foundRiver is None:
        self.dbgPrint("  In riverTree found: %s" % foundRiver.wkt[:30])
        # Get river from riverDamDict dict.
        if not foundRiver.FID in riverDamsDict:
          riverDamsDict[foundRiver.FID] = [dam]
        else:
          riverDamsDict[foundRiver.FID].append(dam)
      else:
        # Add original dam.
        newDams.append(dam)
        
    #---------------------------------------------------------------------------
    # Split found rivers at dam locations. 
    #---------------------------------------------------------------------------

    Log.info("  Splitting rivers...")

    # Init progress.
    self.initProgress(len(rivers))
    
    # Loop all rivers.
    for river in rivers:
      
      # Get nearby dam(s) of river.
      riverDams = riverDamsDict.get(river.FID,None)

      # Not found?
      if riverDams is None:
        # Add river to list.
        newRivers.append(river)
      else:
        
        self.dbgPrint("##########")
        self.dbgPrint("river %s" % river.wkt[:80])
        self.dbgPrint("  nr. of riverdams: %s" % len(riverDams))
        for riverDam in riverDams:
          self.dbgPrint("  riverdams %s" % riverDam.wkt)
      
        # Split river on dam locations.
        splittedRivers,snappedDams = VU.shpLineSplitAtPoints(river,riverDams)

        # DEBUG!!!
        self.dbgPrint("  nr. of splitted rivers: %s" % len(splittedRivers))

        # Set Connected property and add splitted rivers to list.
        for splittedRiver in splittedRivers:
          
          # DEBUG!!!
          self.dbgPrint("  splitted river %s" % splittedRiver.wkt[:80])
          
          splittedRiver.Connected = 1
          newRivers.append(splittedRiver)
        # Set Connected property and add snapped dams to list.
        for snappedDam in snappedDams:
          snappedDam.Connected = 1
          newDams.append(snappedDam)
        
      #@@@@@@@@@@@@@@@@@ BREAK
      #break
        
    return (newRivers,newDams)
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Rivers
    IN VECTOR Dams
    IN FLOAT ToleranceDEG
    OUT VECTOR SplittedRivers
    OUT VECTOR SnappedDams
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inRivShapeFileName = args[2]
    inDamShapeFileName = args[3]
    toleranceDEG = args[4]
    outRivShapeFileName = args[5]
    outDamShapeFileName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inRivShapeFileName)
    self.checkVector(inDamShapeFileName)
    self.checkFloat(toleranceDEG,0.0,100.0)
    self.checkVector(outRivShapeFileName,True)
    self.checkVector(outDamShapeFileName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRivShapeFileName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading river shapefile...")

    # Read shapefile.
    inVector = Vector(inRivShapeFileName)
    inVector.read()

    # Get lines, initialize Connected property.
    lines = []
    FID = 0
    for feat in inVector.layer:
      line = loads(feat.GetGeometryRef().ExportToWkb())
      line.Connected = 0
      line.FID = FID
      lines.append(line)      
      FID += 1

    Log.info("Total number of rivers found: %s" % len(lines))    

    # Clean up.
    inVector.close()
    inVector = None

    #---------------------------------------------------------------------------
    # Read features. 
    #---------------------------------------------------------------------------

    Log.info("Reading dam shapefile...")

    # Read shapefile.
    inVector = Vector(inDamShapeFileName)
    inVector.read()

    # Get points, initialize FID.
    points = []
    FID = 0
    for feat in inVector.layer:
      point = loads(feat.GetGeometryRef().ExportToWkb())
      point.Connected = 0
      point.FID = FID
      points.append(point)      
      FID += 1
      
    Log.info("Total number of dams found: %s" % len(points))    

    # Clean up.
    inVector.close()
    inVector = None

    #-----------------------------------------------------------------------------
    # Calculate connected rivers.
    #-----------------------------------------------------------------------------

    Log.info("Splitting rivers...")    

    # Calculate connected rivers.
    results = self.calculate([0,lines,points,toleranceDEG])
    
    newRivers = results[0]
    newDams = results[1]
    
    Log.info("Number of rivers: %s" % len(newRivers))
    Log.info("Number of dams: %s" % len(newDams))

    # Get connected rivers and dams.
    # 20201209
    # conRivers = filter(lambda x: x.Connected==1,newRivers)
    # conDams = filter(lambda x: x.Connected==1,newDams)
    conRivers = list(filter(lambda x: x.Connected==1,newRivers))
    conDams = list(filter(lambda x: x.Connected==1,newDams))

    Log.info("Number of connected rivers: %s" % len(conRivers))
    Log.info("Number of connected dams: %s" % len(conDams))
      
    #-----------------------------------------------------------------------------
    # Write output.
    #-----------------------------------------------------------------------------

    Log.info("Writing rivers...")

    # Write rivers.
    VU.shapeFileWriteFeatures(outRivShapeFileName,newRivers,["Connected"],[ogr.OFTInteger])

    Log.info("Writing dams...")

    # Write dams.
    VU.shapeFileWriteFeatures(outDamShapeFileName,newDams,["Connected"],[ogr.OFTInteger])

    # Clean up.
    lines = None
    points = None
    newRivers = None
    newDams = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
       
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True
    
    pCalc = GLOBIO_AquaticSplitRivers()
    pCalc.debugPrint = False
    
    extentName = "wrld"
    #extentName = "nl"
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    inDir = r""
    inRiv = "rivers_%s.shp" % extentName
    inDam = "dams_%s.shp" % extentName
    
    outDir = r""
    outRiv = "frag_rivers_%s.shp" % extentName
    outDam = "frag_dams_%s.shp" % extentName

    # Set the tollerance for searching.
    #tolerance = cellSize / 10.0
    #tolerance = cellSize * 5
    tolerance = cs
    
    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)

    # Create outdir.
    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    # Set input/output data.
    inRiv = os.path.join(inDir,inRiv)
    inDam = os.path.join(inDir,inDam)
    outRiv = os.path.join(outDir,outRiv)
    outDam = os.path.join(outDir,outDam)

    # Remove output data.
    VU.vectorDelete(outRiv)    
    VU.vectorDelete(outDam)    

    # Run.
    pCalc.run(ext,cs,inRiv,inDam,outRiv,outDam)
  except:
    MON.cleanup()
    Log.err()
  
