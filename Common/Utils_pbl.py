# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 23 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - id() changed to memaddr().
#           - printArray added.
#           6 oct 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - MemoryStatusEx added.
#           - memGetStatus added.
#           - memPhysical* added.
#           - dateTimeToStr modified "==None" changed to "is None".
#           - dateTimeToStrShort modified "==None" changed to "is None".
#           2 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - import getpass added.
#           - getUserName added.
#           - getUserTempDir added.
#           - from ctypes import ... modified.
#           - def memGetStatus() modified.
#           9 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - asFloat added.
#           - strDQuote added.
#           - getComputerName added.
#           2 dec 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - intToStr/NL modified, Thousands added.
#           - floatToStrE added.
#           5 dec 2016, ES, ARIS B.V.
#           - import inspect added, and getMethodName().
#           7 dec 2016, ES, ARIS B.V.
#           - trunc modified,  casting to int or float added.
#           12 dec 2016, ES, ARIS B.V.
#           - memGetStatus modified.
#           - sec2str modified, precision added.
#           - dateTimeToDayStr added.
#           - dateTimeToShortStr added.
#           - dateTimeToStrShort modified ivm. backwards compatibility.
#           26 apr 2017, ES, ARIS B.V.
#           - tests added.
#           - intToStrNL modified, line removed.
#           21 jun 2017, ES, ARIS B.V.
#           - hasFileNameExtension added.
#           11 aug 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - isString modified, check on "str" added.
#           - printArray modified, np.float32 and np.float64 added.
#           9 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - isLinux added.
#           30 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - Commented out because of duplicate module.
#-------------------------------------------------------------------------------

# import sys
# import os

# import ctypes
# from ctypes import Structure, c_int32, c_uint64, sizeof, byref
# import datetime
# import getpass
# import inspect
# import platform
# import tempfile
# import time
# import locale
# import numpy as np
# import subprocess

# INVALID_DIR_CHARS = r":*?<>|" + chr(34)
# INVALID_FILEDIR_CHARS = INVALID_DIR_CHARS + r"\/" + chr(34)

# #-------------------------------------------------------------------------------
# #-------------------------------------------------------------------------------
# class MemoryStatusEx(Structure):
#   _fields_ = [
#       ('length', c_int32),
#       ('memoryLoad', c_int32),
#       ('totalPhys', c_uint64),
#       ('availPhys', c_uint64),
#       ('totalPageFile', c_uint64),
#       ('availPageFile', c_uint64),
#       ('totalVirtual', c_uint64),
#       ('availVirtual', c_uint64),
#       ('availExtendedVirtual', c_uint64)]
#   #-------------------------------------------------------------------------------
#   def __init__(self):
#     self.length = sizeof(self)

# #-------------------------------------------------------------------------------
# def arrayToMem(arr):
#   a = np.array(arr)
#   return a.nbytes

# #-------------------------------------------------------------------------------
# def arrayToMemStr(arr,Precision = 3):
#   np.array(arr)
#   return bytesToStr(arr.nbytes,Precision)

# #-------------------------------------------------------------------------------
# def asFloat(v):
#   if isString(v):
#     v = v.replace(",",".")
#     return float(v)
#   else:
#     return float(v)

# #-------------------------------------------------------------------------------
# def bytesToStr(NrOfBytes,Precision = 3):
#   if NrOfBytes < 1024:
#     return floatToStr(bytesToUnitFloat(NrOfBytes), 0) + " " + bytesToUnitStr(NrOfBytes)
#   else:
#     return floatToStr(bytesToUnitFloat(NrOfBytes),Precision) + " " + bytesToUnitStr(NrOfBytes)

# #-------------------------------------------------------------------------------
# # Geeft Bytes, KB, MB of GB terug.
# def bytesToUnitStr(NrOfBytes):
#   if NrOfBytes < 1024:
#     return "Bytes"
#   elif NrOfBytes < 1048576:
#     return "KB"
#   elif NrOfBytes < 1073741824:
#     return "MB"
#   else:
#     return "GB"

# #-------------------------------------------------------------------------------
# # Geeft aantal Bytes, KB, MB of GB terug.
# def bytesToUnitFloat(NrOfBytes):
#   if NrOfBytes < 1024:
#     return NrOfBytes
#   elif NrOfBytes < 1048576:
#     return NrOfBytes / float(1024)
#   elif NrOfBytes < 1073741824:
#     return NrOfBytes / float(1048576)
#   else:
#     return NrOfBytes / float(1073741824)

