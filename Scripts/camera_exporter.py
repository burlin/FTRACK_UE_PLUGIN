# :coding: utf-8
"""
Camera bake-and-export for the Project Publisher.

Workflow:
  1. Load the sequence directly from the stored sequence_path (recorded at mark time).
     If not available, fall back to scanning /Game folder-by-folder (non-recursive per
     folder to avoid the UE5 ARFilter recursive_paths bug).
  2. Bake the camera transform every frame (reduce_keys=False, tolerance=0.001).
  3. Export to FBX at <ProjectContent>/Export/<SeqName>_<CameraName>.fbx.
  4. Return the absolute export path.
"""

from __future__ import annotations

import os

try:
    import unreal
except ImportError:
    unreal = None


def _asset_class_name(asset_data) -> str:
    """Return the class name string from an AssetData object (UE4 and UE5)."""
    try:
        return str(asset_data.asset_class_path.asset_name)
    except Exception:
        pass
    try:
        return str(asset_data.asset_class)
    except Exception:
        return ""


def _get_editor_world():
    try:
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        return unreal.EditorLevelLibrary.get_editor_world()


def _get_export_dir() -> str:
    """Return <ProjectContent>/Export as an absolute filesystem path."""
    content_dir = unreal.SystemLibrary.get_project_content_directory()
    return os.path.normpath(os.path.join(content_dir.rstrip("/\\"), "Export"))


def _guid_to_str(guid) -> str:
    """Serialize an unreal.Guid to a stable string using its four uint32 components."""
    return "%08X-%08X-%08X-%08X" % (guid.a, guid.b, guid.c, guid.d)


def _find_binding_by_guid(level_sequence, guid_str: str):
    """Return the binding whose GUID matches guid_str, or None."""
    for binding in (level_sequence.get_bindings() or []):
        try:
            if _guid_to_str(binding.get_id()) == guid_str:
                return binding
        except Exception:
            pass
    return None


def _strip_ue_suffix(name: str) -> str:
    """Strip UE's trailing de-duplication suffix (_N) from an object name.

    e.g. 'sh0010_cam_v01_7' -> 'sh0010_cam_v01'
    Only strips if the suffix is a pure integer (no leading zeros), so
    'sh0010_cam_v02' stays as-is (02 has a leading zero → version number).
    """
    import re
    m = re.match(r'^(.*?)_(\d+)$', name)
    if m:
        suffix = m.group(2)
        # UE de-dup suffixes are plain integers without leading zeros: 2, 7, 13 …
        # Version numbers like 02, 03 have leading zeros — leave those alone.
        if suffix == str(int(suffix)) and len(suffix) <= 4:
            return m.group(1)
    return name


def _find_binding_by_name_only(level_sequence, actor_name: str):
    """Find a binding in level_sequence by name only — no live actor required.

    Search order:
    1. Exact match (direct API + iteration)
    2. Case-insensitive exact match
    3. Exact match after stripping UE de-dup suffix from actor_name
       (handles cases where actor_name is the object name like sh0010_cam_v01_7
        but the binding was created from the label sh0010_cam_v01)
    """
    all_bindings = level_sequence.get_bindings() or []
    binding_names = [b.get_name() for b in all_bindings]

    # Direct lookup first
    try:
        binding = level_sequence.find_binding_by_name(actor_name)
        if binding and binding.get_name() == actor_name:
            return binding
    except Exception:
        pass

    # Exact match by iteration
    for binding in all_bindings:
        if binding.get_name() == actor_name:
            return binding

    # Case-insensitive match
    actor_name_lower = actor_name.lower()
    for binding in all_bindings:
        if binding.get_name().lower() == actor_name_lower:
            return binding

    # Strip UE de-dup suffix and retry (e.g. sh0010_cam_v01_7 → sh0010_cam_v01)
    stripped = _strip_ue_suffix(actor_name)
    if stripped != actor_name:
        for binding in all_bindings:
            if binding.get_name() == stripped:
                return binding
        stripped_lower = stripped.lower()
        for binding in all_bindings:
            if binding.get_name().lower() == stripped_lower:
                return binding

    seq_name = unreal.SystemLibrary.get_object_name(level_sequence)
    unreal.log(
        "Ftrack Export: '%s' not found in '%s'. Available bindings: %s"
        % (actor_name, seq_name, binding_names)
    )
    return None


def _resolve_actor_by_name(actor_name: str):
    """Find a CineCameraActor in the current level by object name or actor label."""
    try:
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        cameras = subsystem.get_all_level_actors_of_class(unreal.CineCameraActor) or []
    except Exception:
        cameras = unreal.EditorLevelLibrary.get_all_level_actors() or []

    for cam in cameras:
        if unreal.SystemLibrary.get_object_name(cam) == actor_name:
            return cam
        if cam.get_actor_label() == actor_name:
            return cam
    return None


