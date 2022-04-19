# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 22 jun 2016, ES, ARIS B.V.
#           - Version 4.0.6
#           - hasPointGeometry added.
#           - getGeometryType modified.
#           - addPointGeometry added.
#           - read modified, see Raster.
#           21 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - self.dataSource added.
#           - write added.
#           - addLine added.
#           - addBox added.
#           - addMultiLine added.
#-------------------------------------------------------------------------------

import os

import osgeo.ogr as ogr
import osgeo.osr as osr

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as UT

import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Vector(object):
  fileName = ""
  driver = None
  dataSource = None
  layer = None
  fieldNames = None
  attrFilter = None
  
  #-------------------------------------------------------------------------------
  # Creates an empty vector when no fileName is specified. To create a new one
  # use create().
  def __init__(self,fileName=None):
    self.fileName = fileName
    self.driver = None
    self.dataSource = None
    self.layer = None
    self.fieldNames = None
    self.attrFilter = None

  #-------------------------------------------------------------------------------
  def __del__(self):
    self.close()
    
  #-------------------------------------------------------------------------------
  # Points: a list of [x,y] array or (x,y) tuple.
  def addBox(self,minX,minY,maxX,maxY,names=None,values=None):

    # Create ring.
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(minX,minY)
    ring.AddPoint(minX,maxY)
    ring.AddPoint(maxX,maxY)
    ring.AddPoint(maxX,minY)
    ring.AddPoint(minX,minY)
    
    # Create polygon.
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    
    # Create the feature.
    toFeature = ogr.Feature(self.layer.GetLayerDefn())
    toFeature.SetGeometry(poly)

    if (not names is None) and (not values is None):
      # Set field values.
      for i in range(len(names)):
        toFeature.SetField(names[i],values[i])

    # Add new feature to output Layer.
    self.layer.CreateFeature(toFeature)
    
  #-------------------------------------------------------------------------------
  # fieldType - ogr.OFTString, ogr.OFTInteger, ogr.OFTReal...
  def addField(self,fieldName,fieldType,fieldWidth=None):
    pField = ogr.FieldDefn(fieldName,fieldType)
    if not fieldWidth is None:
      # TODO: Geeft een warning, maar lijkt wel ok.
      pField.SetWidth(fieldWidth)
    self.layer.CreateField(pField)

  #-------------------------------------------------------------------------------
  # Points: a list of [x,y] array or (x,y) tuple.
  # Example:
  #   from shapely.geometry import LineString
  #   line = LineString([(0, 0), (1, 1)])
  #   outVector.addLine(line.coords)
  def addLine(self,points,names=None,values=None):
    
    # Create line geometry. 
    line = ogr.Geometry(ogr.wkbLineString)

    # Add points.
    for point in points:
      line.AddPoint(point[0],point[1])
    
    # Create the feature.
    toFeature = ogr.Feature(self.layer.GetLayerDefn())
    toFeature.SetGeometry(line)

    if (not names is None) and (not values is None):
      # Set field values.
      for i in range(len(names)):
        toFeature.SetField(names[i],values[i])

    # Add new feature to output Layer.
    self.layer.CreateFeature(toFeature)

  #-------------------------------------------------------------------------------
  # Lines: a list of a list of [x,y] array or (x,y) tuple.
  # Example:
  #   from shapely.geometry import MultiLineString
  #   multiline = MultiLineString([(0, 0), (1, 1)])
  #   outVector.addLine(line.coords)
  def addMultiLine(self,lines,names=None,values=None):
    
    # Create multiline geometry. 
    multiLine = ogr.Geometry(ogr.wkbMultiLineString)

    # Create and add lines.
    for linePoints in lines:
      line = ogr.Geometry(ogr.wkbLineString)
      # Add line points.
      for point in linePoints:
        line.AddPoint(point[0],point[1])
      # Add line.
      multiLine.AddGeometry(line)

    # Create the feature.
    toFeature = ogr.Feature(self.layer.GetLayerDefn())
    toFeature.SetGeometry(multiLine)

    if (not names is None) and (not values is None):
      # Set field values.
      for i in range(len(names)):
        toFeature.SetField(names[i],values[i])

    # Add new feature to output Layer.
    self.layer.CreateFeature(toFeature)

  #-------------------------------------------------------------------------------
  def addPoint(self,x,y,names=None,values=None):
    
    # Create the WKT point.
    wkt = "POINT(%f %f)" %  (float(x),float(y))
    # Create the point from the Well Known Txt
    point = ogr.CreateGeometryFromWkt(wkt)
    
    # Create the feature.
    toFeature = ogr.Feature(self.layer.GetLayerDefn())
    toFeature.SetGeometry(point)

    if (not names is None) and (not values is None):
      # Set field values.
      for i in range(len(names)):
        toFeature.SetField(names[i],values[i])

    # Add new feature to output Layer.
    self.layer.CreateFeature(toFeature)

  #-------------------------------------------------------------------------------
  def addPointGeometry(self,pntGeometry):
    # Create a new feature.
    feature = ogr.Feature(self.layer.GetLayerDefn())
    feature.SetGeometry(pntGeometry)
    # Add the new feature to the Layer.
    self.layer.CreateFeature(feature)

  #-------------------------------------------------------------------------------
  def close(self):
    if not self.dataSource is None:
      self.dataSource.Destroy()
      self.dataSource = None

  #-------------------------------------------------------------------------------
  def copyFrom(self,fromVector):
    fromLayer = fromVector.layer
    toLayerDefn = self.layer.GetLayerDefn()
    toNameRefs = []
    fromFieldIndexs = []
    for i in range(toLayerDefn.GetFieldCount()):
      fieldName = toLayerDefn.GetFieldDefn(i).GetNameRef()
      toNameRefs.append(fieldName)
      fromIndex = fromVector.getFieldIndexByName(fieldName)
      fromFieldIndexs.append(fromIndex)
    
    for fromFeature in fromLayer:
      # Create the feature.
      toFeature = ogr.Feature(toLayerDefn)
      # Add field values from fromLayer.
      for i in range(toLayerDefn.GetFieldCount()):
        fieldName = toLayerDefn.GetFieldDefn(i).GetNameRef()
        fromIndex = fromFieldIndexs[toNameRefs.index(fieldName)]
        value = fromFeature.GetField(fromIndex)
        # Copy field value.
        toFeature.SetField(fieldName,value)
      # Get geometry.
      geom = fromFeature.GetGeometryRef()
      toFeature.SetGeometry(geom.Clone())
      # Add new feature to output Layer.
      self.layer.CreateFeature(toFeature)

  #-------------------------------------------------------------------------------
  # Creates a new shapefile.
  # geomType - ogr.wkbPoint, ogr.wkbLineString, ogr.wkbPolygon,...
  def create(self,fileName,geomType):
    self.fileName = fileName

    # Check vector name.
    if (fileName is None) or (len(fileName)==0):    
      Err.raiseGlobioError(Err.NoVectorSpecified)

    self.driver = ogr.GetDriverByName("ESRI Shapefile")
    self.dataSource = self.driver.CreateDataSource(self.fileName)

    # Set projection (WGS84).
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(GLOB.epsgWGS84)

    # Create the layer.
    name = os.path.basename(self.fileName)
    name = UT.strBeforeLast(name,".")
    self.layer = self.dataSource.CreateLayer(name,srs,geomType)

  #-------------------------------------------------------------------------------
  def getFieldIndexByName(self,fieldName):
    # fieldNames not yet filled?
    if self.fieldNames is None:
      # Fill fieldNames.
      layerDefn = self.layer.GetLayerDefn()
      self.fieldNames = []
      for i in range(layerDefn.GetFieldCount()):
        self.fieldNames.append(layerDefn.GetFieldDefn(i).GetNameRef())
    # Get field index.
    return self.fieldNames.index(fieldName)

  #-------------------------------------------------------------------------------
  def hasPointGeometry(self):
    if self.layer is None: 
      return False
    if self.layer.GetGeomType()==ogr.wkbPoint:
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def getGeometryType(self):
    if self.layer is None: 
      return ogr.wkbUnknown
    return self.layer.GetGeomType()

  #-------------------------------------------------------------------------------
  def getExtent(self):
    if self.layer is None: 
      return ogr.wkbUnknown
    return self.layer.GetExtent()
    
  #-------------------------------------------------------------------------------
  def read(self):
    if RU.isShapeFileName(self.fileName):
      self.driver = ogr.GetDriverByName("ESRI Shapefile")
      self.dataSource = self.driver.Open(self.fileName,0)
      self.layer = self.dataSource.GetLayer()
    elif RU.isFgdbFcName(self.fileName):
      self.driver = ogr.GetDriverByName("FileGDB")
      fgdbName = RU.getFgdbName(self.fileName)
      fcName = RU.getFgdbFcName(self.fileName)
      self.dataSource = self.driver.Open(fgdbName,0)
      self.layer = self.dataSource.GetLayer(fcName)
    else:
      Err.raiseGlobioError(Err.InvalidVectorName1,self.fileName)
  
  #-------------------------------------------------------------------------------
  # Excample: "SUB_REGION = 'Pacific'"
  def setAttributeFilter(self,filterStr):
    self.attrFilter = filterStr
    self.layer.SetAttributeFilter(filterStr)

  #-------------------------------------------------------------------------------
  # Writes a vector file.
  # The vector file should not already exist.
  def write(self):

    # Set vector name.
    fileName = self.fileName

    # Check vector name.
    if (fileName is None) or (len(fileName)==0):    
      Err.raiseGlobioError(Err.NoVectorSpecified)

    # Check directory of vector name.
    dirName = os.path.dirname(fileName)
    if not os.path.isdir(dirName):    
      Err.raiseGlobioError(Err.DirectoryNotFound1,dirName)

    # Write data and close the datasource.
    self.dataSource = None
