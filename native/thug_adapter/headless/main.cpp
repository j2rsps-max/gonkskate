#include <sk/components/skatercorephysicscomponent.h>
#include <sk/components/skaterstatecomponent.h>
#include <sk/components/skaterrotatecomponent.h>
#include <sk/components/skaterscorecomponent.h>
#include <sk/components/skaterbalancetrickcomponent.h>
#include <gel/components/inputcomponent.h>
#include <gel/components/trickcomponent.h>
#include <gel/components/triggercomponent.h>
#include <gel/components/movablecontactcomponent.h>
#include <gel/components/walkcomponent.h>
#include <gel/scripting/struct.h>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <map>
namespace Headless {extern uint64 frame,collisions,lookups;extern std::map<std::string,uint64> peripheral;}
struct Input {int push=0,crouch=0,left=0,right=0,brake=0;};
int main(int argc,char** argv) {
    bool probe=argc==2 && std::string(argv[1])=="--probe-peripheral";
    bool pipe=argc==2 && std::string(argv[1])=="--pipe";
    std::string scenario=argc==3 && std::string(argv[1])=="--scenario" ? argv[2] : "ollie";
    if((argc!=1 && !pipe && !probe && argc!=3) || (argc==3 && std::string(argv[1])!="--scenario") ||
       (scenario!="ollie" && scenario!="idle" && scenario!="steer" && scenario!="soak")) {
        std::cerr<<"Usage: gonkskate-thug-test [--pipe | --scenario idle|ollie|steer|soak]\n";return 2;
    }
    auto skater=new Obj::CSkater;
    skater->AddComponent(new Obj::CSkaterStateComponent);
    skater->AddComponent(new Obj::CInputComponent);
    skater->AddComponent(new Obj::CSkaterScoreComponent);
    skater->AddComponent(new Obj::CTrickComponent);
    auto control=new Obj::CSkaterPhysicsControlComponent;skater->AddComponent(control);
    auto core=new Obj::CSkaterCorePhysicsComponent;skater->AddComponent(core);
    auto rotate=new Obj::CSkaterRotateComponent;skater->AddComponent(rotate);
    skater->AddComponent(new Obj::CTriggerComponent);
    skater->AddComponent(new Obj::CWalkComponent);
    skater->AddComponent(new Obj::CSkaterBalanceTrickComponent);
    skater->AddComponent(new Obj::CMovableContactComponent);
    skater->AddComponent(new Obj::CSkaterSoundComponent);
    Script::CStruct params;
    for(Obj::CBaseComponent* c=GetSkaterStateComponentFromObject(skater);c;c=c->GetNext()) c->InitFromStructure(&params);
    core->Finalize();rotate->Finalize();core->Reset();
    if(probe) {Obj::CManual manual;manual.DoManualPhysics();return 1;}
    std::cout<<std::setprecision(9)<<"frame,push,crouch,left,right,brake,x,y,z,vx,vy,vz,fx,fy,fz,state,terrain,rail,landed,queries,lookups,adapter_calls\n"<<std::flush;
    for(Headless::frame=0;pipe || Headless::frame<(scenario=="soak" ? 10000:360);++Headless::frame) {
        Input input;
        if(pipe) {
            std::string line;if(!std::getline(std::cin,line)) break;
            std::istringstream row(line);std::string extra;
            if(!(row>>input.push>>input.crouch>>input.left>>input.right>>input.brake) || row>>extra ||
               input.push<0 || input.push>1 || input.crouch<0 || input.crouch>1 || input.left<0 || input.left>1 ||
               input.right<0 || input.right>1 || input.brake<0 || input.brake>1) {std::cerr<<"Invalid input frame "<<Headless::frame<<'\n';return 2;}
        } else if(scenario!="idle") {
            input.push=Headless::frame>=30;
            input.crouch=Headless::frame>=150 && Headless::frame<165;
            if(scenario=="steer") {input.left=Headless::frame>=60 && Headless::frame<120;input.right=Headless::frame>=240 && Headless::frame<270;input.brake=Headless::frame>=300;input.push=Headless::frame>=30 && Headless::frame<300;}
            if(scenario=="soak") {input.crouch=Headless::frame%180>=120 && Headless::frame%180<150;input.left=Headless::frame%600>=200 && Headless::frame%600<300;}
        }
        auto& pad=GetInputComponentFromObject(skater)->GetControlPad();
        pad.m_square.Update(input.push ? 255:0);
        pad.m_x.Update(input.crouch ? 255:0);
        pad.m_left.Update(input.left ? 255:0);
        pad.m_right.Update(input.right ? 255:0);
        pad.m_down.Update(input.brake ? 255:0);
        auto before_queries=Headless::collisions,before_lookups=Headless::lookups;
        uint64 before_calls=0;for(auto& p:Headless::peripheral) before_calls+=p.second;
        control->Update();core->Update();rotate->Update();
        // Original SkaterAdjustPhysics Update stores this after core/rotate.
        // Its rendered/moving-object adjustments are outside this flat-floor profile.
        skater->m_old_pos=skater->m_pos;
        uint64 calls=0;for(auto& p:Headless::peripheral) calls+=p.second;
        std::cout<<Headless::frame<<','<<input.push<<','<<input.crouch<<','<<input.left<<','<<input.right<<','<<input.brake<<','
                 <<skater->m_pos[X]<<','<<skater->m_pos[Y]<<','<<skater->m_pos[Z]<<','
                 <<skater->m_vel[X]<<','<<skater->m_vel[Y]<<','<<skater->m_vel[Z]<<','
                 <<skater->m_matrix[Z][X]<<','<<skater->m_matrix[Z][Y]<<','<<skater->m_matrix[Z][Z]<<','
                 <<core->GetState()<<','<<core->GetTerrain()<<','<<core->GetRailNode()<<','<<core->HaveLandedThisFrame()<<','
                 <<Headless::collisions-before_queries<<','<<Headless::lookups-before_lookups<<','<<calls-before_calls<<'\n'<<std::flush;
    }
    for(auto& p:Headless::peripheral) std::cerr<<"ADAPTER_CALL "<<p.first<<' '<<p.second<<'\n';
    delete skater;
}
