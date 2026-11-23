#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "FrontEnd.generated.h"

class ACameraActor;
class SFinalProtocolMenu;

UCLASS()
class AFinalProtocolFrontEnd : public AGameModeBase
{
    GENERATED_BODY()

public:
    AFinalProtocolFrontEnd();
    virtual void StartPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    void RotateSentinel(float Degrees);
    void PlayCampaign(bool bReplay = false);

private:
    enum class EScenery : uint8 { Drone, Rotor, Smoke, Screen };
    struct FScenery
    {
        TWeakObjectPtr<AActor> Actor;
        TWeakObjectPtr<class UMaterialInstanceDynamic> Material;
        FVector Origin;
        FRotator Rotation;
        EScenery Kind;
        float Offset;
    };
    void PrepareScenery();
    TArray<FScenery> Scenery;
    float SceneryTime=0.f;
    TWeakObjectPtr<AActor> Sentinel;
    TSharedPtr<SFinalProtocolMenu> Menu;
};

UCLASS()
class AFinalProtocolTraining : public AGameModeBase
{
    GENERATED_BODY()

public:
    AFinalProtocolTraining();
    virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
    virtual void StartPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    void EquipTrainee();
    void ResetTargets();
    void UpdateTargets();
    UFUNCTION()
    void RegisterHit(AActor* DamagedActor,float Damage,const UDamageType* DamageType,AController* EventInstigator,AActor* Source);

    struct FTarget
    {
        TWeakObjectPtr<class AStaticMeshActor> Actor;
        FVector Origin;
        bool bHit = false;
    };

    TWeakObjectPtr<APawn> EquippedPawn;
    TArray<FTarget> Targets;
    int32 Hits = 0;
    bool bResetHeld = false;
    TSharedPtr<class SWidget> Instructions;
};


