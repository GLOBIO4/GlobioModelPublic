# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Arguments class to get arguments without using an index but with
# checks for getting the correct number of arguments.
# No renumbering of argument indices is needed anymore.
#
# Usage:
#
#   # Create argument checker.
#   pArgs = Arguments(args)
#
#   # Get arguments.
#   extent = pArgs.next()
#   cellSize = pArgs.next()
#
#   # Check number of arguments.
#   pArgs.check(self.name)
#
# Modified: 15 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#-------------------------------------------------------------------------------



import GlobioModel.Core.Error as Err

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Arguments():
  args = []
  idx = 0
  #-------------------------------------------------------------------------------
  def __init__(self,args):
    self.args = args
    self.idx = 0
  #-------------------------------------------------------------------------------
  # Returns the next argument.
  def next(self):
    if self.idx >= len(self.args):
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(self.args),"run")
    value = self.args[self.idx]
    self.idx += 1
    return value
  #-------------------------------------------------------------------------------
  # Checks the used arguments.
  def check(self,name=""):
    if name == "":
      name = "run"
    if len(self.args) != self.idx:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(self.args),name)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  # OK
  def test():

      class Calc():
        def run1(self,*args):
          a = Arguments(args)
          ext = a.next()
          a.check()
          print(ext)
        def run3(self,*args):
          a = Arguments(args)
          ext = a.next()
          cs = a.next()
          reg = a.next()
          a.check()
          print(ext)
          print(cs)
          print(reg)

      a1 = 12
      a2 = 34
      c = Calc()

      print("run(a1)")
      try:
        c.run1(a1)
        print("  OK")
      except Exception as ex:
        print(ex)

      print("."*40)
      print("run()")
      try:
        c.run1()
        print("  OK")
      except Exception as ex:
        print(ex)

      print("."*40)
      print("run(a1,a2)")
      try:
        c.run1(a1,a2)
        print("  OK")
      except Exception as ex:
        print(ex)

      print("."*40)
      print("run2(a1,a2)")
      try:
        c.run3(a1,a2)
        print("  OK")
      except Exception as ex:
        print(ex)

  #-------------------------------------------------------------------------------
  #-------------------------------------------------------------------------------
  # run Core\Arguments.py
  test()