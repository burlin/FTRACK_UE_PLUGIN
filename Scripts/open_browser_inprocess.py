# :coding: utf-8
"""
Launch the Ftrack browser in-process inside Unreal (same process as the editor).

Requires MROYA_FTRACK_CONNECT to point to the mroya root. Adds mroya ftrack_plugins
and this plugin's .venv to sys.path, sets FTRACK_DCC=unreal, then creates and shows
FtrackBrowser. Uses unreal_qt so the window is parented to the Unreal editor.
"""

from __future__ import annotations

import logging
import os
import sys

try:
    from PySide6 import QtCore
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError:
    QtCore = None  # type: ignore[assignment]
    QApplication = None  # type: ignore[assignment]
    QWidget = None  # type: ignore[assignment]

# Resolve plugin root (this file is in PluginRoot/Scripts/)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_ROOT = os.path.dirname(_THIS_DIR)

# Keep reference to browser widget so it is not garbage-collected when open_browser() returns.
_browser_widget_ref = None


def _bootstrap_paths() -> bool:
    """Add mroya and plugin paths to sys.path. Returns True if mroya root is set."""
    mroya_root = os.environ.get("MROYA_FTRACK_CONNECT", "").strip()
    if not mroya_root or not os.path.isdir(mroya_root):
        return False

    mroya_root = os.path.normpath(mroya_root)
    paths_to_add = []

    # ftrack_plugins (must be first so ftrack_inout is found)
    plugins_root = os.path.join(mroya_root, "ftrack_plugins")
    if os.path.isdir(plugins_root) and plugins_root not in sys.path:
        paths_to_add.append(plugins_root)

    # ftrack_inout dependencies (fileseq, boto3, ftrack_api, etc.)
    inout_deps = os.path.join(plugins_root, "ftrack_inout", "dependencies")
    if os.path.isdir(inout_deps) and inout_deps not in sys.path:
        paths_to_add.append(inout_deps)

    # multi-site-location dependencies
    multi_site_deps = os.path.join(plugins_root, "multi-site-location-0.2.0", "dependencies")
    if os.path.isdir(multi_site_deps) and multi_site_deps not in sys.path:
        paths_to_add.append(multi_site_deps)

    # Plugin .venv site-packages (PySide6, unreal_qt)
    venv_site = os.path.join(_PLUGIN_ROOT, ".venv", "Lib", "site-packages")
    if os.path.isdir(venv_site) and venv_site not in sys.path:
        paths_to_add.append(venv_site)

    for p in paths_to_add:
        sys.path.insert(0, p)

    return True


class _UnrealStderrWrapper:
    """Send stderr to unreal.log() so Unreal does not show it as LogPython: Error."""

    def __init__(self, unreal_module):
        self._unreal = unreal_module

    def write(self, msg):
        if msg and msg.strip():
            self._unreal.log(msg.rstrip())

    def flush(self):
        pass

    def writable(self):
        return True


class _UnrealLogHandler(logging.Handler):
    """Send Python logging to Unreal: INFO/DEBUG -> log(), WARNING -> log_warning(), ERROR+ -> log_error()."""

    def __init__(self, unreal_module):
        super().__init__()
        self._unreal = unreal_module

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self._unreal.log_error(msg)
            elif record.levelno >= logging.WARNING:
                self._unreal.log_warning(msg)
            else:
                self._unreal.log(msg)
        except Exception:
            self.handleError(record)