# #-------------------------------------------------------------------------------
# def concatPathFileName(path,fileName):
#   return os.path.join(path,fileName)

# #-------------------------------------------------------------------------------
# # Geeft de tijd terug in het format yyyymmdd hh:mm:ss.
# def dateTimeToStr(dateTime=None):
#   if dateTime is None:
#     dateTime = datetime.datetime.now()
#   return dateTime.strftime("%Y%m%d %H:%M:%S")

# #-------------------------------------------------------------------------------
# # Geeft de tijd terug in het format yyyymmdd.
# def dateTimeToDayStr(dateTime=None):
#   dateTime = datetime.datetime.now()
#   return dateTime.strftime("%Y%m%d")

# #-------------------------------------------------------------------------------
# # Geeft de tijd terug in het format yyyymmddhhmmss.
# def dateTimeToShortStr(dateTime=None):
#   if dateTime is None:
#     dateTime = datetime.datetime.now()
#   return dateTime.strftime("%Y%m%d%H%M%S")

# #-------------------------------------------------------------------------------
# # Ivm. backwards compatabiliy.
# def dateTimeToStrShort(dateTime=None):
#   return dateTimeToShortStr(dateTime)

# #-------------------------------------------------------------------------------
# # Geeft de vrije ruimte op een disk terug in bytes.
# def diskSpaceAvailable(root="/"):
#   if platform.system() == "Windows":
#     free_bytes = ctypes.c_ulonglong(0)
#     ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(root),
#                                            None,None,ctypes.pointer(free_bytes))
#     return free_bytes.value
#   else:
#     st = os.statvfs(root)
#     return st.f_bavail * st.f_frsize

# #-------------------------------------------------------------------------------
# # Geeft de tijdsduur terug in dagen, uur, min, sec.
# # 4 days 8 hour 20 min
# # 10 hour 26 min 5 sec
# # 1 hour 2 min 37 sec
# # 6 min 16 sec
# # 37.734 sec
# # 3.734 sec
# def durationToStr( StartTimeMSec,EndTimeMSec,NL = False):
#   return sec2str((EndTimeMSec - StartTimeMSec) / float(1000), NL)

# #-------------------------------------------------------------------------------
# # Geeft de veldnaam terug van een volledige veldnaam (table\field).
# def extractShortFieldName(tablefieldName):
#   _,fieldName = tablefieldNameSplit(tablefieldName)
#   return fieldName

# #-------------------------------------------------------------------------------
# # Voegt een regel toe aan een file.
# # NIET GETEST.
# def fileAppend(fileName,line):
#   with open(fileName,"a") as f:
#     if not line.endswith("\n"):
#       line += "\n"
#     f.write(line)

# #-------------------------------------------------------------------------------
# # Geeft een lijst met regels terug.
# # Geeft None terug indien niet gevonden.
# def fileRead(fileName):
#   if not os.path.isfile(fileName):
#     return None
#   with open(fileName,"r") as f:
#     return f.readlines()

# #-------------------------------------------------------------------------------
# # Schrijft een lijst van regels weg.
# # Verwijdert een eventueel bestaande file.
# def fileWrite(fileName,lines):
#   if os.path.isfile(fileName):
#     os.remove(fileName)
#   lines = "\n".join(lines)
#   with open(fileName,"w") as f:
#     f.write(lines)

# #-------------------------------------------------------------------------------
# # Formatteert de double naar xxx,xxx.xx of xxxxxx.xx.
# def floatToStr(d,Digits = 3, Thousands = False):
#   loc = locale.getlocale(locale.LC_NUMERIC)
#   try:
#     # For windows.
#     locale.setlocale(locale.LC_NUMERIC,'English')
#   except:
#     # For Linux.
#     locale.setlocale(locale.LC_NUMERIC,'en_US.utf8')
#   s = locale.format('%.'+str(Digits)+'f', d, Thousands)
#   locale.setlocale(locale.LC_NUMERIC,loc)
#   return s

# #-------------------------------------------------------------------------------
# # Formatteert de double naar -1e+10.
# def floatToStrE(d,Digits = 3, Thousands = False):
#   loc = locale.getlocale(locale.LC_NUMERIC)
#   try:
#     # For windows.
#     locale.setlocale(locale.LC_NUMERIC,'English')
#   except:
#     # For Linux.
#     locale.setlocale(locale.LC_NUMERIC,'en_US.utf8')
#   s = locale.format('%.'+str(Digits)+'e', d, Thousands)
#   locale.setlocale(locale.LC_NUMERIC,loc)
#   return s

