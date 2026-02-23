# :coding: utf-8
"""
Run when the MroyaFtrack plugin is enabled. Registers the Ftrack menu in the editor.

Unreal runs this automatically from Content/Python/init_unreal.py (no Startup Scripts needed).
We register the menu on the first Slate tick so LevelEditor.MainMenu is ready.
"""

from __future__ import annotations

import os
import sys
import traceback

def _log(msg):
    try:
        import unreal
        unreal.log("MroyaFtrack: %s" % msg)
    except Exception:
        print("MroyaFtrack:", msg)

# Resolve plugin paths at import time (__file__ is not defined inside Unreal's tick callback)
_THIS_FILE = os.path.abspath(__file__)
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
_SCRIPTS = os.path.join(_PLUGIN_ROOT, "Scripts")

_registered = False

def _on_tick(delta_seconds):
    global _registered
    if _registered:
        return
    _registered = True
    try:
        import unreal
        unreal.unregister_slate_post_tick_callback(_tick_handle)
    except Exception:
        pass
    try:
        if _SCRIPTS and _SCRIPTS not in sys.path:
            sys.path.insert(0, _SCRIPTS)
        if not _SCRIPTS or not os.path.isdir(_SCRIPTS):
            _log("Scripts folder not found at %s" % _SCRIPTS)
        else:
            from init_ftrack_menu import register_ftrack_menu
            register_ftrack_menu()
    except Exception as e:
        _log("Failed to register Ftrack menu: %s" % e)
        _log(traceback.format_exc())

try:
    import unreal
    _tick_handle = unreal.register_slate_post_tick_callback(_on_tick)
    _log("Deferred menu registration scheduled.")
except Exception as e:
    _log("Could not schedule menu registration: %s" % e)
    _log(traceback.format_exc())
