// Synthetic texture stream capture plus exact upstream DX9 Unswizzle method.
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <vector>

namespace NxXbox {
#include "upstream_unswizzle.inc"
}
uint32_t read32(const std::vector<uint8_t>& bytes,size_t& offset){
    if(offset+4>bytes.size())std::abort();uint32_t value;memcpy(&value,&bytes[offset],4);offset+=4;return value;
}
uint64_t hash(const uint8_t* data,size_t size){
    uint64_t value=1469598103934665603ull;
    for(size_t i=0;i<size;++i){value^=data[i];value*=1099511628211ull;}return value;
}
int main(int argc,char** argv){
    if(argc!=2)return 2;std::ifstream input(argv[1],std::ios::binary|std::ios::ate);
    auto length=input.tellg();if(length<8 || length>256*1024*1024)return 3;
    std::vector<uint8_t> bytes(static_cast<size_t>(length));input.seekg(0);input.read((char*)bytes.data(),length);if(!input)return 4;
    size_t offset=0;uint32_t version=read32(bytes,offset),count=read32(bytes,offset);
    std::cout<<"header,"<<version<<','<<count<<'\n';
    for(uint32_t texture=0;texture<count;++texture){
        uint32_t id=read32(bytes,offset),width=read32(bytes,offset),height=read32(bytes,offset),levels=read32(bytes,offset);
        uint32_t depth=read32(bytes,offset),palette_depth=read32(bytes,offset),dxt=read32(bytes,offset),palette_size=read32(bytes,offset);
        if(offset+palette_size>bytes.size())return 5;
        std::cout<<"texture,"<<id<<','<<width<<','<<height<<','<<levels<<','<<depth<<','<<palette_depth<<','<<dxt<<','<<palette_size<<','
                 <<hash(&bytes[offset],palette_size)<<'\n';offset+=palette_size;
        for(uint32_t level=0;level<levels;++level){
            uint32_t size=read32(bytes,offset);if(offset+size>bytes.size())return 6;
            uint32_t w=std::max(1u,width>>level),h=std::max(1u,height>>level);
            uint64_t linear_hash=0;
            if(!dxt){std::vector<char> output(size);NxXbox::Unswizzle(output.data(),(char*)&bytes[offset],w,h,depth/8);linear_hash=hash((uint8_t*)output.data(),size);}
            std::cout<<"mip,"<<texture<<','<<level<<','<<size<<','<<hash(&bytes[offset],size)<<','<<linear_hash<<'\n';offset+=size;
        }
    }
    std::cout<<"end,"<<offset<<'\n';return offset==bytes.size()?0:7;
}
