# :coding: utf-8
"""
Ftrack Out Handle: read UFtrackOutHandle into a dict for PublishJob.from_dict / Publisher.execute.

Object binding (ObjectBinding: sequence_path, actor_label, actor_name, content_path) is editor-side
pointer data and is never merged into the publish job; use component_object_binding_dict() to read it.

Playblast is job-level (one per version): bUsePlayblast and PlayblastPath live on the handle asset. When set,
out_handle_to_publish_job_dict appends a single component (name=playblast, component_type=playblast), same as
ftrack_inout JobBuilder.

Optional scenario keys: include_unreal_metadata=True adds scenario index/description into the main
component Metadata only (not playblast; playblast is never metadata).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import unreal
except ImportError:
    unreal = None


def _get_prop(obj: Any, *names: str) -> Any:
    """Read first available property (Unreal Python naming varies by version)."""
    if obj is None:
        return None
    for n in names:
        try:
            if hasattr(obj, "get_editor_property"):
                return obj.get_editor_property(n)
        except Exception:
            pass
        try:
            return getattr(obj, n)
        except Exception:
            pass
    return None


def _binding_str(raw: Any) -> str:
    """Normalize FString or legacy path structs from Unreal Python to a plain string."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        s = raw.strip()
        return s if s and s != "None" else ""
    for attr in ("to_string", "get_asset_path_string", "path_string"):
        if hasattr(raw, attr):
            try:
                s = getattr(raw, attr)()
                if s is not None:
                    out = str(s).strip()
                    if out and out != "None":
                        return out
            except Exception:
                pass
    try:
        s = str(raw).strip()
        if s and s != "None":
            return s
    except Exception:
        pass
    return ""


def _fstring_map_to_dict(raw: Any) -> Dict[str, str]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    out: Dict[str, str] = {}
    try:
        for k, v in raw.items():
            out[str(k)] = str(v)
    except Exception:
        pass
    return out


def _entry_to_component_dict(
    entry: Any,
    *,
    include_unreal_metadata: bool = False,
    merge_frame_into_metadata: bool = True,
) -> Dict[str, Any]:
    """Map FFtrackPublishComponentEntry to ComponentData.to_dict shape."""
    name = _get_prop(entry, "Name", "name") or ""
    file_path = (_get_prop(entry, "FilePath", "file_path") or "").strip() or None
    component_type = (_get_prop(entry, "ComponentType", "component_type") or "file").strip() or "file"
    export_enabled = _get_prop(entry, "bExportEnabled", "export_enabled")
    if export_enabled is None:
        export_enabled = True
    sequence_pattern = (_get_prop(entry, "SequencePattern", "sequence_pattern") or "").strip() or None
    transfer_after = _get_prop(entry, "bTransferAfterPublish", "transfer_after_publish")
    if transfer_after is None:
        transfer_after = True

    meta = dict(_fstring_map_to_dict(_get_prop(entry, "Metadata", "metadata")))

    b_has_range = bool(_get_prop(entry, "bHasFrameRange", "b_has_frame_range"))
    frame_start = _get_prop(entry, "FrameStart", "frame_start")
    frame_end = _get_prop(entry, "FrameEnd", "frame_end")
    frame_range = None
    if b_has_range and frame_start is not None and frame_end is not None:
        try:
            frame_range = (int(frame_start), int(frame_end))
        except (TypeError, ValueError):
            frame_range = None
    if merge_frame_into_metadata and frame_range is not None:
        meta.setdefault("start_frame", str(frame_range[0]))
        meta.setdefault("end_frame", str(frame_range[1]))

    if include_unreal_metadata:
        idx = _get_prop(entry, "ScenarioLibraryIndex", "scenario_library_index")
        if idx is not None:
            meta.setdefault("scenario_library_index", str(int(idx)))
        desc = (_get_prop(entry, "ScenarioDescription", "scenario_description") or "").strip()
        if desc:
            meta.setdefault("scenario_description", desc)

    comp: Dict[str, Any] = {
        "name": str(name),
        "file_path": file_path,
        "component_type": str(component_type),
        "export_enabled": bool(export_enabled),
        "metadata": meta,
        "sequence_pattern": sequence_pattern,
        "frame_range": frame_range,
        "transfer_after_publish": bool(transfer_after),
    }
    return comp


def _playblast_component_dict(file_path: str) -> Dict[str, Any]:
    """Single playblast component per PublishJob for encode_media; not merged into Metadata."""
    return {
        "name": "playblast",
        "file_path": file_path,
        "component_type": "playblast",
        "export_enabled": True,
        "metadata": {},
        "sequence_pattern": None,
        "frame_range": None,
        "transfer_after_publish": False,
    }


def component_object_binding_dict(entry: Any) -> Dict[str, str]:
    """
    Read FFtrackObjectBinding from one component entry.

    This is Unreal-side pointer data for tools and export scripts; it is not part of the ftrack
    publish job dict.
    """
    binding = _get_prop(entry, "ObjectBinding", "object_binding")
    if not binding:
        return {}
    return {
        "sequence_path": _binding_str(_get_prop(binding, "SequencePath", "sequence_path")),
        "actor_label": _binding_str(_get_prop(binding, "ActorLabel", "actor_label")),
        "actor_name": _binding_str(_get_prop(binding, "ActorName", "actor_name")),
        "content_path": _binding_str(_get_prop(binding, "ContentPath", "content_path")),
    }