# #-------------------------------------------------------------------------------
# # Formatteert de double naar xxx.xxx,xx of xxxxxx,xx.
# def floatToStrNL(d,Digits = 3, Thousands = False):
#   loc = locale.getlocale(locale.LC_NUMERIC)
#   try:
#     # For windows.
#     locale.setlocale(locale.LC_NUMERIC,'Dutch')
#   except:
#     # For Linux.
#     locale.setlocale(locale.LC_NUMERIC,'nl_NL.utf8')
#   s = locale.format('%.'+str(Digits)+'f', d, Thousands)
#   locale.setlocale(locale.LC_NUMERIC,loc)
#   return s

# #-------------------------------------------------------------------------------
# def getComputerName():
#   return platform.node().upper()

# #-------------------------------------------------------------------------------
# # Geeft de extensie terug, inclusief ".".
# def getFileNameExtension(fileName):
#   _,ext = os.path.splitext(fileName)
#   return ext

# #-------------------------------------------------------------------------------
# # Returns the name of the caller method.
# def getMethodName():
#   return inspect.stack()[1][3]
 
# #-------------------------------------------------------------------------------
# # Genereert een nieuwe filenaam <name>_001.ext.
# def getNewFileName(fileName,length=3):
#   i = 1
#   name,ext = os.path.splitext(fileName)
#   while i < pow(10,length):
#     s = str(i).zfill(length)
#     tmpFileName = name + "_" + s
#     if ext != "":
#       tmpFileName = tmpFileName + ext
#     if not os.path.isfile(tmpFileName):
#       return tmpFileName
#   return ""

# #-------------------------------------------------------------------------------
# def getTempDirectoryName():
#   return tempfile.gettempdir()

# #-------------------------------------------------------------------------------
# # Template is a name with %s where to put the generated number.
# # If %s is not found the number will be appended.
# def getTempFileName(dirName=None,template=None):
#   if dirName is None:
#     dirName = getTempDirectoryName()
#   if template is None:
#     template = "temp%s.dat"
#   digits = 3
#   for i in range(1,999):
#     nrStr = str(i).zfill(digits)
#     if template.find("%s")>=0:
#       fileName = os.path.join(dirName,template.replace("%s",nrStr))
#     else:
#       fileName = os.path.join(dirName,template + nrStr)
#     if not os.path.isfile(fileName):
#       return fileName

# #-------------------------------------------------------------------------------
# # Generates a unique filename with a timestamp (1 millisec resolution).
# # Template is a name with %s where to put the generated number.
# # If %s is not found the number will be appended.
# def getUniqueFileName(dirName=None,template=None):
#   if dirName is None:
#     dirName = getTempDirectoryName()
#   if template is None:
#     template = "temp%s.dat"
#   fileName = os.path.join(dirName,getUniqueName(template))
#   return fileName

# #-------------------------------------------------------------------------------
# # Generates a unique name with a timestamp (1 millisec resolution).
# # Template is a name with %s where to put the generated number.
# # If %s is not found the number will be appended.
# def getUniqueName(template=None):
#   if template is None:
#     template = "%s"
#   nrStr = datetime.datetime.now().strftime("%H%M%S%f")[:-3]
#   time.sleep(0.001)  
#   if template.find("%s")>=0:
#     name = template.replace("%s",nrStr)
#   else:
#     name = template
#   return name

# #-------------------------------------------------------------------------------
# def getUserName():
#   return getpass.getuser()

# #-------------------------------------------------------------------------------
# # Geeft:
# #   c:\\users\\<user>\\appdata\\local\\temp      op Windows7,8,10
# #   /tmp                                         op Linux
# def getUserTempDir():
#   return tempfile.gettempdir()

# #-------------------------------------------------------------------------------
# # Geeft terug of de filename de betreffende extensie heeft.
# def hasFileNameExtension(fileName,extension):
#   ext = getFileNameExtension(fileName).lower()
#   if not extension.startswith("."):
#     return (("."+extension).lower() == ext)
#   else:
#     return (extension.lower() == ext.lower())

# #-------------------------------------------------------------------------------
# # Formatteert de integer naar xxx,xxx.
# def intToStr(v, Thousands = True):
#   loc = locale.getlocale(locale.LC_NUMERIC)
#   try:
#     # For windows.
#     locale.setlocale(locale.LC_NUMERIC,'English')
#   except:
#     # For Linux.
#     locale.setlocale(locale.LC_NUMERIC,'en_US.utf8')
#   s = locale.format('%d', v, Thousands)
#   locale.setlocale(locale.LC_NUMERIC,loc)
#   return s

