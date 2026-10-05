import tempfile,unittest,struct
from pathlib import Path
from skate3_readiness import inspect,xex_info
class ReadinessTests(unittest.TestCase):
 def test_no_assets(self):
  self.assertEqual(inspect()['status'],'GAME_FILES_NOT_SUPPLIED')
 def test_metadata_and_missing_patch(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'default.xex'
   header=b'XEX2'+bytes(16)+struct.pack('>I',1)+struct.pack('>II',0x40006,32)
   p.write_bytes(header+struct.pack('>IIII',0x5c087c2c,0,0,0x454108e6)+bytes(8))
   info=xex_info(p);self.assertEqual(info['title_id'],'454108E6');self.assertEqual(info['media_id'],'5C087C2C')
   result=inspect(root);self.assertTrue(result['title_id_matches']);self.assertFalse(result['title_update'][0]['matches_inspected_tu3'])
   self.assertEqual(result['status'],'MISSING_OR_INVALID_XEX_HEADERS')
   self.assertNotIn(str(root),str(result))
   p.write_bytes(header[:28]);self.assertIn('error',xex_info(p))
 def test_corrupt_offsets_and_patch_size(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'default.xex';p.write_bytes(b'XEX2'+bytes(16)+struct.pack('>I',1)+struct.pack('>II',0x40006,999999))
   self.assertIn('error',xex_info(p))
   (root/'default.xexp').write_bytes(b'not a TU')
   self.assertFalse(inspect(root)['title_update'][0]['matches_inspected_tu3'])
if __name__=='__main__':unittest.main()
