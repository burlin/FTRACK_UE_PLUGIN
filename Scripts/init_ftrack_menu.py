# :coding: utf-8
"""
Register Ftrack menu in Unreal Editor: Open browser (in-process).
Import is done directly from the browser via Import button.

Loaded automatically by Content/Python/init_unreal.py when the plugin is enabled.
Requires MROYA_FTRACK_CONNECT to be set to the mroya root for the in-process browser.
"""

from __future__ import annotations

import os
import sys
import time

try:
    import unreal
except ImportError:
    unreal = None


def create_ftrack_handle(component_id: str, content_subpath: str | None = None, asset_version_id: str | None = None) -> str | None:
    """Create a Ftrack Asset Handle (DataAsset) with the given component ID and content subpath.
    The handle is created at the same path as the import destination: /Game/{content_subpath}.
    Returns the created asset path or None on failure.
    """
    if unreal is None:
        return None
    if not component_id or not component_id.strip():
        unreal.log_warning("Ftrack: create_ftrack_handle requires component_id.")
        return None
    try:
        sub = (content_subpath or "").strip().strip("/").replace("\\", "/")
        base_path = "/Game/" + (sub if sub else "FtrackImport")
        asset_name_base = "FtrackHandle"
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        # Find unique name
        existing = unreal.EditorAssetLibrary.list_assets(base_path, recursive=False, include_folder=False)
        used = set()
        for p in existing:
            name = unreal.SystemLibrary.get_object_name(unreal.load_asset(p))
            used.add(name)
        idx = 0
        asset_name = asset_name_base
        while asset_name in used:
            idx += 1
            asset_name = "%s_%d" % (asset_name_base, idx)
        handle_class = unreal.load_object(None, "/Script/MroyaFtrack.FtrackAssetHandle")
        if not handle_class:
            unreal.log_error("Ftrack: FtrackAssetHandle class not found. Is the plugin built?")
            return None
        factory = unreal.DataAssetFactory()
        new_asset = asset_tools.create_asset(asset_name, base_path, handle_class, factory)
        if not new_asset:
            return None
        new_asset.set_editor_property("ComponentId", component_id.strip())
        new_asset.set_editor_property("ContentSubpath", (content_subpath or "").strip())
        if asset_version_id and str(asset_version_id).strip():
            new_asset.set_editor_property("AssetVersionId", str(asset_version_id).strip())
        unreal.EditorAssetLibrary.save_loaded_asset(new_asset)
        path = unreal.SystemLibrary.get_path_name(new_asset)
        unreal.log("Ftrack: Created Ftrack Asset Handle: %s (ComponentId=%s)" % (path, component_id[:16] + "..."))
        return path
    except Exception as e:
        if unreal:
            unreal.log_error("Ftrack: create_ftrack_handle failed: %s" % e)
        return None


def _bootstrap_mroya() -> bool:
    """Add mroya and ftrack_plugins to sys.path. Returns True if MROYA_FTRACK_CONNECT is set."""
    mroya_root = os.environ.get("MROYA_FTRACK_CONNECT", "").strip()
    if not mroya_root or not os.path.isdir(mroya_root):
        return False
    mroya_root = os.path.normpath(mroya_root)
    plugins_root = os.path.join(mroya_root, "ftrack_plugins")
    if os.path.isdir(plugins_root) and plugins_root not in sys.path:
        sys.path.insert(0, plugins_root)
    inout_deps = os.path.join(plugins_root, "ftrack_inout", "dependencies")
    if os.path.isdir(inout_deps) and inout_deps not in sys.path:
        sys.path.insert(0, inout_deps)
    return True


def import_handle_in_unreal(handle_asset_path: str) -> int:
    """Resolve the Ftrack Handle's component to a file path and run import. Returns number of assets imported or 0 on failure."""
    if unreal is None:
        return 0
    try:
        handle = unreal.load_asset(handle_asset_path)
        if not handle:
            unreal.log_error("Ftrack: Could not load handle: %s" % handle_asset_path)
            return 0
        component_id = (handle.get_editor_property("ComponentId") or "").strip()
        content_subpath = (handle.get_editor_property("ContentSubpath") or "").strip() or None
        asset_version_id = (handle.get_editor_property("AssetVersionId") or "").strip() or None
        if not component_id:
            unreal.log_warning("Ftrack: Handle has no ComponentId.")
            return 0
        if not _bootstrap_mroya():
            unreal.log_error("Ftrack: MROYA_FTRACK_CONNECT not set. Cannot resolve component.")
            return 0
        try:
            from ftrack_inout.common.session_factory import get_shared_session
            from ftrack_inout.browser.simple_api_client import SimpleFtrackApiClient
        except ImportError as e:
            unreal.log_error("Ftrack: import_handle_in_unreal failed to import ftrack_inout: %s" % e)
            return 0
        session = get_shared_session()
        if not session:
            unreal.log_error("Ftrack: No ftrack session.")
            return 0
        version_id = asset_version_id
        if not version_id:
            try:
                comp = session.get("Component", component_id)
                version_id = comp.get("version_id") if comp else None
            except Exception as e:
                unreal.log_error("Ftrack: Could not get version for component %s: %s" % (component_id[:16], e))
                return 0
        if not version_id:
            unreal.log_error("Ftrack: Could not determine asset version for component.")
            return 0
        client = SimpleFtrackApiClient(session=session)
        components = client.get_components_with_paths_for_version(version_id)
        path = None
        for c in (components or []):
            if str(c.get("id")) == str(component_id):
                p = (c.get("path") or "").strip()
                if p and p != "N/A" and os.path.isfile(p):
                    path = p
                    break
        if not path:
            unreal.log_warning("Ftrack: Component path not resolved or file not found. Check location.")
            return 0
        return import_paths_into_unreal([path], content_subpath=content_subpath)
    except Exception as e:
        if unreal:
            unreal.log_error("Ftrack: import_handle_in_unreal failed: %s" % e)
        return 0


