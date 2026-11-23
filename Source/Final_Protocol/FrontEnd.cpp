#include "FrontEnd.h"
#include "Algo/AllOf.h"

#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Styling/CoreStyle.h"
#include "Brushes/SlateColorBrush.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "FinalProtocolFrontEnd"

namespace
{
const FName MenuMap(TEXT("/Game/FrontEnd/Lvl_MainMenu"));
const FName LabMap(TEXT("/Game/Lvl_LabTutorial"));
const FName TrainingMap(TEXT("/Game/FrontEnd/Lvl_Training"));
const FLinearColor White(.88f,.93f,.96f);
const FLinearColor Blue(.30f,.79f,.86f);
const FLinearColor Ash(.60f,.70f,.73f);
const FSlateColorBrush Panel(FLinearColor(.008f,.023f,.030f,.93f));
const FSlateColorBrush Accent(FLinearColor(.30f,.79f,.86f,.85f));

FString Slot(TCHAR Suffix)
{
    return FPaths::Combine(FPaths::ProjectSavedDir(), FString::Printf(TEXT("FP_DemoCheckpoint_v2_%c.json"), Suffix));
}

struct FCheckpoint
{
    int32 Rank = 0;
    int32 Capacity = 0;
    int32 Inventory = 0;
};

FCheckpoint ReadCheckpoint()
{
    static const TCHAR* Required[] = {
        TEXT("X"), TEXT("Y"), TEXT("Z"), TEXT("RepairCapacity"), TEXT("PatrolSpared"),
        TEXT("OwnsCarbine"), TEXT("OwnsDischarge"), TEXT("ArmoryAmmoCollected"), TEXT("CyborgMode"),
        TEXT("HunterMagazine"), TEXT("HunterReserve"), TEXT("BreakerMagazine"), TEXT("BreakerReserve"),
        TEXT("HeardWake"), TEXT("HeardMission"), TEXT("HeardPower"), TEXT("HeardPowerReady"),
        TEXT("HeardUpper"), TEXT("HeardArchive"), TEXT("HeardCourtyard"), TEXT("HeardCity"), TEXT("HeardRecovery")
    };
    FCheckpoint Result;
    for (const TCHAR Suffix : {TCHAR('A'), TCHAR('B')})
    {
        FString Source;
        TSharedPtr<FJsonObject> Data;
        int32 Format = 0, Rank = 0, Power = 0;
        if (!FFileHelper::LoadFileToString(Source, *Slot(Suffix)) ||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Source), Data) || !Data ||
            !Data->TryGetNumberField(TEXT("FormatVersion"), Format) || Format != 2 ||
            !Data->TryGetNumberField(TEXT("Milestone"), Rank) || Rank <= Result.Rank || Rank > 8 ||
            !Data->TryGetNumberField(TEXT("PowerOn"), Power) || Power != 1)
        {
            continue;
        }
        const bool bComplete = Algo::AllOf(Required, [&](const TCHAR* Key)
        {
            int32 Value;
            return Data->TryGetNumberField(Key, Value);
        });
        if (bComplete)
        {
            Result = {Rank, int32(Data->GetNumberField(TEXT("RepairCapacity"))),
                      int32(Data->GetNumberField(TEXT("OwnsCarbine")) != 0) +
                      int32(Data->GetNumberField(TEXT("OwnsDischarge")) != 0)};
        }
    }
    return Result;
}

bool ArchiveCheckpoints()
{
    IFileManager& Files = IFileManager::Get();
    const FString Archive = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("CampaignArchive"),
        FDateTime::UtcNow().ToString(TEXT("%Y%m%d_%H%M%S")) + TEXT("_") + FGuid::NewGuid().ToString(EGuidFormats::Short));
    TArray<TPair<FString, FString>> Moves;
    for (const TCHAR Suffix : {TCHAR('A'), TCHAR('B')})
    {
        const FString Original = Slot(Suffix);
        if (!Files.FileExists(*Original))
        {
            continue;
        }
        const FString Destination = FPaths::Combine(Archive, FPaths::GetCleanFilename(Original));
        if (!Files.MakeDirectory(*Archive, true) || !Files.Move(*Destination, *Original, false))
        {
            for (const auto& Moved : Moves)
            {
                if (!Files.Move(*Moved.Key, *Moved.Value, false))
                {
                    UE_LOG(LogTemp, Error, TEXT("Campaign slot remains archived at %s"), *Moved.Value);
                }
            }
            return false;
        }
        Moves.Emplace(Original, Destination);
    }
    return true;
}

