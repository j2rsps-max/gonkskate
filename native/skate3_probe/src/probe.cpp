#include "gonkskate_probe.h"
#include <algorithm>
#include <bit>
#include <charconv>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <fcntl.h>
#ifdef _WIN32
#include <io.h>
#include <share.h>
#include <sys/stat.h>
#else
#include <unistd.h>
#endif

namespace gonkskate::probe {
const char* Name(Kind kind) {
  static constexpr const char* names[] = {"view_add","view_remove","bind_skater","bind_colorized",
    "bind_cac","bind_aux","jobs_start_enter","jobs_start_exit","jobs_end_enter",
    "jobs_end_exit","garment_exit","swap_begin"};
  const auto i = static_cast<unsigned>(kind);
  return i<std::size(names) ? names[i] : "invalid";
}
bool DecodeWorld(const std::array<uint8_t,64>& bytes, std::array<float,12>& rows) {
  std::array<float,16> matrix{};
  for (size_t i=0;i<16;++i) {
    const auto* b = &bytes[i*4];
    const uint32_t bits = (uint32_t(b[0])<<24)|(uint32_t(b[1])<<16)|(uint32_t(b[2])<<8)|b[3];
    matrix[i] = std::bit_cast<float>(bits);
    if (!std::isfinite(matrix[i])) return false;
  }
  if (std::abs(matrix[12])>1e-4f || std::abs(matrix[13])>1e-4f ||
      std::abs(matrix[14])>1e-4f || std::abs(matrix[15]-1)>1e-4f) return false;
  // Same structural bounds as upstream ReadWorldRowsChecked, plus finite checks.
  for (size_t r=0;r<3;++r) {
    float n=0;
    for(size_t c=0;c<3;++c) n+=matrix[r*4+c]*matrix[r*4+c];
    if (!(n>0.0025f && n<400) || std::abs(matrix[r*4+3])>=20000) return false;
  }
  std::copy_n(matrix.begin(),12,rows.begin());
  return true;
}
Event Snapshot(CopyGuest copy, uint8_t* base, uint32_t entity, Kind kind,
               uint32_t hook, uint32_t caller, uint32_t detail) noexcept {
  Event e;
  e.kind=kind;e.entity=entity;e.hook=hook;e.caller=caller;e.detail=detail;
  // View removal and swap are lifetime/presentation markers, not pose samples.
  if(kind==Kind::view_remove || kind==Kind::swap_begin) return e;
  e.pose_status=PoseStatus::unreadable;
  if(!copy || !base || entity<0x10000 || entity>=0x84A10000 || (entity&3)) return e;
  std::array<uint8_t,64> first{},second{};
  if(!copy(first.data(),base+entity+416,first.size()) ||
     !copy(second.data(),base+entity+416,second.size())) return e;
  // Two identical copies reject a visible concurrent write. They do not prove
  // atomicity of an entire game update or make these presentation poses physics.
  if(first!=second) { e.pose_status=PoseStatus::unstable;return e; }
  e.pose_status=DecodeWorld(first,e.rows) ? PoseStatus::valid : PoseStatus::invalid;
  return e;
}
namespace {
template<class T> void Number(std::string& out,T value) {
  char buffer[64];
  auto result = std::to_chars(buffer,buffer+sizeof(buffer),value);
  out.append(buffer,result.ptr);
}
std::string Serialize(const Event& e) {
  std::string s="{\"kind\":\"";
  s+=Name(e.kind);s+="\",\"sequence\":";Number(s,e.sequence);
  s+=",\"mono_ns\":";Number(s,e.mono_ns);
  s+=",\"render_epoch\":";Number(s,e.render_epoch);
  s+=",\"host_thread_tag\":";Number(s,e.host_thread_tag);
  s+=",\"entity\":";Number(s,e.entity);
  s+=",\"hook\":";Number(s,e.hook);
  s+=",\"caller\":";Number(s,e.caller);
  s+=",\"detail\":";Number(s,e.detail);
  s+=",\"pose_status\":";Number(s,static_cast<unsigned>(e.pose_status));
  if (e.pose_status==PoseStatus::valid) {
    s+=",\"world_rows\":[";
    for(size_t i=0;i<12;++i) { if(i)s+=',';Number(s,e.rows[i]); }
    s+=']';
  }
  s+="}\n";
  return s;
}
}
Recorder::Recorder(const std::filesystem::path& path,Limits limits)
  :limits_(limits),started_(std::chrono::steady_clock::now()) {
  if (!limits.queue || limits.queue>65536 || limits.bytes<4096 || limits.events<1)
    throw std::invalid_argument("Invalid probe limits");
  pending_.reserve(limits.queue);
#ifdef _WIN32
  // Some Windows C runtimes silently ignore fopen's C11 'x' flag. Request
  // exclusivity at the descriptor layer so an earlier trace cannot be replaced.
  int descriptor=-1;
  if(_wsopen_s(&descriptor,path.c_str(),_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,
               _SH_DENYWR,_S_IREAD|_S_IWRITE)==0) {
    file_=_fdopen(descriptor,"wb");
    if(!file_)_close(descriptor);
  }
#else
  const int descriptor=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
  if(descriptor>=0) {
    file_=::fdopen(descriptor,"wb");
    if(!file_)::close(descriptor);
  }
#endif
  if (!file_) throw std::runtime_error("Cannot create new probe trace (existing files are preserved)");
  try {
    Write("{\"kind\":\"header\",\"schema_version\":1,\"scope\":\"presentation-only\",\"units\":\"meter\","
          "\"player_identity\":\"unresolved\",\"simulation_tick\":\"unresolved\","
          "\"skate3_commit\":\"f6e0ae87fdfecbadb5c1e36c55d66a744187a3cd\"}\n");
    if(io_error_) throw std::runtime_error("Cannot write probe header");
    writer_=std::thread(&Recorder::WriteLoop,this);
  } catch(...) { std::fclose(file_);file_=nullptr;throw; }
}
Recorder::~Recorder() { Stop(); }
bool Recorder::Submit(Event event) noexcept {
  if(!accepting_.load(std::memory_order_acquire)) return false;
  std::unique_lock lock(mutex_,std::try_to_lock);
  if(!lock.owns_lock()) { dropped_.fetch_add(1);return false; }
  if(stopping_ || !accepting_.load(std::memory_order_relaxed)) return false;
  if(pending_.size()>=limits_.queue) { dropped_.fetch_add(1);return false; }
  // Refuse forged enum/non-finite rows as well as malformed guest snapshots.
  if(static_cast<unsigned>(event.kind)>static_cast<unsigned>(Kind::swap_begin) ||
     static_cast<unsigned>(event.pose_status)>static_cast<unsigned>(PoseStatus::invalid)) return false;
  if(event.pose_status==PoseStatus::valid)
    for(float value:event.rows) if(!std::isfinite(value)) { event.pose_status=PoseStatus::invalid;break; }
  if(event.pose_status!=PoseStatus::none && event.pose_status!=PoseStatus::valid) invalid_.fetch_add(1);
  event.sequence=sequence_++;
  event.render_epoch=epoch_;
  if(event.kind==Kind::swap_begin) ++epoch_;
  event.mono_ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-started_).count();
  event.host_thread_tag=std::hash<std::thread::id>{}(std::this_thread::get_id());
  pending_.push_back(event);
  condition_.notify_one();
  return true;
}
bool Recorder::Write(const std::string& line) {
  if(io_error_) return false;
  if(std::fwrite(line.data(),1,line.size(),file_)!=line.size()) { io_error_=true;accepting_=false;return false; }
  bytes_+=line.size();return true;
}
void Recorder::WriteLoop() {
  try {
  std::vector<Event> batch;batch.reserve(limits_.queue);
  for(;;) {
    bool stopping;
    {
      std::unique_lock lock(mutex_);
      condition_.wait(lock,[this]{ return stopping_ || !pending_.empty(); });
      batch.swap(pending_);stopping=stopping_;
    }
    for(const auto& event:batch) {
      auto line=Serialize(event);
      // Reserve space for the final loss/limit/IO summary.
      if(written_>=limits_.events || bytes_+line.size()>limits_.bytes-2048) {
        limited_=true;accepting_=false;break;
      }
      if(!Write(line))break;
      ++written_;
    }
    batch.clear();
    if(std::fflush(file_)!=0) { io_error_=true;accepting_=false; }
    if(stopping) break;
  }
  } catch(...) { worker_error_=true;accepting_=false; }
  // A failed observer must stop observing, rather than terminate the game.
  uint64_t accepted;
  { std::lock_guard lock(mutex_);accepting_=false;accepted=sequence_; }
  char summary[512];
  const int length=std::snprintf(summary,sizeof(summary),
    "{\"kind\":\"summary\",\"written_events\":%llu,\"accepted_events\":%llu,"
    "\"dropped_events\":%llu,\"invalid_matrices\":%llu,\"limit_reached\":%s,"
    "\"io_error\":%s,\"worker_error\":%s}\n",
    static_cast<unsigned long long>(written_),static_cast<unsigned long long>(accepted),
    static_cast<unsigned long long>(dropped_.load()),static_cast<unsigned long long>(invalid_.load()),
    limited_?"true":"false",io_error_?"true":"false",worker_error_?"true":"false");
  if(length>0 && !io_error_) std::fwrite(summary,1,static_cast<size_t>(length),file_);
  std::fclose(file_);file_=nullptr;
}
void Recorder::Stop() {
  std::lock_guard once(stop_mutex_);
  accepting_.store(false,std::memory_order_release);
  {
    std::lock_guard lock(mutex_);stopping_=true;
  }
  condition_.notify_one();
  if(writer_.joinable())writer_.join();
}
}  // namespace gonkskate::probe
