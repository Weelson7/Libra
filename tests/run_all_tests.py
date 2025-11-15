"""
Run all tests in the tests/ directory
Support for running all tests, scenario tests only, or quick critical tests
"""
import glob
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent

# Test categories
SCENARIO_TESTS = [
    'test_tor_reconnection.py',
    'test_p2p_connection.py',
    'test_file_transfer.py',
    'test_onion_rotation.py',
    'test_integration_scenarios.py'
]

CRITICAL_TESTS = [
    'test_db.py',
    'test_crypto.py',
    'test_tor_reconnection.py'
]


def run_tests(test_files, mode_name="ALL TESTS"):
    """Run specified test files"""
    if not test_files:
        print('No test files found')
        return True
    
    print("\n" + "="*70)
    print(f"LIBRA {mode_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    all_ok = True
    passed = 0
    failed = 0
    
    for f in test_files:
        print(f'Running {Path(f).name}...')
        res = subprocess.run([sys.executable, f], capture_output=True, text=True)
        print(res.stdout, end='')
        
        if res.returncode != 0:
            print(f'ERROR running {Path(f).name}')
            print(res.stderr)
            all_ok = False
            failed += 1
        else:
            passed += 1
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Test Files Run: {len(test_files)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*70 + "\n")
    
    return all_ok


def run_all_tests():
    """Run all test files"""
    files = sorted(glob.glob(str(ROOT / 'test_*.py')))
    return run_tests(files, "ALL TESTS")


def run_scenario_tests():
    """Run only scenario-specific tests"""
    files = [str(ROOT / test) for test in SCENARIO_TESTS if (ROOT / test).exists()]
    return run_tests(files, "SCENARIO TESTS")


def run_quick_tests():
    """Run critical tests only"""
    files = [str(ROOT / test) for test in CRITICAL_TESTS if (ROOT / test).exists()]
    return run_tests(files, "QUICK TESTS")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Libra test suite')
    parser.add_argument('--mode', choices=['all', 'scenario', 'quick'], 
                       default='all', help='Test mode: all, scenario, or quick')
    
    args = parser.parse_args()
    
    if args.mode == 'all':
        success = run_all_tests()
    elif args.mode == 'scenario':
        success = run_scenario_tests()
    elif args.mode == 'quick':
        success = run_quick_tests()
    
    if success:
        print('✓ ALL TESTS PASSED')
        sys.exit(0)
    else:
        print('✗ SOME TESTS FAILED')
        sys.exit(2)