# #-------------------------------------------------------------------------------
# # Formatteert de integer naar xxx.xxx.
# def intToStrNL(v, Thousands = True):
#   loc = locale.getlocale(locale.LC_NUMERIC)
#   try:
#     # For windows.
#     locale.setlocale(locale.LC_NUMERIC,'Dutch')
#   except:
#     # For Linux.
#     locale.setlocale(locale.LC_NUMERIC,'nl_NL.utf8')
#   s = locale.format('%d', v, Thousands)
#   locale.setlocale(locale.LC_NUMERIC,loc)
#   return s

# #-------------------------------------------------------------------------------
# def isArray(a):
#   if type(a) is list:
#     return True
#   else:
#     return False

# #-------------------------------------------------------------------------------
# def isBoolean(s):
#   try:
#     bool(s)
#     return True
#   except ValueError:
#     return False

# #-------------------------------------------------------------------------------
# def isEqualFloat(f1,f2):
#   return np.allclose([f1],[f2])

# #-------------------------------------------------------------------------------
# def isFloat(s):
#   try:
#     float(s)
#     return True
#   except ValueError:
#     return False

# #-------------------------------------------------------------------------------
# def isInteger(s):
#   try:
#     int(s)
#     return True
#   except ValueError:
#     return False

# #-------------------------------------------------------------------------------
# def isLinux():
#   if sys.platform.startswith("linux"):
#     return True
#   else:
#     return False

# #-------------------------------------------------------------------------------
# def isNumpyArray(a):
#   if type(a) is np.ndarray:
#     if a.ndim==1:
#       return True
#     else:
#       return False
#   else:
#     return False

# #-------------------------------------------------------------------------------
# def isNumpyGrid(a):
#   if type(a) is np.ndarray:
#     if a.ndim==2:
#       return True
#     else:
#       return False
#   else:
#     return False

# #-------------------------------------------------------------------------------
# # Returns if the arrays are the same.
# def isSame(arr1,arr2):
#     return id(arr1) == id(arr2)

# #-------------------------------------------------------------------------------
# def isString(s):
#   if isinstance(s,basestring):
#     return True
#   elif isinstance(s,str):
#     return True
#   else:
#     return False

# #-------------------------------------------------------------------------------
# # Geeft terug of de base filename geldig is.
# # De betreffende parent directory hoeft niet te bestaan!
# def isValidBaseFileName(fileName):
#   baseFileName = os.path.basename(fileName)
#   for c in INVALID_FILEDIR_CHARS:
#     if c in baseFileName:
#       return False
#   return True

# #-------------------------------------------------------------------------------
# # Geeft terug of de dirname geldig is.
# # Als een parent pad is opgegeven hoeft deze niet al te bestaan!
# def isValidDirName(dirName):
#   # Haal het gedeelte achter de C:.
#   _,fullPath = os.path.splitdrive(dirName)
#   # Geen pad.
#   if (fullPath=="") or (fullPath=="\\") or (fullPath=="/"):
#     # Root pad.
#     return True
#   else:
#     for c in INVALID_DIR_CHARS:
#       if c in fullPath:
#         return False
#     else:
#       return True

# #-------------------------------------------------------------------------------
# # Geeft terug of de dirname en de filename geldig is.
# # Als een pad is opgegeven hoeft deze niet al te bestaan!
# def isValidFileName(fileName):
#   # Haal het gedeelte achter de C:.
#   _,fullPath = os.path.splitdrive(fileName)
#   # Geen pad.
#   if fullPath=="":
#     return isValidBaseFileName(fileName)
#   else:
#     for c in INVALID_DIR_CHARS:
#       if c in fullPath:
#         return False
#     if not isValidBaseFileName(fileName):
#       return False
#     else:
#       return True

# #-------------------------------------------------------------------------------
# # Returns the memory block address of an array.
# def memaddr(a):
#   return a.__array_interface__['data'][0]

# #-------------------------------------------------------------------------------
# def memGetStatus():
#   m = MemoryStatusEx()
#   if "windll" in dir(ctypes):
#     assert ctypes.windll.kernel32.GlobalMemoryStatusEx(byref(m))
#   else:
#     try:
#       import psutil
#       vm = psutil.virtual_memory()
#       m.totalPhys = vm.total
#       m.availPhys = vm.available
#     except:
#       m.totalPhys = 0
#       m.availPhys = 0
#   return m

