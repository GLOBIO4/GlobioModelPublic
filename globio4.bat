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
REM           - PYTHONEXE added.
REM           - PYTHONHOME added.
REM           - Add GLOBIO paths aangepast.
REM           17 nov 2020, ES, ARIS B.V.
REM           - TAUDEMPATH added.
REM           20 jul 2023, MM, PBL
REM           - Only activate conda environment when not active yet
REM           - Rename some variables
REM           - Load variables from globio.env file
REM           - Add checks with error messages
REM           - Pass all arguments to python script call
REM ###########################################################################

setlocal

set "GLOBIO_ENV_FILE=%~dp0globio.env"
@REM ### Check if the globio.env file exists
if NOT exist "%GLOBIO_ENV_FILE%" (
    echo Could not find file %~dp0globio.env
    echo Please create it in the root GlobioModel folder
    echo See README.md for more detailed instructions
    exit /b
)

@REM ### Load the variables defined in globio.env
for /F "usebackq eol=# tokens=*" %%i in ("%GLOBIO_ENV_FILE%") do set "%%i"

@REM ### Check if the GLOBIO_WORKSPACE_DIR variable was set, and exists
if "%GLOBIO_WORKSPACE_DIR%"=="" (
    echo Please set your GLOBIO_WORKSPACE_DIR in globio.env
    echo See README.md for more detailed instructions
    exit /b
)
if NOT exist "%GLOBIO_WORKSPACE_DIR%\" (
    echo The directory "%GLOBIO_WORKSPACE_DIR%\" could not be found
    echo Please update your GLOBIO_WORKSPACE_DIR in globio.env
    echo See README.md for more detailed instructions
    exit /b
)

@REM ### Check if the GRASS_PATH variable was set, and exists
if "%GRASS_PATH%"=="" (
    echo Please set your GRASS_PATH in globio.env
    echo See README.md for more detailed instructions
    exit /b
)
if NOT exist "%GRASS_PATH%\" (
    echo The directory "%GRASS_PATH%\" could not be found
    echo Please update your GRASS_PATH in globio.env
    echo See README.md for more detailed instructions
    exit /b
)

@REM ### If not explicitly defined in globio.env, use globio4env as the default conda environment
if "%CONDA_ENV%"=="" (
    set "CONDA_ENV=globio4env"
)

@REM ### If not yet activated, activate the conda environment
if NOT "%CONDA_DEFAULT_ENV%"=="%CONDA_ENV%" (
    if NOT "%CONDA_PREFIX%"=="%CONDA_ENV%" (
        echo Activating %CONDA_ENV% ...
        call activate %CONDA_ENV%
    )
)

@REM ### Set GISBASE environment variable to the grass installation path
set GISBASE=%GRASS_PATH%

@REM ### Set path to TauDEM as environment variable
set "TAUDEMPATH=%CONDA_PREFIX%\Library\bin\"

@REM ### Add globio workspace and grass python lib to PYTHONPATH
set PYTHONPATH=%GLOBIO_WORKSPACE_DIR%;%GRASS_PATH%\etc\python

@REM ### Run Globio Python script and pass along all arguments
python "%GLOBIO_WORKSPACE_DIR%\GlobioModel\Core\Globio4.py" %*

endlocal
