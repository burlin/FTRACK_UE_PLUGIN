// Copyright Mroya. Ftrack plugin editor module.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FSpawnTabArgs;

class FMroyaFtrackModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	/** Spawns the "Ftrack Resources Control" dockable tab. */
	static TSharedRef<class SDockTab> SpawnFtrackResourcesTab(const FSpawnTabArgs& Args);

	/** Spawns the "Ftrack Browser" dockable tab. */
	static TSharedRef<class SDockTab> SpawnFtrackBrowserTab(const FSpawnTabArgs& Args);
};
