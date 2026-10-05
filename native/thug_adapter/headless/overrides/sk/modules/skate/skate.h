#pragma once
#include <core/defines.h>
enum { SKATE_TYPE_SKATER = 1 };
namespace Obj { class CSkaterCareer; class CRailManager; class CTrickObjectManager; }
namespace Mdl {
struct HeadlessControllerPreferences { bool AutoKickOn; };
// Environmental host facade. Core skating code remains upstream.
class Skate {
public:
    static Skate* Instance();
    Obj::CSkaterCareer* GetCareer();
    Obj::CRailManager* GetRailManager();
    bool ShouldBeAbsentNode(Script::CStruct*);
    Obj::CTrickObjectManager* GetTrickObjectManager();
    HeadlessControllerPreferences mp_controller_preferences[1];
};
}