def _find_binding_in_sequence(actor, level_sequence, world):
    """Return the SequencerBindingProxy for actor in level_sequence, or None."""
    actor_label = actor.get_actor_label()
    actor_obj_name = unreal.SystemLibrary.get_object_name(actor)

    # Fast path: find_binding_by_name is a direct lookup
    for name in (actor_label, actor_obj_name):
        try:
            binding = level_sequence.find_binding_by_name(name)
            if binding and binding.get_name() == name:
                return binding
        except Exception:
            pass

    # Fallback: iterate bindings
    playback_range = level_sequence.get_playback_range()
    for binding in (level_sequence.get_bindings() or []):
        if binding.get_name() not in (actor_label, actor_obj_name):
            continue
        try:
            results = unreal.SequencerTools.get_bound_objects(
                world, level_sequence, [binding], playback_range
            )
            for result in (results or []):
                for obj in (result.bound_objects or []):
                    if obj == actor:
                        return binding
        except Exception:
            return binding
    return None


def _find_sequence_and_binding_by_scan(actor_name: str, world):
    """
    Fallback scan: walk /Game with list_assets(recursive=False, include_folder=True)
    per folder so we never trigger the ARFilter recursive_paths bug.
    Falls back to the currently open sequence as a last resort.
    """
    _ = world
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ["/Game"]
    scanned = 0

    while folders:
        folder = folders.pop(0)
        try:
            items = unreal.EditorAssetLibrary.list_assets(
                folder, recursive=False, include_folder=True
            ) or []
        except Exception as e:
            unreal.log_warning("Ftrack Export: list_assets failed for '%s': %s" % (folder, e))
            continue

        for item in items:
            last = item.rstrip("/").split("/")[-1]
            if "." not in last:
                # Folder entry — enqueue for next iteration
                folders.append(item)
                continue
            # Asset entry — check class without loading
            try:
                ad = ar.get_asset_by_object_path(item)
                if not ad or _asset_class_name(ad) != "LevelSequence":
                    continue
                seq = unreal.load_asset(item)
                if not seq:
                    continue
                scanned += 1
                binding = _find_binding_by_name_only(seq, actor_name)
                if binding:
                    unreal.log(
                        "Ftrack Export: Found '%s' in '%s' (scanned %d sequence(s))."
                        % (actor_name, unreal.SystemLibrary.get_object_name(seq), scanned)
                    )
                    return seq, binding
            except Exception:
                pass

    # Last resort: check the currently open sequence
    try:
        seq = unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        if seq:
            binding = _find_binding_by_name_only(seq, actor_name)
            if binding:
                unreal.log(
                    "Ftrack Export: Found '%s' in currently open sequence '%s'."
                    % (actor_name, unreal.SystemLibrary.get_object_name(seq))
                )
                return seq, binding
    except Exception:
        pass

    unreal.log_warning("Ftrack Export: Scanned %d sequence(s), binding '%s' not found." % (scanned, actor_name))
    return None, None


