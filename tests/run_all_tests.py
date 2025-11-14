import glob
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

files = sorted(glob.glob(str(ROOT / 'test_*.py')))
if not files:
    print('No test files found')
    sys.exit(0)

all_ok = True
for f in files:
    print('Running', f)
    res = subprocess.run([sys.executable, f], capture_output=True, text=True)
    print(res.stdout, end='')
    if res.returncode != 0:
        print('ERROR running', f)
        print(res.stderr)
        all_ok = False

if all_ok:
    print('\nALL TESTS PASSED')
    sys.exit(0)
else:
    print('\nSOME TESTS FAILED')
    sys.exit(2)
