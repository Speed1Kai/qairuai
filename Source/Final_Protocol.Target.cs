using UnrealBuildTool;

public class Final_ProtocolTarget : TargetRules
{
    public Final_ProtocolTarget(TargetInfo Target) : base(Target)
    {
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        Type = TargetType.Game;
        ExtraModuleNames.Add("Final_Protocol");
    }
}
