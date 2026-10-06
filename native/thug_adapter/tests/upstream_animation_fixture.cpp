// Original loaders, key decoders, interpolation and skeleton local-pose math
// are extracted into build/. Fixtures contain only synthetic animation data.
#include <fstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <cstdarg>
#include <cstdlib>
#include <core/allmath.h>
#include <gfx/bonedanimtypes.h>
#define protected public
#include <gfx/bonedanim.h>
#include <gfx/nxquickanim.h>
#undef protected
#include <sys/mem/memman.h>

int OurPrintf(const char* format, ...){va_list args;va_start(args,format);int n=vfprintf(stderr,format,args);va_end(args);return n;}
namespace Dbg {
char storage[8192];char* sprintf_pad=storage;
char null_message[]="Null Pointer";char* msg_null_pointer=null_message;
void pad_printf(const char* format,...){va_list args;va_start(args,format);vsnprintf(storage,sizeof(storage),format,args);va_end(args);}
void message(char* format,...){va_list args;va_start(args,format);vfprintf(stderr,format,args);va_end(args);}
void Assert(char* file,unsigned int line,char* message){fprintf(stderr,"%s:%u %s\n",file,line,message?message:"");std::abort();}
}
namespace File {
bool CAsyncFileLoader::sClose(CAsyncFileHandle*){std::abort();}
}
namespace Gfx {
CCustomAnimKey* ReadCustomAnimKey(uint8**){std::abort();}
CBonedAnimFrameData::~CBonedAnimFrameData(){} // File buffer is owned by the fixture.
#include "upstream_animation_layout.inc"
#include "upstream_animation_methods.inc"
#include "upstream_animation_skeleton.inc"
}

std::vector<uint32> read_file(const char* path){
    std::ifstream file(path,std::ios::binary|std::ios::ate);
    auto size=file.tellg();if(size<0 || size>16*1024*1024)std::abort();
    std::vector<uint32> bytes((static_cast<size_t>(size)+3)/4);
    file.seekg(0);file.read(reinterpret_cast<char*>(bytes.data()),size);if(!file)std::abort();
    return bytes;
}
void q_row(int bone,const Gfx::CStandardAnimQKey& key){
    std::cout<<"q,"<<bone<<','<<key.timestamp<<','<<bool(key.signBit)<<','<<key.qx<<','<<key.qy<<','<<key.qz<<'\n';
}
void t_row(int bone,const Gfx::CStandardAnimTKey& key){
    std::cout<<"t,"<<bone<<','<<key.timestamp<<','<<key.tx<<','<<key.ty<<','<<key.tz<<'\n';
}
int main(int argc,char** argv){
    if(argc!=5)return 2;
    static_assert(sizeof(Gfx::CStandardAnimQKey)==8 && sizeof(Gfx::CStandardAnimTKey)==8);
    auto bytes=read_file(argv[1]);auto qt=read_file(argv[2]);auto tt=read_file(argv[3]);auto times=read_file(argv[4]);
    if(qt.size()!=512 || tt.size()!=512)return 3;
    memcpy(Gfx::sQTable,qt.data(),2048);memcpy(Gfx::sTTable,tt.data(),2048);
    Gfx::CBonedAnimFrameData clip;clip.mp_fileBuffer=bytes.data();
    if(!clip.PostLoad(true,static_cast<int>(bytes.size()*4),false))return 4;
    std::cout<<std::setprecision(9);
    std::cout<<"header,"<<clip.m_numBones<<','<<clip.m_num_qFrames<<','<<clip.m_num_tFrames<<','
             <<clip.m_duration<<','<<(clip.mp_qFrames-reinterpret_cast<char*>(bytes.data()))<<','
             <<(clip.mp_tFrames-reinterpret_cast<char*>(bytes.data()))<<'\n';
    char* qp=clip.mp_qFrames;char* tp=clip.mp_tFrames;
    for(int bone=0;bone<clip.m_numBones;++bone){
        if(clip.m_flags & nxBONEDANIMFLAGS_USECOMPRESSTABLE){
            char* qe=qp+clip.mp_perBoneQFrameSize[bone];char* te=tp+clip.mp_perBoneTFrameSize[bone];
            while(qp<qe){Gfx::CStandardAnimQKey key;qp=Gfx::get_compressed_q_frame(qp,&key);q_row(bone,key);}
            while(tp<te){Gfx::CStandardAnimTKey key;tp=Gfx::get_compressed_t_frame(tp,&key);t_row(bone,key);}
            if(qp!=qe || tp!=te)return 5;
        }else{
            int nq=clip.get_num_qkeys(clip.mp_perBoneFrames,bone),nt=clip.get_num_tkeys(clip.mp_perBoneFrames,bone);
            for(int index=0;index<nq;++index)q_row(bone,reinterpret_cast<Gfx::CStandardAnimQKey*>(qp)[index]);
            for(int index=0;index<nt;++index)t_row(bone,reinterpret_cast<Gfx::CStandardAnimTKey*>(tp)[index]);
            qp+=nq*8;tp+=nt*8;
        }
    }
    auto* seconds=reinterpret_cast<float*>(times.data());
    for(size_t frame=0;frame<times.size();++frame){
        Mth::Quat q[64];Mth::Vector t[64];
        if(!clip.GetInterpolatedFrames(q,t,seconds[frame],nullptr))return 6;
        for(int bone=0;bone<clip.m_numBones;++bone){
            Mth::Matrix local;Gfx::sQuatVecToMatrix(&q[bone],&t[bone],&local,false,false);
            std::cout<<"pose,"<<frame<<','<<bone;
            for(int axis=0;axis<4;++axis)std::cout<<','<<q[bone][axis];
            for(int axis=0;axis<3;++axis)std::cout<<','<<t[bone][axis];
            for(int row=0;row<4;++row)for(int col=0;col<4;++col)std::cout<<','<<local[row][col];
            std::cout<<'\n';
        }
    }
}
