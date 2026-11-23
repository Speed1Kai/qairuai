using UnrealBuildTool;

public class Final_ProtocolEditorTarget : TargetRules
{
    public Final_ProtocolEditorTarget(TargetInfo Target) : base(Target)
    {
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        Type = TargetType.Editor;
        ExtraModuleNames.Add("Final_Protocol");
    }
}
