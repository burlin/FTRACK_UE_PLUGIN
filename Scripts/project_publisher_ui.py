# :coding: utf-8
"""
Project Publisher UI - window with Create Publish Node button, publisher node list, and Exit button.

Launched from ftrack menu > Project Publisher.
Create Publish Node creates an empty UFtrackOutHandle DataAsset.
"""

from __future__ import annotations

import os
import sys

try:
    import unreal
except ImportError:
    unreal = None

# Resolve plugin root (this file is in PluginRoot/Scripts/)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_ROOT = os.path.dirname(_THIS_DIR)

_publisher_window = None   # keep reference to prevent GC
_setup_windows = []        # keep setup publisher windows alive


def _bootstrap_paths() -> None:
    """Add plugin dependencies dir (PySide6, unreal_qt) to sys.path."""
    deps_dir = os.path.join(_PLUGIN_ROOT, "dependencies")
    if os.path.isdir(deps_dir) and deps_dir not in sys.path:
        sys.path.insert(0, deps_dir)


def open_project_publisher() -> None:
    """Open the Project Publisher window. Reuses existing window if already open."""
    global _publisher_window
    _bootstrap_paths()

    if _publisher_window is not None:
        try:
            if _publisher_window.isVisible():
                _publisher_window.raise_()
                _publisher_window.activateWindow()
                return
        except Exception:
            _publisher_window = None

    try:
        import unreal_qt
        from PySide6 import QtCore, QtWidgets
    except ImportError as e:
        if unreal:
            unreal.log_error("Ftrack: ProjectPublisher requires PySide6/unreal_qt: %s" % e)
        else:
            print("Ftrack: ProjectPublisher requires PySide6/unreal_qt: %s" % e, file=sys.stderr)
        return

    unreal_qt.setup()

    class SetupPublisherWindow(QtWidgets.QWidget):
        def __init__(self, asset_name, asset_path):
            super().__init__()
            self.asset_name = asset_name
            self.asset_path = asset_path
            self.setWindowTitle("Setup Publisher — %s" % asset_name)
            self.setMinimumWidth(300)
            self._build_ui()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)

            self.btn_mark = QtWidgets.QPushButton("Mark for Publish")
            layout.addWidget(self.btn_mark)

            layout.addStretch()

            btn_row = QtWidgets.QHBoxLayout()
            self.btn_ok = QtWidgets.QPushButton("OK")
            self.btn_close = QtWidgets.QPushButton("Close")
            self.btn_close.clicked.connect(self.close)
            btn_row.addWidget(self.btn_ok)
            btn_row.addWidget(self.btn_close)
            layout.addLayout(btn_row)

    class ProjectPublisherWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Project Publisher")
            self.resize(400, 380)
            self._build_ui()
            self._scan_publish_folder()  # auto-scan on open

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)

            # Create Publish Node button (top)
            self.btn_create = QtWidgets.QPushButton("Create Publish Node")
            self.btn_create.clicked.connect(self._on_create_publish_node)
            layout.addWidget(self.btn_create)

            # Scan Project button
            self.btn_scan = QtWidgets.QPushButton("Scan Project")
            self.btn_scan.clicked.connect(self._scan_publish_folder)
            layout.addWidget(self.btn_scan)

            # List of publish nodes found in /Game/FtrackPublish
            self.list_widget = QtWidgets.QListWidget()
            layout.addWidget(self.list_widget, stretch=1)

            # Exit button (bottom)
            self.btn_exit = QtWidgets.QPushButton("Exit")
            self.btn_exit.clicked.connect(self.close)
            layout.addWidget(self.btn_exit)

        def _scan_publish_folder(self):
            self.list_widget.clear()
            if not unreal:
                return
            try:
                handle_cls = getattr(unreal, "FtrackOutHandle", None)
                all_paths = unreal.EditorAssetLibrary.list_assets(
                    "/Game/FtrackPublish", recursive=True, include_folder=False
                ) or []
                found = []
                for obj_path in all_paths:
                    try:
                        asset = unreal.load_asset(obj_path)
                        if not asset:
                            continue
                        if handle_cls:
                            match = isinstance(asset, handle_cls)
                        else:
                            match = type(asset).__name__ == "FtrackOutHandle"
                        if match:
                            found.append((unreal.SystemLibrary.get_object_name(asset), obj_path))
                    except Exception:
                        pass
                for name, path in found:
                    item = QtWidgets.QListWidgetItem()
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
                    row = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row)
                    row_layout.setContentsMargins(4, 2, 4, 2)
                    row_layout.addWidget(QtWidgets.QLabel(name), stretch=1)
                    btn = QtWidgets.QPushButton("Setup Publisher")
                    btn.setFixedWidth(120)
                    btn.clicked.connect(lambda checked=False, n=name, p=path: self._open_setup_publisher(n, p))
                    row_layout.addWidget(btn)
                    item.setSizeHint(row.sizeHint())
                    self.list_widget.addItem(item)
                    self.list_widget.setItemWidget(item, row)
                unreal.log("Ftrack: Found %d publish node(s) in /Game/FtrackPublish." % len(found))
            except Exception as e:
                unreal.log_warning("Ftrack: Scan failed: %s" % e)

        def _open_setup_publisher(self, asset_name, asset_path):
            win = SetupPublisherWindow(asset_name, asset_path)
            win.setWindowFlags(win.windowFlags() | QtCore.Qt.WindowType.Window)
            win.show()
            win.raise_()
            win.activateWindow()
            _setup_windows.append(win)

        def _on_create_publish_node(self):
            try:
                import ftrack_out_handle
                path = ftrack_out_handle.create_ftrack_out_handle(package_path="/Game/FtrackPublish")
                if path:
                    if unreal:
                        unreal.log("Ftrack: Created Publish Node: %s" % path)
                    self._scan_publish_folder()  # refresh list after creation
                else:
                    if unreal:
                        unreal.log_warning("Ftrack: create_ftrack_out_handle returned None.")
            except Exception as e:
                if unreal:
                    unreal.log_error("Ftrack: Failed to create publish node: %s" % e)
                else:
                    print("Ftrack: Failed to create publish node: %s" % e, file=sys.stderr)

    win = ProjectPublisherWindow()

    # unreal_qt.wrap() calls widget.close.connect(...), but PySide6 QWidget.close is a slot
    # method, not a signal — patch it with a real Signal the same way open_browser_inprocess does.
    try:
        class _CloseSignalHolder(QtCore.QObject):
            close = QtCore.Signal()

        _holder = _CloseSignalHolder(win)
        _orig_close_event = win.closeEvent

        def _close_event(event):
            _holder.close.emit()
            if _orig_close_event:
                _orig_close_event(event)

        win.closeEvent = _close_event
        win.close = _holder.close
    except Exception:
        pass

    try:
        unreal_qt.wrap(win)
    except Exception:
        pass

    win.setWindowFlags(win.windowFlags() | QtCore.Qt.WindowType.Window)
    win.show()
    win.raise_()
    win.activateWindow()
    _publisher_window = win
