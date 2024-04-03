# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Argument NumberOfCores added.
#-------------------------------------------------------------------------------

import os
import numpy as np

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Core.CellArea as CA
import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticLakeReservoirFractions import AquaticLakeReservoirFractions
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticLakeReservoirFractions(CalculationBase):
  """
  Calculates fractions for lakes and reservoirs.
  """
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR LakesReservoirs
    IN STRING TypeFieldName
    IN STRING LakeTypes
    IN STRING ReservoirTypes
    IN STRING DepthFieldName
    IN FLOAT DepthThresholdM
    IN INTEGER NumberOfCores
    OUT RASTER LakeShallowFractions
    OUT RASTER LakeDeepFractions
    OUT RASTER ReservoirShallowFractions
    OUT RASTER ReservoirDeepFractions
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=12:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    inShapeFileName = args[2]
    typeFieldName = args[3]
    lakeTypesStr = args[4]
    reservTypesStr = args[5]
    depthFieldName = args[6]
    depthThresholdM = args[7]
    nrOfCores = args[8]
    lakeShallRasterName = args[9]
    lakeDeepRasterName = args[10]
    reservShallRasterName = args[11]
    reservDeepRasterName = args[12]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(inShapeFileName)
    self.checkFieldName(typeFieldName,"type")
    self.checkIntegerList(lakeTypesStr)
    self.checkIntegerList(reservTypesStr)
    self.checkFieldName(depthFieldName,"depth")
    self.checkFloat(depthThresholdM,0.0,9999.0)
    self.checkInteger(nrOfCores,-9999,9999)    
    self.checkRaster(lakeShallRasterName,True)
    self.checkRaster(lakeDeepRasterName,True)
    self.checkRaster(reservShallRasterName,True)
    self.checkRaster(reservDeepRasterName,True)

    # Convert types to array.
    lakeTypes = self.splitIntegerList(lakeTypesStr)
    reservTypes = self.splitIntegerList(reservTypesStr)
    
    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(lakeShallRasterName)
    
    self.enableLogToFile(self.outDir)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Create the watertype area and fraction rasters.
    #-----------------------------------------------------------------------------

    # Initialize area raster.
    areaRas = None

    # Set parameters: fracRasterName,waterTypes,deepFlag.
    params = [(lakeShallRasterName,lakeTypes,False),
              (lakeDeepRasterName,lakeTypes,True),
              (reservShallRasterName,reservTypes,False),
              (reservDeepRasterName,reservTypes,True)
              ]

    # Loop parameters.    
    for param in params:
      fracRasterName = param[0]
      waterTypes = param[1]
      deepFlag = param[2]
    
      Log.info("Creating raster '%s'..." % os.path.basename(fracRasterName))
        
      # Create worker.
      w = AquaticLakeReservoirFractions(nrOfCores)
      nrOfChunks = w.nrOfCores * 8

      #-----------------------------------------------------------------------------
      # Create the cell area raster.
      #-----------------------------------------------------------------------------
      if areaRas is None:
        Log.info("Creating cell area raster...")
        # Create the cell area raster array.
        areaRas = CA.createCellAreaRaster(extent,cellSize)

      #---------------------------------------------------------------------------
      # Read features. 
      #---------------------------------------------------------------------------

      Log.info("Reading shapefile...")
      
      # Create the attribute filter using fields: Lake_type and Depth_avg.
      selType = []
      for waterType in waterTypes:
        selType.append("(%s = %s)" % (typeFieldName,waterType))
      attrFilter = " OR ".join(selType)  
      if deepFlag:
        attrFilter = "(%s) and (%s > %s)" % (attrFilter,depthFieldName,depthThresholdM)
      else:
        attrFilter = "(%s) and (%s <=  %s)" % (attrFilter,depthFieldName,depthThresholdM)
      self.dbgPrint("  Using filter: %s" % attrFilter)    
        
      # Read the shapefile.
      inVector = Vector(inShapeFileName)
      inVector.read()
      inVector.setAttributeFilter(attrFilter)
  
      # Get the lake and reservoir polygons.
      polys = [loads(feat.GetGeometryRef().ExportToWkb()) for feat in inVector.layer]

      Log.info("Total number of features found: %s" % len(polys))    

      # Clean up.
      inVector.close()
      inVector = None
      
      #-----------------------------------------------------------------------------
      # Calculate the watertype area raster.
      #-----------------------------------------------------------------------------

      Log.info("Calculating watertype area raster...")

      # Calculate watertype area raster.
      w.debug = self.debugPrint
      Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
      wtAreaRaster = w.run(extent,cellSize,polys,
                           depthThresholdM,deepFlag,nrOfChunks)

      # Save temporary data?
      if GLOB.saveTmpData:
        Log.info("Writing watertype area raster...")
        # Create tmp raster name.
        tmpRasterName = os.path.join(self.outDir,"tmp_"+os.path.basename(fracRasterName))
        # Remove tmp data.
        RU.rasterDelete(tmpRasterName)
        # Write watertype area.
        wtAreaRaster.writeAs(tmpRasterName)

      #-----------------------------------------------------------------------------
      # Calculate the watertype fraction raster.
      #-----------------------------------------------------------------------------
       
      Log.info("Creating watertype fraction raster...")

      # Create fraction raster.
      fracRaster = Raster(fracRasterName)
      noDataValue = -999.0
      fracRaster.initRaster(extent,cellSize,np.float32,noDataValue)
      
      # Select valid watertype cells.
      mask = (wtAreaRaster.r > 0.0)
      
      Log.info("Calculating fraction...")

      # Calculate fraction.
      fracRaster.r[mask] = wtAreaRaster.r[mask] / areaRas[mask]

      Log.info("Writing watertype fraction raster...")

      # Write watertype fraction.
      fracRaster.write()
       
      # Cleanup.
      mask = None
      wtAreaRaster.close()
      wtAreaRaster = None
      fracRaster.close()
      fracRaster = None

    # Cleanup.
    areaRas = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-----------------------------------------------------------------------------
  def main_20200908():
    try:
      GLOB.saveTmpData = False
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticLakeReservoirFractions()
      pCalc.debugPrint = False

      extentName = "wrld"
      #extentName = "nl"
      cellSizeName = "30sec"

      ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "nl":
        inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20181109"
        lakes = "lakes_nl_wgs84.shp"
      else:
        inDir = r"G:\data\Globio4LA\data\pbl_20181023\HydroLakes\shapefile"
        lakes = "HydroLAKES_polys_v10.shp"

      lsfrac = "shallow_lake_fractions.tif"
      ldfrac = "deep_lake_fractions.tif"
      rsfrac = "shallow_reservoir_fractions.tif"
      rdfrac = "deep_reservoir_fractions.tif"

      outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_%s\in_20181123" % extentName

      tyField = "Lake_type"
      laTypes = "1|3"  
      resTypes = "2"  
      depField = "Depth_avg"
      depTh = 9.0

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      lakes = os.path.join(inDir,lakes)
      lsfrac = os.path.join(outDir,lsfrac)
      ldfrac = os.path.join(outDir,ldfrac)
      rsfrac = os.path.join(outDir,rsfrac)
      rdfrac = os.path.join(outDir,rdfrac)

      # Remove output data.
      RU.rasterDelete(lsfrac)
      RU.rasterDelete(ldfrac)
      RU.rasterDelete(rsfrac)
      RU.rasterDelete(rdfrac)

      # Run.
      pCalc.run(ext,cs,lakes,tyField,laTypes,resTypes,depField,depTh,
                lsfrac,ldfrac,rsfrac,rdfrac)
    except:
      MON.cleanup()
      Log.err()

  #-----------------------------------------------------------------------------
  def main():
    try:
      GLOB.saveTmpData = False
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticLakeReservoirFractions()
      pCalc.debugPrint = False

      extentName = "wrld"
      #extentName = "nl"
      cellSizeName = "30sec"

      ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      if extentName == "nl":
        inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\test_20181109"
        lakes = "lakes_nl_wgs84.shp"
      else:
        #inDir = r"G:\data\Globio4LA\data\pbl_20181023\HydroLakes\shapefile"
        inDir = r"G:\data\Globio4LA\data\pbl_20200806\HydroLAKES_polys_v10_shp"
        lakes = "HydroLAKES_polys_v10.shp"

      lsfrac = "shallow_lake_fractions.tif"
      ldfrac = "deep_lake_fractions.tif"
      rsfrac = "shallow_reservoir_fractions.tif"
      rdfrac = "deep_reservoir_fractions.tif"

      #outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_%s\in_20181123" % extentName
      outDir = r"G:\data\Globio4LA\data\referentie\v4015\30sec_%s\in_20200909" % extentName

      tyField = "Lake_type"
      laTypes = "1|3"  
      resTypes = "2"  
      depField = "Depth_avg"
      # 20200908
      #depTh = 9.0
      depTh = 3.0

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input/output data.
      lakes = os.path.join(inDir,lakes)
      lsfrac = os.path.join(outDir,lsfrac)
      ldfrac = os.path.join(outDir,ldfrac)
      rsfrac = os.path.join(outDir,rsfrac)
      rdfrac = os.path.join(outDir,rdfrac)

      # Remove output data.
      RU.rasterDelete(lsfrac)
      RU.rasterDelete(ldfrac)
      RU.rasterDelete(rsfrac)
      RU.rasterDelete(rdfrac)

      # Run.
      pCalc.run(ext,cs,lakes,tyField,laTypes,resTypes,depField,depTh,
                lsfrac,ldfrac,rsfrac,rdfrac)
    except:
      MON.cleanup()
      Log.err()

  #-------------------------------------------------------------------------------
  main()
