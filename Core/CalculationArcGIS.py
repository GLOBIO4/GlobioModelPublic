# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: -
#-------------------------------------------------------------------------------

#import arcpy
import GlobioModel.Core._arcpy as arcpy

import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log

# Enable using ArcGIS library. 
GLOB.gisLib = GLOB.GIS_LIB_ARCGIS

from GlobioModel.Core.CalculationBase import CalculationBase

import GlobioModel.Common.Utils as Utils

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class CalculationArcGIS(CalculationBase):

  #-------------------------------------------------------------------------------
  # Creates a RasterCalculator expresion to normalize the raster values.
  # Calculation: (value - min) / (max - min)
  def createNormalizeExpr(self,rasterName,minValue,maxValue):
    delta = maxValue-minValue
    expr = "(%s - %s) / %s" % (Utils.strDQuote(rasterName),minValue,delta)
    return expr 

  #-------------------------------------------------------------------------------
  # Creates a RasterCalculator expresion to reclass a list of codes to values.
  # fromCodes  = list of integer codes.
  # toValues   = list of integer or float values.
  # otherValue = will be assigned to cells with codes not in the list. If not
  #              specified then these cells with get the nodata value.
  def createReclassToValueExpr(self,selectRasterName,fromCodes,toValues,otherValue=None):
    expr = ""
    for i in range(len(fromCodes)):
      fromCode = fromCodes[i] 
      toValue = toValues[i]
      if expr == "":
        if otherValue is None:
          expr = "Con(%s == %s,%s)" % (Utils.strDQuote(selectRasterName),
                                       fromCode,toValue)
        else:
          expr = "Con(%s == %s,%s,%s)" % (Utils.strDQuote(selectRasterName),
                                          fromCode,toValue,otherValue)
      else:
        expr = "Con(%s == %s,%s,%s)" % (Utils.strDQuote(selectRasterName),
                                        fromCode,toValue,expr)
    return expr        

  #-------------------------------------------------------------------------------
  # Creates a RasterCalculator expresion to replace a codes with a value.
  # Other cells get their original value.
  # selectRasterName = name of raster where to select code from. 
  # fromCode         = code to select.
  # toValue          = value to change to.
  # orgRasterName    = name of raster with initial values where values of selected
  #                    cells are replaced with toValue.
  def createReplaceToValueExpr(self,selectRasterName,fromCode,toValue,orgRasterName):
    expr = "Con(%s == %s,%s,%s)" % (Utils.strDQuote(selectRasterName),
                                    fromCode,toValue,Utils.strDQuote(orgRasterName))
    return expr
          
  #-------------------------------------------------------------------------------
  # Creates a RasterCalculator expresion to replace a list of codes with values.
  # Cells with codes not in the list get their original value.
  # selectRasterName = name of raster where to select fromCodes from. 
  # fromCodes        = list of integer codes.
  # toValues         = list of integer or float values.
  # orgRasterName    = name of raster with initial values where values of selected
  #                    cells are replaced with toValues.
  def createReplaceToValuesExpr(self,selectRasterName,fromCodes,toValues,orgRasterName):
    expr = ""
    for i in range(len(fromCodes)):
      fromCode = fromCodes[i] 
      toValue = toValues[i]
      if expr == "":
        expr = "Con(%s == %s,%s,%s)" % (Utils.strDQuote(selectRasterName),
                                        fromCode,toValue,Utils.strDQuote(orgRasterName))
      else:
        expr = "Con(%s == %s,%s,%s)" % (Utils.strDQuote(selectRasterName),
                                        fromCode,toValue,expr)
    return expr        

  #-------------------------------------------------------------------------------
  def rasterNormalize(self,inRasterName,outRasterName):
 
    # Get minimum and maximum distance value.
    propResult = arcpy.GetRasterProperties_management(inRasterName,"MINIMUM")
    minValue = Utils.asFloat(propResult.getOutput(0))
    propResult = arcpy.GetRasterProperties_management(inRasterName,"MAXIMUM")
    maxValue = Utils.asFloat(propResult.getOutput(0))

    Log.dbg("minValue: %s" % minValue)
    Log.dbg("maxValue: %s" % maxValue)

    # Minimum and maximum are equal?
    if minValue == maxValue:
      Log.dbg("minValue == maxValue")
      # Set to value 1.0.
      expr = "Con(~IsNull(%s),1)" % Utils.strDQuote(inRasterName)
    else:
      # Normalize.
      expr = self.createNormalizeExpr(inRasterName,minValue,maxValue)

    #Log.dbg("expr: %s" % expr)
      
    # Normalize.
    arcpy.gp.RasterCalculator_sa(expr,outRasterName)

  #-------------------------------------------------------------------------------
  # Replaces nodata with value. 
  def rasterReplaceNoData(self,inRasterName,outRasterName,value):
    expr = "Con(IsNull(%s),%s,%s)" % (Utils.strDQuote(inRasterName),value,Utils.strDQuote(inRasterName))
    arcpy.gp.RasterCalculator_sa(expr,outRasterName)

  #-------------------------------------------------------------------------------
  def rasterToFloat32(self,inRasterName,outRasterName,noDataValue):
    arcpy.CopyRaster_management(inRasterName,outRasterName,
                              "","",noDataValue,"NONE","NONE","32_BIT_FLOAT","NONE","NONE")

  #-------------------------------------------------------------------------------
  def rasterToUInt8(self,inRasterName,outRasterName,noDataValue):
    arcpy.CopyRaster_management(inRasterName,outRasterName,
                              "","",noDataValue,"NONE","NONE","8_BIT_UNSIGNED","NONE","NONE")

  #-------------------------------------------------------------------------------
  # Show an extra header with execution start date and time.
  def showStartMsg(self,args):
    Log.info("")
    Log.headerLine("=")
    Log.info(Utils.strConcatAlignRight(
                        "# Execution start: "+Utils.dateTimeToStr(),
                        Utils.getComputerName(),
                        GLOB.logfileHeaderLength))
    Log.headerLine("=")
    super(CalculationArcGIS,self).showStartMsg(args)
    
