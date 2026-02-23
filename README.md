# Mroya Ftrack — Unreal Engine plugin

This is the **FTRACK_UE_PLUGIN** repo. Use it in an Unreal project by linking or copying this folder into the project's `Plugins` folder (e.g. as `Plugins/MroyaFtrack`).

## Option 1: Symlink (recommended)

One source of truth: all code stays in mroya; the project only references it.

**Windows (run as Administrator, or enable Developer Mode for symlinks):**
```cmd
mklink /D "C:\Path\To\YourProject\Plugins\MroyaFtrack" "G:\mroya\Plugins\MroyaFtrack"
```

**Windows junction (no admin required):**
```cmd
mklink /J "C:\Path\To\YourProject\Plugins\MroyaFtrack" "G:\mroya\Plugins\MroyaFtrack"
```

**Linux / macOS:**
```bash
ln -s /path/to/mroya/Plugins/MroyaFtrack /path/to/YourProject/Plugins/MroyaFtrack
```

## Option 2: Copy

Copy this folder into your project: `YourProject/Plugins/MroyaFtrack`.  
Updates require copying again from mroya.

## Layout

- This folder is the plugin (and this repo). You can place it e.g. at `mroya/Plugins/MroyaFtrack` or anywhere else.
- **Source/MroyaFtrack/** — C++ module: `UFtrackAssetHandle` (DataAsset) for the "handle" workflow (store component ID, load/re-import later). Requires compiling the project in Unreal (right-click .uproject -> Generate Visual Studio project files, then Build).
- Ftrack Connect integration and browser launcher live in the mroya tree: `ftrack_plugins/ftrack_framework_unreal-0.0.0/`, `tools/run_browser.py`. Set `MROYA_FTRACK_CONNECT` to the mroya root so the plugin can find them.

## Usage

1. **Enable the plugin**: Edit -> Plugins -> search "Mroya Ftrack" -> Enable -> restart the editor if asked.
2. Set **MROYA_FTRACK_CONNECT** to the mroya root (e.g. `G:\mroya`) in your environment so the browser can find ftrack_plugins.

The **ftrack** menu appears in the main menu. **ftrack -> Open browser** opens the browser in-process (parented to the editor). Import is done from the browser via the Import button (with import options dialog). The built-in **Python Editor Script** plugin must be enabled (Edit -> Plugins -> Scripting).

**If the menu does not appear:** (1) Enable **Python Editor Script** and restart the editor. (2) In Output Log (Window -> Developer Tools -> Output Log) search for `MroyaFtrack` — you should see "Deferred menu registration scheduled." and then "Ftrack: Menu registered...". If there is no "MroyaFtrack" line, Unreal may not be running our `Content/Python/init_unreal.py`. Add the script manually: **Edit -> Project Settings -> Plugins -> Python -> Startup Scripts**, add the full path to `Scripts/init_ftrack_menu.py` (e.g. `G:\mroya\Plugins\MroyaFtrack\Scripts\init_ftrack_menu.py`), restart the editor.

**If the menu still shows the old name (e.g. "Ftrack" instead of "ftrack):** Unreal caches menu data. Fully close the editor, then either: disable the Mroya Ftrack plugin and restart, enable the plugin again and restart; or delete the project's `Saved` folder (back it up first if needed) and restart the editor.

## Building the C++ module (Ftrack Handle)

The plugin has an Editor C++ module that provides **Ftrack Asset Handle** (DataAsset with `ComponentId`, `ContentSubpath`, `AssetVersionId`).

**If you see "This project does not have any source code"** when generating project files, your project is Blueprint-only and has no C++ module. Add C++ to the project once:

1. Open the project in **Unreal Editor**.
2. **File -> New C++ Class** (or **Tools -> New C++ Class**). Choose **None** (parent class) or **Actor**, name it e.g. `DummyGameModule`, and click Create. This creates a `Source/YourProjectName/` folder and a minimal module so the project is considered a C++ project.
3. Close the editor. Right-click the `.uproject` file -> **Generate Visual Studio project files**. It should succeed.
4. Open the solution and build, or open the project in the editor again so it compiles the plugin.

Then:

1. Right-click the `.uproject` file -> **Generate Visual Studio project files** (or **Generate Xcode project** on macOS).
2. Open the generated solution and build the project (e.g. Build -> Build Solution), or build from Unreal Editor (it will compile when you open the project if the module was added).
3. After the first successful build, the **FtrackAssetHandle** class is available: create a Blueprint or DataAsset based on it in Content Browser, or create it from Python.

If your Unreal version uses a different path for `UPrimaryDataAsset`, change the include in `Source/MroyaFtrack/Public/FtrackAssetHandle.h` (e.g. to `Engine/DataAsset.h` and inherit from `UDataAsset` if needed).

## Development setup (Python)

Use Python 3.11 (same as Unreal 5) and a local venv:

```cmd
cd Plugins\MroyaFtrack
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r dependencies\requirements.txt
```

Installed packages (PySide6, unreal-qt) are in `.venv`; `dependencies/` is for Unreal's sys.path when running in-editor. The repo ignores `.venv` and installed content in `dependencies/` (see `.gitignore`).

## Environment

When the plugin is used via **symlink**, Unreal sees the project path (e.g. `YourProject/Plugins/MroyaFtrack`), not the real mroya path, so the plugin cannot derive the mroya root from disk. Set the mroya root explicitly:

- **`MROYA_FTRACK_CONNECT`** — mroya repo root (e.g. `G:\mroya`). The bootstrap script uses it to find `tools/run_browser.py` and run the browser. Set this in system env or in Connect launch so that Unreal (and the Python startup script) see it.
