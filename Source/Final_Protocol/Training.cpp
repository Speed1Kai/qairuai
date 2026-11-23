#include "FrontEnd.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Styling/CoreStyle.h"
#include "Brushes/SlateColorBrush.h"
#include "UObject/UnrealType.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "FinalProtocolTraining"

namespace
{
const FSlateColorBrush TrainingPanel(FLinearColor(.009f,.025f,.033f,.89f));

template<typename Field, typename Value>
bool SetPawnField(APawn* Pawn, const TCHAR* Name, Value NewValue)
{
    if (Field* Property = FindFProperty<Field>(Pawn->GetClass(), Name))
    {
        Property->SetPropertyValue_InContainer(Pawn, NewValue);
        return true;
    }
    return false;
}
}

AFinalProtocolTraining::AFinalProtocolTraining()
{
    PrimaryActorTick.bCanEverTick = true;
}

void AFinalProtocolTraining::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
    if (UClass* Player = LoadClass<APawn>(nullptr,
        TEXT("/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C")))
    {
        DefaultPawnClass = Player;
    }
    Super::InitGame(MapName,Options,ErrorMessage);
}

void AFinalProtocolTraining::StartPlay()
{
    Super::StartPlay();
    APlayerController* Controller = GetWorld()->GetFirstPlayerController();
    if (!Controller)
    {
        return;
    }
    if (!Controller->GetPawn())
    {
        RestartPlayer(Controller);
    }
    Controller->SetInputMode(FInputModeGameOnly());
    Controller->bShowMouseCursor = false;
    EquipTrainee();
    ResetTargets();

    if (GEngine && GEngine->GameViewport)
    {
        Instructions = SNew(SOverlay).Visibility(EVisibility::HitTestInvisible)
            + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(28,40,0,0)
            [
                SNew(SBorder).BorderImage(&TrainingPanel).Padding(15.f)
                [
                    SNew(STextBlock)
                    .Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),17))
                    .ColorAndOpacity(FLinearColor(.71f,.93f,.97f))
                    .Text_Lambda([WeakThis=TWeakObjectPtr<AFinalProtocolTraining>(this)]()
                    {
                        return WeakThis.IsValid() ? FText::Format(
                            LOCTEXT("Score","ТРЕНИРОВКА   /   МИШЕНИ {0} ИЗ 3\nЛКМ  выстрел    Q  смена    R  перезарядка\nBackspace  сбросить мишени    Esc  в меню"),
                            WeakThis->Hits) : FText::GetEmpty();
                    })
                ]
            ];
        GEngine->GameViewport->AddViewportWidgetContent(Instructions.ToSharedRef(),90);
    }
}

void AFinalProtocolTraining::EquipTrainee()
{
    APlayerController* Controller = GetWorld()->GetFirstPlayerController();
    APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
    if (!Pawn || EquippedPawn == Pawn)
    {
        return;
    }
    bool bFieldsFound = SetPawnField<FBoolProperty>(Pawn,TEXT("OwnsCarbine"),true);
    bFieldsFound &= SetPawnField<FBoolProperty>(Pawn,TEXT("OwnsDischarge"),true);
    // The campaign navigation HUD is suppressed while using the same pawn on the range.
    bFieldsFound &= SetPawnField<FBoolProperty>(Pawn,TEXT("StoryBusy"),true);
    bFieldsFound &= SetPawnField<FIntProperty>(Pawn,TEXT("CyborgMode"),1);
    bFieldsFound &= SetPawnField<FIntProperty>(Pawn,TEXT("HunterMagazine"),30);
    bFieldsFound &= SetPawnField<FIntProperty>(Pawn,TEXT("HunterReserve"),90);
    bFieldsFound &= SetPawnField<FIntProperty>(Pawn,TEXT("BreakerMagazine"),1);
    bFieldsFound &= SetPawnField<FIntProperty>(Pawn,TEXT("BreakerReserve"),8);
    if (UFunction* Sync = Pawn->FindFunction(TEXT("Weapon_Sync")); Sync && bFieldsFound)
    {
        Pawn->ProcessEvent(Sync,nullptr);
        EquippedPawn = Pawn;
        UE_LOG(LogTemp, Display, TEXT("FrontEnd training loadout ready"));
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("FrontEnd cannot configure the training loadout"));
        EquippedPawn = Pawn;
    }
}

