"""Convert recorded raw Godot controller frames with the compiled SDK bridge."""
import json,subprocess
from pathlib import Path
def convert(trace,executable,output,runner=()):
 frames=[json.loads(line) for line in Path(trace).read_text().splitlines()]
 rows=[]
 for item in frames:
  axes=[*item['left_stick_raw'],*item['right_stick_raw'],item['left_trigger'],item['right_trigger']]
  assert len(axes)==6
  rows.append(' '.join(map(str,[item['frame'],item['buttons'],*axes])))
 result=subprocess.run([*runner,str(executable),'--pipe'],input='\n'.join(rows)+'\n',capture_output=True,text=True,timeout=60,check=True)
 packets=result.stdout.splitlines();assert len(packets)==len(frames)
 with Path(output).open('w') as f:
  for item,packet in zip(frames,packets):
   assert len(packet)==32 and len(bytes.fromhex(packet))==16
   f.write(json.dumps({'frame':item['frame'],'connected':item['device']>=0,'guest_state_hex':packet})+'\n')
 return len(frames)
