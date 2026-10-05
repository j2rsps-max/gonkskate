#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct GonkThugParamProvider {
    void* user;
    uint8_t (*get_float)(void* user, const char* name, float* out_value);
    uint8_t (*get_int)(void* user, const char* name, int32_t* out_value);
} GonkThugParamProvider;
#ifdef __cplusplus
}
#endif
