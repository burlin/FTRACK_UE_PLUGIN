// Copyright Mroya. Ftrack Browser tab panel - Open button launches the Ftrack browser (Python).

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

/**
 * Slate panel for the "Ftrack Browser" tab.
 * Shows an "Open Ftrack Browser" button that runs Python open_browser_inprocess.open_browser().
 * (Embedding the browser inside the tab would require engine-specific HWND API.)
 */
class MROYAFTRACK_API SFtrackBrowserPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SFtrackBrowserPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FReply OnOpenBrowser();
};
