# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************

import os

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcAquaticMSA(CalculationBase):
  """
  Creates a raster with the total aquatic MSA.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER LakeShallowMSA
    IN RASTER LakeDeepMSA
    IN RASTER ReservoirMSA
    IN RASTER RiverMSA
    IN RASTER FlootplainMSA
    IN RASTER WetlandMSA
    IN RASTER LakeShallowFractions
    IN RASTER LakeDeepFractions
    IN RASTER ReservoirShallowFractions
    IN RASTER ReservoirDeepFractions
    IN RASTER RiverFractions
    IN RASTER FlootplainFractions
    IN RASTER WetlandFractions
    OUT RASTER AquaticMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=15:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    lakeShallowMSARasterName = args[2]
    lakeDeepMSARasterName = args[3]
    reservoirMSARasterName = args[4]
    riverMSARasterName = args[5]
    floodplainMSARasterName = args[6]
    wetlandMSARasterName = args[7]
    lakeShallowFractionsRasterName = args[8]
    lakeDeepFractionsRasterName = args[9]
    reservoirShallowFractionsRasterName = args[10]
    reservoirDeepFractionsRasterName = args[11]
    riverFractionsRasterName = args[12]
    floodplainFractionsRasterName = args[13]
    wetlandFractionsRasterName = args[14]
    outRasterName = args[15]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(lakeShallowMSARasterName)
    self.checkRaster(lakeDeepMSARasterName)
    self.checkRaster(reservoirMSARasterName)
    self.checkRaster(riverMSARasterName)
    self.checkRaster(floodplainMSARasterName)
    self.checkRaster(wetlandMSARasterName)
    self.checkRaster(lakeShallowFractionsRasterName)
    self.checkRaster(lakeDeepFractionsRasterName)
    self.checkRaster(reservoirShallowFractionsRasterName)
    self.checkRaster(reservoirDeepFractionsRasterName)
    self.checkRaster(riverFractionsRasterName)
    self.checkRaster(floodplainFractionsRasterName)
    self.checkRaster(wetlandFractionsRasterName)
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Create weighted wetland MSA.
    #-----------------------------------------------------------------------------

    # Create a lists with all msa and fraction rasters.
    msaRasterNames = [lakeShallowMSARasterName,
                      lakeDeepMSARasterName,
                      reservoirMSARasterName,
                      reservoirMSARasterName,
                      riverMSARasterName,
                      floodplainMSARasterName,
                      wetlandMSARasterName]
    msaDescriptions = ["lake (shallow)",
                       "lake (deep)",
                       "reservoir",
                       "reservoir",
                       "river",
                       "floodplain",
                       "wetland"]  
    fracRasterNames = [lakeShallowFractionsRasterName,
                       lakeDeepFractionsRasterName,
                       reservoirShallowFractionsRasterName,
                       reservoirDeepFractionsRasterName,
                       riverFractionsRasterName,
                       floodplainFractionsRasterName,
                       wetlandFractionsRasterName]
    fracDescriptions = ["lake (shallow)",
                        "lake (deep)",
                        "reservoir (shallow)",
                        "reservoir (deep)",
                        "river",
                        "floodplain",
                        "wetland"]  

    Log.info("Calculate weighted MSA...")
    
    # Calculate weighte MSA.
    outRaster = self.calcWeightedMSA(extent,cellSize,
                                     msaRasterNames,msaDescriptions,
                                     fracRasterNames,fracDescriptions)

    #-----------------------------------------------------------------------------
    # Write output raster.
    #-----------------------------------------------------------------------------

    # Save the aquatic MSA raster.
    Log.info("Writing aquatic MSA raster...")
    outRaster.writeAs(outRasterName)

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
    
    inDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
    
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\data\Globio4LA\data\kanweg\20181031_v1"

    pCalc = GLOBIO_CalcAquaticMSA()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec
    laks = os.path.join(inDir,"shallow_lake_msa.tif")
    lakd = os.path.join(inDir,"deep_lake_msa.tif")
    res = os.path.join(inDir,"reservoir_msa.tif")
    riv = os.path.join(inDir,"river_msa.tif")
    flo = os.path.join(inDir,"flootplain_msa.tif")
    wet = os.path.join(inDir,"wetland_msa.tif")
    laksf = os.path.join(inDir,"shallow_lake_fractions.tif")
    lakdf = os.path.join(inDir,"deep_lake_fractions.tif")
    ressf = os.path.join(inDir,"shallow_reservoir_fractions.tif")
    resdf = os.path.join(inDir,"deep_reservoir_fractions.tif")
    rivf = os.path.join(inDir,"river_fractions.tif")
    flof = os.path.join(inDir,"flootplain_fractions.tif")
    wetf = os.path.join(inDir,"wetland_fractions.tif")
    out = os.path.join(outDir,"aquatic_msa.tif")
   
#     ### ZETTEN DUMMIES
#     Log.info("USING DUMMY RASTERS!!!")
#     testDir = r"G:\data\Globio4LA\data\kanweg\20181031_v1"
#     laks = os.path.join(testDir,"shallow_lake_msa.tif")
#     lakd = os.path.join(testDir,"deep_lake_msa.tif")
#     riv = lakd
#     flo = laks
#     wet = lakd

    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,laks,lakd,res,riv,flo,wet,laksf,lakdf,ressf,resdf,rivf,flof,wetf,out)
  except:
    MON.cleanup()
    Log.err()
