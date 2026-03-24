// Copyright Mroya. Ftrack Out Handle - passive PublishJob-shaped data for Publisher.execute().
// Optional per-component: UE object binding, scenario index. One playblast path per job (version), not per component.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "FtrackOutHandle.generated.h"

/**
 * Resolves an object in the Unreal scene or content: sequence, actor, content root.
 * Not serialized into the ftrack publish job; used by editor tools and export scripts for binding.
 */
USTRUCT(BlueprintType)
struct FFtrackObjectBinding
{
	GENERATED_BODY()

	/** Level Sequence or other asset path string (e.g. /Game/Shots/.../LS_shot.LS_shot). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Binding", meta = (DisplayName = "sequence_path"))
	FString SequencePath;

	/** Actor label in the sequence or level (e.g. bound actor name). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Binding", meta = (DisplayName = "actor_label"))
	FString ActorLabel;

	/** World actor or subobject path string (e.g. ...PersistentLevel.ActorName). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Binding", meta = (DisplayName = "actor_name"))
	FString ActorName;

	/** Content root or package path under /Game/ (pipeline-specific). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Binding", meta = (DisplayName = "content_path"))
	FString ContentPath;
};

/**
 * One publish component: mirrors ComponentData plus UE-only fields (object binding, scenario index).
 */
USTRUCT(BlueprintType)
struct FFtrackPublishComponentEntry
{
	GENERATED_BODY()

	/** Component name (e.g. main.abc). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	FString Name;

	/** Path to file or sequence pattern on disk (after export step). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	FString FilePath;

	/** snapshot | playblast | file | sequence */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	FString ComponentType;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	bool bExportEnabled = true;

	/** Optional sequence pattern when different from FilePath. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	FString SequencePattern;

	/** If true, FrameStart/FrameEnd are written to frame_range and metadata when building the job dict. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	bool bHasFrameRange = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish", meta = (EditCondition = "bHasFrameRange"))
	int32 FrameStart = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish", meta = (EditCondition = "bHasFrameRange"))
	int32 FrameEnd = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	bool bTransferAfterPublish = true;

	/** Key-value metadata attached to the ftrack component. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Publish")
	TMap<FString, FString> Metadata;

	/**
	 * Pointer data for the object to bind in editor / export (sequencer, level, content).
	 * Not passed to ftrack publish; read from the asset in Python/Blueprint when needed.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Binding")
	FFtrackObjectBinding ObjectBinding;

	/** Passive index into an external scenario library (resolved by pipeline Python, not by this asset). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Unreal")
	int32 ScenarioLibraryIndex = 0;

	/** Optional human-readable note for the scenario slot. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Unreal")
	FString ScenarioDescription;
};

/**
 * DataAsset holding full publish payload for ftrack_inout Publisher (PublishJob shape).
 */
UCLASS(BlueprintType)
class MROYAFTRACK_API UFtrackOutHandle : public UDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString TaskId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString AssetId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString AssetName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString AssetType;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job", meta = (MultiLine = true))
	FString Comment;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString ThumbnailPath;

	/** Enable the job-level playblast component (not duplicated per file component). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job", meta = (DisplayName = "use_playblast"))
	bool bUsePlayblast = false;

	/**
	 * Single preview video path for this publish (one per AssetVersion). Shown only when use_playblast is on.
	 * If bUsePlayblast is true, the bridge adds one ComponentData (component_type=playblast) for encode_media.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job", meta = (DisplayName = "playblast_path", EditCondition = "bUsePlayblast", EditConditionHides))
	FString PlayblastPath;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString SourceDcc = TEXT("unreal");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString TransferTargetLocation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	TArray<FFtrackPublishComponentEntry> Components;
};
