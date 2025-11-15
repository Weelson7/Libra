"""Run a test file with timeout"""
import subprocess
import sys
import time

if len(sys.argv) < 2:
    print("Usage: python run_test_with_timeout.py <test_file> [timeout_seconds]")
    sys.exit(1)

test_file = sys.argv[1]
timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30

print(f"Running {test_file} with {timeout}s timeout...")
start = time.time()

try:
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nCompleted in {time.time() - start:.2f}s")
    sys.exit(result.returncode)
except subprocess.TimeoutExpired:
    print(f"\n❌ TEST TIMEOUT after {timeout}s")
    sys.exit(124)
