#include "RepairPass.h"

#include "Components/AudioComponent.h"
#include "Components/PrimitiveComponent.h"
#include "UObject/UnrealType.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"
#include "Brushes/SlateColorBrush.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "SignalTuning"

namespace
{
const FLinearColor Ice(.48f,.90f,.91f);
const FLinearColor Amber(1.f,.69f,.30f);
const FLinearColor Paper(.93f,.96f,.95f);
const FSlateColorBrush Frame(FLinearColor(.022f,.036f,.040f,.985f));
const FSlateColorBrush DialFace(FLinearColor(.041f,.066f,.069f,1.f));
const FSlateColorBrush ScopeFace(FLinearColor(.013f,.036f,.036f,1.f));

UObject* GuideObject(UObject* Object,const TCHAR* Name);

class SSignalTrace : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SSignalTrace) {}
        SLATE_ATTRIBUTE(float, Frequency)
        SLATE_ATTRIBUTE(float, Trim)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args) { Frequency=Args._Frequency; Trim=Args._Trim; }
    virtual FVector2D ComputeDesiredSize(float) const override { return {640,104}; }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
        FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
    {
        const FVector2f Size(Geometry.GetLocalSize());
        const auto Paint=Geometry.ToPaintGeometry();
        FSlateDrawElement::MakeBox(Out,Layer,Paint,&ScopeFace,ESlateDrawEffect::None,FLinearColor(.015f,.044f,.042f));
        for (int32 X=24; X<Size.X; X+=24)
        {
            FSlateDrawElement::MakeLines(Out,Layer+1,Paint,TArray<FVector2f>{{float(X),0},{float(X),Size.Y}},
                ESlateDrawEffect::None,FLinearColor(.12f,.24f,.23f,.65f),false);
        }
        for (int32 Y=16; Y<Size.Y; Y+=16)
        {
            FSlateDrawElement::MakeLines(Out,Layer+1,Paint,TArray<FVector2f>{{0,float(Y)},{Size.X,float(Y)}},
                ESlateDrawEffect::None,FLinearColor(.12f,.24f,.23f,.65f),false);
        }
        for (int32 Trace=0; Trace<2; ++Trace)
        {
            TArray<FVector2f> Points;
            Points.Reserve(161);
            const float Cycles=Trace==0 ? 3.f : 3.f+Frequency.Get()*0.115f;
            const float Phase=Trace==0 ? 0.f : Trim.Get()*0.30f;
            const float Noise=Trace==0 ? 0.f : FMath::Min(1.f,FMath::Abs(Trim.Get())/7.f);
            const float Sweep=FMath::Fmod(float(FSlateApplication::Get().GetCurrentTime()),20.f)*2.f*PI;
            for (int32 Index=0; Index<=160; ++Index)
            {
                const float U=float(Index)/160.f;
                const float Angle=U*2.f*PI*Cycles-Sweep+Phase;
                const float Wave=FMath::Sin(Angle)+Noise*.16f*FMath::Sin(Angle*5.f+U*33.f);
                Points.Add({U*Size.X,(.5f+.28f*Wave)*Size.Y});
            }
            FSlateDrawElement::MakeLines(Out,Layer+2+Trace,Paint,Points,ESlateDrawEffect::None,
                Trace==0 ? FLinearColor(.45f,.60f,.50f) : Ice,true,Trace==0 ? 1.5f : 2.f);
        }
        return Layer+3;
    }
private:
    TAttribute<float> Frequency;
    TAttribute<float> Trim;
};

class SSignalDial : public SLeafWidget
{
public:
    DECLARE_DELEGATE_OneParam(FInt32Delegate, int32);

