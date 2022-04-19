# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#           17 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - getTauDEMPath modified, now throws an exception.
#           - runTauDEMAreaD8 modified, now throws an exception.
#           - run modified, handling TauDEM function returns.
#           17 nov 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           - getTauDEMPath modified.
#           - runTauDEMAreaD8 modified, quotes for Windows to path added.
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - runTauDEMAreaD8 modified.
#-------------------------------------------------------------------------------

import os
import numpy as np
import subprocess as sp

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.CellArea as CA
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcAquaticFRHLU(CalculationBase):
  """
  Creates a raster with the anthropogenic landuse fractions in 
  upstream catchments (FRHLU).
  """

  # Name of TAUDEMPATH environment variable.
  varTaudemPath = "TAUDEMPATH"
  
  #-----------------------------------------------------------------------------
  # Gets the TAUDEMPATH environment variable. Also checks if the 
  # environment variable variable exists and has an valid path.
  # Returns the path.
  # Throws an exception when an error occurred.
  def getTauDEMPath(self):

    # Check environment variable.
    if not self.varTaudemPath in os.environ:
      msg = "The environment variable '%s' is not defined. " + \
            "Run aborted." % self.varTaudemPath
      Err.raiseGlobioError(Err.UserDefined1,msg)

    # Get path and check.
    taudemPath = os.environ[self.varTaudemPath]
    if taudemPath=="":
      # 20201117
#      msg = "The TauDEM path '%s' is not specified. " + \
#            "Run aborted." % self.taudemPath
      msg = "The TauDEM path '%s' is not specified. " + \
            "Run aborted." % (taudemPath)
      Err.raiseGlobioError(Err.UserDefined1,msg)
    if not os.path.isdir(taudemPath):
      # 20201117