# #-------------------------------------------------------------------------------
# def memPhysicalAvailable():
#   m = memGetStatus()
#   return m.availPhys

# #-------------------------------------------------------------------------------
# def memPhysicalAvailableGB():
#   m = memGetStatus()
#   return m.availPhys / 1024. / 1024. / 1024.

# #-------------------------------------------------------------------------------
# def memPhysicalTotal():
#   m = memGetStatus()
#   return m.totalPhys

# #-------------------------------------------------------------------------------
# def memPhysicalTotalGB():
#   m = memGetStatus()
#   return m.totalPhys / 1024. / 1024. / 1024.

# #-------------------------------------------------------------------------------
# def memPhysicalUsed():
#   m = memGetStatus()
#   return (m.totalPhys - m.availPhys)

# #-------------------------------------------------------------------------------
# def memPhysicalUsedGB():
#   m = memGetStatus()
#   return (m.totalPhys - m.availPhys) / 1024. / 1024. / 1024.
      
# #-------------------------------------------------------------------------------
# def nrOfCores():
#   cmd = "wmic cpu get NumberOfCores /value"
#   p = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#   out,_ = p.communicate()
#   out = out.replace("\n","")
#   out = out.replace("\r","")
#   out = out.split("=")[1]
#   if out=="":
#     return 0
#   else:
#     return int(out)

# #-------------------------------------------------------------------------------
# def nrOfLogicalProcessors():
#   cmd = "wmic cpu get NumberOfLogicalProcessors /value"
#   p = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#   out,_ = p.communicate()
#   out = out.replace("\n","")
#   out = out.replace("\r","")
#   out = out.split("=")[1]
#   if out=="":
#     return 0
#   else:
#     return int(out)

# #-------------------------------------------------------------------------------
# # precision = number of decimals for floats.
# def printArray(name,data,precision=1):
  
#   def formatValue(v):
#     if isinstance(value,float):
#       fmt = "{:7."+str(precision)+"f}"
#       return fmt.format(value)
#     elif isinstance(value,np.float32):
#       fmt = "{:7."+str(precision)+"f}"
#       return fmt.format(value)
#     elif isinstance(value,np.float64):
#       fmt = "{:7."+str(precision)+"f}"
#       return fmt.format(value)
#     elif isinstance(value,np.uint8):
#       return "{:6d} ".format(value)
#     elif isinstance(value,np.int):
#       return "{:6d} ".format(value)
#     elif isinstance(value,np.int64):
#       return "{:6d} ".format(value)
#     else:
#       return "{:^7s}".format(str(value))

#   if (not name is None) and (name != ""):
#     print(name + ":")
    
#   if data.ndim == 1:
#     s = ""
#     for i in range(len(data)):
#       value = data[i]
#       s += formatValue(value)
#     print(s)
#   elif data.ndim == 2:
#     nrRows,nrCols = data.shape
#     for r in range(nrRows):
#       s = ""
#       for c in range(nrCols):
#         value = data[r,c]
#         s += formatValue(value)
#       print(s)

# #-------------------------------------------------------------------------------
# # Aanroepen met pythonGetScriptDir(__file__)
# def pythonGetScriptDir(fileName):
#   return os.path.dirname(os.path.realpath(fileName))

# #-------------------------------------------------------------------------------
# def pythonVersion():
#   return sys.version

# #-------------------------------------------------------------------------------
# def sameText(s1,s2):
#   return s1.lower()==s2.lower()