    SLATE_BEGIN_ARGS(SSignalDial) {}
        SLATE_ATTRIBUTE(float, Position)
        SLATE_EVENT(FInt32Delegate, OnTurn)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args) { Position=Args._Position; OnTurn=Args._OnTurn; }
    virtual FVector2D ComputeDesiredSize(float) const override { return {134,134}; }
    virtual FReply OnMouseButtonDown(const FGeometry&, const FPointerEvent& Event) override
    {
        if (Event.GetEffectingButton()!=EKeys::LeftMouseButton)
        {
            return FReply::Unhandled();
        }
        Travel=0;
        return FReply::Handled().CaptureMouse(SharedThis(this));
    }
    virtual FReply OnMouseButtonUp(const FGeometry&, const FPointerEvent& Event) override
    {
        return HasMouseCapture() && Event.GetEffectingButton()==EKeys::LeftMouseButton
            ? FReply::Handled().ReleaseMouseCapture() : FReply::Unhandled();
    }
    virtual FReply OnMouseWheel(const FGeometry&, const FPointerEvent& Event) override
    {
        OnTurn.ExecuteIfBound(Event.GetWheelDelta()>0 ? 1 : -1);
        return FReply::Handled();
    }
    virtual FReply OnMouseMove(const FGeometry&, const FPointerEvent& Event) override
    {
        if (!HasMouseCapture())
        {
            return FReply::Unhandled();
        }
        const FVector2D Delta=Event.GetCursorDelta();
        Travel+=Delta.X-Delta.Y;
        const int32 Steps=FMath::TruncToInt(Travel/13.f);
        if (Steps)
        {
            Travel-=Steps*13.f;
            OnTurn.ExecuteIfBound(Steps);
        }
        return FReply::Handled();
    }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
        FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const override
    {
        const FVector2f Size(Geometry.GetLocalSize());
        const FVector2f Center=Size*.5f;
        const auto Paint=Geometry.ToPaintGeometry();
        FSlateDrawElement::MakeBox(Out,Layer,Paint,&DialFace,ESlateDrawEffect::None,FLinearColor(.054f,.077f,.078f));
        auto Line=[&](const TArray<FVector2f>& Points, FLinearColor Color, float Width)
        {
            FSlateDrawElement::MakeLines(Out,Layer+1,Paint,Points,ESlateDrawEffect::None,Color,true,Width);
        };
        auto Point=[&](float Degrees,float Radius)
        {
            const float Radians=FMath::DegreesToRadians(Degrees);
            return Center+FVector2f(FMath::Sin(Radians),-FMath::Cos(Radians))*Radius;
        };
        for (const float Radius : {37.f,40.f,48.f})
        {
            TArray<FVector2f> Ring;
            for (int32 Index=0; Index<=64; ++Index)
            {
                Ring.Add(Point(float(Index)*360.f/64.f,Radius));
            }
            Line(Ring,FLinearColor(.25f,.35f,.35f),Radius==40.f ? 4.f : 1.f);
        }
        for (int32 Tick=0; Tick<=12; ++Tick)
        {
            const float Angle=-135.f+Tick*22.5f;
            Line({Point(Angle,52.f),Point(Angle,Tick%3==0 ? 62.f : 57.f)},
                Tick%3==0 ? Ice : FLinearColor(.32f,.48f,.46f),1.f);
        }
        const float Needle=FMath::Lerp(-135.f,135.f,Position.Get());
        Line({Point(Needle,12),Point(Needle,36)},Amber,4.f);
        return Layer+1;
    }

private:
    TAttribute<float> Position;
    FInt32Delegate OnTurn;
    double Travel=0;
};

DECLARE_DELEGATE_TwoParams(FOnSignalDialChange,bool,float);