def _bake_transform_manual(world, level_sequence, camera_binding, start_frame, end_frame):
    """
    Scrub the sequencer frame-by-frame, capture the camera actor's world-space
    transform at each frame, then write explicit linear keyframes into the
    binding's MovieScene3DTransformTrack.  Replaces SequencerTools.bake_transform
    which was removed in UE 5.3+.
    """
    seq_lib = unreal.LevelSequenceEditorBlueprintLibrary
    camera_name = camera_binding.get_name()

    # Make sure the sequence is open in the editor so spawnables are live
    try:
        seq_lib.open_level_sequence(level_sequence)
    except AttributeError:
        try:
            unreal.get_editor_subsystem(
                unreal.AssetEditorSubsystem
            ).open_editor_for_assets([level_sequence])
        except Exception:
            pass

    # Capture world transform at every frame by scrubbing the playhead
    baked = {}
    for frame in range(start_frame, end_frame + 1):
        try:
            seq_lib.set_current_time(float(frame))
        except Exception as e:
            unreal.log_warning("Ftrack Bake: set_current_time(%d) failed: %s" % (frame, e))
            continue

        try:
            sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actors = sub.get_all_level_actors() or []
        except Exception:
            actors = unreal.EditorLevelLibrary.get_all_level_actors() or []

        for actor in actors:
            try:
                if actor.get_actor_label() == camera_name:
                    baked[frame] = actor.get_actor_transform()
                    break
            except Exception:
                pass

    if not baked:
        unreal.log_warning(
            "Ftrack Export: Manual bake captured no frames for '%s'. "
            "Open the camera sub-sequence in the Sequencer before publishing." % camera_name
        )
        return

    # Find or create the 3D transform track on this binding
    xform_track = None
    for track in (camera_binding.get_tracks() or []):
        if isinstance(track, unreal.MovieScene3DTransformTrack):
            xform_track = track
            break
    if xform_track is None:
        xform_track = camera_binding.add_track(unreal.MovieScene3DTransformTrack)

    # Replace any existing sections with a single freshly-baked section
    for sec in list(xform_track.get_sections() or []):
        xform_track.remove_section(sec)
    section = xform_track.add_section()
    section.set_range(start_frame, end_frame + 1)

    # Float channels are ordered: TX TY TZ  RX RY RZ  SX SY SZ
    channels = section.get_channels_by_type(unreal.MovieSceneScriptingFloatChannel)
    if len(channels) < 9:
        unreal.log_warning(
            "Ftrack Export: Transform section has %d channels (expected 9) — bake may be incomplete."
            % len(channels)
        )

    for frame, xform in sorted(baked.items()):
        t = xform.translation
        r = xform.rotation.euler()   # FRotator: roll, pitch, yaw
        s = xform.scale3d
        vals = [t.x, t.y, t.z, r.roll, r.pitch, r.yaw, s.x, s.y, s.z]
        fn = unreal.FrameNumber(frame)
        for i, ch in enumerate(channels[: len(vals)]):
            try:
                ch.add_key(
                    fn, vals[i], 0.0,
                    unreal.SequenceTimeUnit.DISPLAY_RATE,
                    unreal.MovieSceneKeyInterpolation.LINEAR,
                )
            except Exception as e:
                unreal.log_warning(
                    "Ftrack Bake: ch%d frame %d: %s" % (i, frame, e)
                )

    unreal.log(
        "Ftrack Export: Baked %d frames for '%s'." % (len(baked), camera_name)
    )


def _bake_transform(world, level_sequence, camera_binding, start_frame, end_frame):
    """Bake camera transform keys. Uses native API when available, manual scrub otherwise."""
    if hasattr(unreal.SequencerTools, "bake_transform"):
        try:
            bake_settings = unreal.BakingAnimationKeySettings()
            bake_settings.reduce_keys = False
            bake_settings.tolerance = 0.001
            unreal.SequencerTools.bake_transform(
                world, [camera_binding], start_frame, end_frame, bake_settings
            )
            return
        except Exception as e:
            unreal.log_warning("Ftrack Export: bake_transform failed: %s — falling back to manual bake." % e)

    # UE 5.3+: manual frame-by-frame bake
    _bake_transform_manual(world, level_sequence, camera_binding, start_frame, end_frame)


def _export_fbx(world, level_sequence, camera_binding, export_path: str) -> bool:
    """Export a single sequence binding to FBX. Tries known UE5 API variants."""

    # UE 5.0-5.2: MovieSceneExportFBXParams + export_fbx(params)
    if hasattr(unreal, "MovieSceneExportFBXParams"):
        try:
            params = unreal.MovieSceneExportFBXParams()
            params.world = world
            params.sequence = level_sequence
            params.root_sequence = level_sequence
            params.bindings = [camera_binding]
            params.master_tracks = []
            params.override_options = unreal.FbxExportOption()
            params.fbx_file_path = export_path
            unreal.SequencerTools.export_fbx(params)
            return True
        except Exception as e:
            unreal.log_warning("Ftrack Export: FBX method 1 (MovieSceneExportFBXParams) failed: %s" % e)

    # UE 5.3+: export_fbx(world, sequence, bindings, override_options, filepath)
    if hasattr(unreal.SequencerTools, "export_fbx"):
        try:
            unreal.SequencerTools.export_fbx(
                world,
                level_sequence,
                [camera_binding],
                unreal.FbxExportOption(),
                export_path,
            )
            return True
        except Exception as e:
            unreal.log_warning("Ftrack Export: FBX method 2 (export_fbx positional) failed: %s" % e)

    # UE 5.4+: export_level_sequence_fbx(SequencerExportFBXParams)
    if hasattr(unreal.SequencerTools, "export_level_sequence_fbx") and \
            hasattr(unreal, "SequencerExportFBXParams"):
        try:
            params = unreal.SequencerExportFBXParams()
            params.world = world
            params.sequence = level_sequence
            params.root_sequence = level_sequence
            params.bindings = [camera_binding]
            params.tracks = []
            params.override_options = unreal.FbxExportOption()
            params.fbx_file_name = export_path
            unreal.SequencerTools.export_level_sequence_fbx(params)
            return True
        except Exception as e:
            unreal.log_warning("Ftrack Export: FBX method 3 (export_level_sequence_fbx) failed: %s" % e)

    return False


