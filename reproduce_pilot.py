#!/usr/bin/env python3
"""Recompute the public-data pilot with pinned inputs; no model/API key needed."""
import hashlib,json,subprocess,sys,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'pilot/qwen_human_disagreement_manifest.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 m=json.loads(MANIFEST.read_text()); commit=m['package_commit']
 with tempfile.TemporaryDirectory(prefix='orgsci-replay-') as tmp:
  base=Path(tmp)
  for name,expected in m['source_sha256'].items():
   req=urllib.request.Request(f'https://raw.githubusercontent.com/FutureTech-OB/ai-taste/{commit}/{name}',headers={'User-Agent':'OrganizationScience-Replay-Reproduction'})
   with urllib.request.urlopen(req,timeout=60) as response: data=response.read()
   if sha(data)!=expected: raise RuntimeError('Source checksum mismatch: '+name)
   dest=base/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
  out=base/'result.csv'
  subprocess.run([sys.executable,str(ROOT/'pilot/qwen_human_disagreement.py'),'--package',str(base),'--out',str(out)],check=True)
  if sha(out.read_bytes())!=m['output_sha256']: raise RuntimeError('Output differs from reference aggregate')
  if out.read_bytes()!=(ROOT/'pilot/qwen_human_disagreement_by_tier.csv').read_bytes(): raise RuntimeError('Bundled CSV differs from expected output')
  print('PASS: four pinned public input hashes and all eight aggregate rows reproduced exactly.')
  print('Temporary source data removed on exit. This reproduces archived-output analysis, not model inference.')
if __name__=='__main__': main()
