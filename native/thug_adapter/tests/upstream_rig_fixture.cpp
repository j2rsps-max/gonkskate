// Exact upstream CSkeletonData methods are extracted into build/ by the test.
// Only diagnostics and fixture I/O are supplied here. No renderer/game assets.
#include <core/allmath.h>
#include <gfx/skeleton.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <cstdarg>
#include <cstdlib>

int OurPrintf(const char* format,...){va_list args;va_start(args,format);int n=vfprintf(stderr,format,args);va_end(args);return n;}
namespace Dbg {
char storage[8192];char* sprintf_pad=storage;
char null_message[]="Null Pointer";char* msg_null_pointer=null_message;
void pad_printf(const char* format,...){va_list args;va_start(args,format);vsnprintf(storage,sizeof(storage),format,args);va_end(args);}
void Assert(char* file,unsigned int line,char* message){fprintf(stderr,"%s:%u %s\n",file,line,message?message:"");std::abort();}
}
#define MAX_LOD_DISTANCE 3.4e+38f
namespace Gfx {
#include "upstream_skeleton_data.inc"
}
int main(int argc,char** argv){
    if(argc!=2)return 2;
    std::ifstream input(argv[1],std::ios::binary|std::ios::ate);
    const auto size=input.tellg();if(size<12 || size>12+44*63)return 3;
    std::vector<uint32> data((static_cast<size_t>(size)+3)/4);
    input.seekg(0);input.read(reinterpret_cast<char*>(data.data()),size);if(!input)return 4;
    Gfx::CSkeletonData skeleton;if(!skeleton.Load(data.data(),static_cast<int>(size),true))return 5;
    auto* inverse=skeleton.GetInverseNeutralPoseMatrices();
    std::cout<<std::setprecision(9);
    for(int bone=0;bone<skeleton.GetNumBones();++bone){
        std::cout<<skeleton.GetBoneName(bone);
        for(int row=0;row<4;++row)for(int col=0;col<4;++col)std::cout<<','<<inverse[bone][row][col];
        std::cout<<'\n';
    }
}
