# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON
import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticStreamflow30sec(CalculationBase):
  """
  Creates a 30sec raster with downscaled (pcr-globwb) streamflow discharge.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER ScenarioStreamflow
    IN RASTER ReferenceStreamflowMean5min
    IN RASTER ReferenceStreamflowMin5min
    IN RASTER ReferenceStreamflowMax5min
    IN RASTER ReferenceStreamflowMean30sec
    IN RASTER ReferenceStreamflowMin30sec
    IN RASTER ReferenceStreamflowMax30sec
    OUT RASTER OutStreamflow 
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    scenStreamflowRasterName = args[1]
    refStreamflowMean5secRasterName = args[2]
    refStreamflowMin5secRasterName = args[3]
    refStreamflowMax5secRasterName = args[4]
    refStreamflowMean30minRasterName = args[5]
    refStreamflowMin30minRasterName = args[6]
    refStreamflowMax30minRasterName = args[7]
    outRasterName = args[8]
 
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(scenStreamflowRasterName)
    self.checkRaster(refStreamflowMean5secRasterName)
    self.checkRaster(refStreamflowMin5secRasterName)
    self.checkRaster(refStreamflowMax5secRasterName)
    self.checkRaster(refStreamflowMean30minRasterName)
    self.checkRaster(refStreamflowMin30minRasterName)
    self.checkRaster(refStreamflowMax30minRasterName)
    self.checkRaster(outRasterName,True)

    # Set cellsize.
    cellSizeName = "30sec"
    cellSize = GLOB.constants[cellSizeName].value
    
    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the scenario raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    scenRaster = self.readAndPrepareInRaster(extent,cellSize,scenStreamflowRasterName,"scenario")

    #-----------------------------------------------------------------------------
    # Read the reference rasters.
    #-----------------------------------------------------------------------------

    # Reads the rasters and resizes to extent and resamples to cellsize.
    refMean5secRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMean5secRasterName,"mean streamflow reference (5min)")
    refMin5secRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMin5secRasterName,"min streamflow reference (5min)")
    refMax5secRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMax5secRasterName,"max streamflow reference (5min)")
    refMean30minRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMean30minRasterName,"mean streamflow reference (30sec)")
    refMin30minRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMin30minRasterName,"min streamflow reference (30sec)")
    refMax30minRaster = self.readAndPrepareInRaster(extent,cellSize,
                                            refStreamflowMax30minRasterName,"max streamflow reference (30sec)")

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------
    
    # Create output raster.
    # Initialize with NoData.
    Log.info("Creating output raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate "Q month Scenario <= Q mean Reference".
    #-----------------------------------------------------------------------------
    
    # Create mask.
    mask = (scenRaster.r <= refMean5secRaster.r)
    mask = np.logical_and(mask,refMean30minRaster.getDataMask())
    mask = np.logical_and(mask,refMin30minRaster.getDataMask())
    mask = np.logical_and(mask,refMean5secRaster.getDataMask())
    mask = np.logical_and(mask,refMin5secRaster.getDataMask())
    mask = np.logical_and(mask,scenRaster.getDataMask())
    
    # Create temporary delta raster for divide.
    noDataValue = -999.0
    deltaRaster = Raster()
    deltaRaster.initRaster(extent,cellSize,np.float32,noDataValue)
    deltaRaster.r[mask] = refMean5secRaster.r[mask] - refMin5secRaster.r[mask]
      
    # Extend mask.
    dMask = (deltaRaster.r != 0.0)
    mask = np.logical_and(mask,dMask)

    # Calculate value.
    outRaster.r[mask] = refMean30minRaster.r[mask] - refMin30minRaster.r[mask]
    outRaster.r[mask] /= deltaRaster.r[mask]
    outRaster.r[mask] *= refMean5secRaster.r[mask] - scenRaster.r[mask]
    outRaster.r[mask] *= -1.0
    outRaster.r[mask] += refMean30minRaster.r[mask]
    
    # Cleanup.
    deltaRaster.close()
    deltaRaster = None
    
    #-----------------------------------------------------------------------------
    # Calculate "Q month Scenario > Q mean Reference".
    #-----------------------------------------------------------------------------

    # Create mask.
    mask = (scenRaster.r > refMean5secRaster.r)
    mask = np.logical_and(mask,refMean30minRaster.getDataMask())
    mask = np.logical_and(mask,refMax30minRaster.getDataMask())
    mask = np.logical_and(mask,refMean5secRaster.getDataMask())
    mask = np.logical_and(mask,refMax5secRaster.getDataMask())
    mask = np.logical_and(mask,scenRaster.getDataMask())

    # Create temporary delta raster for divide.
    noDataValue = -999.0
    deltaRaster = Raster()
    deltaRaster.initRaster(extent,cellSize,np.float32,noDataValue)
    deltaRaster.r[mask] = refMax5secRaster.r[mask] - refMean5secRaster.r[mask]
      
    # Extend mask.
    dMask = (deltaRaster.r != 0.0)
    mask = np.logical_and(mask,dMask)
      
    # Calculate value.
    outRaster.r[mask] = refMax30minRaster.r[mask] - refMean30minRaster.r[mask]
    outRaster.r[mask] /= deltaRaster.r[mask]
    outRaster.r[mask] *= scenRaster.r[mask] - refMean5secRaster.r[mask] 
    outRaster.r[mask] *= -1.0
    outRaster.r[mask] += refMean30minRaster.r[mask]
      
    # Cleanup.
    deltaRaster.close()
    deltaRaster = None
      
    # Clear mask.
    dMask = None
    mask = None

    # Save the streamflow discharge raster.
    Log.info("Writing streamflow discharge raster...")
    outRaster.write()
  
    # Cleanup.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  try:
    # Enable the monitor.
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True
    
    pCalc = GLOBIO_AquaticStreamflow30sec()
    
    extName = "wrld"
    ext = GLOB.constants[extName].value

    inDir1 = r"G:\Data\Globio4LA\data\referentie\v4012\5min_%s\in_20181026" % extName
    inDir2 = r"G:\Data\Globio4LA\data\referentie\v4012\30sec_%s\in_20181026" % extName
    outDir = r"G:\data\Globio4LA\data\kanweg"
    
    if os.path.isdir("/root"):
      inDir1 = UT.toLinux(inDir1)
      inDir2 = UT.toLinux(inDir2)
      outDir = UT.toLinux(outDir)

    sce5 = os.path.join(inDir1,"pcrglobwb_qmi_2015.tif")
    qav5 = os.path.join(inDir1,"pcrglobwb_qav_2015.tif")
    qmi5 = os.path.join(inDir1,"pcrglobwb_qmi_2015.tif")
    qma5 = os.path.join(inDir1,"pcrglobwb_qma_2015.tif")
    qav30 = os.path.join(inDir2,"flo1k_qav_2015.tif")
    qmi30 = os.path.join(inDir2,"flo1k_qmi_2015.tif")
    qma30 = os.path.join(inDir2,"flo1k_qma_2015.tif")
    out = os.path.join(outDir,"scen_streamflow.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)

    # Run.
    pCalc.run(ext,sce5,qav5,qmi5,qma5,qav30,qmi30,qma30,out)
  except:
    Log.err()
