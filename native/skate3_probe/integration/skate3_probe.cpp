#include "skate3_probe.h"
#include <cstdlib>
#include <memory>
#include <exception>

// Use upstream's fault-guarded copy implementation. Including the full renderer
// header would couple this observer to its unrelated mesh/material types.
namespace skate3::native_scene {
bool GuestTryCopy(void* dst, const void* src, size_t size);
}

namespace gonkskate::guest_probe {
namespace {
std::unique_ptr<probe::Recorder> owner;
std::atomic<probe::Recorder*> published{nullptr};
bool started=false;
}
void Start() noexcept {
  if(started) return;
  started=true;
#ifdef _WIN32
  const wchar_t* directory=_wgetenv(L"GONKSKATE_GUEST_PROBE_DIR");
#else
  const char* directory=std::getenv("GONKSKATE_GUEST_PROBE_DIR");
#endif
  if(!directory || !*directory) return;
  try {
    const auto folder=std::filesystem::path(directory);
    std::filesystem::create_directories(folder);
    const auto stamp=std::chrono::duration_cast<std::chrono::microseconds>(
      std::chrono::system_clock::now().time_since_epoch()).count();
    const auto filename="skate3-presentation-"+std::to_string(stamp)+".jsonl";
    const auto path=folder/filename;
    owner=std::make_unique<probe::Recorder>(path);
    published.store(owner.get(),std::memory_order_release);
    std::fprintf(stderr,"GonkSkate presentation probe: %s in GONKSKATE_GUEST_PROBE_DIR (32 MiB/100000 events maximum)\n",filename.c_str());
  } catch(const std::exception& e) {
    std::fprintf(stderr,"GonkSkate presentation probe disabled: %s\n",e.what());
  } catch(...) {
    std::fprintf(stderr,"GonkSkate presentation probe disabled: initialization failed\n");
  }
}
void Stop() noexcept {
  if(auto* recorder=published.exchange(nullptr,std::memory_order_acq_rel)) recorder->Stop();
}
void Observe(uint8_t* base,uint32_t entity,probe::Kind kind,
             uint32_t hook,uint32_t caller,uint32_t detail) noexcept {
  auto* recorder=published.load(std::memory_order_acquire);
  if(!recorder || !recorder->Accepting()) return;
  recorder->Submit(probe::Snapshot(skate3::native_scene::GuestTryCopy,base,
                                entity,kind,hook,caller,detail));
}
}
