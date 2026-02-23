// Copyright Mroya. Ftrack Resources Control panel implementation.

#include "FtrackResourcesPanel.h"
#include "FtrackAssetHandle.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Views/SListView.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Styling/AppStyle.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "IPythonScriptPlugin.h"

#define LOCTEXT_NAMESPACE "FtrackResourcesPanel"

void SFtrackResourcesPanel::Construct(const FArguments& InArgs)
{
	RefreshHandleList();

	ChildSlot
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(4.0f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(2.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("Refresh", "Refresh"))
				.OnClicked(this, &SFtrackResourcesPanel::OnRefresh)
			]
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(2.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("Import", "Import"))
				.OnClicked(this, &SFtrackResourcesPanel::OnImportSelected)
			]
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(2.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("Reimport", "Re-import"))
				.OnClicked(this, &SFtrackResourcesPanel::OnReimportSelected)
			]
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(2.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("Update", "Update"))
				.OnClicked(this, &SFtrackResourcesPanel::OnUpdateSelected)
			]
		]
		+ SVerticalBox::Slot()
		.FillHeight(1.0f)
		.Padding(4.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
			.Padding(4.0f)
			[
				SAssignNew(HandleListView, SListView<TSharedPtr<FAssetData>>)
				.ListItemsSource(&HandleList)
				.OnGenerateRow(this, &SFtrackResourcesPanel::OnGenerateRow)
				.SelectionMode(ESelectionMode::Single)
			]
		]
	];
}

void SFtrackResourcesPanel::RefreshHandleList()
{
	HandleList.Reset();
	IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry").Get();
	FARFilter Filter;
	Filter.ClassPaths.Add(UFtrackAssetHandle::StaticClass()->GetClassPathName());
	Filter.bRecursiveClasses = true;
	TArray<FAssetData> OutAssets;
	Registry.GetAssets(Filter, OutAssets);
	for (const FAssetData& Data : OutAssets)
	{
		HandleList.Add(MakeShared<FAssetData>(Data));
	}
	if (HandleListView.IsValid())
	{
		HandleListView->RequestListRefresh();
	}
}

FReply SFtrackResourcesPanel::OnRefresh()
{
	RefreshHandleList();
	return FReply::Handled();
}

UFtrackAssetHandle* SFtrackResourcesPanel::GetSelectedHandle() const
{
	if (!HandleListView.IsValid()) return nullptr;
	TArray<TSharedPtr<FAssetData>> Selected = HandleListView->GetSelectedItems();
	if (Selected.Num() != 1) return nullptr;
	FSoftObjectPath Path(Selected[0]->GetSoftObjectPath());
	return Cast<UFtrackAssetHandle>(Path.TryLoad());
}

