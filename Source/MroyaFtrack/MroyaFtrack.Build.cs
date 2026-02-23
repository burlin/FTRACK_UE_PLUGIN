// Copyright Mroya. Ftrack Handle and editor integration.

using UnrealBuildTool;

public class MroyaFtrack : ModuleRules
{
	public MroyaFtrack(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate",
			"SlateCore",
			"EditorStyle",
			"UnrealEd",
			"LevelEditor",
			"AssetRegistry",
			"InputCore",
			"Projects",
			"ToolMenus",
			"ContentBrowser",
			"PythonScriptPlugin",
			"Projects",
		});
	}
}
