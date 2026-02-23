// Copyright Mroya. Ftrack Browser tab panel implementation.

#include "FtrackBrowserPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Styling/AppStyle.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "IPythonScriptPlugin.h"

#define LOCTEXT_NAMESPACE "FtrackBrowserPanel"

void SFtrackBrowserPanel::Construct(const FArguments& InArgs)
{
	ChildSlot
	[
		SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder"))
		.Padding(16.0f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0, 0, 0, 12.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("Description", "Ftrack Task Hub browser: browse components and import into the project."))
				.AutoWrapText(true)
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SButton)
				.Text(LOCTEXT("OpenBrowser", "Open Ftrack Browser"))
				.OnClicked(this, &SFtrackBrowserPanel::OnOpenBrowser)
			]
		]
	];
}

FReply SFtrackBrowserPanel::OnOpenBrowser()
{
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("MroyaFtrack"));
	if (!Plugin.IsValid())
	{
		FNotificationInfo Info(LOCTEXT("PluginNotFound", "MroyaFtrack plugin path not found."));
		Info.ExpireDuration = 3.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}

	FString PluginDir = Plugin->GetBaseDir();
	FString ScriptsDir = FPaths::Combine(PluginDir, TEXT("Scripts"));
	FPaths::NormalizeDirectoryName(ScriptsDir);
	ScriptsDir = ScriptsDir.Replace(TEXT("\\"), TEXT("/"));

	IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
	if (!PythonPlugin || !PythonPlugin->IsPythonAvailable())
	{
		FNotificationInfo Info(LOCTEXT("PythonNotAvailable", "Python Editor Script plugin is not available. Enable it in Edit -> Plugins and use ftrack -> Open browser from the menu."));
		Info.ExpireDuration = 5.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
		return FReply::Handled();
	}

	// Python: add Scripts to path and call open_browser_inprocess.open_browser()
	FString QuotedPath;
	QuotedPath.Reserve(ScriptsDir.Len() + 4);
	QuotedPath += TEXT("'");
	for (TCHAR c : ScriptsDir)
	{
		if (c == TEXT('\\')) QuotedPath += TEXT("\\\\");
		else if (c == TEXT('\'')) QuotedPath += TEXT("\\'");
		else QuotedPath += c;
	}
	QuotedPath += TEXT("'");
	FString Code = FString::Printf(TEXT("import sys\nsys.path.insert(0, %s)\nimport open_browser_inprocess\nopen_browser_inprocess.open_browser()\n"), *QuotedPath);

	bool bOk = PythonPlugin->ExecPythonCommand(*Code);
	if (!bOk)
	{
		FNotificationInfo Info(LOCTEXT("PythonExecFailed", "Failed to run Ftrack browser. Check Output Log for errors."));
		Info.ExpireDuration = 4.0f;
		FSlateNotificationManager::Get().AddNotification(Info);
	}
	return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
