# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# List of landuse types (codes/names).
#
# Modified: 18 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#-------------------------------------------------------------------------------

from typing import Optional

import GlobioModel.Core.Error as Err

import GlobioModel.Common.Utils as UT

from GlobioModel.LanduseAllocation.LanduseType import LanduseType

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class LanduseTypes(object):

  # List of LanduseType instances, i.e. with per landuse type:
  # - name
  # - code
  # - claims per region (dict with region as key)
  # - suitability rastername.
  # - suitability raster.
  list = []

  #-------------------------------------------------------------------------------
  def init(self,codeList: str,nameList: str):
    self.list = []
    codes = self.splitIntegerList(codeList)
    names = self.splitStringList(nameList)
    # TODO: Check op equal length?
    for i in range(len(codes)):
      self.add(codes[i],names[i])

  #-------------------------------------------------------------------------------
  # Creates a landuse type object and adds it to the list.
  def add(self,code: int,name: str):
    luType = LanduseType(name,code)
    self.list.append(luType)

  #-------------------------------------------------------------------------------
  # Checks if the codeList is a list of valid integer landuse codes.
  def checkLanduseCodes(self,codeList: str,errNotSpecified,errInvalid,optional=False):
    if (optional) and (codeList==""):
      # No checks needed.
      return
    if codeList=="":
      Err.raiseGlobioError(errNotSpecified)
    # Get codes.
    codes = self.splitIntegerList(codeList)
    for code in codes:
      # Get land-use type?
      luType = self.getLanduseTypeByCode(code)
      # No land-use type found?
      if luType is None:
        Err.raiseGlobioError(errInvalid,code)

  #-------------------------------------------------------------------------------
  #def getLanduseTypeByCode(self,code: int) -> Optional[str,None]:
  def getLanduseTypeByCode(self,code: int):
    for luType in self.list:
      if luType.code == code:
        return luType
    return None

  #-------------------------------------------------------------------------------
  #def getLanduseTypeByName(self,name: str) -> Optional[int,None]:
  def getLanduseTypeByName(self,name: str):
    for luType in self.list:
      if luType.name == name:
        return luType
    return None

  #-------------------------------------------------------------------------------
  # Recalculates the claims.
  # Remark: used for testing.
  def recalculateClaims(self,landuseCodes: [int],areaMultipliers: [float]):
    # Loop landuse codes.
    for idx,landuseCode in enumerate(landuseCodes):
      # Get landuse type.
      luType = self.getLanduseTypeByCode(landuseCode)
      # Found?
      if not luType is None:
        # Get area multiplier.
        areaMultiplier = areaMultipliers[idx]
        # Loop claim regions.
        for region in luType.getRegions():
          area = luType.claims[region]
          area = area * areaMultiplier
          luType.claims[region] = area

  #-------------------------------------------------------------------------------
  def show(self):
    for luType in self.list:
      luType.show()

  #-------------------------------------------------------------------------------
  # Converts a list of format int1|int2|int3 to an array of integers.
  def splitIntegerList(self,intList: str) -> [int]:
    if not UT.isValueSet(intList):
      return []
    return [int(i) for i in intList.split("|")]

  #-------------------------------------------------------------------------------
  # Converts a list of format s1|s2|s3 to an array of strings.
  def splitStringList(self,strList: str) -> [str]:
    if not UT.isValueSet(strList):
      return []
    return strList.split("|")