class SSignalTuning : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SSignalTuning) {}
        SLATE_ARGUMENT(bool, Telephone)
        SLATE_EVENT(FSimpleDelegate, OnConfirm)
        SLATE_EVENT(FSimpleDelegate, OnCancel)
        SLATE_EVENT(FOnSignalDialChange, OnAdjust)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        Confirm=Args._OnConfirm;
        Cancel=Args._OnCancel;
        Adjust=Args._OnAdjust;
        ChannelTarget=Args._Telephone ? 92 : 108;
        TrimTarget=Args._Telephone ? 5 : -4;
        Channel=Args._Telephone ? 105 : 96;
        Trim=Args._Telephone ? -6 : 7;
        auto Caption=[](FText Text, int32 Size, FLinearColor Color)
        {
            return SNew(STextBlock).Text(Text)
                .Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),Size)).ColorAndOpacity(Color);
        };
        auto Knob=[&](FText Label,bool bFrequency)
        {
            return SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0,0,0,3)
                [Caption(Label,15,Ice)]
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                [
                    SNew(SSignalDial)
                    .Position_Lambda([this,bFrequency]()
                    {
                        return bFrequency ? (Channel-84)/30.f : (Trim+12)/24.f;
                    })
                    .OnTurn_Lambda([this,bFrequency](int32 Amount){Turn(bFrequency,Amount);})
                ]
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0,6,0,0)
                [
                    SNew(STextBlock).ColorAndOpacity(Paper)
                    .Font(FCoreStyle::GetDefaultFontStyle(TEXT("Bold"),21))
                    .Text_Lambda([this,bFrequency]()
                    {
                        return FText::FromString(bFrequency ? FString::Printf(TEXT("%d кГц"),Channel)
                                                            : FString::Printf(TEXT("%+d"),Trim));
                    })
                ];
        };
        const FText Name=Args._Telephone ? LOCTEXT("Telephone","ТЕЛЕФОННАЯ СТАНЦИЯ / МЕСТНАЯ ЛИНИЯ")
                                           : LOCTEXT("Station","СТАНЦИЯ 07 / ПЕРЕДАТЧИК");
        ChildSlot
        [
            SNew(SOverlay)
            + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(32,38)
            [
                SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
                [
                    SNew(SBox).WidthOverride(688)
                    [
                        SNew(SBorder).BorderImage(&Frame).Padding(24)
                        [
                            SNew(SVerticalBox)
                            + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Caption(Name,21,Ice)]
                            + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
                            [Caption(FText::Format(LOCTEXT("Prompt","Выставь {0} кГц и совмести обе линии на экране."),
                                FText::AsNumber(ChannelTarget)),16,Paper)]
                            + SVerticalBox::Slot().AutoHeight()
                            [
                                SNew(SSignalTrace)
                                .Frequency_Lambda([this](){return float(Channel-ChannelTarget);})
                                .Trim_Lambda([this](){return float(Trim-TrimTarget);})
                            ]
                            + SVerticalBox::Slot().AutoHeight().Padding(0,18,0,12)
                            [
                                SNew(SHorizontalBox)
                                + SHorizontalBox::Slot().FillWidth(1.f)[Knob(LOCTEXT("Channel","ЧАСТОТА"),true)]
                                + SHorizontalBox::Slot().FillWidth(1.f)[Knob(LOCTEXT("Phase","ФАЗА"),false)]
                                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                                [
                                    SNew(STextBlock).ColorAndOpacity_Lambda([this](){return FSlateColor(Ready() ? Ice : Amber);})
                                    .Font(FCoreStyle::GetDefaultFontStyle(TEXT("Bold"),17))
                                    .Text_Lambda([this]()
                                    {
                                        if (Ready()) {return LOCTEXT("Locked","СИГНАЛ УСТОЙЧИВ");}
                                        return Channel==ChannelTarget ? LOCTEXT("PhaseStatus","СВЕДИ ФАЗУ")
                                                                       : LOCTEXT("ChannelStatus","НАЙДИ ЧАСТОТУ");
                                    })
                                ]
                            ]
                            + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,12)
                            [Caption(LOCTEXT("Controls","Поверни ручки мышью или колёсиком   ·   Esc — отойти"),15,Paper)]
                            + SVerticalBox::Slot().AutoHeight()
                            [
                                SNew(SHorizontalBox)
                                + SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)
                                [
                                    SNew(SButton).IsEnabled_Lambda([this](){return Ready();})
                                    .ContentPadding(FMargin(17,9)).OnClicked_Lambda([this](){return Apply();})
                                    [Caption(LOCTEXT("Apply","Включить передачу"),16,Paper)]
                                ]
                                + SHorizontalBox::Slot().AutoWidth()
                                [
                                    SNew(SButton).ContentPadding(FMargin(17,9)).OnClicked_Lambda([this](){return Leave();})
                                    [Caption(LOCTEXT("Cancel","Отойти"),16,Paper)]
                                ]
                            ]
                        ]
                    ]
                ]
            ]
        ];
    }
    virtual bool SupportsKeyboardFocus() const override {return true;}
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent& Event) override
    {
        if (Event.GetKey()==EKeys::Escape) {return Leave();}
        if (Event.GetKey()==EKeys::Enter) {return Apply();}
        if (Event.GetKey()==EKeys::Left || Event.GetKey()==EKeys::Right)
        {
            Turn(true,Event.GetKey()==EKeys::Right ? 1 : -1);
            return FReply::Handled();
        }
        if (Event.GetKey()==EKeys::Up || Event.GetKey()==EKeys::Down)
        {
            Turn(false,Event.GetKey()==EKeys::Up ? 1 : -1);
            return FReply::Handled();
        }
        return FReply::Unhandled();
    }
    virtual FReply OnMouseButtonDown(const FGeometry&,const FPointerEvent&) override
    {
        return FReply::Handled();
    }
    bool Ready() const {return Channel==ChannelTarget && Trim==TrimTarget;}

