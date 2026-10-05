#include <iostream>
#include <type_traits>
#include "gonkskate_thug.h"
#include "gonkskate_thug_params.h"

static_assert(std::is_standard_layout<GonkVec3>::value, "GonkVec3 must be standard layout");
static_assert(sizeof(GonkVec3) == 12, "GonkVec3 ABI size changed");
static_assert(sizeof(uint8_t) == 1, "Unexpected uint8_t size");

int main()
{
    GonkVec3 v{1.0f, 2.0f, 3.0f};
    GonkThugInput input{};
    input.ollie = 1;

    std::cout << "GonkSkate native ABI smoke test\n";
    std::cout << "sizeof(GonkVec3)=" << sizeof(GonkVec3) << "\n";
    std::cout << "sizeof(GonkThugInput)=" << sizeof(GonkThugInput) << "\n";
    std::cout << "sizeof(GonkThugPlayerState)=" << sizeof(GonkThugPlayerState) << "\n";
    std::cout << "vec=" << v.x << "," << v.y << "," << v.z << "\n";
    std::cout << "ollie=" << static_cast<int>(input.ollie) << "\n";
    std::cout << "ABI_SMOKE_PASS\n";
    return 0;
}
