#include "gonkskate_probe.h"
#include <bit>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace gonkskate::probe;
void Check(bool condition,const char* message) { if(!condition)throw std::runtime_error(message); }
std::array<uint8_t,64> Encode(std::array<float,16> matrix) {
  std::array<uint8_t,64> bytes{};
  for(size_t i=0;i<16;++i) {
    auto bits=std::bit_cast<uint32_t>(matrix[i]);
    for(size_t j=0;j<4;++j)bytes[4*i+j]=uint8_t(bits>>(24-8*j));
  }
  return bytes;
}
std::string Read(const std::filesystem::path& path) {
  std::ifstream stream(path);return {std::istreambuf_iterator<char>(stream),{}};
}
int main(int argc,char** argv) {
 try {
  Check(argc==2,"Pass an output fixture path");
  const std::filesystem::path path=argv[1];
  auto matrix=std::array<float,16>{1,0,0,10.125f,0,1,0,-3.5f,0,0,1,0.33333334f,0,0,0,1};
  std::array<float,12> rows{};
  Check(DecodeWorld(Encode(matrix),rows) && rows[3]==10.125f && rows[11]==matrix[11],"BE pose decoding");
  auto bad=matrix;bad[15]=0;Check(!DecodeWorld(Encode(bad),rows),"Homogeneous validation");
  bad=matrix;bad[4]=std::numeric_limits<float>::infinity();Check(!DecodeWorld(Encode(bad),rows),"Non-finite validation");
  bad=matrix;bad[3]=20000;Check(!DecodeWorld(Encode(bad),rows),"Translation bound");
  bad=matrix;bad[0]=0;Check(!DecodeWorld(Encode(bad),rows),"Collapsed rotation");
  std::filesystem::remove(path);
  {
    Recorder recorder(path);
    Event event;event.kind=Kind::bind_cac;event.entity=0x10000;event.rows=rows;
    DecodeWorld(Encode(matrix),event.rows);event.pose_status=PoseStatus::valid;
    // Retry only in this contract test, never on guest threads.
    while(!recorder.Submit(event))std::this_thread::yield();
    event.rows[0]=std::numeric_limits<float>::quiet_NaN();
    while(!recorder.Submit(event))std::this_thread::yield();
    recorder.Stop();recorder.Stop();Check(!recorder.Submit(event),"Stopped recorder accepted an event");
  }
  const auto text=Read(path);
  Check(text.find("\"invalid_matrices\":1")!=std::string::npos,"Invalid matrix accounting");
  Check(text.find("nan")==std::string::npos,"JSON contained NaN");
  bool refused=false;
  try { Recorder existing(path); } catch(const std::runtime_error&) { refused=true; }
  Check(refused && Read(path)==text,"Existing trace was overwritten");
  const auto concurrent=path.string()+".concurrent";
  std::filesystem::remove(concurrent);
  {
    Recorder recorder(concurrent);
    std::array<std::thread,4> threads;
    for(auto& thread:threads)thread=std::thread([&] {
      for(int i=0;i<10000;++i) { Event e;e.kind=Kind::swap_begin;recorder.Submit(e); }
    });
    for(auto& thread:threads)thread.join();
    recorder.Stop();
  }
  Check(Read(concurrent).find("\"kind\":\"summary\"")!=std::string::npos,"Concurrent shutdown missing summary");
  const auto limited=path.string()+".limited";
  std::filesystem::remove(limited);
  {
    Recorder recorder(limited,{8,4096,1});
    for(int i=0;i<100;++i) { Event e;e.kind=Kind::swap_begin;recorder.Submit(e); }
    recorder.Stop();
  }
  Check(std::filesystem::file_size(limited)<=4096,"Byte limit exceeded");
  Check(Read(limited).find("\"written_events\":1")!=std::string::npos,"Event limit failed");
  const auto byte_limited=path.string()+".byte-limited";
  std::filesystem::remove(byte_limited);
  {
    Recorder recorder(byte_limited,{8,4096,100000});
    while(recorder.Accepting()) {
      Event e;e.kind=Kind::swap_begin;
      if(!recorder.Submit(e))std::this_thread::yield();
    }
    recorder.Stop();
  }
  Check(std::filesystem::file_size(byte_limited)<=4096,"Byte limit exceeded");
  Check(Read(byte_limited).find("\"limit_reached\":true")!=std::string::npos,"Byte limit did not stop recording");
  std::cout<<"Probe contracts passed: decoding, invalid poses, exclusive output, concurrency, limits, stop\n";
  return 0;
 } catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