TSharedRef<STextBlock> Label(const FText& Text, int32 Size = 22, FLinearColor Color = White, bool bBold = false)
{
    return SNew(STextBlock)
        .Text(Text)
        .Font(FCoreStyle::GetDefaultFontStyle(bBold ? TEXT("Bold") : TEXT("Regular"), Size))
        .ColorAndOpacity(Color)
        .ShadowColorAndOpacity(FLinearColor(0,0,0,.8f))
        .ShadowOffset(FVector2D(1,2));
}

const FButtonStyle& ButtonStyle(bool bPrimary)
{
    static const FButtonStyle Normal = FButtonStyle()
        .SetNormal(FSlateColorBrush(FLinearColor(.020f,.047f,.057f,.82f)))
        .SetHovered(FSlateColorBrush(FLinearColor(.047f,.135f,.151f,.98f)))
        .SetPressed(FSlateColorBrush(FLinearColor(.13f,.27f,.30f,1.f)))
        .SetDisabled(FSlateColorBrush(FLinearColor(.020f,.031f,.036f,.62f)))
        .SetNormalPadding(FMargin(18.f,8.f)).SetPressedPadding(FMargin(18.f,8.f));
    static const FButtonStyle Primary = FButtonStyle(Normal)
        .SetNormal(FSlateColorBrush(FLinearColor(.054f,.20f,.22f,.97f)))
        .SetHovered(FSlateColorBrush(FLinearColor(.10f,.32f,.35f,1.f)));
    return bPrimary ? Primary : Normal;
}

TSharedRef<SButton> Action(const FText& Text, FOnClicked OnClick, bool bEnabled = true, bool bPrimary = false)
{
    return SNew(SButton).IsEnabled(bEnabled).ButtonStyle(&ButtonStyle(bPrimary))
        .Cursor(EMouseCursor::Hand).OnClicked(OnClick)
        [Label(Text,22,bEnabled ? White : Ash,bPrimary)];
}

class SInspectSentinel final : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SInspectSentinel) {} SLATE_END_ARGS()

    void Construct(const FArguments&, AFinalProtocolFrontEnd* InMode)
    {
        Mode = InMode;
        SetCursor(EMouseCursor::GrabHand);
        ChildSlot[SNew(SBox)];
    }

    FReply OnMouseButtonDown(const FGeometry&, const FPointerEvent& Event) override
    {
        return Event.GetEffectingButton() == EKeys::LeftMouseButton ?
            FReply::Handled().CaptureMouse(AsShared()) : FReply::Unhandled();
    }

    FReply OnMouseMove(const FGeometry& Geometry, const FPointerEvent& Event) override
    {
        if (!HasMouseCapture() || !Mode.IsValid())
        {
            return FReply::Unhandled();
        }
        Mode->RotateSentinel(-Event.GetCursorDelta().X / Geometry.Scale * .42f);
        return FReply::Handled();
    }

    FReply OnMouseButtonUp(const FGeometry&, const FPointerEvent& Event) override
    {
        return Event.GetEffectingButton() == EKeys::LeftMouseButton && HasMouseCapture() ?
            FReply::Handled().ReleaseMouseCapture() : FReply::Unhandled();
    }

private:
    TWeakObjectPtr<AFinalProtocolFrontEnd> Mode;
};
}