# #-------------------------------------------------------------------------------
# # Geeft de seconden terug in dagen, uur, min, sec.
# # 4 days 8 hour 20 min
# # 10 hour 26 min 5 sec
# # 1 hour 2 min 37 sec
# # 6 min 16 sec
# # 37.734 sec
# # 3.734 sec
# def sec2str(Sec,Nl=False,precision=3):
#   if Sec < 60:
#     formatStr = "{:.%sf} sec" % precision
#     if Nl:
#       #return format + " sec".format(Sec).replace(".",",")
#       return formatStr.format(Sec).replace(".",",")
#     else:
#       return formatStr.format(Sec)
#   elif Sec < 3600:
#     Min = trunc(Sec / 60)
#     Sec = Sec - (Min * 60)
#     if Nl:
#       return "{:d} min {:.0f} sec".format(Min,Sec).replace(".",",")
#     else:
#       return "{:d} min {:.0f} sec".format(Min,Sec)
#   elif Sec < 86400:
#     Hours = trunc(Sec / 3600)
#     Sec = Sec - (Hours * 3600)
#     Min = trunc(Sec / 60)
#     Sec = Sec - (Min * 60)
#     if Nl:
#       return "{:d} uur {:d} min {:.0f} sec".format(Hours,Min,Sec).replace(".",",")
#     else:
#       return "{:d} hour {:d} min {:.0f} sec".format(Hours,Min,Sec)
#   else:
#     Days = trunc(Sec / 86400)
#     Sec = Sec - (Days * 86400)
#     Hours = trunc(Sec / 3600)
#     Sec = Sec - (Hours * 3600)
#     Min = trunc(Sec / 60)
#     Sec = Sec - (Min * 60)
#     if Nl:
#       if Days == 1:
#         StrDays = "dag"
#       else:
#         StrDays = "dagen"
#       return "{:d} {} {:d} uur {:d} min".format(Days,StrDays,Hours,Min).replace(".",",")
#     else:
#       if Days == 1:
#         StrDays = "day"
#       else:
#         StrDays = "days"
#       return "{:d} {} {:d} hour {:d} min".format(Days,StrDays,Hours,Min)

# #-------------------------------------------------------------------------------
# def sec2str_short(sec):
#   hours, remainder = divmod(sec,3600)
#   minutes, seconds = divmod(remainder,60)
#   return "{:0>2d}:{:0>2d}:{:0>2d}".format(hours,minutes,seconds)

# #-----------------------------------------------------------------------------
# def sec2strNL(Sec):
#   return sec2str(Sec,True)

# #-------------------------------------------------------------------------------
# # Case-insensitive.
# def startsWith(s,swith):
#   return s.lower().startswith(swith.lower())

# #-------------------------------------------------------------------------------
# # Geeft het deel van de string achter de eerste positie van de opgegeven
# # string terug.
# # Geeft een lege string terug indien niet gevonden.
# # Case-insensitive.
# def strAfter(s,after):
#   index = s.lower().find(after.lower())
#   if index < 0:
#     return ""
#   else:
#     return s[(index+len(after)):]

# #-------------------------------------------------------------------------------
# # Geeft het deel van de string achter de eerste positie van de opgegeven
# # string terug.
# # Geeft een lege string terug indien niet gevonden.
# # Case-insensitive.
# def strAfterLast(s,after):
#   index = s.lower().rfind(after.lower())
#   if index < 0:
#     return ""
#   else:
#     return s[(index+len(after)):]

# #-------------------------------------------------------------------------------
# # Geeft het deel van de string voor de eerste positie van de opgegeven string
# # terug.
# # Geeft een lege string terug indien niet gevonden.
# # Case-insensitive.
# def strBefore(s,before):
#   index = s.lower().find(before.lower())
#   if index < 0:
#     return ""
#   else:
#     return s[:index]

# #-------------------------------------------------------------------------------
# # Geeft het deel van de string voor de laatste positie van de opgegeven string
# # terug.
# # Geeft een lege string terug indien niet gevonden.
# # Case-insensitive.
# def strBeforeLast(s,before):
#   index = s.lower().rfind(before.lower())
#   if index < 0:
#     return ""
#   else:
#     return s[:index]

# #-------------------------------------------------------------------------------
# # Voegt 2 strings samen waarbij s2 rechts uitgelijnd wordt.
# def strConcatAlignRight(s1,s2,totaLLength):
#   cnt = totaLLength - len(s1) - len(s2)
#   if cnt>0:
#     t = strFill(" ",cnt)
#   else:
#     t = ""
#   return s1 + t + s2

# #-------------------------------------------------------------------------------
# def strDQuote(s):
#   return "\"" + s + "\""

# #-------------------------------------------------------------------------------
# def strFill(c,count):
#   return c * count

# #-------------------------------------------------------------------------------
# def strReplaceBackslash(s):
#   return s.replace("\\","/")

# #-------------------------------------------------------------------------------
# def strReplaceTabs(s,tabstop = 2):
#   result = str()
#   for c in s:
#     if c == "\t":
#       while (len(result) % tabstop != 0):
#         result += " ";
#     else:
#       result += c
#   return result

