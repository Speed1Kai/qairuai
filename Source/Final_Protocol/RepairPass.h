#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RepairPass.generated.h"

class AActor;
class APawn;
class UAudioComponent;

UCLASS()
class UFinalProtocolRepairPass : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Final Protocol|Repair")
    static bool BeginOrConsumeSignalTuning(AActor* Mission, APawn* Player, int32 Circuit, FVector Panel);

    UFUNCTION(BlueprintCallable, Category="Final Protocol|Audio")
    static void RefreshGuideContext(AActor* Guide, APawn* Player);

    UFUNCTION(BlueprintCallable, Category="Final Protocol|Audio")
    static void BalanceStoryVoices(AActor* Mission, float DeltaSeconds);
};



