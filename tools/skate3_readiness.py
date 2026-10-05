"""Read local file metadata only; never copy retail files into reports."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN=json.loads((ROOT/'native/skate3_adapter/config/upstream.json').read_text())
def xex_info(path):
 result={'found':path.is_file()}
 if not result['found']:return result
 try:
  result['size']=path.stat().st_size
  with path.open('rb') as f:
   header=f.read(24)
   result['xex2_header']=header[:4]==b'XEX2' and len(header)==24
   if not result['xex2_header'] or len(header)!=24:return result
   count=struct.unpack_from('>I',header,20)[0]
   if count>1024:result['error']='optional header count exceeds inspection bound';return result
   table=f.read(count*8)
   if len(table)!=count*8:result['error']='truncated optional header table';return result
   for i in range(count):
    key,offset=struct.unpack_from('>II',table,i*8)
    if key==0x00040006:
     if offset<24+count*8 or offset+24>result['size']:result['error']='execution info outside file';return result
     f.seek(offset);execution=f.read(24)
     media,version,base,title=struct.unpack_from('>IIII',execution)
     result.update(media_id=f'{media:08X}',title_id=f'{title:08X}',version_hex=f'{version:08X}',base_version_hex=f'{base:08X}')
     break
 except (OSError,struct.error) as e:result['error']=type(e).__name__
 return result

def inspect(game_root=None):
 report={'schema_version':1,'upstream':PIN,'scope':'local metadata and known TU3 hashes; not game boot or asset compatibility validation','game_root_supplied':game_root is not None}
 if game_root is None:report['status']='GAME_FILES_NOT_SUPPLIED';return report
 root=Path(game_root)
 report['executables']={n:xex_info(root/n) for n in ['default.xex','data/webkit/EAWebkit.xex']}
 report['content_directory_found']=(root/'data/content').is_dir()
 report['title_update']=[]
 for expected in PIN['title_update_payloads']:
  p=root/expected['path'];entry={'path':expected['path'],'found':p.is_file(),'matches_inspected_tu3':False}
  if entry['found']:
   try:
    entry['size']=p.stat().st_size
    if entry['size']==expected['size']:
     entry['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
     entry['matches_inspected_tu3']=entry['sha256']==expected['sha256']
   except OSError as e:entry['error']=type(e).__name__
  report['title_update'].append(entry)
 default=report['executables']['default.xex']
 report['title_id_matches']=default.get('title_id')==PIN['title_id']
 report['media_id_matches_tu3']=default.get('media_id')==PIN['tu3_media_id']
 report['status']='FILES_DETECTED_NEED_RUNTIME_VALIDATION' if all(e.get('xex2_header') and not e.get('error') for e in report['executables'].values()) else 'MISSING_OR_INVALID_XEX_HEADERS'
 return report
