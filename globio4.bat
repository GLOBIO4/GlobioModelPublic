@echo off

REM ###########################################################################
REM 
REM GLOBIO4.BAT
REM 
REM Runs a GLOBIO 4 script.
REM
REM Example:
REM
REM   globio4.bat Scripts\Run_All.glo
REM
REM Modified: 3 nov 2016, ES, ARIS B.V.
REM           - Version 4.0.2
REM           - Path of var GLOBIO4 changed.
REM           6 mar 2017, ES, ARIS B.V.
REM           - Version 4.0.5
REM           - More checks added for env.var. PATH.
REM           22 mar 2017, ES, ARIS B.V.
REM           - Version 4.0.5
REM           - En/disable Windows Error Reporting added.
REM           8 nov 2018, ES, ARIS B.V.
REM           - Version 4.0.12
REM           - Set to Globio4AQ directory.
REM           - PYTHONPATH - /Preprocessing and /Workers added.
REM           13 nov 2020, ES, ARIS B.V.
REM           - PYTHONEXE toegevoegd.
REM           - PYTHONHOME toegevoegd.
REM           - Add GLOBIO paths aangepast.
REM           17 nov 2020, ES, ARIS B.V.
REM           - TAUDEMPATH toegevoegd.
REM ###########################################################################


@REM ### Activate globio environment.
call C:\PBLprogs\Anaconda3\condabin\conda activate globio41

@REM ### Set GLOBIO4 env. var.
set GLOBIO4=Z:\GlobioModel41\DEV_GIT

@REM ### Set PYTHON env. vars.
set PYTHONEXEPATH=C:\PBLprogs\Anaconda3\envs\globio41
set PYTHONEXE=%PYTHONEXEPATH%\python.exe

@REM ### Set GRASS env. vars.
set GRASS=C:\PBLprogs\OSGeo4W64\apps\grass\grass78
set GISBASE=%GRASS%

@REM ### Set TauDEM path.
set TAUDEMPATH=%PYTHONEXEPATH%\Library\bin\

@REM ### Set PYTHONPATH env. var.
set PYTHONPATH=%GLOBIO4%;%GRASS%\etc\python

@REM ### Run globio Python script.
%PYTHONEXE% %GLOBIO4%\GlobioModel\Core\Globio4.py %1 %2