void AFinalProtocolTraining::ResetTargets()
{
    for (const FTarget& Target : Targets)
    {
        if (AStaticMeshActor* Actor = Target.Actor.Get())
        {
            Actor->Destroy();
        }
    }
    Targets.Reset();
    Hits = 0;
    UStaticMesh* Disc = LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    UMaterialInterface* Face = LoadObject<UMaterialInterface>(nullptr,
        TEXT("/Game/LabTutorial/Industrial/M_AmberIndicator.M_AmberIndicator"));
    for (const FVector Point : {FVector(550,-215,155), FVector(860,0,182), FVector(1150,240,158)})
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        AStaticMeshActor* Target = GetWorld()->SpawnActor<AStaticMeshActor>(Point,FRotator(90,0,0),Params);
        if (!Target)
        {
            continue;
        }
        UStaticMeshComponent* Mesh = Target->GetStaticMeshComponent();
        Mesh->SetMobility(EComponentMobility::Movable);
        Mesh->SetStaticMesh(Disc);
        if (Face)
        {
            Mesh->SetMaterial(0,Face);
        }
        Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
        Target->SetCanBeDamaged(true);
        Target->SetActorScale3D(FVector(.70,.70,.12));
        Target->Tags.Add(TEXT("TrainingTarget"));
        Targets.Add({Target,Point});
        Target->OnTakeAnyDamage.AddDynamic(this,&AFinalProtocolTraining::RegisterHit);
    }
}

void AFinalProtocolTraining::UpdateTargets()
{
    for (int32 Index=0; Index<Targets.Num(); ++Index)
    {
        FTarget& Target = Targets[Index];
        if (AStaticMeshActor* Actor = Target.Actor.Get(); Actor && !Target.bHit && Index>0)
        {
            const float Phase = GetWorld()->GetTimeSeconds() * (Index == 1 ? 1.25f : .92f);
            Actor->SetActorLocation(Target.Origin + FVector(0,FMath::Sin(Phase)*62.f,0));
        }
    }
}

void AFinalProtocolTraining::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    EquipTrainee();
    APlayerController* Controller = GetWorld()->GetFirstPlayerController();
    if (!Controller)
    {
        return;
    }
    if (Controller->WasInputKeyJustPressed(EKeys::Escape))
    {
        UGameplayStatics::OpenLevel(this,TEXT("/Game/FrontEnd/Lvl_MainMenu"));
        return;
    }
    const bool bResetPressed = Controller->IsInputKeyDown(EKeys::BackSpace);
    if (bResetPressed && !bResetHeld)
    {
        ResetTargets();
        EquippedPawn.Reset();
        EquipTrainee();
    }
    bResetHeld = bResetPressed;
    UpdateTargets();

}

void AFinalProtocolTraining::RegisterHit(AActor* DamagedActor,float Damage,const UDamageType*,
                                         AController*,AActor*)
{
    if (Damage <= 0)
    {
        return;
    }
    for (FTarget& Target : Targets)
    {
        if (Target.Actor.Get() == DamagedActor && !Target.bHit)
        {
            Target.bHit = true;
            ++Hits;
            DamagedActor->SetActorHiddenInGame(true);
            DamagedActor->SetActorEnableCollision(false);
            UE_LOG(LogTemp,Display,TEXT("FrontEnd training hit %d"),Hits);
            return;
        }
    }
}

void AFinalProtocolTraining::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Instructions && GEngine && GEngine->GameViewport)
    {
        GEngine->GameViewport->RemoveViewportWidgetContent(Instructions.ToSharedRef());
    }
    Instructions.Reset();
    Super::EndPlay(Reason);
}

#undef LOCTEXT_NAMESPACE

