# GlobioModel
Repository for the GLOBIO4 model code.

* [Installation prerequisites](#installation-prerequisites)
* [Cloning the model](#cloning-the-model)
* [Setting up the globio4env conda environment](#setting-up-the-globio4env-conda-environment)
* [Running GLOBIO with Visual Studio Code](#running-globio-with-visual-studio-code)
    * [Setting up Python configuration](#setting-up-python-configuration)
    * [Setting up debug configuration](#setting-up-debug-configuration)
    * [Setting up IntelliSense](#setting-up-intellisense)
    * [Running GLOBIO in the VSCode integrated terminal](#running-globio-in-the-vscode-integrated-terminal)
* [Running GLOBIO in the terminal through `globio.bat` (Windows)](#running-globio-in-the-terminal-through-globiobat-windows)

## Installation prerequisites
* [Visual Studio Code](https://code.visualstudio.com/download) is recommended to manage your workspace and edit files.
* [Git](https://git-scm.com/downloads) is needed to clone the model. A workaround is to download and unpack a zip from [GitHub](https://github.com/GLOBIO4/GlobioModelPublic).
* [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html) is used to create and manage a python environment to run from.
* [GRASS](https://grass.osgeo.org/download/windows/) is used in certain GLOBIO modules. Make sure to set the following settings during installation: `Important MS Dlls: ON` and `Download msvc\*: YES`

## Cloning the model
* Create a workspace folder called `GlobioWorkspace` or whatever your preference is.
* Navigate to your workspace folder and start a command prompt.
* Clone the GLOBIO model code with `git clone git@github.com:GLOBIO4/GlobioModelPublic.git GlobioModel`.
* Navigate to the cloned model with `cd GlobioModel`.

## Setting up the globio4env conda environment
If you do not have access to the shared `globio4env` conda environment, you will have to create one from the `environment.yml`.
* `conda env create -f environment.yml`
* `conda activate globio4env`

For non-Windows platforms, the `environment_loose.yml` may be used instead, which leaves more flexibility to conda for creating the environment.

## Running GLOBIO with Visual Studio Code
Open Visual Studio Code and open your root Globio folder, e.g., `GlobioWorkspace`. Before we can properly work with the model, this section contains some tips to get your working environment in VSCode working optimally.

### Setting up Python configuration
For running the model from the integrated terminal in VS Code, we need to make a few adjustments to the workspace settings.
* Make a new folder called `.vscode` in your `GlobioWorkspace` folder.
* Make a new file called `settings.json` in the `.vscode` folder.
* Copy-paste the following to `settings.json`:

```
{
    "python.defaultInterpreterPath": "[path-to-anaconda-installation]/envs/globio4env/python.exe",
    "python.terminal.activateEnvironment": true,
    "terminal.integrated.env.windows": {
        "PYTHONPATH": "${workspaceFolder};[path-to-grass-installation]/etc/python",
        "PATH": "${workspaceFolder}/GlobioModel;${env:PATH}",
        "GISBASE": "[path-to-grass-installation]"
    }
}
```
and substitute your paths to the Anaconda and GRASS installations.

(for Linux or OSX, replace `terminal.integrated.env.windows` with `terminal.integrated.env.linux` or `terminal.integrated.env.osx`, respectively)

This is what the above lines do:
* The first line makes sure that by default, VS Code should use the python interpreter of the `globio4env` conda environment. This is overwritten if you select a python interpreter manually in VS Code, and is mainly for convenience.
* The second line makes sure that when an integrated terminal is started, the conda environment is automatically started. This means you should not have to run `conda activate globio4env` any more when you start an integrated terminal in VS Code.
* In the terminal-specific settings, we first add the workspace folder to the `PYTHONPATH`. Otherwise, this might lead to a "could not find 'GlobioModel' module" error. We also add the GRASS python modules to the `PYTHONPATH` so that the GRASS-related imports work.
* The `PATH` environment variable is augmented with the `GlobioModel` directory. This allows directly running `globio4.bat` from the `GlobioWorkspace` directory.
* Finally, we define the environment variable `GISBASE`, which is used in the `Grass.py` module.

### Setting up debug configuration
For using the integrated debug functionality within VS Code, we need to create a launch configuration and specify some parameters. Create a file `launch.json` in the `.vscode` folder and paste the following lines:

```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "GISBASE": "[path-to-grass-installation]",
                "PYTHONPATH": "${workspaceFolder};[path-to-grass-installation]/etc/python"
            },
            "python": "[path-to-anaconda-installation]/envs/globio4env/python.exe"
        }
    ]
}
```

Most of these settings speak for themselves. Unfortunately, the debug configurations in `launch.json` do not automatically inherit from `settings.json`, so we have to re-set some of the variables that we defined earlier.

### Setting up IntelliSense
Some tools in Visual Studio Code, like IntelliSense (which performs for example code completion) do not run from the terminal, so to configure these correctly we have to make an addition to the `PYTHONPATH` environment variable via an environment definition file `.env`. It is important to note that environment variables defined in `.env` overwrite environment variables set in `settings.json`.

The only change to the environment variables we need to make is to add the path to the GRASS python modules to the `PYTHONPATH`. This will ensure that IntelliSense recognizes the `import` lines related to the GRASS modules. Also, we will add a line to `settings.json` specifying where VS code can find the environment file.

* Add `"python.envFile": "${workspaceFolder}/.vscode/.env"` to `.vscode/settings.json`.
* Make a new file `.vscode/.env`.
* Add `PYTHONPATH="[path-to-workspace];[path-to-grass-installation]/etc/python"` as the only line in `.vscode/.env`, where you substitute your own path to the GRASS application. Note that this now overwrites the line in `settings.json` where the `PYTHONPATH` variable for the terminal was set.

### Running GLOBIO in the VSCode integrated terminal
After completing all the VS Code configuration steps described above, you should be able to run the GLOBIO model by running `Core/Globio4.py`. You can either do this in VS Code by pressing the 'Run' button, or via the integrated terminal by typing `python GlobioModel/Core/Globio4.py`. You should get a help message explaining the usage of the model. Individual files containing a `if __name__ == "__main__":` part (usually intended for testing or debugging individual modules) can also be run in either of these two ways.

## Running GLOBIO in the terminal through `globio.bat` (Windows)
The alternative way to run the GLOBIO model is via the `globio4.bat` batch script. You can call this script by simply typing `globio4` or `globio4.bat` in a terminal. Make sure that either you are in the `GlobioModel` directory when you run this, or this directory is added to your `PATH` environment variable. 
(In the integrated terminal of VS Code, we fixed this earlier and you should be able to run `globio4` from the root `GlobioWorkspace` directory.)

Before you can run `globio4.bat`, you must first set some variables relating to your local installation. First, create a file called `globio.env` in the `GlobioModel` folder. Open it, and add the following lines depending to your installation of the model:

```
GLOBIO_WORKSPACE_DIR=[path-to-globio-workspace]
CONDA_ENV=[path-to-conda-env] (OPTIONAL)
GRASS_PATH=[path-to-grass-installation]
```

* The `GLOBIO_WORKSPACE_DIR` variable should point to your workspace directory, i.e., the path to `GlobioWorkspace`.
* The `CONDA_ENV` should point to a conda environment, i.e., `[path-to-conda-installation]/envs/[your-env]`. If not specified, the script will try to find a conda environment called `globio4env` and try to activate it. Hence, you only need to set the `CONDA_ENV` variable if you want to explicitly use a conda environment other than the `globio4env` environment.
* The `GRASS_PATH` variable should point to your GRASS installation directory, for example `C:\Program Files\GRASS GIS 7.8`.

If you now run the script from any terminal (command prompt, Anaconda Prompt, PowerShell), you should get the default GLOBIO model help message.

## Further information on getting started
Check out [the wiki](https://github.com/GLOBIO4/GlobioModelPublic/wiki) for more information on how to work with the GLOBIO model.
