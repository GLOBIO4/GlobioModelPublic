# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with cell areas in km2 for different resolutions.
#
# Modified: -
#-------------------------------------------------------------------------------

import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.CalculationBase import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcCellAreaRasters(CalculationBase):
  """
  Calculates rasters with cell areas in km2 for different resolutions.
  """

  # # Wikipedia.
  # worldAreaKM2 = 510100000
  # http://www.jpz.se/Html_filer/wgs_84.html
  worldAreaKM2 = 510065621.724

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcCellAreaRasters,self).__init__()

    # Set internal settings.
    self.mtimer = None
    self.debug = GLOB.debug
    self.test = False

    # Set cellAreaVerion.
    #cellAreaVersion = 1
    self.cellAreaVersion = 2

  #-------------------------------------------------------------------------------
  def calcWorldAreaKm2(self,version: int,cellSizeNames:[str],cellSizes:[float]):

    Log.info("")

    if version == 3:
      cellSizeNames = ["30sec"]
      cellSizes = [GLOB.constants["30sec"].value]


    # Check cell area rasters.
    for idx,cellSize in enumerate(cellSizes):

      cellSizeName = cellSizeNames[idx]

      #Log.info("Processing %s..." % cellSizeName)

      # Get raster filename.
      rasterName = self.getCellAreaRasterName(self.outDir,cellSize,version)

      # Read raster info.
      raster = Raster(rasterName)
      raster.readInfo()

      # Read and sum rows.
      sumArea = float(0.0)
      for r in range(raster.nrRows):
        sumArea += raster.readRow(r).sum()

      Log.info("#"*80)
      Log.info("### v%s - %s ###" % (version,cellSizeName))
      Log.info("#"*80)
      Log.info("World area km2: %s" % self.worldAreaKM2)
      Log.info("Total area km2: %s" % sumArea)
      Log.info("Diff. area km2: %s" % abs(self.worldAreaKM2-sumArea))
      Log.info("")

      # Cleanup.
      del raster

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN STRING CellSizes
    IN INTEGER Version
    OUT DIR OutDir
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=2:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    cellSizeNamesStr = args[0]
    versionStr = args[1]
    outDirName = args[2]

    # Check arguments.
    self.checkInteger(versionStr,1,3)
    self.checkDirectory(outDirName)

    # Convert codes and names to arrays.
    cellSizeNames = self.splitStringList(cellSizeNamesStr)
    cellSizes = [GLOB.constants[c].value for c in cellSizeNames]
    version = int(versionStr)

    # TESTEN RUN
    #test2 = True
    test2 = False
    if test2:
      # 1 cellsize.
      cellSizeNames = [cellSizeNames[0]]
      cellSizes = [cellSizes[0]]

    # Initialize extent (always world).
    extent = GLOB.extent_World

    # Set members.
    self.extent = extent
    self.outDir = outDirName

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    Log.info("Creating: %s" % ",".join(cellSizeNames))

    # Create cell area rasters.
    for idx,cellSize in enumerate(cellSizes):

      cellSizeName = cellSizeNames[idx]

      Log.info("Processing %s..." % cellSizeName)

      # Get raster filename.
      rasterName = self.getCellAreaRasterName(self.outDir,cellSize,version)

      # Overwrite.
      if RU.rasterExists(rasterName):
        RU.rasterDelete(rasterName)

      # Create raster and initialize.
      raster = Raster(rasterName)
      noDataValue = 0.0
      raster.initDataset(extent,cellSize,np.float32,noDataValue)

      # Select cellarea version.
      if version == 1:
        import GlobioModel.Core.CellArea as CellArea
      elif version == 2:
        import GlobioModel.Core.CellArea_V2 as CellArea
      elif version == 3:
        CellArea = None
      else:
        CellArea = None
        Err.raiseGlobioError(Err.UserDefined1,"Invalid cell area Version.")

      if (version == 1) or (version == 2):
        # Calculate cell area column list.
        areaColList = CellArea.createCellAreaList(extent,cellSize,
                                               raster.nrRows,raster.dataType)
        # Write rows.
        for r in range(raster.nrRows):
          # Fill 2d row with repeated column value.
          row = np.repeat(areaColList[r],raster.nrCols).reshape(1,raster.nrCols)
          raster.writeRow(r,row)

      # Cleanup.
      del raster

    #-----------------------------------------------------------------------------
    # Check areas.
    #-----------------------------------------------------------------------------

    self.calcWorldAreaKm2(version,cellSizeNames,cellSizes)

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
