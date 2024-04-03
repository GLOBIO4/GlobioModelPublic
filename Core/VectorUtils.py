# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# All VectorUtils methods are implemented for using with the GDAL/OGR and
# Shapely libs. 
# Some method are also implemented using the ArcGIS lib arcpy.
#
# The value GLOB.gisLib specifies which lib will be imported, GDAL/OGR or
# ArcGIS, and which mehods can be used.
#
# All shp* methods/functions are related to Shapely geometries.
#
# All ogr* methods/functions are related to GDAL/OGR geometries.
#
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - shpCalcGeodeticLineLengthKM - degreeToKM_v2 replaced with degreeToKM.
#           10 feb 2019, ES, ARIS B.V.
#           - shpLineToMultiLine modified, is_empty added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - vectorExtent added.
#           - vectorInExtent added.
#           - vectorIntersectByExtent added.
#           - shpWriteFeatures renamed to shapeFileWriteFeatures.
#           - ogrPolygonFromBounds added.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - shapeFileWriteFeatures modified, because of propNames.
#-------------------------------------------------------------------------------

import os
import math

from shapely.geometry import Point,LineString,MultiLineString,Polygon
from shapely.ops import split,nearest_points

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB

if GLOB.gisLib == GLOB.GIS_LIB_GDAL:
  import osgeo.ogr as ogr
  import osgeo.osr as osr
else:
  # 20201118
  #import arcpy.sa
  import GlobioModel.Core._arcpy as arcpy

import GlobioModel.Common.Utils as UT

import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.Vector import Vector

#-------------------------------------------------------------------------------
# Creates a regular grid (fishnet) of polygons.
# Params:
# - featureLayer: When specified, the polygons are added to this layer, 
#                 otherwise the grid is returned as a a list of polygon
#                 geometries. 
def createFishNetPolygons(extent,cellSize,featureLayer=None):

  # Get extent coords.
  minx = extent[0]
  miny = extent[1]
  maxx = extent[2]
  maxy = extent[3]

  # Get columns and rows.
  nrCols = math.ceil((maxx-minx)/cellSize)
  nrRows = math.ceil((maxy-miny)/cellSize)

  # Start grid cell envelope.
  xLeftOrigin = minx
  xRightOrigin = minx + cellSize
  yTopOrigin = maxy
  yBottomOrigin = maxy-cellSize

  # Add polygons to layer?
  if not featureLayer is None:
    polys = None
    featureDefn = featureLayer.GetLayerDefn()
  else:
    polys = []
    featureDefn = None
    
  # Create the grid cells.
  col = 0
  while col < nrCols:
    col += 1

    # Reset envelope for rows.
    yTop = yTopOrigin
    yBottom =yBottomOrigin
    row = 0
    while row < nrRows:
      row += 1
      
      # Create the polygon.
      ring = ogr.Geometry(ogr.wkbLinearRing)
      ring.AddPoint(xLeftOrigin, yTop)
      ring.AddPoint(xRightOrigin, yTop)
      ring.AddPoint(xRightOrigin, yBottom)
      ring.AddPoint(xLeftOrigin, yBottom)
      ring.AddPoint(xLeftOrigin, yTop)
      poly = ogr.Geometry(ogr.wkbPolygon)
      poly.AddGeometry(ring)
      
      # Add to layer?
      if not featureDefn is None:
        # Create a feature and add polygon.
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(poly)
        featureLayer.CreateFeature(feature)
        feature = None
      else:
        # Add polygon to list.
        polys.append(poly)

      # Set new envelope for next poly.
      yTop = yTop - cellSize
      yBottom = yBottom - cellSize

    # Set new envelope for next poly.
    xLeftOrigin = xLeftOrigin + cellSize
    xRightOrigin = xRightOrigin + cellSize

  # Return the polygons.
  return polys

#-------------------------------------------------------------------------------
# Creates a shapefile with regular grid (fishnet) of polygons.
# Caution: Shapefiles are limitted to a maximum size of 4 GB.
def createFishNetShapeFile(shapeFileName,extent,cellSize):

  # Check the shapefile.
  if vectorExists(shapeFileName):
    vectorDelete(shapeFileName)

  # Create the shapefile.
  driver = ogr.GetDriverByName('ESRI Shapefile')
  dataSource = driver.CreateDataSource(shapeFileName)
  
  # Create the spatial reference, WGS84.
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)
  
  # Create the layer.
  featureLayer = dataSource.CreateLayer(shapeFileName,srs,ogr.wkbPolygon)

  # Create the grid cells.
  createFishNetPolygons(extent,cellSize,featureLayer)

  # Save and close datasource.
  dataSource = None