def export_binding_from_sequence(
    actor_path: str,
    export_dir: str | None = None,
    sequence_path: str = "",
    actor_label: str = "",
    binding_guid: str = "",
) -> str | None:
    """
    Bake and export any sequencer binding (camera, animation, etc.) to FBX.

    Args:
        actor_path:    UE object path of the actor.
        export_dir:    Absolute filesystem directory. Defaults to <ProjectContent>/Export.
        sequence_path: UE object path of the owning LevelSequence, recorded at mark time.
        actor_label:   Actor display label, used for logging and name-based fallback.
        binding_guid:  Sequencer binding GUID recorded at mark time (preferred lookup).
    Returns:
        Absolute path to the exported FBX, or None on failure.
    """
    if unreal is None:
        return None

    if export_dir is None:
        export_dir = _get_export_dir()

    try:
        world = _get_editor_world()
        if not world:
            unreal.log_error("Ftrack Export: Could not get editor world.")
            return None

        # Display name used in log messages and as FBX filename component.
        actor_name = actor_label if actor_label else actor_path.split(".")[-1]

        # --- Find sequence and binding ------------------------------------------
        level_sequence = None
        camera_binding = None

        if sequence_path and binding_guid:
            # Primary path: load stored sequence and look up binding by stable GUID.
            level_sequence = unreal.load_asset(sequence_path)
            if level_sequence:
                camera_binding = _find_binding_by_guid(level_sequence, binding_guid)
                if not camera_binding:
                    unreal.log_error(
                        "Ftrack Export: Binding GUID '%s' not found in sequence '%s'. "
                        "The camera was likely removed from the sequence — re-mark it."
                        % (binding_guid, sequence_path)
                    )
                    return None

        if not level_sequence or not camera_binding:
            # Legacy / no-GUID path: name-based lookup in stored sequence, then full scan.
            if sequence_path and not level_sequence:
                level_sequence = unreal.load_asset(sequence_path)
            if level_sequence:
                camera_binding = _find_binding_by_name_only(level_sequence, actor_name)
                if not camera_binding:
                    existing_bindings = level_sequence.get_bindings() or []
                    if existing_bindings:
                        unreal.log_error(
                            "Ftrack Export: Binding '%s' not found in sequence '%s'. "
                            "Re-mark the camera with the correct sequence open."
                            % (actor_name, sequence_path)
                        )
                        return None
                    # Empty sequence → master/parent; fall through to scan.
                    unreal.log_warning(
                        "Ftrack Export: Stored sequence '%s' has no bindings (master sequence). "
                        "Scanning for '%s'..." % (sequence_path, actor_name)
                    )
                    level_sequence = None

        if not level_sequence or not camera_binding:
            level_sequence, camera_binding = _find_sequence_and_binding_by_scan(actor_name, world)

        if not level_sequence or not camera_binding:
            unreal.log_error(
                "Ftrack Export: No Level Sequence found containing binding '%s'." % actor_name
            )
            return None

        seq_name = unreal.SystemLibrary.get_object_name(level_sequence)

        # --- Frame range -------------------------------------------------------
        start_frame = level_sequence.get_playback_start()
        end_frame = level_sequence.get_playback_end()

        unreal.log(
            "Ftrack Export: Baking '%s' in '%s' frames %s-%s "
            "(all frames, reduce_keys=off, tolerance=0.001)..."
            % (actor_name, seq_name, start_frame, end_frame)
        )

        # --- Bake transform: every frame, no key reduction ---------------------
        _bake_transform(world, level_sequence, camera_binding, start_frame, end_frame)

        # --- Export to FBX -----------------------------------------------------
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, "%s_%s.fbx" % (seq_name, actor_name))

        ok = _export_fbx(world, level_sequence, camera_binding, export_path)
        if not ok:
            unreal.log_error(
                "Ftrack Export: All FBX export methods failed. "
                "Available SequencerTools attrs: %s"
                % [a for a in dir(unreal.SequencerTools) if "fbx" in a.lower() or "export" in a.lower()]
            )
            return None

        if os.path.isfile(export_path):
            unreal.log("Ftrack Export: Exported -> %s" % export_path)
            return export_path
        else:
            unreal.log_error("Ftrack Export: Export ran but file not found at: %s" % export_path)
            return None

    except Exception as e:
        unreal.log_error("Ftrack Export: Export failed: %s" % e)
        return None


# Backward-compatibility alias
export_camera_from_sequence = export_binding_from_sequence
