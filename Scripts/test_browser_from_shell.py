# :coding: utf-8
"""
Test Ftrack browser launch from Unreal Python shell (Window -> Developer Tools -> Python Console).

Run in Unreal:
  exec(open(r"G:\\mroya\\Plugins\\MroyaFtrack\\Scripts\\test_browser_from_shell.py").read())

Or: Run Python Script and select this file.

Prints each step so we can see what happens (wrap, window parent, visibility).
"""

from __future__ import annotations

import os
import sys

# Same paths as open_browser_inprocess
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_ROOT = os.path.dirname(_THIS_DIR)


def _bootstrap_paths() -> bool:
    mroya_root = os.environ.get("MROYA_FTRACK_CONNECT", "").strip()
    if not mroya_root or not os.path.isdir(mroya_root):
        print("[test] MROYA_FTRACK_CONNECT not set or not a directory:", repr(mroya_root))
        return False
    mroya_root = os.path.normpath(mroya_root)
    plugins_root = os.path.join(mroya_root, "ftrack_plugins")
    inout_deps = os.path.join(plugins_root, "ftrack_inout", "dependencies")
    multi_site_deps = os.path.join(plugins_root, "multi-site-location-0.2.0", "dependencies")
    deps_dir = os.path.join(_PLUGIN_ROOT, "dependencies")
    for label, p in [
        ("ftrack_plugins", plugins_root),
        ("inout deps", inout_deps),
        ("multi-site deps", multi_site_deps),
        ("dependencies", deps_dir),
    ]:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
            print("[test] Added to sys.path (%s): %s" % (label, p))
    print("[test] Bootstrap OK, mroya_root=%s" % mroya_root)
    return True


def run_test() -> None:
    global _browser_test_widget
    print("[test] === Ftrack browser shell test ===\n")

    if not _bootstrap_paths():
        print("[test] Abort: bootstrap failed")
        return

    os.environ["FTRACK_DCC"] = "unreal"

    # unreal_qt
    print("[test] Importing unreal_qt...")
    try:
        import unreal_qt
        print("[test] unreal_qt: %s" % unreal_qt)
        print("[test] dir(unreal_qt): %s" % [x for x in dir(unreal_qt) if not x.startswith("_")])
    except Exception as e:
        print("[test] Failed to import unreal_qt: %s" % e)
        import traceback
        traceback.print_exc()
        return

    print("[test] Calling unreal_qt.setup()...")
    try:
        unreal_qt.setup()
        print("[test] unreal_qt.setup() OK")
    except Exception as e:
        print("[test] unreal_qt.setup() failed: %s" % e)
        import traceback
        traceback.print_exc()
        return

    if hasattr(unreal_qt, "wrap"):
        print("[test] unreal_qt.wrap: %s" % unreal_qt.wrap)
    else:
        print("[test] unreal_qt has NO 'wrap' attribute")

    # FtrackBrowser
    print("[test] Importing FtrackBrowser...")
    try:
        from ftrack_inout.browser import FtrackBrowser
        print("[test] FtrackBrowser: %s" % FtrackBrowser)
    except Exception as e:
        print("[test] Failed to import FtrackBrowser: %s" % e)
        import traceback
        traceback.print_exc()
        return

    print("[test] Creating FtrackBrowser()...")
    try:
        widget = FtrackBrowser()
        print("[test] widget=%s, class=%s" % (widget, type(widget).__name__))
        print("[test] widget.parent()=%s" % widget.parent())
        print("[test] hasattr(widget,'close')=%s, type(widget.close)=%s" % (hasattr(widget, "close"), type(getattr(widget, "close", None))))
    except Exception as e:
        print("[test] Failed to create FtrackBrowser: %s" % e)
        import traceback
        traceback.print_exc()
        return

    # PySide6 close signal workaround
    try:
        from PySide6 import QtCore
        from PySide6.QtWidgets import QWidget
        class _CloseSignalHolder(QtCore.QObject):
            close = QtCore.Signal()
        _holder = _CloseSignalHolder(widget)
        _orig = widget.closeEvent
        def _close_event(event):
            _holder.close.emit()
            if _orig:
                _orig(event)
        widget.closeEvent = _close_event
        widget.close = _holder.close
        print("[test] Added close signal for PySide6")
    except Exception as e:
        print("[test] Close signal workaround skipped: %s" % e)

    # wrap
    if hasattr(unreal_qt, "wrap"):
        print("[test] Calling unreal_qt.wrap(widget)...")
        try:
            unreal_qt.wrap(widget)
            print("[test] unreal_qt.wrap(widget) OK")
        except Exception as e:
            print("[test] unreal_qt.wrap(widget) raised: %s" % e)
            import traceback
            traceback.print_exc()
        print("[test] After wrap: widget.parent()=%s" % widget.parent())
    else:
        print("[test] Skipping wrap (not available)")

    # Window flags and show
    try:
        from PySide6 import QtCore
        widget.setWindowFlags(widget.windowFlags() | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        widget.setMinimumSize(900, 600)
        widget.resize(1000, 700)
        print("[test] Set window flags and size")
    except Exception as e:
        print("[test] Window flags/size: %s" % e)

    print("[test] Calling widget.show()...")
    widget.show()
    try:
        widget.raise_()
        widget.activateWindow()
        print("[test] raise_() and activateWindow() done")
    except Exception as e:
        print("[test] raise_/activateWindow: %s" % e)

    # Diagnostics
    print("\n[test] === Diagnostics ===")
    print("[test] widget.isVisible()=%s" % widget.isVisible())
    print("[test] widget.windowHandle()=%s" % widget.windowHandle())
    print("[test] widget.geometry()=%s" % widget.geometry())
    print("[test] widget.parent()=%s" % widget.parent())
    print("[test] widget.window()=%s" % widget.window())
    app = None
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        print("[test] QApplication.instance()=%s" % app)
        if app:
            toplevels = app.topLevelWidgets()
            print("[test] topLevelWidgets() count=%s" % len(toplevels))
            for i, w in enumerate(toplevels[:5]):
                print("[test]   [%s] %s visible=%s" % (i, w, w.isVisible() if w else None))
    except Exception as e:
        print("[test] QApplication check: %s" % e)

    print("\n[test] === Done. Check if browser window is visible. ===")
    _browser_test_widget = widget  # keep reference so not GC'd when run via exec()
    print("[test] Reference kept: _browser_test_widget (in shell you can use it to inspect)")


# Run when executed (e.g. exec(open(...).read()) or Run Script)
_browser_test_widget = None
run_test()