class SFinalProtocolMenu final : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFinalProtocolMenu) {} SLATE_END_ARGS()

    void Construct(const FArguments&, AFinalProtocolFrontEnd* InMode)
    {
        Mode = InMode;
        Checkpoint = ReadCheckpoint();
        ChildSlot[SAssignNew(Container,SBox)];
        Show(Page::Home);
    }

    bool SupportsKeyboardFocus() const override { return true; }

    FReply OnKeyDown(const FGeometry&, const FKeyEvent& Event) override
    {
        if (Event.GetKey() == EKeys::Escape && Current != Page::Home)
        {
            return Go(Page::Home);
        }
        if (Event.GetKey() == EKeys::Left || Event.GetKey() == EKeys::Right)
        {
            if (Mode.IsValid())
            {
                Mode->RotateSentinel(Event.GetKey() == EKeys::Left ? -12.f : 12.f);
            }
            return FReply::Handled();
        }
        return FReply::Unhandled();
    }

private:
    enum class Page { Home, NewGame, Missions, Training, Statistics, Settings, Controls, Error };
    TWeakObjectPtr<AFinalProtocolFrontEnd> Mode;
    TSharedPtr<SBox> Container;
    FCheckpoint Checkpoint;
    Page Current = Page::Home;

    FReply Go(Page Next)
    {
        Show(Next);
        FSlateApplication::Get().SetKeyboardFocus(AsShared(), EFocusCause::SetDirectly);
        return FReply::Handled();
    }

    FReply Continue()
    {
        if (Mode.IsValid())
        {
            Mode->PlayCampaign();
        }
        return FReply::Handled();
    }

    FReply Replay()
    {
        if (Mode.IsValid())
        {
            Mode->PlayCampaign(true);
        }
        return FReply::Handled();
    }

    FReply StartNew()
    {
        return Checkpoint.Rank ? Go(Page::NewGame) : ConfirmNew();
    }

    FReply ConfirmNew()
    {
        return ArchiveCheckpoints() ? Continue() : Go(Page::Error);
    }

    FReply Training()
    {
        if (Mode.IsValid())
        {
            UGameplayStatics::OpenLevel(Mode.Get(), TrainingMap);
        }
        return FReply::Handled();
    }

    FReply Exit()
    {
        if (Mode.IsValid())
        {
            UKismetSystemLibrary::QuitGame(Mode.Get(), Mode->GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, false);
        }
        return FReply::Handled();
    }

    FReply Performance(float Percentage, float Limit)
    {
        UGameUserSettings* Settings = GEngine->GetGameUserSettings();
        Settings->SetResolutionScaleValueEx(Percentage);
        Settings->SetFrameRateLimit(Limit);
        Settings->ApplySettings(false);
        return Go(Page::Settings);
    }

    FReply ToggleWindow()
    {
        UGameUserSettings* Settings = GEngine->GetGameUserSettings();
        Settings->SetFullscreenMode(Settings->GetFullscreenMode() == EWindowMode::Windowed ?
            EWindowMode::WindowedFullscreen : EWindowMode::Windowed);
        Settings->ApplySettings(false);
        return Go(Page::Settings);
    }

    void Show(Page Next)
    {
        Current = Next;
        const bool bHome = Next == Page::Home;
        TSharedRef<SConstraintCanvas> Layout = SNew(SConstraintCanvas);
        auto Place = [&](const TSharedRef<SWidget>& Widget, float X, float Y, float W, float H)
        {
            Layout->AddSlot().Alignment(FVector2D(0,0)).Offset(FMargin(X,Y,W,H))[Widget];
        };

        TSharedRef<SVerticalBox> Titles = SNew(SVerticalBox);
        Titles->AddSlot().AutoHeight()[Label(LOCTEXT("Title","FINAL PROTOCOL"),60,White,true)];
        Titles->AddSlot().AutoHeight().HAlign(HAlign_Left).Padding(4,10,0,0)
            [SNew(SBox).WidthOverride(184).HeightOverride(2)[SNew(SBorder).BorderImage(&Accent)]];
        Place(Titles,890,51,655,125);

        if (Mode.IsValid())
        {
            Place(SNew(SInspectSentinel, Mode.Get()), 650,138,790,677);
        }
        Place(Label(LOCTEXT("Rotate","ЛКМ + движение мыши  ·  Повернуть Сентинела"),19,Ash),
              758,838,590,34);

        TSharedRef<SVerticalBox> Entries = SNew(SVerticalBox);
        auto Put = [&](const TSharedRef<SWidget>& W, float Gap = 8.f)
        {
            Entries->AddSlot().AutoHeight().Padding(0,0,0,Gap)[W];
        };
        auto Button = [&](const FText& Caption, FOnClicked Hit, bool Enabled = true, bool Primary = false)
        {
            Put(SNew(SBox).HeightOverride(52.f)[Action(Caption,Hit,Enabled,Primary)]);
        };
        auto PageButton = [&](const FText& Caption, Page Target)
        {
            Button(Caption,FOnClicked::CreateSP(this,&SFinalProtocolMenu::Go,Target));
        };
        auto Paragraph = [&](const FText& Caption)
        {
            TSharedRef<STextBlock> Text = Label(Caption,22,Ash);
            Text->SetAutoWrapText(true);
            Put(Text,18.f);
        };
        auto Heading = [&](const FText& Caption)
        {
            Put(Label(Caption,34,White,true),26);
        };
        auto Back = [&]() { PageButton(LOCTEXT("Back","Назад"),Page::Home); };

        switch (Next)
        {
        case Page::Home:
            Put(Label(LOCTEXT("Home","ГЛАВНОЕ МЕНЮ"),19,Blue,true),19);
            Button(LOCTEXT("Continue","Продолжить игру"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Continue),Checkpoint.Rank>0,Checkpoint.Rank>0);
            Button(LOCTEXT("New","Новая игра"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::StartNew),true,Checkpoint.Rank==0);
            PageButton(LOCTEXT("Missions","Выбор задания"),Page::Missions);
            PageButton(LOCTEXT("Training","Тренировка"),Page::Training);
            PageButton(LOCTEXT("Statistics","Статистика"),Page::Statistics);
            PageButton(LOCTEXT("Settings","Настройки"),Page::Settings);
            PageButton(LOCTEXT("Controls","Управление"),Page::Controls);
            Button(LOCTEXT("Exit","Выход"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Exit));
            break;
        case Page::NewGame:
            Heading(LOCTEXT("NewTitle","Новая игра"));
            Paragraph(LOCTEXT("NewInfo","Кампания начнётся с первой активации. Текущая контрольная точка будет перемещена в архив."));
            Button(LOCTEXT("Start","Начать заново"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::ConfirmNew),true,true);
            Back();
            break;
        case Page::Missions:
            Heading(LOCTEXT("MissionTitle","Выбор задания"));
            Paragraph(LOCTEXT("MissionReplay","Повтор запускается с капсулы. Сохранение кампании защищено."));
            Button(LOCTEXT("Frequency","Своя частота"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Replay),true,true);
            Button(LOCTEXT("SecondVoice","Второй голос в эфире"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Continue),Checkpoint.Rank==8);
            if (Checkpoint.Rank<8)
            {
                Paragraph(LOCTEXT("Locked","Заверши «Свою частоту», чтобы открыть следующее задание."));
            }
            Back();
            break;
        case Page::Training:
            Heading(LOCTEXT("TrainingTitle","Тренировка"));
            Paragraph(LOCTEXT("TrainingInfo","Два игровых оружия и три мишени. Esc возвращает в меню. Прогресс кампании на полигоне не меняется."));
            Button(LOCTEXT("TrainingStart","Войти на полигон"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Training),true,true);
            Back();
            break;
        case Page::Statistics:
            Heading(LOCTEXT("StatsTitle","Статистика"));
            if (!Checkpoint.Rank)
            {
                Paragraph(LOCTEXT("NoCheckpoint","Данные появятся после первой контрольной точки кампании."));
            }
            else
            {
                Put(Label(FText::Format(LOCTEXT("Rank","Контрольная точка   {0} / 8"),Checkpoint.Rank),22,Blue,true),19);
                Put(Label(FText::Format(LOCTEXT("Capacity","Прочность корпуса   {0}"),Checkpoint.Capacity)),17);
                Put(Label(FText::Format(LOCTEXT("Gear","Оружие   {0} / 2"),Checkpoint.Inventory)),17);
                Paragraph(Checkpoint.Rank==8 ? LOCTEXT("Finished","«Своя частота» завершена.") :
                                               LOCTEXT("Unfinished","«Своя частота» в процессе."));
            }
            Back();
            break;
        case Page::Settings:
        {
            Heading(LOCTEXT("SettingsTitle","Настройки"));
            const UGameUserSettings* Settings = GEngine->GetGameUserSettings();
            Put(Label(FText::Format(LOCTEXT("Limit","Лимит кадров   {0} FPS"),
                FMath::RoundToInt(Settings->GetFrameRateLimit())),22,Blue,true),18);
            Button(LOCTEXT("Balanced","Баланс  ·  85%  ·  60 FPS"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Performance,85.f,60.f));
            Button(LOCTEXT("Economy","Экономия  ·  70%  ·  30 FPS"),FOnClicked::CreateSP(this,&SFinalProtocolMenu::Performance,70.f,30.f));
            Button(Settings->GetFullscreenMode() == EWindowMode::Windowed ? LOCTEXT("Fullscreen","На весь экран") : LOCTEXT("Windowed","В оконный режим"),
                   FOnClicked::CreateSP(this,&SFinalProtocolMenu::ToggleWindow));
            Back();
            break;
        }
        case Page::Controls:
            Heading(LOCTEXT("ControlsTitle","Управление"));
            Paragraph(LOCTEXT("Movement","WASD — движение\nПробел — прыжок\nE — подобрать предмет\nF — взаимодействовать"));
            Paragraph(LOCTEXT("Weapons","ЛКМ — выстрел\nQ — сменить оружие\nR — перезарядить"));
            Back();
            break;
        case Page::Error:
            Heading(LOCTEXT("ArchiveErrorTitle","Сохранение"));
            Paragraph(LOCTEXT("ArchiveError","Не удалось переместить контрольные точки в архив. Текущая кампания остаётся доступной."));
            Back();
            break;
        }

        Place(SNew(SBorder).BorderImage(&Panel).Padding(24.f)[Entries],
              112,bHome ? 159.f : 193.f,438,bHome ? 571.f : 520.f);
        Container->SetContent(SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SBox).WidthOverride(1600.f).HeightOverride(900.f)[Layout]]);
    }
};

