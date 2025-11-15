"""
Phase 8: Comprehensive Test Report Generator
Aggregates all Phase 8 test results and generates detailed reports.
"""
import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class Phase8TestRunner:
    """Orchestrates all Phase 8 tests and generates comprehensive report."""
    
    def __init__(self):
        self.test_suites = [
            ('Connectivity Testing', 'test_connectivity_benchmarks.py'),
            ('Security & Penetration Testing', 'test_security_penetration.py'),
            ('Privacy Analysis', 'test_privacy_analysis.py'),
            ('Isolation Verification', 'test_isolation_verification.py'),
            ('Data Protection Audit', 'test_data_protection_audit.py'),
            ('Dependency Security', 'test_dependency_security.py'),
        ]
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def run_test_suite(self, name: str, filename: str) -> Tuple[bool, str, float]:
        """Run a single test suite and return results."""
        print(f"\n{'=' * 70}")
        print(f"Running: {name}")
        print('=' * 70)
        
        test_path = Path('tests') / filename
        
        if not test_path.exists():
            print(f"⚠ Test file not found: {filename}")
            return False, "Test file not found", 0.0
        
        start = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            duration = time.time() - start
            
            # Print output
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:", result.stderr)
            
            success = result.returncode == 0
            
            return success, result.stdout, duration
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"✗ Test timed out after 120 seconds")
            return False, "Test timed out", duration
        
        except Exception as e:
            duration = time.time() - start
            print(f"✗ Error running test: {e}")
            return False, str(e), duration
    
    def run_all_tests(self):
        """Run all Phase 8 test suites."""
        self.start_time = datetime.now()
        
        print("=" * 70)
        print("LIBRA v2.0 - PHASE 8 COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for name, filename in self.test_suites:
            success, output, duration = self.run_test_suite(name, filename)
            
            self.results.append({
                'name': name,
                'filename': filename,
                'success': success,
                'output': output,
                'duration': duration,
            })
        
        self.end_time = datetime.now()
    
    def generate_summary_report(self) -> str:
        """Generate summary report of all test results."""
        report = []
        report.append("=" * 70)
        report.append("LIBRA v2.0 - PHASE 8 TEST SUMMARY REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Completed: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        report.append(f"Total Duration: {total_duration:.2f}s")
        report.append("")
        
        # Overall statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report.append("OVERALL RESULTS:")
        report.append(f"  Total Test Suites: {total_tests}")
        report.append(f"  Passed: {passed_tests} ✓")
        report.append(f"  Failed: {failed_tests} ✗")
        report.append(f"  Success Rate: {success_rate:.1f}%")
        report.append("")
        
        # Individual test suite results
        report.append("TEST SUITE RESULTS:")
        report.append("-" * 70)
        
        for result in self.results:
            status = "✓ PASSED" if result['success'] else "✗ FAILED"
            report.append(f"{status} | {result['name']}")
            report.append(f"         Duration: {result['duration']:.2f}s")
            report.append(f"         File: {result['filename']}")
            report.append("")
        
        report.append("=" * 70)
        
        # Overall assessment
        if passed_tests == total_tests:
            report.append("✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        elif success_rate >= 80:
            report.append("⚠ MOST TESTS PASSED - REVIEW FAILED TESTS BEFORE DEPLOYMENT")
        else:
            report.append("✗ MULTIPLE TESTS FAILED - SYSTEM NOT READY FOR PRODUCTION")
        
        report.append("=" * 70)
        
        return '\n'.join(report)
    
    def generate_detailed_report(self) -> str:
        """Generate detailed report with all test outputs."""
        report = []
        report.append("=" * 70)
        report.append("LIBRA v2.0 - PHASE 8 DETAILED TEST REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for result in self.results:
            report.append("=" * 70)
            report.append(f"TEST SUITE: {result['name']}")
            report.append(f"File: {result['filename']}")
            report.append(f"Status: {'PASSED' if result['success'] else 'FAILED'}")
            report.append(f"Duration: {result['duration']:.2f}s")
            report.append("-" * 70)
            report.append("OUTPUT:")
            report.append(result['output'])
            report.append("")
        
        report.append("=" * 70)
        report.append("END OF DETAILED REPORT")
        report.append("=" * 70)
        
        return '\n'.join(report)
    
    def generate_json_report(self) -> str:
        """Generate JSON report for programmatic consumption."""
        report_data = {
            'test_run': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_seconds': (self.end_time - self.start_time).total_seconds(),
            },
            'summary': {
                'total_suites': len(self.results),
                'passed': sum(1 for r in self.results if r['success']),
                'failed': sum(1 for r in self.results if not r['success']),
                'success_rate': sum(1 for r in self.results if r['success']) / len(self.results) * 100,
            },
            'test_suites': [
                {
                    'name': r['name'],
                    'filename': r['filename'],
                    'success': r['success'],
                    'duration': r['duration'],
                }
                for r in self.results
            ]
        }
        
        return json.dumps(report_data, indent=2)
    
    def save_reports(self):
        """Save all reports to files."""
        report_dir = Path('tests/reports')
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary report
        summary_path = report_dir / f'phase8_summary_{timestamp}.txt'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_summary_report())
        print(f"\n✓ Summary report saved: {summary_path}")
        
        # Save detailed report
        detailed_path = report_dir / f'phase8_detailed_{timestamp}.txt'
        with open(detailed_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_detailed_report())
        print(f"✓ Detailed report saved: {detailed_path}")
        
        # Save JSON report
        json_path = report_dir / f'phase8_results_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_json_report())
        print(f"✓ JSON report saved: {json_path}")
        
        # Save latest symlinks (overwrite)
        latest_summary = report_dir / 'latest_summary.txt'
        latest_detailed = report_dir / 'latest_detailed.txt'
        latest_json = report_dir / 'latest_results.json'
        
        with open(latest_summary, 'w', encoding='utf-8') as f:
            f.write(self.generate_summary_report())
        
        with open(latest_detailed, 'w', encoding='utf-8') as f:
            f.write(self.generate_detailed_report())
        
        with open(latest_json, 'w', encoding='utf-8') as f:
            f.write(self.generate_json_report())
        
        print(f"✓ Latest reports updated in {report_dir}")


class QualityGateChecker:
    """Check if system passes quality gates for production readiness."""
    
    def __init__(self, results: List[Dict]):
        self.results = results
    
    def check_all_gates(self) -> Tuple[bool, List[str]]:
        """Check all quality gates."""
        gates_passed = []
        gates_failed = []
        
        # Gate 1: All test suites must pass
        all_passed = all(r['success'] for r in self.results)
        if all_passed:
            gates_passed.append("✓ All test suites passed")
        else:
            failed_suites = [r['name'] for r in self.results if not r['success']]
            gates_failed.append(f"✗ Failed test suites: {', '.join(failed_suites)}")
        
        # Gate 2: Critical test suites (security, privacy) must pass
        critical_suites = ['Security & Penetration Testing', 'Privacy Analysis']
        critical_passed = all(
            r['success'] for r in self.results 
            if r['name'] in critical_suites
        )
        if critical_passed:
            gates_passed.append("✓ Critical security/privacy tests passed")
        else:
            gates_failed.append("✗ Critical security/privacy tests failed")
        
        # Gate 3: Test execution time reasonable
        total_duration = sum(r['duration'] for r in self.results)
        if total_duration < 300:  # 5 minutes
            gates_passed.append(f"✓ Test execution time acceptable ({total_duration:.1f}s)")
        else:
            gates_failed.append(f"⚠ Test execution time high ({total_duration:.1f}s)")
        
        # Gate 4: No timeout failures
        timeout_failures = [r for r in self.results if 'timeout' in r['output'].lower()]
        if not timeout_failures:
            gates_passed.append("✓ No test timeouts")
        else:
            gates_failed.append(f"✗ Test timeouts detected: {len(timeout_failures)}")
        
        return len(gates_failed) == 0, gates_passed + gates_failed
    
    def generate_quality_report(self) -> str:
        """Generate quality gate report."""
        passed, gates = self.check_all_gates()
        
        report = []
        report.append("=" * 70)
        report.append("QUALITY GATE ASSESSMENT")
        report.append("=" * 70)
        
        for gate in gates:
            report.append(gate)
        
        report.append("")
        report.append("=" * 70)
        
        if passed:
            report.append("✓ SYSTEM PASSES ALL QUALITY GATES")
            report.append("✓ READY FOR PRODUCTION DEPLOYMENT")
        else:
            report.append("✗ SYSTEM FAILS QUALITY GATES")
            report.append("✗ NOT READY FOR PRODUCTION - ADDRESS FAILURES FIRST")
        
        report.append("=" * 70)
        
        return '\n'.join(report)


def main():
    """Main entry point for Phase 8 test runner."""
    print("\n" + "=" * 70)
    print("LIBRA v2.0 - PHASE 8: TESTING & QUALITY GATES")
    print("=" * 70)
    print("\nInitializing comprehensive test suite...")
    print("This will run all Phase 8 tests and generate detailed reports.")
    print()
    
    # Run all tests
    runner = Phase8TestRunner()
    runner.run_all_tests()
    
    # Generate and display summary
    print("\n")
    summary = runner.generate_summary_report()
    print(summary)
    
    # Check quality gates
    print("\n")
    checker = QualityGateChecker(runner.results)
    quality_report = checker.generate_quality_report()
    print(quality_report)
    
    # Save all reports
    runner.save_reports()
    
    # Save quality gate report
    report_dir = Path('tests/reports')
    report_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    quality_path = report_dir / f'quality_gates_{timestamp}.txt'
    with open(quality_path, 'w', encoding='utf-8') as f:
        f.write(quality_report)
    print(f"✓ Quality gate report saved: {quality_path}")
    
    print("\n" + "=" * 70)
    print("PHASE 8 TEST RUN COMPLETE")
    print("=" * 70)
    
    # Return exit code based on quality gates
    passed, _ = checker.check_all_gates()
    return 0 if passed else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
