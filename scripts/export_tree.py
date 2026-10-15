"""Emit a small group of tracked text files for publication through the connector."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
files = list(filter(None, files))
start = int(sys.argv[1])
items = [{'path': name, 'mode': '100755' if name.endswith('run.sh') else '100644',
          'type': 'blob', 'content': (root / name).read_text(encoding='utf-8')}
         for name in files[start:start + 5]]
print(json.dumps({'tree_elements': items, 'count': len(files)}, ensure_ascii=True))