# #-------------------------------------------------------------------------------
# # Verwijdert dubbele delimitors en leading en tailing delimitors.
# # Geeft een lege lijst terug indien s leeg is.
# # Geeft een lijst met de oorspronkelijke string terug indien niet gevonden.
# def strSplit(s,t):
#   # Een lege string?
#   if len(s)==0:
#     return []
#   # Maak een kopie.
#   r1 = s
#   # Vervang tot er niets meer veranderd.
#   while True:
#     r2 = r1.replace(t+t,t)
#     if r2==r1:
#       break
#     r1 = r2
#   return r2.strip(t).split(t)

# #-------------------------------------------------------------------------------
# # Splitst een volledige veldnaam (table\field) uit in tabelnaam en veldnaam.
# def tablefieldNameSplit(tablefieldname):
#   tableName = strBeforeLast(tablefieldname,"\\")
#   fieldName = strAfterLast(tablefieldname,"\\")
#   return (tableName,fieldName)

# #-------------------------------------------------------------------------------
# # Truncs a float. Standard Python int() function does not always give
# # correct results.
# # 
# # Example:
# #   int(24.4 / 0.2)         gives 121
# #
# # Deze doet het ook goed.
# # def trunc(a):
# #   fr,mo = math.modf(a)
# #   if fr > mod_delta2:
# #     mo += 1
# #   return mo
# #-------------------------------------------------------------------------------
# # Truncs a float with n decimals, with no rounding.
# def trunc(f,n=0):
#   s = "{}".format(f)
#   if "e" in s or "E" in s:
#     if n==0:
#       return int("{0:.{1}f}".format(f,n))
#     else:
#       return float("{0:.{1}f}".format(f, n))
#   i,_,d = s.partition(".")
#   if n==0:
#     return int(float("".join([i,(d+"0"*n)[:n]])))
#   else:
#     return float(".".join([i,(d+"0"*n)[:n]]))

# #-------------------------------------------------------------------------------
# #-------------------------------------------------------------------------------
# if __name__ == "__main__":

#   print(sec2str(45))
#   print(sec2str(121))
#   print(sec2str(3605))
#   print(sec2str(3605*24))
#   print(sec2strNL(3605*24))

#   print(1234567890.12345678)

#   print(floatToStr(1234567890.12345678))
#   print(floatToStr(1234567890.12345678,1))
#   print(floatToStr(1234567890.12345678,5,True))

#   print(floatToStrNL(1234567890.12345678))
#   print(floatToStrNL(1234567890.12345678,1))
#   print(floatToStrNL(1234567890.12345678,5,True))

#   print(intToStr(1234567890))
#   print(intToStrNL(1234567890))

#   print(bytesToStr(123))
#   print(bytesToStr(123 + 1024))
#   print(bytesToStr(123 + 1024*1024))
#   print(bytesToStr(123 + 1024*1024*1024))

#   print(strAfter("Dit is een test."," "))
#   print(strAfter("Dit is een test.","xxx"))
#   print(strAfter("Dit is een test.","s ee"))

#   print(strBefore("Dit is een test."," "))
#   print(strBefore("Dit is een test.","xxx"))
#   print(strBefore("Dit is een test.","s ee"))

#   print(strSplit("  1111 222   333  "," "))
#   print(strSplit("----1111-222---333----4444----","--"))
#   print(strSplit("---1111-222---333----4444---","--"))
#   print(strSplit("  1111 222   333  ","X"))

#   print(strSplit("sssss",","))
#   print(strSplit("",","))

#   print(strBeforeLast("c:\\tabelname\\fieldname","\\"))
#   print(strAfterLast("c:\\tabelname\\fieldname","\\"))

#   print(strFill("-",5))

#   print(pythonVersion())
#   print(pythonGetScriptDir(__file__))
  
#   print(dateTimeToStr())
#   print(dateTimeToStrShort())

#   print(getNewFileName("C:\\Temp\\aaa.dat"))
#   print(getNewFileName("C:\\Temp\\aaa.dat",2))
#   print(getNewFileName("C:\\Temp\\aaa.dat",5))
#   print(getNewFileName("C:\\Temp\\bbb"))

#   def testIsValidFileName(fileName):
#     print(fileName + "      " + str(isValidFileName(fileName)))

#   def testIsValidDirName(dirName):
#     print(dirName + "      " + str(isValidDirName(dirName)))

# #   def testIsValidDirFileName(fileName):
# #     print fileName + "      " + str(isValidDirFileName(fileName))
    
