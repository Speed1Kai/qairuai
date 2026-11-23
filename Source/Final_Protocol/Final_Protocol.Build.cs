using UnrealBuildTool;

public class Final_Protocol : ModuleRules
{
    public Final_Protocol(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "ApplicationCore", "InputCore", "Json", "Slate", "SlateCore" });
    }
}