AFinalProtocolFrontEnd::AFinalProtocolFrontEnd()
{
    PrimaryActorTick.bCanEverTick = true;
    DefaultPawnClass = nullptr;
    HUDClass = nullptr;
}

void AFinalProtocolFrontEnd::StartPlay()
{
    Super::StartPlay();
    APlayerController* Controller = GetWorld()->GetFirstPlayerController();
    if (!GEngine->GameViewport || !Controller)
    {
        return;
    }
    TArray<AActor*> Actors;
    UGameplayStatics::GetAllActorsWithTag(this, TEXT("FrontEndSentinel"), Actors);
    if (!Actors.IsEmpty())
    {
        Sentinel = Actors[0];
    }
    UGameplayStatics::GetAllActorsWithTag(this, TEXT("FrontEndCamera"), Actors);
    if (!Actors.IsEmpty())
    {
        Controller->SetViewTarget(Actors[0]);
    }
    PrepareScenery();
    Menu = SNew(SFinalProtocolMenu,this);
    GEngine->GameViewport->AddViewportWidgetContent(Menu.ToSharedRef(),100);
    FInputModeUIOnly Input;
    Input.SetWidgetToFocus(Menu);
    Controller->SetInputMode(Input);
    Controller->bShowMouseCursor = true;
    FSlateApplication::Get().SetKeyboardFocus(Menu, EFocusCause::SetDirectly);
}

