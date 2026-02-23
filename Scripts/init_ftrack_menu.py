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