private:
    void Turn(bool bFrequency,int32 Amount)
    {
        if (bFrequency) {Channel=FMath::Clamp(Channel+Amount,84,114);}
        else {Trim=FMath::Clamp(Trim+Amount,-12,12);}
        Adjust.ExecuteIfBound(bFrequency,bFrequency ? (Channel-84)/30.f : (Trim+12)/24.f);
    }
    FReply Apply()
    {
        if (Ready()) {Confirm.ExecuteIfBound();}
        return FReply::Handled();
    }
    FReply Leave()
    {
        Cancel.ExecuteIfBound();
        return FReply::Handled();
    }
    FOnSignalDialChange Adjust;
    FSimpleDelegate Confirm;
    FSimpleDelegate Cancel;
    int32 Channel=0, Trim=0, ChannelTarget=0, TrimTarget=0;
};

struct FSignalSession
{
    TWeakObjectPtr<AActor> Mission;
    TWeakObjectPtr<APawn> Pawn;
    TWeakObjectPtr<APlayerController> Controller;
    TWeakObjectPtr<UGameViewportClient> Viewport;
    TSharedPtr<SSignalTuning> Widget;
    FVector Panel=FVector::ZeroVector;
    int32 Circuit=0;
    bool bConfirmed=false;
    bool bConsumed=false;
    bool bOldCursor=false;