void AFinalProtocolFrontEnd::PrepareScenery()
{
    const TPair<FName,EScenery> Groups[] = {
        {TEXT("MenuDrone"), EScenery::Drone}, {TEXT("MenuRotor"), EScenery::Rotor},
        {TEXT("MenuSmoke"), EScenery::Smoke}, {TEXT("MenuScreen"), EScenery::Screen}
    };
    for (const auto& Group : Groups)
    {
        TArray<AActor*> Actors;
        UGameplayStatics::GetAllActorsWithTag(this,Group.Key,Actors);
        Actors.Sort([](const AActor& Left,const AActor& Right){return Left.GetFName().LexicalLess(Right.GetFName());});
        for (int32 Index=0; Index<Actors.Num(); ++Index)
        {
            AActor* Actor=Actors[Index];
            UMaterialInstanceDynamic* Material=nullptr;
            if (Group.Value==EScenery::Smoke || Group.Value==EScenery::Screen)
            {
                if (UStaticMeshComponent* Mesh=Actor->FindComponentByClass<UStaticMeshComponent>())
                {
                    Material=Mesh->CreateDynamicMaterialInstance(0);
                }
            }
            Scenery.Add({Actor,Material,Group.Value==EScenery::Rotor
                               ? Actor->GetRootComponent()->GetRelativeLocation() : Actor->GetActorLocation(),
                         Group.Value==EScenery::Rotor ? Actor->GetRootComponent()->GetRelativeRotation()
                                                      : Actor->GetActorRotation(),
                         Group.Value,Index*1.87f});
        }
    }
}

