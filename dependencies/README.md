# MroyaFtrack plugin dependencies

Python packages used when running the Ftrack browser (or other Qt UI) **inside** Unreal Editor.

## Unreal Python version

**Unreal Engine 5** ships with **Python 3.11.8** (embedded). The Python Editor Script Plugin uses this by default. So install dependencies with Python 3.11:

```bash
python3.11 -m pip install -r requirements.txt -t .
```

On Windows, if Unreal is installed but you use a separate Python 3.11:

```cmd
py -3.11 -m pip install -r requirements.txt -t .
```

Or point to Unreal's Python (example path; your install may differ):

```cmd
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m pip install -r requirements.txt -t .
```

## Packages

- **PySide6** — Qt for Python (widgets, windows). Required for the browser UI when run in-process.
- **unreal-qt** — Integrates PySide6 with Unreal (parent windows to editor, event loop). Depends on PySide6 and unreal-stylesheet.

After installing, the `dependencies` folder will contain these packages (and their dependencies). The plugin adds this folder to `sys.path` when loading so Unreal's Python can import them.
