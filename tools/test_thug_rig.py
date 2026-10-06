"""Source-format rig fixtures, invalid data and unit/parent/rotation semantics."""
import math
import struct
import unittest
from import_thug_rig import parse


def fixture(names=(10,20,30),parents=(0,10,20),flips=(0,0,0),poses=None,version=2):
    if poses is None:poses=[(0,0,0,1,0,0,0,0),(0,0,0,1,0,12,0,0),(0,0,0,1,0,8,0,0)]
    return struct.pack("<III",version,0,len(names))+struct.pack(f"<{len(names)*3}I",*names,*parents,*flips)+b"".join(struct.pack("<8f",*p) for p in poses)


class RigTests(unittest.TestCase):
    def test_hierarchy_and_inches_to_meters(self):
        rig=parse(fixture())
        self.assertEqual([b["parent_index"] for b in rig["bones"]],[None,0,1])
        self.assertAlmostEqual(rig["bones"][2]["rest_world_matrix"][7],20*0.0254)
        self.assertAlmostEqual(rig["bones"][2]["inverse_bind_matrix"][7],-20*0.0254)
        self.assertFalse(rig["mesh_imported"])
        self.assertFalse(rig["retail_validated"])

    def test_root_rotation_is_preserved(self):
        half=math.sqrt(0.5)
        data=fixture(poses=[(0,0,half,half,0,0,0,0),(0,0,0,1,12,0,0,0),(0,0,0,1,0,8,0,0)])
        rig=parse(data)
        # Source quaternion inversion + row-vector composition rotates +X to -Y.
        self.assertAlmostEqual(rig["bones"][1]["rest_world_matrix"][7],-12*0.0254,places=6)

    def test_version_length_and_count(self):
        for data in [b"",fixture(version=1),fixture(version=3),fixture()[:-1],fixture()+b"x",
                     struct.pack("<III",2,0,64)]:
            with self.assertRaises(ValueError):parse(data)

    def test_invalid_hierarchy_and_flip(self):
        for data in [fixture(names=(10,10,30)),fixture(parents=(0,30,10)),fixture(parents=(0,999,20)),fixture(flips=(0,999,0))]:
            with self.assertRaises(ValueError):parse(data)

    def test_nonfinite_and_nonuniform_pose(self):
        for value in [float("nan"),float("inf"),4]:
            poses=[(value,0,0,1,0,0,0,0),(0,0,0,1,0,12,0,0),(0,0,0,1,0,8,0,0)]
            with self.assertRaises(ValueError):parse(fixture(poses=poses))


if __name__=="__main__":unittest.main()