def import_paths_into_unreal(paths: list, content_subpath: str | None = None) -> int:
    """Import given file paths into Unreal. Destination: /Game/{content_subpath} or /Game/FtrackImport if not set."""
    if unreal is None:
        return 0
    if not paths:
        return 0
    t0 = time.perf_counter()
    destination_path = "/Game/FtrackImport"
    if content_subpath and content_subpath.strip():
        sub = content_subpath.strip().strip("/").replace("\\", "/")
        if sub:
            destination_path = "/Game/" + sub
    unreal.log("Ftrack: Import starting for %s -> %s" % (paths[0][:80] + "..." if len(paths[0]) > 80 else paths[0], destination_path))
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    tasks = []
    for file_path in paths:
        if not file_path or not os.path.isfile(file_path):
            unreal.log_warning("Ftrack: Skip missing path: %s" % file_path)
            continue
        task = unreal.AssetImportTask()
        task.filename = os.path.abspath(file_path)
        task.destination_path = destination_path
        task.destination_name = ""
        task.automated = False  # show import options dialog
        task.save = True
        task.replace_existing = False
        tasks.append(task)
    if not tasks:
        return 0
    t_before = time.perf_counter()
    asset_tools.import_asset_tasks(tasks)
    t_after = time.perf_counter()
    unreal.log("Ftrack: import_asset_tasks took %.2fs" % (t_after - t_before))
    imported = sum(1 for t in tasks if t.imported_object_paths)
    unreal.log("Ftrack: Imported %s asset(s) to %s. Total %.2fs." % (imported, destination_path, time.perf_counter() - t0))
    return imported


def _open_browser_inprocess() -> None:
    """Launch Ftrack browser in-process (same process as Unreal, window parented to editor)."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if this_dir not in sys.path:
        sys.path.insert(0, this_dir)
    try:
        import open_browser_inprocess
        open_browser_inprocess.open_browser()
    except Exception as e:
        if unreal:
            unreal.log_error("Ftrack: Failed to open browser in-process: %s" % e)
        else:
            print("Ftrack: Failed to open browser: %s" % e, file=sys.stderr)


def register_ftrack_menu() -> None:
    """Add Ftrack menu to the Level Editor main menu."""
    if unreal is None:
        return
    menus = unreal.ToolMenus.get()
    main_menu = menus.find_menu("LevelEditor.MainMenu")
    if not main_menu:
        unreal.log_warning("Ftrack: LevelEditor.MainMenu not found.")
        return

    ftrack_menu = main_menu.add_sub_menu(
        "ftrack.Menu",
        "ftrack",
        "ftrack",
        "ftrack",  # display label in menu bar (this param is shown in UE)
    )

    @unreal.uclass()
    class OpenBrowserEntryScript(unreal.ToolMenuEntryScript):
        @unreal.ufunction(override=True)
        def get_label(self, context):
            return "Open browser"

        @unreal.ufunction(override=True)
        def get_tool_tip(self, context):
            return "Open the Ftrack Task Hub browser in-process (parented to the editor)."

        @unreal.ufunction(override=True)
        def execute(self, context):
            _open_browser_inprocess()

    entry_open = unreal.ToolMenuEntry(
        name="FtrackOpenBrowser",
        type=unreal.MultiBlockType.MENU_ENTRY,
        script_object=OpenBrowserEntryScript(),
    )

    ftrack_menu.add_menu_entry("FtrackActions", entry_open)
    menus.refresh_all_widgets()
    unreal.log("Ftrack: Menu registered (Ftrack -> Open browser).")


if __name__ == "__main__":
    register_ftrack_menu()
else:
    register_ftrack_menu()
