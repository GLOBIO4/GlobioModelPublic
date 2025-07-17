# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
#
# Constants are uppercase sensitive.
#
# The ConstantList is modified to have the same order as when the
# constants are added.
#
# Variables with the same name are not allowed.
#
# Modified: -
#-------------------------------------------------------------------------------

import GlobioModel.Core.Globals as GLOB

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Constant(object):
  name = ""
  description = ""
  type = None                        # The type.
  value = None

  #-------------------------------------------------------------------------------
  def __init__(self,name,description,typeName,value):
    self.name = name
    self.description = description
    self.type = GLOB.types[typeName]
    self.value = value

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ConstantList(dict):
  list = []

  #-------------------------------------------------------------------------------
  def __init__(self):
    super(ConstantList,self).__init__()
    self.list = []

  #-------------------------------------------------------------------------------
  def __iter__(self):
    return iter(self.list)

  #-------------------------------------------------------------------------------
  def __setitem__(self,name,value):
    super(ConstantList,self).__setitem__(name,value)
    self.list.append(name)

  #-------------------------------------------------------------------------------
  def add(self,name,description,typeName,value):
    self[name] = Constant(name,description,typeName,value)

  #-------------------------------------------------------------------------------
  def exists(self,name):
    return name in self

  #-------------------------------------------------------------------------------
  def keys(self):
    return self.list

  #-------------------------------------------------------------------------------
  def values(self):
    v = []
    for k in self.list:
      v.append(self[k])
    return v
