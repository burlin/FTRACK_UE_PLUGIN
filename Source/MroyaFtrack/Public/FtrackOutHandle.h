// Copyright Mroya. Ftrack Out Handle - passive PublishJob-shaped data for Publisher.execute().
// Optional per-component: UE object path string and scenario library index for external export scripts.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "FtrackOutHandle.generated.h"

/**
 * One publish component: mirrors ComponentData plus UE-only fields (source object path, scenario index).
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
	 * Optional: path to the Unreal object to export (free-form string).
	 * Examples: soft object path, sequencer binding path, subobject path (e.g. camera in a Level Sequence).
	 * Not sent to ftrack unless copied to Metadata by the Python bridge.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Unreal")
	FString SourceObjectPath;

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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString Comment;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString ThumbnailPath;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString SourceDcc;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString SourceScene;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	FString TransferTargetLocation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack|Job")
	TArray<FFtrackPublishComponentEntry> Components;
};
