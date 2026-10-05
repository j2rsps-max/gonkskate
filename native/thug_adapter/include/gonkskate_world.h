#pragma once
#include "gonkskate_thug_mesh.h"
#include <vector>
#include <string>

namespace Gonk {
struct Rail { std::vector<GonkVec3> points; uint16_t terrain; };
// Owns world geometry and an immutable BVH after load. The callback's user
// pointer must stay valid for the entire simulation (no concurrent reloading).
class World {
 public:
  std::vector<GonkThugTriangle> triangles;
  std::vector<Rail> rails;
  GonkVec3 spawn{0,0,0}, facing{0,0,1};
  bool floor = false;
  void load(const std::string& path);
  void build_index();
  static uint8_t query(void*,const GonkThugCollisionQuery*,GonkThugCollisionHit*);
 private:
  struct Node { GonkVec3 low,high; uint32_t first,count,left,right; };
  std::vector<Node> nodes_;
  std::vector<uint32_t> order_;
  uint32_t build_node(uint32_t first,uint32_t count);
};
}