#      msg = "The TauDEM path '%s' is not found. " + \
#            "Run aborted." % self.taudemPath
      msg = "The TauDEM path '%s' is not found. " + \
            "Run aborted." % (taudemPath)
      Err.raiseGlobioError(Err.UserDefined1,msg)
    
    return taudemPath

  #-----------------------------------------------------------------------------
  # Runs the TauDEM AreaD8 molule.
  # Throws an exception when an error occurred.
  def runTauDEMAreaD8(self,taudemPath,flowDirectionRasterName,
                      weightRasterName,outRasterName,nrOfCores=6):

    # Set exe's.
    mpiexecExe = os.path.join(taudemPath,"mpiexec")
    taudemExe = os.path.join(taudemPath,"aread8")

    if not UT.isLinux():
      # Add quotes for Windows.
      if not mpiexecExe.startswith('"'):
        mpiexecExe = '"%s"' % (mpiexecExe)
      if not taudemExe.startswith('"'):
        taudemExe = '"%s"' % (taudemExe)

    # Create commandline.  
    flowArg = "-p %s" % flowDirectionRasterName
    if weightRasterName!="":
      weightArg = "-wg %s" % weightRasterName
    else:
      weightArg = ""
    outArg = "-ad8 %s" % outRasterName
    cmd = "%s -np %s %s %s %s %s" % (mpiexecExe,nrOfCores,taudemExe,
                                     flowArg,weightArg,outArg)

    print('cmd: %s' %cmd)
    # Run the TauDEM AreaD8 molule.
    p = sp.Popen(cmd,shell=True,stdout=sp.PIPE,stderr=sp.STDOUT)

    # Collect stdout.    
    linesSTDOUT = []
    for line in p.stdout.readlines():
      linesSTDOUT.append(line.decode("utf-8"))
      
    # Wait and get return value.  
    retval = p.wait()

    # Check return value.
    if retval!=0:
      # Toon de TauDEM AreaD8 uitvoer.
      msg = "Error while running the TauDEM AreaD8 molule:"
      for line in linesSTDOUT:
        if line.strip() != "":
          msg += "  " + line
      Err.raiseGlobioError(Err.UserDefined1,msg)
  # 20201202    
  # def runTauDEMAreaD8(self,taudemPath,flowDirectionRasterName,
  #                      weightRasterName,outRasterName,nrOfCores=6):

  #   # 20201117
  #   # Add quotes to path for Windows.
  #   if not UT.isLinux():
  #     # Windows, not already quoted?
  #     if not taudemPath.startswith('"'):
  #       taudemPath = '"%s"' % (taudemPath)


  #   # Create commandline.  
  #   flowArg = "-p %s" % flowDirectionRasterName
  #   if weightRasterName!="":
  #     weightArg = "-wg %s" % weightRasterName
  #   else:
  #     weightArg = ""
  #   outArg = "-ad8 %s" % outRasterName
  #   # cmd = "mpiexec -np %s %s/aread8 %s %s %s" % (nrOfCores,taudemPath,
  #   #                                              flowArg,weightArg,outArg)
  #   cmd = "mpiexec -np %s %s\\aread8 %s %s %s" % (nrOfCores,taudemPath,
  #                                                flowArg,weightArg,outArg)
  #   # Run the TauDEM AreaD8 molule.
  #   p = sp.Popen(cmd,shell=True,stdout=sp.PIPE,stderr=sp.STDOUT)

  #   # Collect stdout.    
  #   linesSTDOUT = []
  #   for line in p.stdout.readlines():
  #     linesSTDOUT.append(line)
      
  #   # Wait and get return value.  
  #   retval = p.wait()

  #   # Check return value.
  #   if retval!=0:
  #     # Toon de TauDEM AreaD8 uitvoer.
  #     msg = "Error while running the TauDEM AreaD8 molule:"
  #     for line in linesSTDOUT:
  #       if line.strip() != "":
  #         #msg += "  " + line
  #         msg += "  %s" % line
  #     Err.raiseGlobioError(Err.UserDefined1,msg)

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER Landuse10sec
    IN RASTER FlowDirections
    OUT RASTER FRHLU
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    luRasterName = args[2]
    flowDirectionRasterName = args[3]
    outFRHLURasterName = args[4]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(luRasterName)
    self.checkRaster(flowDirectionRasterName)
    self.checkRaster(outFRHLURasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outFRHLURasterName)

    # Set tmp raster names.
    tmpAntFracRasterName = os.path.join(self.outDir,"tmp_frhlu_anthro_fractions.tif")
    tmpWeightedAreaRasterName = os.path.join(self.outDir,"tmp_frhlu_weighted_area.tif")
    tmpTotalAreaRasterName = os.path.join(self.outDir,"tmp_frhlu_total_area.tif")
    # 20200917
    tmpFlowDirectionRasterName = os.path.join(self.outDir,"tmp_flowdirection.tif")
    
    # Remove tmp rasters.
    RU.rasterDelete(tmpAntFracRasterName)
    RU.rasterDelete(tmpWeightedAreaRasterName)
    RU.rasterDelete(tmpTotalAreaRasterName)
    # 20200917
    RU.rasterDelete(tmpFlowDirectionRasterName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Get and check the TAUDEMPATH environment variable.
    #-----------------------------------------------------------------------------

    # Get and check the path.
    taudemPath = self.getTauDEMPath()  

    #-----------------------------------------------------------------------------
    # Create 10sec area raster for anthropogenic landuse.
    #-----------------------------------------------------------------------------

    Log.info("Creating anthropogenic area raster...")

    # Set 10sec cellsize.
    areaCellSizeName = "10sec"
    areaCellSize = GLOB.constants[areaCellSizeName].value

    # Create area raster.
    anthrAreaRaster = Raster()
    anthrAreaRaster.initRasterEmpty(extent,areaCellSize,np.float32,-999.0)
    anthrAreaRaster.r = CA.createCellAreaRaster(extent,areaCellSize,np.float32)

    #-----------------------------------------------------------------------------
    # Read landuse raster.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    luRaster = self.readAndPrepareInRaster(extent,areaCellSize,luRasterName,"landuse")

    #-----------------------------------------------------------------------------
    # Create mask for anthropogenic landuse.
    #-----------------------------------------------------------------------------

    Log.info("Selecting anthropogenic landuse...")

    # Select the anthropogenic landuse types: urban|crop|pasture.
    luTypes = [1,2,3]
    mask = None
    for luType in luTypes:
      if mask is None:
        mask = (luRaster.r == luType)
      else:
        mask = np.logical_or(mask,(luRaster.r == luType))
        
    # Set area to 0.0 for all non-anthropogenic cells.
    anthrAreaRaster.r[~mask] = 0.0                  # pylint: disable=invalid-unary-operand-type

    # Cleanup.
    luRaster.close()
    luRaster = None
    
    #-----------------------------------------------------------------------------
    # Calculate anthropogenic area of <cellsize> cells.
    #-----------------------------------------------------------------------------

    Log.info("Calculating anthropogenic landuse area...")

    # Resample 10sec raster to <cellsize> and sum areas.
    resAnthrAreaRaster = anthrAreaRaster.resample(cellSize,calcSumDiv=True)

    # Cleanup.
    anthrAreaRaster.close()
    anthrAreaRaster = None
    
    #-----------------------------------------------------------------------------
    # Create <cellsize> total area raster.
    #-----------------------------------------------------------------------------

    # Create area raster.
    totAreaRaster = Raster()
    totAreaRaster.initRasterEmpty(extent,cellSize,np.float32,-999.0)
    totAreaRaster.r = CA.createCellAreaRaster(extent,cellSize,np.float32)

    #-----------------------------------------------------------------------------
    # Calculate anthropogenic fraction.
    #-----------------------------------------------------------------------------

    Log.info("Calculating anthropogenic fractions...")
    
    # Create anthropogenic fraction raster.
    anthrFracRaster = Raster(tmpAntFracRasterName)
    anthrFracRaster.initRasterEmpty(extent,cellSize,np.float32,-999.0)
    anthrFracRaster.r = resAnthrAreaRaster.r / totAreaRaster.r
    
    # Correct fractions > 1.0.
    mask = (anthrFracRaster.r > 1.0)
    anthrFracRaster.r[mask] = 1.0
    
    # Cleanup.
    mask = None
    resAnthrAreaRaster.close()
    resAnthrAreaRaster = None
    totAreaRaster.close()
    totAreaRaster = None

    #-----------------------------------------------------------------------------
    # Write anthropogenic fraction.
    #-----------------------------------------------------------------------------

    # Save the anthropogenic fractions.
    Log.info("Writing anthropogenic fractions...")
    anthrFracRaster.write()

    # Cleanup.
    anthrFracRaster.close()
    anthrFracRaster = None

    #-----------------------------------------------------------------------------
    # Resize/resample flow direction raster.
    #-----------------------------------------------------------------------------

    # Need to resize/resample?
    if not RU.rasterHasExtentCellSize(flowDirectionRasterName,extent,cellSize):
      
      # Read the raster and resizes to extent and resamples to cellsize.
      flowDirRaster = self.readAndPrepareInRaster(extent,cellSize,
                                                  flowDirectionRasterName,"flow direction")
      # Save the flow direction.
      Log.info("Writing flow direction...")
      flowDirRaster.writeAs(tmpFlowDirectionRasterName)

      # Cleanup.
      flowDirRaster.close()
      flowDirRaster = None
    else:
      # No resize/resample is needed. Just set tmp flow direction raster name.
      tmpFlowDirectionRasterName = flowDirectionRasterName
      
    #-----------------------------------------------------------------------------
    # Calculate weighted upstream anthropogenic areas.
    # Use fractions as weighting.
    #-----------------------------------------------------------------------------

    # Run the TauDEM AreaD8 module.
    Log.info("Calculating weighted upstream anthropogenic areas...")
    self.runTauDEMAreaD8(taudemPath,tmpFlowDirectionRasterName,
                         tmpAntFracRasterName,tmpWeightedAreaRasterName)  

    #-----------------------------------------------------------------------------
    # Calculate total upstream anthropogenic areas.
    # Use no weighting.
    #-----------------------------------------------------------------------------

    # Run the TauDEM AreaD8 module.
    Log.info("Calculating total upstream areas...")
    self.runTauDEMAreaD8(taudemPath,tmpFlowDirectionRasterName,"",
                         tmpTotalAreaRasterName)  

    #-----------------------------------------------------------------------------
    # Calculate upstream anthropogenic fractions.
    #-----------------------------------------------------------------------------
  
    Log.info("Reading weighted upstream anthropogenic areas...")
    
    # Reads the weighted upstream anthropogenic areas.
    weightedAreaRaster = Raster(tmpWeightedAreaRasterName)
    weightedAreaRaster.read()

    Log.info("Reading total upstream areas...")
    
    # Reads the total upstream areas.
    totalAreaRaster = Raster(tmpTotalAreaRasterName)
    totalAreaRaster.read()

    # Create mask.
    mask = (totalAreaRaster.r > 0.0)

    Log.info("Creating upstream anthropogenic fractions raster...")

    # Create raster.
    # Initialize with NoData.
    noDataValue = -999.0
    outFRHLURaster = Raster(outFRHLURasterName)
    outFRHLURaster.initRaster(extent,cellSize,np.float32,noDataValue)
    
    Log.info("Calculating upstream anthropogenic fractions...")

    outFRHLURaster.r[mask] = weightedAreaRaster.r[mask] / totalAreaRaster.r[mask]
     
    # Cleanup.
    mask = None
    weightedAreaRaster.close()
    weightedAreaRaster = None
    totalAreaRaster.close()
    totalAreaRaster = None

    # Remove tmp rasters?   
    if not GLOB.saveTmpData:
      RU.rasterDelete(tmpAntFracRasterName)
      RU.rasterDelete(tmpWeightedAreaRasterName)
      RU.rasterDelete(tmpTotalAreaRasterName)
      # 20200917
      # 20211115: MB: Only remove tmpFlowDirectionRasterName if tmpFlowDirection is
      #           resized or changed extent; the original code removes input FlowDirection 
      #           raster
      if not RU.rasterHasExtentCellSize(flowDirectionRasterName,extent,cellSize):
        RU.rasterDelete(tmpFlowDirectionRasterName)

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the wetland loss fractions.
    Log.info("Writing upstream anthropogenic fractions...")
    outFRHLURaster.write()

    # Cleanup.
    outFRHLURaster.close()
    outFRHLURaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    #GLOB.monitorEnabled = True
    GLOB.monitorEnabled = False
    GLOB.SHOW_TRACEBACK_ERRORS = True
    GLOB.saveTmpData = True

    pCalc = GLOBIO_CalcAquaticFRHLU()
    
    extentName = "wrld"
    cellSizeName = "30sec"

    ext = GLOB.constants[extentName].value
    cs = GLOB.constants[cellSizeName].value

    inLuDir = r"G:\data\Globio4LA\data\referentie\v407\10sec_wrld\landalloc_20170830"
    inFlDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
    outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"

    if os.path.isdir("/root"):
      inLuDir = UT.toLinux(inLuDir)
      inFlDir = UT.toLinux(inFlDir)
      outDir = UT.toLinux(outDir)

    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    lu = os.path.join(inLuDir,"landuse_alloc_v2.tif")
    flow = os.path.join(inFlDir,"river_flowdirection.tif")
    outLuFrac = os.path.join(outDir,"frhlu_lu_fractions.tif")
    outFrhlu = os.path.join(outDir,"frhlu.tif")

    RU.rasterDelete(outLuFrac)
    RU.rasterDelete(outFrhlu)

    pCalc.run(ext,cs,lu,flow,outLuFrac,outFrhlu)
  except:
    Log.err()