def out_handle_component_bindings(handle: Any) -> List[Dict[str, str]]:
    """
    Return object binding dicts for each component on the handle (same order as Components array).
    """
    if unreal is None:
        raise RuntimeError("unreal module is not available (run inside Unreal Editor).")
    asset = handle
    if isinstance(handle, str):
        asset = unreal.load_asset(handle)
    if not asset:
        raise ValueError("Could not load Ftrack Out Handle asset.")
    raw = _get_prop(asset, "Components", "components")
    out: List[Dict[str, str]] = []
    if not raw:
        return out
    for entry in raw:
        out.append(component_object_binding_dict(entry))
    return out


def out_handle_to_publish_job_dict(
    handle: Any,
    *,
    include_unreal_metadata: bool = False,
    merge_frame_into_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Build a dict suitable for PublishJob.from_dict from a UFtrackOutHandle asset.

    Args:
        handle: Loaded UFtrackOutHandle UObject, or asset path string.
        include_unreal_metadata: If True, push scenario index/description into the main component metadata.
        merge_frame_into_metadata: If True and frame range is set, add start_frame/end_frame to metadata.
    """
    if unreal is None:
        raise RuntimeError("unreal module is not available (run inside Unreal Editor).")
    asset = handle
    if isinstance(handle, str):
        asset = unreal.load_asset(handle)
    if not asset:
        raise ValueError("Could not load Ftrack Out Handle asset.")

    task_id = (_get_prop(asset, "TaskId", "task_id") or "").strip()
    asset_id = (_get_prop(asset, "AssetId", "asset_id") or "").strip() or None
    asset_name = (_get_prop(asset, "AssetName", "asset_name") or "").strip() or None
    asset_type = (_get_prop(asset, "AssetType", "asset_type") or "").strip() or None
    comment = (_get_prop(asset, "Comment", "comment") or "").strip()
    thumbnail_path = (_get_prop(asset, "ThumbnailPath", "thumbnail_path") or "").strip() or None
    use_pb = _get_prop(asset, "bUsePlayblast", "use_playblast")
    pb_path = (_get_prop(asset, "PlayblastPath", "playblast_path") or "").strip()
    source_dcc = (_get_prop(asset, "SourceDcc", "source_dcc") or "unreal").strip() or "unreal"
    transfer_loc = (_get_prop(asset, "TransferTargetLocation", "transfer_target_location") or "").strip() or None

    raw_components = _get_prop(asset, "Components", "components")
    components: List[Dict[str, Any]] = []
    if raw_components:
        for entry in raw_components:
            components.append(
                _entry_to_component_dict(
                    entry,
                    include_unreal_metadata=include_unreal_metadata,
                    merge_frame_into_metadata=merge_frame_into_metadata,
                )
            )
    if bool(use_pb) and pb_path:
        components.append(_playblast_component_dict(pb_path))

    job: Dict[str, Any] = {
        "task_id": task_id,
        "asset_id": asset_id,
        "asset_name": asset_name,
        "asset_type": asset_type,
        "comment": comment,
        "components": components,
        "thumbnail_path": thumbnail_path,
        "source_dcc": source_dcc,
        "transfer_target_location": transfer_loc,
    }
    return job


def create_ftrack_out_handle(
    package_path: str = "/Game/FtrackPublish",
    asset_name_base: str = "FtrackOutHandle",
) -> Optional[str]:
    """Create an empty UFtrackOutHandle DataAsset. Returns asset path or None."""
    if unreal is None:
        return None
    try:
        raw = package_path.strip().replace("\\", "/")
        if raw.startswith("/Game/"):
            base_path = raw
        else:
            sub = raw.strip("/")
            base_path = "/Game/" + sub
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        existing = unreal.EditorAssetLibrary.list_assets(base_path, recursive=False, include_folder=False)
        used = set()
        for p in existing or []:
            a = unreal.load_asset(p)
            if a:
                used.add(unreal.SystemLibrary.get_object_name(a))
        idx = 0
        asset_name = asset_name_base
        while asset_name in used:
            idx += 1
            asset_name = "%s_%d" % (asset_name_base, idx)
        handle_class = unreal.load_object(None, "/Script/MroyaFtrack.FtrackOutHandle")
        if not handle_class:
            unreal.log_error("Ftrack: FtrackOutHandle class not found. Is the plugin built?")
            return None
        factory = unreal.DataAssetFactory()
        new_asset = asset_tools.create_asset(asset_name, base_path, handle_class, factory)
        if not new_asset:
            return None
        unreal.EditorAssetLibrary.save_loaded_asset(new_asset)
        path = unreal.SystemLibrary.get_path_name(new_asset)
        unreal.log("Ftrack: Created Ftrack Out Handle: %s" % path)
        return path
    except Exception as e:
        unreal.log_error("Ftrack: create_ftrack_out_handle failed: %s" % e)
        return None
