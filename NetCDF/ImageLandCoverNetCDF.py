# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Remarks:
#          Class instances will be created dynamically. So a class constructor
#          can not be used (does not work).
#
# Example:
#          C:\data\GLANDCOVER_30MIN.nc#ImageLandCoverNetCDF|1970|Cropland
#
# Modified: 11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#-------------------------------------------------------------------------------

import GlobioModel.Core.Globals as GLOB
from GlobioModel.Core.NetCDF import NetCDF
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ImageLandCoverNetCDF(NetCDF):

  landcoverNamesNetCDFVarName = "NGLNDCOV"
  yearNetCDFVarName = "TIME"
  dataNetCDFVarName = "GLANDCOVER_30MIN"

  #-------------------------------------------------------------------------------
  # Class instances will be created dynamically. So a class constructor can not
  # be used (does not work).
  def __init__(self):
    super(ImageLandCoverNetCDF,self).__init__()

  #-------------------------------------------------------------------------------
  # Filename = .nc filename.
  def init(self,fileName,year,landCoverName):

    # Set world extent.
    extent = GLOB.extent_World

    # Create the NetCDF variable definitions.
    varDefs = [
      "%s%s=%s" % (self.yearNetCDFVarName,"@TIME",year),
      "%s%s=%s" % (self.dataNetCDFVarName,"@RASTER",""),
      "%s%s=%s" % (self.landcoverNamesNetCDFVarName,"@STRING",landCoverName),
    ]

    # Init base class.
    super(ImageLandCoverNetCDF,self).init(fileName,extent,varDefs)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #GLOB.SHOW_TRACEBACK_ERRORS = True

  #-------------------------------------------------------------------------------
  # Reading raster: GLANDCOVER_30MIN.nc#ImageLandCoverNetCDF|1970|Cropland
  # GLANDCOVER_30MIN.nc
  # True
  # ImageLandCoverNetCDF
  # ['GLANDCOVER_30MIN.nc', '1970', 'Cropland']
  # float32
  def testCreateInstance():
    import GlobioModel.Common.Utils as UT

    GLOB.SHOW_TRACEBACK_ERRORS = True

    inRasterName = "GLANDCOVER_30MIN.nc"
    inRasterName += "#ImageLandCoverNetCDF"
    inRasterName += "|1970|Cropland"

    print("Reading raster: %s" % inRasterName)

    print(RU.getNetCDFFileName(inRasterName))
    print(RU.isNetCDFName(inRasterName))

    netCDFType = RU.getNetCDFType(inRasterName)
    print(netCDFType)
    netCDFArgs = RU.getNetCDFArguments(inRasterName)
    print(netCDFArgs)

    netCDF = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)
    netCDF.init(*netCDFArgs)
    if not netCDF is None:
      netCDF.read()
      print(netCDF.r.dtype)

  #-------------------------------------------------------------------------------
  #-------------------------------------------------------------------------------
  #
  # run NetCDF\ImageLandCoverNetCDF.py
  #

  testCreateInstance()
