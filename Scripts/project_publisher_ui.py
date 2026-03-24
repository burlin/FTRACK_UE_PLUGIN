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
    """Open the Project Publisher window, closing any stale window from a previous module load."""
    global _publisher_window
    _bootstrap_paths()

    # Close any window that survived a module reload (reference stored on the unreal module
    # so it persists across reloads of this file; stale windows carry old class closures).
    if unreal:
        for _stale in getattr(unreal, "_mroya_publisher_windows", []):
            try:
                _stale.hide()
            except Exception:
                pass
        unreal._mroya_publisher_windows = []

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
            self.setMinimumWidth(380)
            self.resize(420, 340)
            self._build_ui()
            self._load_existing_components()

        def _build_ui(self):
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(8)

            self.btn_mark = QtWidgets.QPushButton("Mark for Publish")
            self.btn_mark.clicked.connect(self._on_mark_for_publish)
            layout.addWidget(self.btn_mark)

            # List of objects marked for publish
            self.marked_list = QtWidgets.QListWidget()
            self.marked_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            layout.addWidget(self.marked_list, stretch=1)

            self.btn_remove = QtWidgets.QPushButton("Remove from Publish")
            self.btn_remove.clicked.connect(self._on_remove_from_publish)
            layout.addWidget(self.btn_remove)

            btn_row = QtWidgets.QHBoxLayout()
            self.btn_ok = QtWidgets.QPushButton("OK")
            self.btn_ok.clicked.connect(self._on_ok)
            self.btn_close = QtWidgets.QPushButton("Close")
            self.btn_close.clicked.connect(self.close)
            btn_row.addWidget(self.btn_ok)
            btn_row.addWidget(self.btn_close)
            layout.addLayout(btn_row)

        def _on_ok(self):
            self.close()

        def _load_existing_components(self):
            """Read Components already stored in the DataAsset and populate the list."""
            if not unreal:
                return
            try:
                asset = unreal.load_asset(self.asset_path)
                if not asset:
                    return
                components = list(asset.get_editor_property("Components") or [])
                for c in components:
                    try:
                        object_id = c.get_editor_property("Name") or ""
                        if not object_id:
                            continue
                        component_type = ""
                        try:
                            component_type = c.get_editor_property("ComponentType") or ""
                        except Exception:
                            pass
                        # Derive a readable label from the stored path
                        # Actor paths:  /Game/Maps/L.L:PersistentLevel.MyCam  → "MyCam"
                        # Asset paths:  /Game/Meshes/Rock.Rock                → "Rock"
                        short = object_id.split(".")[-1] if "." in object_id else object_id.split("/")[-1]
                        label = "%s  (%s)" % (short, component_type) if component_type else short
                        self._add_marked_item(label, object_id)
                    except Exception:
                        pass
            except Exception as e:
                unreal.log_warning("Ftrack: Could not load existing components: %s" % e)

        def _on_mark_for_publish(self):
            if not unreal:
                return
            added = 0

            # Collect content browser assets and level actors separately so we
            # can apply the sequencer filter before adding anything.
            content_assets = []
            try:
                content_assets = unreal.EditorUtilityLibrary.get_selected_assets() or []
            except Exception as e:
                unreal.log_warning("Ftrack: Could not get selected assets: %s" % e)

            actors = []
            try:
                try:
                    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors() or []
                except Exception:
                    actors = unreal.EditorLevelLibrary.get_selected_level_actors() or []
            except Exception as e:
                unreal.log_warning("Ftrack: Could not get selected actors: %s" % e)

            # When a camera (or any actor) is selected inside the Sequencer, the open
            # LevelSequence asset also appears in the content browser selection — drop it
            # so only the actual actor is added, not the sequence document.
            if actors:
                level_seq_cls = getattr(unreal, "LevelSequence", None)
                if level_seq_cls:
                    content_assets = [a for a in content_assets if not isinstance(a, level_seq_cls)]

            for asset in content_assets:
                object_id = unreal.SystemLibrary.get_path_name(asset)
                label = "%s  (%s)" % (unreal.SystemLibrary.get_object_name(asset), type(asset).__name__)
                if self._write_component_to_asset(object_id):
                    self._add_marked_item(label, object_id)
                    added += 1

            # Record the currently open sequence so export doesn't need to scan
            seq_path = ""
            try:
                seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
                if seq:
                    seq_path = unreal.SystemLibrary.get_path_name(seq)
            except Exception:
                pass

            cine_cam_cls = getattr(unreal, "CineCameraActor", None)
            for actor in actors:
                object_id = unreal.SystemLibrary.get_path_name(actor)
                actor_label = actor.get_actor_label()
                label = "%s  (%s)" % (actor_label, type(actor).__name__)
                is_camera = cine_cam_cls and isinstance(actor, cine_cam_cls)
                component_type = "camera" if is_camera else "animation"
                # Record the sequencer binding GUID so export can find the binding
                # by stable ID rather than by name.
                binding_guid = ""
                if seq:
                    try:
                        for b in (seq.get_bindings() or []):
                            if b.get_name() == actor_label:
                                g = b.get_id()
                                binding_guid = "%08X-%08X-%08X-%08X" % (g.a, g.b, g.c, g.d)
                                break
                    except Exception:
                        pass
                if self._write_component_to_asset(object_id, component_type=component_type, sequence_path=seq_path, actor_label=actor_label, binding_guid=binding_guid):
                    self._add_marked_item(label, object_id)
                    added += 1

            if added == 0:
                unreal.log_warning("Ftrack: Nothing selected — select assets in the Content Browser or actors in the viewport.")
            else:
                unreal.log("Ftrack: Marked %d object(s) for publish." % added)

        def _on_remove_from_publish(self):
            for item in self.marked_list.selectedItems():
                object_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
                self._remove_component_from_asset(object_id)
                self.marked_list.takeItem(self.marked_list.row(item))

        def _write_component_to_asset(self, object_id: str, component_type: str = "", sequence_path: str = "", actor_label: str = "", binding_guid: str = "") -> bool:
            """Append a new FFtrackPublishComponentEntry to the DataAsset. Returns True on success."""
            try:
                asset = unreal.load_asset(self.asset_path)
                if not asset:
                    unreal.log_error("Ftrack: Could not load DataAsset: %s" % self.asset_path)
                    return False
                components = list(asset.get_editor_property("Components") or [])
                # Skip if already present
                for c in components:
                    try:
                        if c.get_editor_property("Name") == object_id:
                            return True
                    except Exception:
                        pass
                entry = unreal.FtrackPublishComponentEntry()
                entry.set_editor_property("Name", object_id)
                if component_type:
                    entry.set_editor_property("ComponentType", component_type)
                metadata = {}
                if sequence_path:
                    metadata["sequence_path"] = sequence_path
                if actor_label:
                    metadata["actor_label"] = actor_label
                if binding_guid:
                    metadata["binding_guid"] = binding_guid
                if metadata:
                    entry.set_editor_property("Metadata", metadata)
                components.append(entry)
                asset.set_editor_property("Components", components)
                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                return True
            except Exception as e:
                unreal.log_error("Ftrack: Failed to write component to DataAsset: %s" % e)
                return False

        def _remove_component_from_asset(self, object_id: str) -> None:
            """Remove the FFtrackPublishComponentEntry with Name=object_id from the DataAsset."""
            try:
                asset = unreal.load_asset(self.asset_path)
                if not asset:
                    return
                components = list(asset.get_editor_property("Components") or [])
                filtered = []
                for c in components:
                    try:
                        if c.get_editor_property("Name") == object_id:
                            continue
                    except Exception:
                        pass
                    filtered.append(c)
                if len(filtered) != len(components):
                    asset.set_editor_property("Components", filtered)
                    unreal.EditorAssetLibrary.save_loaded_asset(asset)
            except Exception as e:
                unreal.log_error("Ftrack: Failed to remove component from DataAsset: %s" % e)

        def _add_marked_item(self, label, path):
            """Add item to the list, skipping duplicates."""
            for i in range(self.marked_list.count()):
                if self.marked_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole) == path:
                    return
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            self.marked_list.addItem(item)

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
                    btn_pub = QtWidgets.QPushButton("Publish")
                    btn_pub.setFixedWidth(70)
                    btn_pub.clicked.connect(lambda checked=False, p=path: self._publish_asset(p))
                    row_layout.addWidget(btn_pub)
                    btn_ren = QtWidgets.QPushButton("Rename")
                    btn_ren.setFixedWidth(70)
                    btn_ren.clicked.connect(lambda checked=False, n=name, p=path: self._on_rename_publisher(n, p))
                    row_layout.addWidget(btn_ren)
                    btn_del = QtWidgets.QPushButton("Delete")
                    btn_del.setFixedWidth(60)
                    btn_del.clicked.connect(lambda checked=False, n=name, p=path: self._on_delete_publisher(n, p))
                    row_layout.addWidget(btn_del)
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

        def _on_rename_publisher(self, asset_name, asset_path):
            new_name, ok = QtWidgets.QInputDialog.getText(
                self, "Rename Handle", "New name:", text=asset_name
            )
            if not ok or not new_name.strip() or new_name.strip() == asset_name:
                return
            new_name = new_name.strip()
            try:
                # Build new asset path: same package folder, new asset name
                package_path = asset_path.rsplit("/", 1)[0]
                new_asset_path = "%s/%s.%s" % (package_path, new_name, new_name)
                success = unreal.EditorAssetLibrary.rename_asset(asset_path, new_asset_path)
                if success:
                    unreal.log("Ftrack: Renamed '%s' -> '%s'." % (asset_name, new_name))
                else:
                    unreal.log_warning("Ftrack: Could not rename '%s' — asset may be in use." % asset_name)
            except Exception as e:
                unreal.log_error("Ftrack: Rename failed for '%s': %s" % (asset_name, e))
            self._scan_publish_folder()

        def _on_delete_publisher(self, asset_name, asset_path):
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Publisher",
                "Delete publish node '%s'?\nThis will permanently remove the DataAsset." % asset_name,
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            try:
                success = unreal.EditorAssetLibrary.delete_asset(asset_path)
                if success:
                    unreal.log("Ftrack: Deleted publish node '%s'." % asset_name)
                else:
                    unreal.log_warning("Ftrack: Could not delete '%s' — asset may be in use." % asset_name)
            except Exception as e:
                unreal.log_error("Ftrack: Delete failed for '%s': %s" % (asset_name, e))
            self._scan_publish_folder()

        def _publish_asset(self, asset_path: str):
            if not unreal:
                return
            try:
                import camera_exporter
            except ImportError as e:
                unreal.log_error("Ftrack: Could not import camera_exporter: %s" % e)
                return

            export_dir = camera_exporter._get_export_dir()
            total_exported = 0
            total_skipped = 0

            try:
                asset = unreal.load_asset(asset_path)
                if not asset:
                    unreal.log_error("Ftrack Publish: Could not load asset: %s" % asset_path)
                    return
                components = list(asset.get_editor_property("Components") or [])
                dirty = False
                for c in components:
                    try:
                        name = c.get_editor_property("Name") or ""
                        component_type = (c.get_editor_property("ComponentType") or "").strip().lower()
                        if component_type not in ("camera", "animation"):
                            unreal.log_warning(
                                "Ftrack Publish: '%s' (type: '%s') — unsupported type, skipping."
                                % (name.split(".")[-1], component_type or "unset")
                            )
                            total_skipped += 1
                            continue
                        meta = dict(c.get_editor_property("Metadata") or {})
                        sequence_path = meta.get("sequence_path", "")
                        actor_label = meta.get("actor_label", "")
                        binding_guid = meta.get("binding_guid", "")
                        export_path = camera_exporter.export_binding_from_sequence(
                            name, export_dir, sequence_path=sequence_path,
                            actor_label=actor_label, binding_guid=binding_guid
                        )
                        if export_path:
                            c.set_editor_property("FilePath", export_path)
                            dirty = True
                            total_exported += 1
                    except Exception as e:
                        unreal.log_error("Ftrack Publish: Error on component '%s': %s" % (name, e))
                if dirty:
                    asset.set_editor_property("Components", components)
                    unreal.EditorAssetLibrary.save_loaded_asset(asset)
            except Exception as e:
                unreal.log_error("Ftrack Publish: Error processing asset '%s': %s" % (asset_path, e))

            unreal.log(
                "Ftrack Publish: Done — %d exported, %d skipped." % (total_exported, total_skipped)
            )

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
    if unreal:
        unreal._mroya_publisher_windows = [win]
