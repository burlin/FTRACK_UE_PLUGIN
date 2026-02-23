// Copyright Mroya. Ftrack Resources Control panel - lists Ftrack Asset Handles and provides Import/Reimport/Update.

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "AssetRegistry/AssetData.h"

class UFtrackAssetHandle;

/**
 * Slate panel that shows all UFtrackAssetHandle assets in the project
 * and provides toolbar actions: Refresh, Import, Re-import, Update.
 * Used as the content of the "Ftrack Resources Control" dockable tab.
 */
class MROYAFTRACK_API SFtrackResourcesPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SFtrackResourcesPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	void RefreshHandleList();
	UFtrackAssetHandle* GetSelectedHandle() const;
	FReply OnRefresh();
	FReply OnImportSelected();
	FReply OnReimportSelected();
	FReply OnUpdateSelected();
	TSharedRef<ITableRow> OnGenerateRow(TSharedPtr<FAssetData> Item, const TSharedRef<STableViewBase>& OwnerTable);
	FText GetSelectedHandleSummary() const;

	TSharedPtr<SListView<TSharedPtr<FAssetData>>> HandleListView;
	TArray<TSharedPtr<FAssetData>> HandleList;
};
