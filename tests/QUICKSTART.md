# Phase 8 Quick Start Guide

## Installation

1. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

2. **Verify installation**:
```powershell
python -c "import safety, bandit, pip_audit, psutil; print('All Phase 8 dependencies installed!')"
```

## Running Tests

### Quick Test (All Suites)
```powershell
python tests/run_phase8_tests.py
```

### Individual Test Suites
```powershell
# Run specific test suite
python tests/test_connectivity_benchmarks.py
python tests/test_security_penetration.py
python tests/test_privacy_analysis.py
python tests/test_isolation_verification.py
python tests/test_data_protection_audit.py
python tests/test_dependency_security.py
```

## Security Scans

### Run all security tools
```powershell
# CVE scanning
safety check

# Static security analysis
bandit -r . -ll

# Official PyPA vulnerability scanner
pip-audit
```

## Understanding Results

### Test Reports Location
All reports saved in: `tests/reports/`

### Key Reports
- `latest_summary.txt` - Quick overview
- `latest_detailed.txt` - Full test output
- `latest_results.json` - Machine-readable results
- `quality_gates_*.txt` - Production readiness

### Quality Gates

✅ **READY FOR PRODUCTION** if:
- All test suites pass
- Security/privacy tests pass
- No critical vulnerabilities
- No test timeouts

❌ **NOT READY** if any of the above fail

## Production Checklist

Before deploying:
- [ ] Run `python tests/run_phase8_tests.py`
- [ ] Run `safety check`
- [ ] Run `bandit -r . -ll`
- [ ] Run `pip-audit`
- [ ] Review all reports
- [ ] Verify quality gates pass
- [ ] Configure isolation (Docker/sandbox)
- [ ] Set up monitoring
- [ ] Enable encryption at rest

## Common Issues

### "Test file not found"
- Ensure you're in project root directory
- Check all test files exist in `tests/` folder

### "Module not found"
- Run: `pip install -r requirements.txt`

### Tests timeout
- Check system resources
- Ensure Tor is not blocking
- Run individual tests to isolate issue

### Security tools not found
- Install: `pip install safety bandit pip-audit`

## Need Help?

1. Check `tests/PHASE8_GUIDE.md` for detailed documentation
2. Review test output in `tests/reports/latest_detailed.txt`
3. Run tests individually to isolate failures

## Continuous Integration

Add to CI/CD pipeline:
```yaml
- run: pip install -r requirements.txt
- run: python tests/run_phase8_tests.py
- run: safety check
- run: bandit -r . -ll
```

---

**Quick Reference**: Phase 8 Testing & Quality Gates
