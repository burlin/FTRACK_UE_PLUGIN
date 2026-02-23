// Copyright Mroya. Ftrack asset handle - stores component ID for deferred load/re-import.
// Path to source file is resolved at import time via Python/ftrack; only generic data in version control.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "FtrackAssetHandle.generated.h"

/**
 * DataAsset that holds a reference to an ftrack component by ID.
 * Used for "handle" workflow: create handle in Content, then Load/Re-import resolves path and imports.
 * Only ComponentId (and optional ContentSubpath) are stored - no machine-specific paths.
 */
UCLASS(BlueprintType)
class MROYAFTRACK_API UFtrackAssetHandle : public UDataAsset
{
	GENERATED_BODY()

public:
	/** Ftrack Component ID - used to resolve file path at import time. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack")
	FString ComponentId;

	/** Optional: Content subpath for import (e.g. "Assets/Props/Table"). Empty = use default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack")
	FString ContentSubpath;

	/** Optional: Ftrack Asset Version ID (for display or version pinning). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ftrack")
	FString AssetVersionId;
};
