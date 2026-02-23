// Copyright Mroya. Ftrack plugin editor module.

#include "MroyaFtrackModule.h"
#include "FtrackResourcesPanel.h"
#include "FtrackBrowserPanel.h"
#include "Widgets/Docking/SDockTab.h"
#include "Framework/Docking/TabManager.h"
#include "LevelEditor.h"
#include "Modules/ModuleManager.h"
#include "ToolMenus.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Styling/AppStyle.h"

#define LOCTEXT_NAMESPACE "FMroyaFtrackModule"

static const FName FtrackResourcesTabName("FtrackResourcesControl");
static const FName FtrackBrowserTabName("FtrackBrowser");

static void RegisterFtrackWindowMenu()
{
	UToolMenus* ToolMenus = UToolMenus::Get();
	if (!ToolMenus) return;
	UToolMenu* WindowMenu = ToolMenus->ExtendMenu("LevelEditor.MainMenu.Window");
	if (!WindowMenu) return;

	FToolMenuSection& Section = WindowMenu->FindOrAddSection("FtrackTabs");
	Section.AddMenuEntry(
		"FtrackResourcesControl",
		LOCTEXT("FtrackResourcesTabTitle", "Ftrack Resources Control"),
		LOCTEXT("FtrackResourcesTabTooltip", "List and manage Ftrack Asset Handles: Import, Re-import, Update."),
		FSlateIcon(),
		FUIAction(FExecuteAction::CreateLambda([]() { FGlobalTabmanager::Get()->TryInvokeTab(FtrackResourcesTabName); }))
	);
	// Ftrack Browser tab not shown in Window menu; open via ftrack -> Open browser
}

void FMroyaFtrackModule::StartupModule()
{
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(FtrackResourcesTabName, FOnSpawnTab::CreateStatic(&FMroyaFtrackModule::SpawnFtrackResourcesTab))
		.SetDisplayName(LOCTEXT("FtrackResourcesTabTitle", "Ftrack Resources Control"))
		.SetTooltipText(LOCTEXT("FtrackResourcesTabTooltip", "List and manage Ftrack Asset Handles: Import, Re-import, Update."))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(FtrackBrowserTabName, FOnSpawnTab::CreateStatic(&FMroyaFtrackModule::SpawnFtrackBrowserTab))
		.SetDisplayName(LOCTEXT("FtrackBrowserTabTitle", "Ftrack Browser"))
		.SetTooltipText(LOCTEXT("FtrackBrowserTabTooltip", "Open the Ftrack Task Hub browser."))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateStatic(&RegisterFtrackWindowMenu));
}

void FMroyaFtrackModule::ShutdownModule()
{
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(FtrackResourcesTabName);
	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(FtrackBrowserTabName);
}

TSharedRef<SDockTab> FMroyaFtrackModule::SpawnFtrackResourcesTab(const FSpawnTabArgs& Args)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("FtrackResourcesTabLabel", "Ftrack Resources Control"))
		[
			SNew(SFtrackResourcesPanel)
		];
}

TSharedRef<SDockTab> FMroyaFtrackModule::SpawnFtrackBrowserTab(const FSpawnTabArgs& Args)
{
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("FtrackBrowserTabLabel", "Ftrack Browser"))
		[
			SNew(SFtrackBrowserPanel)
		];
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FMroyaFtrackModule, MroyaFtrack)