#   print("----------")
#   testIsValidFileName("aaa.dat")
#   testIsValidFileName("aa:a.dat")
#   testIsValidFileName("C:\\Temp\\aaa.dat")
#   testIsValidFileName("C:\\Temp\\xxx\\aaa.dat")
#   testIsValidFileName("C:\\Temp\\aaa.dat")
#   testIsValidFileName("C:\\Temp\\aa:a.dat")
#   testIsValidFileName("C:\\Temp\\aa$a.dat")
#   testIsValidFileName("C:\\Temp\\aa|a.dat")
#   testIsValidFileName("C:\\Temp\\aa\"a.dat")
#   testIsValidFileName("C:\\Tex\\aaa.dat")
#   testIsValidFileName("C:\\Temp\\:\\http:\\aaa.dat")
#   testIsValidFileName("C:\\Te/mp\\aaa.dat")
#   testIsValidFileName("C:\\Te|mp\\aaa.dat")
#   testIsValidFileName("C:\\Temp\\aaaa<bbbb\\aaa.dat")
        
#   print("----------")
#   testIsValidDirName("aaa")
#   testIsValidDirName("aaa.gdb")
#   testIsValidDirName("C:")
#   testIsValidDirName("C:\\")
#   testIsValidDirName("C:/")
#   testIsValidDirName("K:\\")
#   testIsValidDirName("C:\\Temp\\aaa")
#   testIsValidDirName("C:\\Temp\\aaa.gdb")
#   testIsValidDirName("C:\\Temp\\xxx\\aaa.gdb")
#   testIsValidDirName("C:\\Temp\\aa:a.gdb")
#   testIsValidDirName("C:\\Temp\\aa$a.gdb")
#   testIsValidDirName("C:\\Temp\\aa|a.gdb")
#   testIsValidDirName("C:\\Tex\\aaa.gdb")
#   testIsValidDirName("C:\\Temp\\:\\http:\\aaa.gdb")

# #   print "----------"
# #   testIsValidDirFileName("aaa.dat")
# #   testIsValidDirFileName("aa:a.dat")
# #   testIsValidDirFileName("C:\\Temp\\aaa.dat")
# #   testIsValidDirFileName("C:\\Temp\\xxx\\aaa.dat")
# #   testIsValidDirFileName("C:\\Temp\\aa:a.dat")
# #   testIsValidDirFileName("C:\\Temp\\aa$a.dat")
# #   testIsValidDirFileName("C:\\Temp\\aa|a.dat")
# #   testIsValidDirFileName("C:\\Temp\\aa\"a.dat")
# #   testIsValidDirFileName("C:\\Tex\\aaa.dat")
# #   testIsValidDirFileName("C:\\Temp\\:\\http:\\aaa.dat")
# #   testIsValidDirFileName("C:\\Te/mp\\aaa.dat")
# #   testIsValidDirFileName("C:\\Te|mp\\aaa.dat")
# #   testIsValidDirFileName("C:\\Temp\\aaaa<bbbb\\aaa.dat")
        
#   print(isEqualFloat(0.1, 0.1))
#   print(isEqualFloat(0.1, 0.100001)      )
#   print(isEqualFloat(0.1, 0.100000001)      )
#   print(isEqualFloat(0.1, 0.100000000001)      )
#   print(isEqualFloat(1.0/3.0,2.0/6.0)      )
#   print(isEqualFloat(0.1, 0.11))
#   print(isEqualFloat(0.1, 0.101))
  
#   print("---- int")
  
#   print(int(122))
#   print(int(122.0))
#   print(int(24.4 / 0.2))
  
#   print("---- trunc")
  
#   # 1.99
#   # 999.0
#   # 12345.0
#   # 0.0
#   # 122.0
#   # 122.0
#   # 122.0
#   print(trunc(1.9999345,2))
#   print(trunc(999.12345))
#   print(trunc(12345))
#   print(trunc(0.12345))
#   print(trunc(122))
#   print(trunc(122.0))
#   print(trunc(24.4 / 0.2))

#   # 20161207
#   print(trunc(4.07999982601e-05))
#   print(type(trunc(4.07999982601e-05)))

#   print(trunc(4.07999982601e-05,1))
#   print(type(trunc(4.07999982601e-05,1)))
  
#   print(trunc(4.07999982601e-05,2))
#   print(type(trunc(4.07999982601e-05,2)))

#   print(trunc(4.07999982601e-05,3))
#   print(type(trunc(4.07999982601e-05,3)))
  
#   print(trunc(4.07999982601e-05,6))
#   print(trunc(4.07999982601e-05,10))
  
#   # 20172604
#   print(getFileNameExtension("C:\\Temp\\aaa"))
#   print(getFileNameExtension("C:\\Temp\\aaa.dat"))