FReply SFtrackResourcesPanel::OnImportSelected()
{
	if (!HandleListView.IsValid()) return FReply::Handled();
	TArray<TSharedPtr<FAssetData>> Selected = HandleListView->GetSelectedItems();
	if (Selected.Num() != 1)
	{
		FNotificationInfo Info(LOCTEXT("NoSelection", "Select one Ftrack Asset Handle in the list."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}
	FString HandlePath = Selected[0]->GetSoftObjectPath().ToString();
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("MroyaFtrack"));
	if (!Plugin.IsValid())
	{
		FNotificationInfo Info(LOCTEXT("PluginNotFound", "MroyaFtrack plugin not found."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}
	FString ScriptsDir = FPaths::Combine(Plugin->GetBaseDir(), TEXT("Scripts"));
	FPaths::NormalizeDirectoryName(ScriptsDir);
	FString QuotedPath;
	QuotedPath.Reserve(ScriptsDir.Len() + 4);
	QuotedPath += TEXT("'");
	for (TCHAR c : ScriptsDir.Replace(TEXT("\\"), TEXT("/")))
	{
		if (c == TEXT('\\')) QuotedPath += TEXT("\\\\");
		else if (c == TEXT('\'')) QuotedPath += TEXT("\\'");
		else QuotedPath += c;
	}
	QuotedPath += TEXT("'");
	FString QuotedHandlePath;
	QuotedHandlePath.Reserve(HandlePath.Len() + 4);
	QuotedHandlePath += TEXT("'");
	for (TCHAR c : HandlePath)
	{
		if (c == TEXT('\\')) QuotedHandlePath += TEXT("\\\\");
		else if (c == TEXT('\'')) QuotedHandlePath += TEXT("\\'");
		else QuotedHandlePath += c;
	}
	QuotedHandlePath += TEXT("'");
	IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
	if (!PythonPlugin || !PythonPlugin->IsPythonAvailable())
	{
		FNotificationInfo Info(LOCTEXT("PythonNotAvailable", "Python Editor Script plugin is not available."));
		Info.ExpireDuration = 4.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}
	FString Code = FString::Printf(
		TEXT("import sys\nsys.path.insert(0, %s)\nimport init_ftrack_menu\nn = init_ftrack_menu.import_handle_in_unreal(%s)\n"),
		*QuotedPath, *QuotedHandlePath);
	bool bOk = PythonPlugin->ExecPythonCommand(*Code);
	if (bOk)
	{
		FNotificationInfo Info(LOCTEXT("ImportDone", "Import triggered. Check Output Log and import dialog."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
	}
	else
	{
		FNotificationInfo Info(LOCTEXT("ImportFailed", "Import failed. Check Output Log for errors."));
		Info.ExpireDuration = 4.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
	}
	return FReply::Handled();
}

FReply SFtrackResourcesPanel::OnReimportSelected()
{
	UFtrackAssetHandle* Handle = GetSelectedHandle();
	if (!Handle)
	{
		FNotificationInfo Info(LOCTEXT("NoSelection", "Select one Ftrack Asset Handle in the list."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}
	// TODO: re-import component for this handle
	FNotificationInfo Info(FText::Format(
		LOCTEXT("ReimportPlanned", "Re-import for \"{0}\" will be wired to import pipeline."),
		FText::FromString(Handle->GetName())));
	Info.ExpireDuration = 4.0f;
	FSlateNotificationManager::Get().AddNotification(Info);
	return FReply::Handled();
}

FReply SFtrackResourcesPanel::OnUpdateSelected()
{
	UFtrackAssetHandle* Handle = GetSelectedHandle();
	if (!Handle)
	{
		FNotificationInfo Info(LOCTEXT("NoSelection", "Select one Ftrack Asset Handle in the list."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}
	// TODO: update component (e.g. pull latest version) for this handle
	FNotificationInfo Info(FText::Format(
		LOCTEXT("UpdatePlanned", "Update for \"{0}\" will be wired to update pipeline."),
		FText::FromString(Handle->GetName())));
	Info.ExpireDuration = 4.0f;
	FSlateNotificationManager::Get().AddNotification(Info);
	return FReply::Handled();
}

TSharedRef<ITableRow> SFtrackResourcesPanel::OnGenerateRow(TSharedPtr<FAssetData> Item, const TSharedRef<STableViewBase>& OwnerTable)
{
	if (!Item.IsValid())
	{
		return SNew(STableRow<TSharedPtr<FAssetData>>, OwnerTable)[ SNew(STextBlock).Text(LOCTEXT("Invalid", "(invalid)"))];
	}
	FString Display = FString::Printf(TEXT("%s  |  %s"), *Item->AssetName.ToString(), *Item->GetObjectPathString());
	return SNew(STableRow<TSharedPtr<FAssetData>>, OwnerTable)
		[
			SNew(STextBlock)
			.Text(FText::FromString(Display))
		];
}

FText SFtrackResourcesPanel::GetSelectedHandleSummary() const
{
	UFtrackAssetHandle* Handle = GetSelectedHandle();
	if (!Handle) return LOCTEXT("NoHandle", "No handle selected");
	return FText::FromString(Handle->GetName());
}

#undef LOCTEXT_NAMESPACE
