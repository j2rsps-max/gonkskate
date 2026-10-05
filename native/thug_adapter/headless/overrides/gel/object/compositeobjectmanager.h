#pragma once
#include <gel/object/basecomponent.h>
namespace Headless { void called(const char*); }
namespace Obj {
class CCompositeObjectManager {
public:
    static CCompositeObjectManager* Instance() {static CCompositeObjectManager manager;return &manager;}
    CBaseComponent* GetFirstComponentByType(uint32) {
        Headless::called("GetFirstComponentByType:empty-world");
        return nullptr;
    }
};
}