    void Close()
    {
        if (Viewport.IsValid() && Widget)
        {
            Viewport->RemoveViewportWidgetContent(Widget.ToSharedRef());
        }
        if (APlayerController* PC=Controller.Get())
        {
            PC->SetIgnoreMoveInput(false);
            PC->SetIgnoreLookInput(false);
            PC->bShowMouseCursor=bOldCursor;
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
};

TMap<TWeakObjectPtr<UWorld>,TSharedPtr<FSignalSession>> Sessions;
FDelegateHandle WorldCleanup;

void Finish(const TWeakObjectPtr<UWorld> World,bool bConfirm)
{
    TSharedPtr<FSignalSession> Session=Sessions.FindRef(World);
    if (!Session)
    {
        return;
    }
    Session->Close();
    if (bConfirm && Session->Mission.IsValid() && Session->Pawn.IsValid()
        && Session->Controller.IsValid() && Session->Controller->GetPawn()==Session->Pawn.Get()
        && FVector::DistSquared(Session->Pawn->GetActorLocation(),Session->Panel)<FMath::Square(235.f))
    {
        Session->bConfirmed=true;
        if (UFunction* Apply=Session->Mission->FindFunction(TEXT("RequestRecovery")); Apply && Apply->ParmsSize==0)
        {
            Session->Mission->ProcessEvent(Apply,nullptr);
        }
        if (Session->bConsumed)
        {
            USoundBase* Click=LoadObject<USoundBase>(nullptr,
                TEXT("/Game/Combat/CyborgModes/S_ModeSelect.S_ModeSelect"));
            UGameplayStatics::PlaySound2D(Session->Mission.Get(),Click,.65f);
            UE_LOG(LogTemp,Display,TEXT("Final Protocol signal tuned circuit=%d"),Session->Circuit);
        }
    }
    Sessions.Remove(World);
}
}

bool UFinalProtocolRepairPass::BeginOrConsumeSignalTuning(AActor* Mission,APawn* Player,int32 Circuit,FVector Panel)
{
    if (!IsValid(Mission) || !IsValid(Player) || Mission->GetWorld()!=Player->GetWorld())
    {
        return false;
    }
    const TWeakObjectPtr<UWorld> World=Mission->GetWorld();
    if (const TSharedPtr<FSignalSession> Existing=Sessions.FindRef(World))
    {
        if (Existing->bConfirmed && !Existing->bConsumed && Existing->Mission.Get()==Mission
            && Existing->Pawn.Get()==Player && Existing->Circuit==Circuit)
        {
            Existing->bConsumed=true;
            return true;
        }
        return false;
    }
    APlayerController* PC=Cast<APlayerController>(Player->GetController());
    UGameViewportClient* Viewport=World.IsValid() ? World->GetGameViewport() : nullptr;
    if (!PC || !PC->IsLocalController() || !Viewport || !FSlateApplication::IsInitialized())
    {
        return false;
    }
    if (!WorldCleanup.IsValid())
    {
        WorldCleanup=FWorldDelegates::OnWorldCleanup.AddLambda([](UWorld* Leaving,bool,bool)
        {
            Finish(TWeakObjectPtr<UWorld>(Leaving),false);
        });
    }
    const TSharedRef<FSignalSession> Session=MakeShared<FSignalSession>();
    Session->Mission=Mission;
    Session->Pawn=Player;
    Session->Controller=PC;
    Session->Viewport=Viewport;
    Session->Panel=Panel;
    Session->Circuit=Circuit;
    Session->bOldCursor=PC->bShowMouseCursor;
    const TWeakObjectPtr<AActor> TuningOwner=Mission;
    Session->Widget=SNew(SSignalTuning).Telephone(Circuit==1)
        .OnAdjust_Lambda([TuningOwner,Circuit](bool bFrequency,float Fraction)
        {
            const FString Name=FString::Printf(TEXT("%s%d"),Circuit==1 ? TEXT("TunePhone") : TEXT("Tune07"),bFrequency ? 0 : 1);
            if (USceneComponent* Dial=Cast<USceneComponent>(GuideObject(TuningOwner.Get(),*Name)))
            {
                const FQuat Base=FRotator(90,Circuit==1 ? 90.f : 0.f,0).Quaternion();
                Dial->SetRelativeRotation(Base*FQuat(FVector::UpVector,FMath::DegreesToRadians(-135.f+270.f*Fraction)));
            }
        })
        .OnConfirm_Lambda([World](){Finish(World,true);})
        .OnCancel_Lambda([World](){Finish(World,false);});
    Sessions.Add(World,Session);
    Viewport->AddViewportWidgetContent(Session->Widget.ToSharedRef(),125);
    PC->SetIgnoreMoveInput(true);
    PC->SetIgnoreLookInput(true);
    PC->bShowMouseCursor=true;
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(Session->Widget);
    Mode.SetHideCursorDuringCapture(false);
    PC->SetInputMode(Mode);
    UE_LOG(LogTemp,Display,TEXT("Final Protocol signal panel opened circuit=%d"),Circuit);
    return false;
}

namespace
{
template<class Field>
Field* GuideProperty(UObject* Object,const TCHAR* Name)
{
    return Object ? FindFProperty<Field>(Object->GetClass(),Name) : nullptr;
}

UObject* GuideObject(UObject* Object,const TCHAR* Name)
{
    if (const FObjectPropertyBase* Property=GuideProperty<FObjectPropertyBase>(Object,Name))
    {
        return Property->GetObjectPropertyValue_InContainer(Object);
    }
    return nullptr;
}

bool GuideFlag(UObject* Object,const TCHAR* Name)
{
    if (const FBoolProperty* Property=GuideProperty<FBoolProperty>(Object,Name))
    {
        return Property->GetPropertyValue_InContainer(Object);
    }
    return false;
}

int32 GuideInt(UObject* Object,const TCHAR* Name,int32 Missing=-1)
{
    if (const FIntProperty* Property=GuideProperty<FIntProperty>(Object,Name))
    {
        return Property->GetPropertyValue_InContainer(Object);
    }
    return Missing;
}

void ExpireCue(AActor* Guide,const TCHAR* Heard,int32 Line)
{
    const FBoolProperty* Delivered=GuideProperty<FBoolProperty>(Guide,Heard);
    if (Delivered)
    {
        Delivered->SetPropertyValue_InContainer(Guide,true);
    }
    const FIntProperty* Last=GuideProperty<FIntProperty>(Guide,TEXT("LastLine"));
    if (!Last || Last->GetPropertyValue_InContainer(Guide)!=Line)
    {
        return;
    }
    Last->SetPropertyValue_InContainer(Guide,-1);
    for (const TCHAR* Name : {TEXT("BusyUntil"),TEXT("VisorGuideUntil")})
    {
        if (const FDoubleProperty* Clock=GuideProperty<FDoubleProperty>(Guide,Name))
        {
            Clock->SetPropertyValue_InContainer(Guide,0.0);
        }
    }
    if (UAudioComponent* Voice=Cast<UAudioComponent>(GuideObject(Guide,TEXT("Voice"))))
    {
        Voice->Stop();
    }
    UE_LOG(LogTemp,Verbose,TEXT("Final Protocol expired Omega line %d"),Line);
}
}

void UFinalProtocolRepairPass::RefreshGuideContext(AActor* Guide,APawn* Player)
{
    if (!IsValid(Guide) || !IsValid(Player))
    {
        return;
    }
    const FVector Location=Player->GetActorLocation();
    UObject* Power=GuideObject(Guide,TEXT("PowerSource"));
    UObject* Lift=GuideObject(Player,TEXT("DemoIntroLift"));
    const UPrimitiveComponent* Zone=Cast<UPrimitiveComponent>(GuideObject(Lift,TEXT("BoardingZone")));
    const bool InCabin=(Lift && Player->GetAttachParentActor()==Lift) || (Zone && Zone->IsOverlappingActor(Player));
    const int32 Stage=GuideInt(GuideObject(Guide,TEXT("DemoStorySpeaker")),TEXT("Stage"));
    const bool bOutside=GuideFlag(Player,TEXT("DemoReachedSurface")) || (Location.Y>3040. && Location.Z>2100.);
    const bool bAboveBasement=Location.Z>950.;
    if (bOutside || Stage>=1)
    {
        ExpireCue(Guide,TEXT("HeardWake"),0);
        ExpireCue(Guide,TEXT("HeardMission"),1);
    }
    if (GuideFlag(Power,TEXT("bBuildingPowered")) || bAboveBasement)
    {
        ExpireCue(Guide,TEXT("HeardPower"),2);
    }
    if (InCabin || bAboveBasement)
    {
        ExpireCue(Guide,TEXT("HeardPowerReady"),3);
    }
    if (bOutside || (bAboveBasement && Location.Y>1580.))
    {
        ExpireCue(Guide,TEXT("HeardUpper"),4);
    }
    if (bOutside)
    {
        ExpireCue(Guide,TEXT("HeardArchive"),5);
    }
    if (Location.Y>=21950. || Stage>=1)
    {
        ExpireCue(Guide,TEXT("HeardCourtyard"),6);
    }
    if (Stage>=1)
    {
        ExpireCue(Guide,TEXT("HeardCity"),7);
    }
}


void UFinalProtocolRepairPass::BalanceStoryVoices(AActor* Mission,float DeltaSeconds)
{
    UAudioComponent* Guide=Cast<UAudioComponent>(GuideObject(GuideObject(Mission,TEXT("Guide")),TEXT("Voice")));
    UAudioComponent* Story=Cast<UAudioComponent>(GuideObject(Mission,TEXT("Voice")));
    UAudioComponent* Radio=Cast<UAudioComponent>(GuideObject(Mission,TEXT("ExternalRadioVoice")));
    const bool bExternal=Radio && Radio->IsPlaying();
    for (UAudioComponent* Speaker : {Guide,Story})
    {
        if (Speaker)
        {
            const float Target=bExternal ? (Speaker==Guide ? .19f : .25f) : (Speaker==Guide ? .95f : 1.f);
            const float Volume=FMath::FInterpTo(Speaker->VolumeMultiplier,Target,DeltaSeconds,bExternal ? 28.f : 9.f);
            if (!FMath::IsNearlyEqual(Volume,Speaker->VolumeMultiplier,.001f))
            {
                Speaker->SetVolumeMultiplier(Volume);
            }
        }
    }
}

#undef LOCTEXT_NAMESPACE