void AFinalProtocolFrontEnd::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    SceneryTime=FMath::Fmod(SceneryTime+DeltaSeconds,3600.f);
    for (const FScenery& Item : Scenery)
    {
        AActor* Actor=Item.Actor.Get();
        if (!Actor) {continue;}
        const float T=SceneryTime+Item.Offset;
        if (Item.Kind==EScenery::Drone)
        {
            const float Angle=T*(Item.Offset<1.f ? .24f : .19f);
            const float X=FMath::Sin(Angle), Direction=FMath::Cos(Angle);
            Actor->SetActorLocation(Item.Origin+FVector(X*104.f,27.f*FMath::Cos(Angle),8.f*FMath::Sin(T*.63f)));
            Actor->SetActorRotation(Item.Rotation+FRotator(4.f*Direction,58.f*Direction,(-8.f)*X));
        }
        else if (Item.Kind==EScenery::Rotor)
        {
            Actor->GetRootComponent()->SetRelativeRotation(Item.Rotation+FRotator(0,FMath::Fmod(T*870.f,360.f),0));
        }
        else if (UMaterialInstanceDynamic* Material=Item.Material.Get())
        {
            if (Item.Kind==EScenery::Smoke)
            {
                Actor->SetActorLocation(Item.Origin+FVector(18.f*FMath::Sin(T*.18f),0,6.f*FMath::Sin(T*.31f)));
                Material->SetScalarParameterValue(TEXT("Strength"),.26f+.09f*FMath::Sin(T*.64f));
            }
            else
            {
                const float Signal=FMath::Sin(T*1.65f)+.14f*FMath::Sin(T*13.7f);
                Material->SetScalarParameterValue(TEXT("Strength"),FMath::GetMappedRangeValueClamped(
                    FVector2D(-1,1),FVector2D(.22f,1.5f),Signal));
            }
        }
    }
}


void AFinalProtocolFrontEnd::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Menu && GEngine && GEngine->GameViewport)
    {
        GEngine->GameViewport->RemoveViewportWidgetContent(Menu.ToSharedRef());
    }
    Menu.Reset();
    Super::EndPlay(Reason);
}

void AFinalProtocolFrontEnd::RotateSentinel(float Degrees)
{
    if (AActor* Actor = Sentinel.Get())
    {
        Actor->AddActorWorldRotation(FRotator(0,Degrees,0));
    }
}

void AFinalProtocolFrontEnd::PlayCampaign(bool bReplay)
{
    if (APlayerController* Controller = GetWorld()->GetFirstPlayerController())
    {
        Controller->SetInputMode(FInputModeGameOnly());
        Controller->bShowMouseCursor = false;
    }
    UGameplayStatics::OpenLevel(this,LabMap,true,bReplay ? TEXT("FPReplay=1") : TEXT(""));
}

#undef LOCTEXT_NAMESPACE


