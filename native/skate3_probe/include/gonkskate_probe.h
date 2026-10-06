#pragma once
#include <array>
#include <atomic>
#include <condition_variable>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <mutex>
#include <thread>
#include <string>
#include <vector>

namespace gonkskate::probe {
enum class Kind { view_add, view_remove, bind_skater, bind_colorized, bind_cac,
                  bind_aux, jobs_start_enter, jobs_start_exit, jobs_end_enter,
                  jobs_end_exit, garment_exit, swap_begin };
enum class PoseStatus { none, valid, unreadable, unstable, invalid };
struct Event {
  Kind kind{};
  uint32_t entity = 0, hook = 0, caller = 0, detail = 0;
  PoseStatus pose_status = PoseStatus::none;
  std::array<float, 12> rows{};
  uint64_t sequence = 0, mono_ns = 0, render_epoch = 0, host_thread_tag = 0;
};
bool DecodeWorld(const std::array<uint8_t,64>& bytes, std::array<float,12>& rows);
using CopyGuest = bool (*)(void*, const void*, size_t);
Event Snapshot(CopyGuest copy, uint8_t* base, uint32_t entity, Kind kind,
               uint32_t hook, uint32_t caller, uint32_t detail = 0) noexcept;
const char* Name(Kind kind);
struct Limits { size_t queue = 4096; uint64_t bytes = 32*1024*1024, events = 100000; };

// Hooks perform a bounded try-lock enqueue. Only this worker writes the file.
// Stop refuses new observations and joins the writer; keep the Recorder alive
// until all possible guest callers have stopped. Existing output is never replaced.
class Recorder {
 public:
  explicit Recorder(const std::filesystem::path& path, Limits limits = {});
  ~Recorder();
  bool Submit(Event event) noexcept;
  bool Accepting() const noexcept { return accepting_.load(std::memory_order_acquire); }
  void Stop();
  Recorder(const Recorder&) = delete;
  Recorder& operator=(const Recorder&) = delete;
 private:
  void WriteLoop();
  bool Write(const std::string& line);
  Limits limits_;
  std::FILE* file_ = nullptr;
  std::thread writer_;
  std::mutex mutex_, stop_mutex_;
  std::condition_variable condition_;
  std::vector<Event> pending_;
  std::atomic<bool> accepting_{true};
  std::atomic<uint64_t> dropped_{0}, invalid_{0};
  uint64_t sequence_ = 0, epoch_ = 0, written_ = 0, bytes_ = 0;
  bool stopping_ = false, limited_ = false, io_error_ = false, worker_error_ = false;
  std::chrono::steady_clock::time_point started_;
};
}  // namespace gonkskate::probe