#-------------------------------------------------------------------------------
def fgdbFcExists(vectorName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    return arcpy.Exists(vectorName)
  else:
    driver = ogr.GetDriverByName("FileGDB")
    fgdbName = getFgdbName(vectorName)
    fcName = getFgdbFcName(vectorName).lower()
    try:
      fgdb = driver.Open(fgdbName, 0)
      for idx in range(fgdb.GetLayerCount()):
        if fgdb.GetLayerByIndex(idx).GetName().lower()==fcName:
          return True
      return False
    except:
      return False
 
#-------------------------------------------------------------------------------
def getFgdbFcName(vectorName):
  idx1 = vectorName.find("\\")
  idx2 = vectorName.find("/")
  if idx1 > idx2:
    c = "\\"
  else:
    c = "/"
  return UT.strAfterLast(vectorName,c)

#-------------------------------------------------------------------------------
def getFgdbName(vectorName):
  idx1 = vectorName.find("\\")
  idx2 = vectorName.find("/")
  if idx1 > idx2:
    c = "\\"
  else:
    c = "/"
  return UT.strBeforeLast(vectorName,c)

#-------------------------------------------------------------------------------
def isShapeFileName(datasourceName):
  return UT.sameText(UT.getFileNameExtension(datasourceName),".shp")

#-------------------------------------------------------------------------------
# Creates a polygon from the bounds (i.e. tuple (x1,y1,x2,y2) or array).  
def ogrPolygonFromBounds(bnds):
  ring = ogr.Geometry(ogr.wkbLinearRing)
  ring.AddPoint(bnds[0],bnds[1])
  ring.AddPoint(bnds[0],bnds[3])
  ring.AddPoint(bnds[2],bnds[3])
  ring.AddPoint(bnds[2],bnds[1])
  ring.AddPoint(bnds[0],bnds[1])
  poly = ogr.Geometry(ogr.wkbPolygon)
  poly.AddGeometry(ring)
  return poly

#-------------------------------------------------------------------------------
def shapeFileDelete(shapeFileName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    if shapeFileExists(shapeFileName):
      arcpy.Delete_management(shapeFileName)
  else:
    driver = ogr.GetDriverByName("ESRI Shapefile")
    driver.DeleteDataSource(shapeFileName)

#-------------------------------------------------------------------------------
def shapeFileExists(shapeFileName):
  if os.path.isfile(shapeFileName):
    ext = UT.getFileNameExtension(shapeFileName)
    fileName = shapeFileName.replace(ext,".dbf")
    if not os.path.isfile(fileName):
      return False
    fileName = shapeFileName.replace(ext,".shx")
    if not os.path.isfile(fileName):
      return False
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Writes a list of SHAPELY features to a shapefile.
# If fieldnames are specified all features must have the corresponding
# properties. Differences in upper/lowercase of the first character is allowed. 
# The fieldTypes can be: ogr.OFTString, ogr.OFTInteger, ogr.OFTReal...
#
# ONLY POINTS, LINES and MULTILINES ARE SUPPORTED!!!
#
def shapeFileWriteFeatures(shpFileName,features,fieldNames=None,fieldTypes=None):

  # Check features.
  if len(features)==0:
    Err.raiseGlobioError(Err.UserDefined1,"No features found.")
  
  # Check fieldNames and fieldTypes.
  if (fieldNames is None) and (fieldTypes is None):
    # Valid.
    pass
  elif (not fieldNames is None) and (fieldTypes is None):
    # Invalid.
    Err.raiseGlobioError(Err.UserDefined1,"No fieldtypes specified.")
  elif (fieldNames is None) and (not fieldTypes is None):
    # Invalid.
    Err.raiseGlobioError(Err.UserDefined1,"No fieldnames specified.")
  else:
    # Check length.
    if len(fieldNames) != len(fieldTypes):
      Err.raiseGlobioError(Err.UserDefined1,"Invalid fieldnames or fieldtypes specified.")

  # Get first feature.
  feat = features[0]

  # Check feature geometry type.
  if shpIsGeometryCollection(feat):
    # No heterogeneous are supported.
    Err.raiseGlobioError(Err.UserDefined1,"Invalid features. Cannot be a geometry collection.")
  
  # Get GDAL geometry type.
  geomType = shpGeometryTypeToGDAL(feat.geom_type)

  # Check geomtype.
  if (not shpIsPoint(feat)) and (not shpIsLine(feat)) and (not shpIsMultiLine(feat)):
    Err.raiseGlobioError(Err.UserDefined1,"Geometrytype '%s' not supported." % feat.geom_type)

  # Check fieldNames and create corresponding property names.
  # 20201209
  propNames = []
  if not fieldNames is None:
    # 20201209
    #propNames = []
    for fieldName in fieldNames:
      # Has fieldname property?
      if hasattr(feat,fieldName):
        # Add to propname list.
        propNames.append(fieldName)
      else:
        # Create propname with first character with lower case.
        propName = fieldName[0].lower() + fieldName[1:] 
        # This propname still not found?
        if not hasattr(feat,propName):
          Err.raiseGlobioError(Err.UserDefined1,"Feature fieldname '%s' or '%s' not found." % (fieldName,propName))
        # Add to propname list.
        propNames.append(propName)
  
  # Create the shapefile.
  outVector = Vector()
  outVector.create(shpFileName,geomType)

  # Add fields?
  if not fieldNames is None:
    for i in range(len(fieldNames)):
      outVector.addField(fieldNames[i],fieldTypes[i])
      
  # Add the lines.
  values = None
  for feat in features:
    # Add field values?
    # 20201209
    #if not fieldNames is None:
    if len(propNames) > 0:
      # Get values using propnames.
      values = [getattr(feat,propName) for propName in propNames]
    # Write feature.
    if shpIsPoint(feat):
      outVector.addPoint(feat.x,feat.y,fieldNames,values)
    elif shpIsLine(feat):
      outVector.addLine(feat.coords,fieldNames,values)
    elif shpIsMultiLine(feat):
      # Create a list of multiline coordinates.
      lineCoords = []
      for line in feat.geoms:
        lineCoords.append(line.coords)
      # Add multiline coordinates.
      outVector.addMultiLine(lineCoords,fieldNames,values)

  # Write and close the shapefile.
  outVector.write()
  outVector.close()
  outVector = None

#-------------------------------------------------------------------------------
# Calculates the geodetic length of a SHAPELY line, multiline or geomcollection.
# Returns the length in km.
def shpCalcGeodeticLineLengthKM(line):
  # Split multilines.
  lines = shpMultiLineToLines(line)
  # Loop intersect lines.
  lengthKM = 0.0
  for line in lines:
    for i in range(0,len(line.coords)-1):
      c1 = line.coords[i]
      c2 = line.coords[i+1]
      lengthKM += RU.degreeToKM(c1[0],c1[1],c2[0],c2[1])
  return lengthKM

#-------------------------------------------------------------------------------
# Calculates the geodetic area of a SHAPELY polygon or multipolygon.
# The area of inner holes is subtracted.
# Returns the area in km2.
# CAUTION: This method uses degreeToKM2 which is relative slow.
def shpCalcGeodeticPolygonAreaKM2(poly):
  # Split multipolygons.
  polys = shpMultiPolygonToPolygons(poly)    
  # Loop polygons. 
  areaKM2 = 0.0
  for poly in polys:
    # Add area.
    areaKM2 += RU.degreeToKM2(poly.exterior.coords)
    # Substract holes.
    for interior in poly.interiors:
      areaKM2 -= RU.degreeToKM2(interior.coords)
  return areaKM2

#-------------------------------------------------------------------------------
# Extends the line between two SHAPELY points.
# The new line is extended by factor * original distance between the points.
# Returns the new point. 
# https://stackoverflow.com/questions/7740507/extend-a-line-segment-a-specific-distance
def shpExtentLine(point1,point2,factor=0.1):
  # Get length.
  length = point1.distance(point2)
  if length == 0.0:
    return point1
  # Set extra length.
  newLength = (length * factor) / length
  x = point2.x + (point2.x - point1.x) * newLength
  y = point2.y + (point2.y - point1.y) * newLength
  return Point(x,y)

#-------------------------------------------------------------------------------
# Gets nearest feature from SHAPELY features by point.
# Returns a feature or None.
def shpFeaturesGetNearestByPoint(features,point):
  # Check features.
  if len(features)==0:
    return None
  # Get first feature.
  minFeat = features[0]
  minDist = minFeat.distance(point)
  for i in range(1,len(features)):
    dist = features[i].distance(point)
    if dist < minDist:
      minDist = dist
      minFeat = features[i]
  return minFeat

#-------------------------------------------------------------------------------
# Converts a SHAPELY geometry type to a GDAL type.
def shpGeometryTypeToGDAL(geometryType):
  if geometryType == "Point":
    return ogr.wkbPoint
  elif geometryType == "MultiPoint":
    return ogr.wkbMultiPoint
  elif geometryType == "LineString":
    return ogr.wkbLineString
  elif geometryType == "MultiLineString":
    return ogr.wkbMultiLineString
  elif geometryType == "Polygon":
    return ogr.wkbPolygon
  elif geometryType == "MultiPolygon":
    return ogr.wkbMultiPolygon

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a geometrycollection.
def shpIsGeometryCollection(shp):
  if shp.geom_type=="GeometryCollection":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a line.
def shpIsLine(shp):
  if shp.geom_type=="LineString":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a multiline.
def shpIsMultiLine(shp):
  if shp.geom_type=="MultiLineString":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a multipoint.
def shpIsMultiPoint(shp):
  if shp.geom_type=="MultiPoint":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a multipolygon.
def shpIsMultiPolygon(shp):
  if shp.geom_type=="MultiPolygon":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a point.
def shpIsPoint(shp):
  if shp.geom_type=="Point":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if the SHAPELY shape is a polygon.
def shpIsPolygon(shp):
  if shp.geom_type=="Polygon":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Calculate coordinates of origin and the number of cols and rows of 
# the surrounding box of a SHAPELY line.
# Returns a (minx,miny,nrCols,nrRows) tuple.
# nrCols and nrRows are alway > 0.
def shpLineCalcOriginNrColsRows(line,cellSize):
                
  # Get line boundary (as tuple).
  bnds = line.bounds
  
  # Calculate bound coords. Add extra padding cells for sure.
  minx = int(bnds[0] / cellSize) * cellSize - cellSize
  miny = int(bnds[1] / cellSize) * cellSize - cellSize
  maxx = int(bnds[2] / cellSize) * cellSize + cellSize
  maxy = int(bnds[3] / cellSize) * cellSize + cellSize
  
  # Calculate number of cols and rows.
  nrCols = int((maxx - minx) / cellSize)      
  nrRows = int((maxy - miny) / cellSize)

  # Ensure minimal 1 col and row.
  if nrCols < 1:
    nrCols = 1
  if nrRows < 1:
    nrRows = 1
  
  nrCols += 1      
  nrRows += 1
  
  return (minx,miny,nrCols,nrRows)

#-------------------------------------------------------------------------------
# Returns the line network connected to the SHAPELY line.
# Starts searching from the lines endpoint.
# From all found lines the id property is set to the labelId.
# The search is stopped when a line is found which is already labeled. 
# When a stoptree is given the search will be stopped when a
# line is found if the endpoint exists in the stoptree.
def shpLineGetConnectedLinesFromPoint_NOK(line,lineBeginPoint,labelId,
                                          lineTree,stopTree=None):

  # Check if line already is processed? Then stop.
  if line.id > 0:
    return []

  # Set the id.
  line.id = labelId
    
  # Create list with the first line.
  foundLines = [line]
    
  # Get begin and endpoint of line.
  lineBeginPnt = Point(line.coords[0])
  lineEndPnt = Point(line.coords[-1])
  
  # Get opposite point of lineBeginPoint.
  if lineBeginPoint.equals(lineBeginPnt):
    nextSearchtPoint = lineEndPnt
  else:
    nextSearchtPoint = lineBeginPnt

  #  Need to check stoptree?
  if not stopTree is None:
    # Next point is stopnode?
    stopNodes = stopTree.query(nextSearchtPoint)
    if len(stopNodes)>0:
      return foundLines

  # Get lines connected to the next search point.
  connectedLines = lineTree.query(nextSearchtPoint)

  # Process found connected lines.
  for connectedLine in connectedLines:
    # Find additional connected lines.
    nextFoundLines = shpLineGetConnectedLinesFromPoint_NOK(connectedLine,
                                              nextSearchtPoint,
                                              labelId,lineTree,stopTree)
    foundLines.extend(nextFoundLines)
             
  return foundLines

#-------------------------------------------------------------------------------
# Returns the beginpoint of a SHAPELY line.
def shpLineGetBeginPoint(line):
  return Point(line.coords[0][0],line.coords[0][1])

#-------------------------------------------------------------------------------
# Returns the endpoint of a SHAPELY line.
def shpLineGetEndPoint(line):
  return Point(line.coords[-1][0],line.coords[-1][1])

#-------------------------------------------------------------------------------
# Returns the point the two SHAPELY lines share as endpoint.
# Returns None if there are no shared points.
def shpLineGetSharedEndPoint(line1,line2):

  startPnt1 = line1.coords[0]
  startPnt2 = line2.coords[0]
  if (UT.isEqualFloat(startPnt1[0],startPnt2[0])) and (UT.isEqualFloat(startPnt1[1],startPnt2[1])):
    return Point(startPnt1)

  endPnt2 = line2.coords[-1]
  if (UT.isEqualFloat(startPnt1[0],endPnt2[0])) and (UT.isEqualFloat(startPnt1[1],endPnt2[1])):
    return Point(startPnt1)

  endPnt1 = line1.coords[-1]
  if (UT.isEqualFloat(endPnt1[0],startPnt2[0])) and (UT.isEqualFloat(endPnt1[1],startPnt2[1])):
    return Point(endPnt1)

  if (UT.isEqualFloat(endPnt1[0],endPnt2[0])) and (UT.isEqualFloat(endPnt1[1],endPnt2[1])):
    return Point(endPnt1)
  
  return None

#-------------------------------------------------------------------------------
# Split a SHAPELY line at the nearest point from SHAPELY point.
# Uses a splitline form point to nearest point for splitting.
# The splitline is extended by the length * factor. 
# Returns a list of linestrings and the (snapped) splitpoint.
# Returns: (splittedLines,splitPoint)
def shpLineSplitAtNearestPoint(line,point,factor=0.1):

  # Get nearest point on line.
  nearestPnt = Point(nearest_points(point,line)[1])

  # Get intersection of line and nearest point.
  splitPoint = line.intersection(nearestPnt)
  
  # Is nearest point on line?
  if not splitPoint.is_empty:
    # Split line with the intersectPoint.
    splittedLine = split(line,splitPoint)
  else:
    # Use a line from point to nearest point for splitting.
    # Extend the line from point to nearest point.    
    newPoint = shpExtentLine(point,nearestPnt,factor)
    # Create intersection line.
    splitLine = LineString([point,newPoint])
    # Get split point.
    splitPoint = line.intersection(splitLine)
    # Split line with the splitPoint.
    splittedLine = split(line,splitLine)

  # Convert to simple lines.
  splittedLines = shpMultiLineToLines(splittedLine)
  
  return (splittedLines,splitPoint)

#-------------------------------------------------------------------------------
# Returns (splittedLines,splitPoints)
def shpLineSplitAtPoints(line,points,factor=0.1):

  # Check points.
  if len(points)==0:
    return ([line],[])
  
  # Create list.
  splitPoints = []
  
  # Get first point and do first split.
  pnt = points[0]
  splittedLines,splitPnt = shpLineSplitAtNearestPoint(line,pnt)

  # Add splitpoint to list.
  splitPoints.append(splitPnt)
  
  # Process next points.
  for i in range(1,len(points)):
    # Get point.
    pnt = points[i]
    #print "    shpLineSplitAtPoints - processing %s" % pnt.wkt
    #  Get nearest splitted line.
    splittedLine = shpFeaturesGetNearestByPoint(splittedLines,pnt)
    #print "    shpLineSplitAtPoints - processing %s" % splittedLine.wkt[:80]
    # Found?
    if not splittedLine is None:
      # Remove from list.
      splittedLines.remove(splittedLine)
      # Split line.
      newSplittedLines,splitPnt = shpLineSplitAtNearestPoint(splittedLine,pnt)
      #print "    shpLineSplitAtPoints - new lines %s" % len(newSplittedLines)
      # Add to splitted lines list.
      splittedLines.extend(newSplittedLines)
      # Add splitpoint to list.
      splitPoints.append(splitPnt)
    else:
      print("    shpLineSplitAtPoints - no nearest line found")
      
  return (splittedLines,splitPoints)

#-------------------------------------------------------------------------------
# Convert SHAPELY line to multiline.
# NOT FULLY TESTED!!!
def shpLineToMultiLine(line):
  # Is it empty?
  if line.is_empty:
    return []
  elif shpIsMultiLine(line):
    # It is already a multilinestring?
    return line
  elif shpIsGeometryCollection(line):
    # NOT TESTED!!!
    return MultiLineString(line)
  elif shpIsLine(line):
    return MultiLineString([line])
  else:
    return MultiLineString([])

#-------------------------------------------------------------------------------
# Split multilinestrings into linestrings.
# line: SHAPELY line.
# Returns a list of linestrings.
def shpMultiLineToLines(line):
  # Is it a multilinestring?
  if shpIsMultiLine(line):
    lines = []
    for geom in line.geoms:
      lines.extend(shpMultiLineToLines(geom))
    return lines
  elif shpIsGeometryCollection(line):
    lines = []
    for geom in line.geoms:
      lines.extend(shpMultiLineToLines(geom))
    return lines
  elif shpIsLine(line):
    return [line] 
  else:
    return []

#-------------------------------------------------------------------------------
# Split multipolygons into polygons.
# poly: SHAPELY polygon.
# Returns a list of polygons.
def shpMultiPolygonToPolygons(poly):
  # Is it a multipolygon?
  if shpIsMultiPolygon(poly):
    polys = []
    for geom in poly.geoms:
      polys.extend(shpMultiPolygonToPolygons(geom))
    return polys
  elif shpIsGeometryCollection(poly):
    polys = []
    for geom in poly.geoms:
      polys.extend(shpMultiPolygonToPolygons(geom))
    return polys
  elif shpIsPolygon(poly):
    return [poly] 
  else:
    return []

#-------------------------------------------------------------------------------
# Creates a polygon from the bounds (i.e. tuple (x1,y1,x2,y2) or array).  
def shpPolygonFromBounds(bnds):
  return Polygon([(bnds[0],bnds[1]),(bnds[0],bnds[3]),
                  (bnds[2],bnds[3]),(bnds[2],bnds[1]),
                  (bnds[0],bnds[1])])
      
#-------------------------------------------------------------------------------
# Gets features from a SHAPELY tree by point.  
def shpTreeFeaturesGetByPoint(tree,point,tolerance=0.0):
  if tolerance <= 0.0:
    return tree.query(point)
  else:
    return tree.query(point.buffer(tolerance))

#-------------------------------------------------------------------------------
# Gets nearest feature from a SHAPELY tree by point.
# Returns a feature or None.  
# When the tree contains multilinestrings a single 
# linestring is returned.
def shpTreeFeaturesGetNearestByPoint(tree,point,tolerance=0.0):
  # Get features.
  resolution = 1 # Square buffer.
  if tolerance <= 0.0:
    features = tree.query(point)
  else:
    features = tree.query(point.buffer(tolerance,resolution))
  # No one found?
  if len(features)==0:
    return None
  elif len(features)==1:
    return features[0]
  else:  
    # More than one found. Get nearest.
    return shpFeaturesGetNearestByPoint(features,point)

#-------------------------------------------------------------------------------
def vectorDelete(vectorName):
  if isShapeFileName(vectorName) and shapeFileExists(vectorName):
    shapeFileDelete(vectorName)

#-------------------------------------------------------------------------------
def vectorExists(vectorName):
  if shapeFileExists(vectorName) or fgdbFcExists(vectorName):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def vectorExtent(vectorName):
  # Open input vector dataset and read datasource and layer.
  vector = Vector(vectorName)
  vector.read()
  # Get extent.
  extent = vector.layer.GetExtent()
  # Cleanup.
  vector.close()
  vector = None
  return extent

#-------------------------------------------------------------------------------
# Returns if the vector is in the specified extent.
def vectorInExtent(vectorName,extent):
  # Get extent.
  vecExtent = vectorExtent(vectorName)
  # Check if in extent.
  return RU.isExtentInExtent(vecExtent,extent)

#-------------------------------------------------------------------------------
# Creates a new vector file with all features from in input vector that 
# intersects (i.e. crosses) the extent.
# Remark: The output vector can only be a shapefile.
def vectorIntersectByExtent(inVectorName,extent,outVectorName):

  # Open input vector dataset and read datasource and layer.
  inVector = Vector(inVectorName)
  inVector.read()

  # Create polygon from extent.
  polygon = ogrPolygonFromBounds(extent)

  # Set extent polygon as spatial filter.
  inVector.layer.SetSpatialFilter(polygon)

  # Create output shapefile.
  outVector = Vector()
  outVector.create(outVectorName,inVector.getGeometryType())

  # Add all input feature to the output vector.
  map(lambda feat: outVector.layer.CreateFeature(feat), inVector.layer)

  # Cleanup input vector.
  inVector.close()
  inVector = None

  # Write and close the shapefile.
  outVector.write()
  outVector.close()
  outVector = None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  