def open_browser() -> None:
    """Run bootstrap, then create and show FtrackBrowser in-process with unreal_qt."""
    global _browser_widget_ref
    if not _bootstrap_paths():
        try:
            import unreal
            unreal.log_warning(
                "Ftrack (in-process): MROYA_FTRACK_CONNECT is not set or not a valid directory. "
                "Set it to the mroya root (e.g. G:\\mroya)."
            )
        except ImportError:
            print("Ftrack: MROYA_FTRACK_CONNECT not set or invalid.", file=sys.stderr)
        return

    os.environ["FTRACK_DCC"] = "unreal"

    # Optional: load .env from mroya config
    mroya_root = os.environ.get("MROYA_FTRACK_CONNECT", "").strip()
    if mroya_root:
        _load_dotenv(os.path.join(mroya_root, "config", ".env"))

    try:
        import unreal_qt
        unreal_qt.setup()
    except Exception as e:
        try:
            import unreal
            unreal.log_error("Ftrack (in-process): unreal_qt setup failed: %s" % e)
        except ImportError:
            print("Ftrack: unreal_qt setup failed: %s" % e, file=sys.stderr)
        return

    # Route Python logging to Unreal (INFO -> log, WARNING -> log_warning, ERROR -> log_error).
    try:
        import unreal
        _root = logging.getLogger()
        for h in _root.handlers[:]:
            _root.removeHandler(h)
        _root.addHandler(_UnrealLogHandler(unreal))
        _root.setLevel(logging.DEBUG)
        # Redirect stderr to unreal.log() so any remaining logging to stderr
        # (e.g. from ftrack loggers created later) does not show as LogPython: Error.
        sys.stderr = _UnrealStderrWrapper(unreal)
    except Exception:
        pass

    try:
        from ftrack_inout.browser import FtrackBrowser
    except ImportError as e:
        try:
            import unreal
            unreal.log_error("Ftrack (in-process): Failed to import FtrackBrowser: %s" % e)
        except ImportError:
            print("Ftrack: Failed to import FtrackBrowser: %s" % e, file=sys.stderr)
        return

    # Remove handlers from ftrack loggers so they don't write to stderr (Unreal shows as Error).
    try:
        for _name, _logger in logging.root.manager.loggerDict.items():
            if isinstance(_logger, logging.Logger) and "ftrack" in _name:
                for _h in _logger.handlers[:]:
                    _logger.removeHandler(_h)
    except Exception:
        pass

    # Optional: direct import into Unreal when browser runs in-process (no menu step).
    _import_callback = None
    try:
        import init_ftrack_menu as _menu
        import unreal as _unreal
        _do_import = getattr(_menu, "import_paths_into_unreal", None)
        if _do_import:
            def _import_callback(paths, content_subpath=None):
                n = _do_import(paths, content_subpath=content_subpath)
                dest = ("/Game/" + content_subpath.strip().strip("/").replace("\\", "/")) if content_subpath and content_subpath.strip() else "/Game/FtrackImport"
                try:
                    _unreal.EditorDialog.show_message(
                        "Import from Ftrack",
                        "Imported %s asset(s) to %s." % (n, dest),
                        _unreal.AppMsgType.OK,
                        _unreal.AppReturnType.OK,
                    )
                except Exception:
                    pass
                return n
    except Exception:
        pass

    # Reuse existing browser window if still open (second menu call brings it to front).
    if _browser_widget_ref is not None:
        try:
            w = _browser_widget_ref
            w.show()
            w.raise_()
            w.activateWindow()
            try:
                import unreal
                unreal.log("Ftrack: Browser already open, brought to front.")
            except ImportError:
                pass
            return
        except RuntimeError:
            _browser_widget_ref = None
        except Exception:
            _browser_widget_ref = None

    try:
        widget = FtrackBrowser(on_import_to_unreal=_import_callback)
        _browser_widget_ref = widget  # keep reference so widget is not GC'd when we return
        # unreal_qt.wrap() parents the widget to Unreal's window. It may do widget.close.connect(...).
        # In PySide6 QWidget has no close signal, so add one and emit it from closeEvent.
        if QtCore is not None and QWidget is not None:
            try:
                class _CloseSignalHolder(QtCore.QObject):
                    close = QtCore.Signal()

                _holder = _CloseSignalHolder(widget)
                _original_close_event = widget.closeEvent

                def _close_event(event):
                    _holder.close.emit()
                    if _original_close_event:
                        _original_close_event(event)

                widget.closeEvent = _close_event
                widget.close = _holder.close  # so unreal_qt.wrap() can widget.close.connect(...)
            except Exception:
                pass
        try:
            import unreal_qt as _uq
            _uq.wrap(widget)
        except (AttributeError, TypeError, Exception):
            pass
        if QtCore is not None:
            try:
                widget.setWindowFlags(
                    widget.windowFlags() | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint
                )
                widget.setMinimumSize(900, 600)
                widget.resize(1000, 700)
            except Exception:
                pass
        widget.show()
        if QtCore is not None:
            try:
                widget.raise_()
                widget.activateWindow()
            except Exception:
                pass
        # Force Qt to process show/raise so the window is visible before the menu callback returns.
        if QApplication is not None:
            try:
                app = QApplication.instance()
                if app is not None:
                    app.processEvents()
            except Exception:
                pass
        try:
            import unreal
            unreal.log("Ftrack: Browser opened in-process.")
        except ImportError:
            pass
    except Exception as e:
        try:
            import unreal
            unreal.log_error("Ftrack (in-process): Failed to show browser: %s" % e)
        except ImportError:
            print("Ftrack: Failed to show browser: %s" % e, file=sys.stderr)


def _load_dotenv(path: str) -> None:
    """Load .env file if present (best-effort)."""
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


if __name__ == "__main__":
    open_browser()
