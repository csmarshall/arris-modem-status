# Debug Tools Directory

This directory contains specialized tools for protocol analysis, testing, and debugging the Arris modem client. These tools are specifically designed to help maintain compatibility with future Arris firmware changes and detect protocol modifications.

## 🔧 Available Tools

### [`comprehensive_test.py`](comprehensive_test.py) - Production Validation Suite

**Purpose**: Complete validation and performance testing of the Arris client implementation.

**Key Features**:
- **Performance Benchmarking**: Authentication speed, data retrieval timing, concurrent request handling
- **Data Validation**: Channel parsing accuracy, completeness scoring, format validation
- **HTTP Compatibility Analysis**: Detection and recovery from urllib3 parsing issues
- **Stress Testing**: Rapid request reliability, connection stability
- **Comparison Testing**: Performance vs original client implementation
- **Automated Recommendations**: Performance optimization suggestions

**When to Use**:
- After any code changes to validate functionality
- When investigating performance regressions
- To verify HTTP compatibility handling is working
- Before releasing new versions
- When debugging connection or parsing issues

**Usage**:
```bash
# Basic validation test
python comprehensive_test.py --password "your_password"

# Full test with debug output and result saving
python comprehensive_test.py --password "your_password" --debug --save-results

# Custom host and output file
python comprehensive_test.py --password "password" --host "192.168.1.1" --output-file "test_results.json"
```

**Output**: Detailed console logging plus optional JSON export with complete test metrics, timing data, and recommendations.

---

### [`enhanced_deep_capture.py`](enhanced_deep_capture.py) - Protocol Reverse Engineering Tool

**Purpose**: Capture complete browser sessions to understand the "ground truth" HNAP protocol implementation.

**Key Features**:
- **HAR File Export**: Complete network capture compatible with Chrome DevTools
- **JSON Data Export**: Structured data for Python analysis
- **Full Session Recording**: Login flow, authentication, all HNAP requests/responses
- **Browser Storage Capture**: Cookies, localStorage, sessionStorage timelines
- **Console Log Recording**: JavaScript errors and debug information
- **Timing Analysis**: Request timing and sequencing data

**When to Use**:
- **Before major client changes**: Establish baseline protocol behavior
- **When Arris releases firmware updates**: Detect protocol changes
- **When debugging authentication issues**: Compare browser vs client behavior
- **For new model support**: Reverse engineer protocol variations
- **When responses change unexpectedly**: Identify what browsers do differently

**Usage**:
```bash
# Standard capture session
python enhanced_deep_capture.py --password "your_password"

# Custom host
python enhanced_deep_capture.py --password "password" --host "192.168.1.1" --username "admin"
```

**Output**:
- `deep_capture.har` - HAR file for Chrome DevTools Network tab analysis
- `deep_capture.json` - Structured data for programmatic analysis

**Analysis Workflow**:
1. Run capture to establish baseline behavior
2. Import HAR file into Chrome DevTools → Network tab
3. Analyze request patterns, headers, timing
4. Use JSON data for automated comparison scripts
5. Wait 30+ minutes before testing client changes (avoid rate limiting)

## 🎯 Strategic Use Cases

### For Future Arris Firmware Changes

These tools provide a **protocol change detection system**:

1. **Baseline Establishment**: Use `enhanced_deep_capture.py` to record current firmware behavior
2. **Change Detection**: After firmware updates, run capture again and compare
3. **Validation**: Use `comprehensive_test.py` to verify client still works correctly
4. **Debugging**: When issues arise, compare browser behavior vs client behavior

### For Development Workflow

**Before Code Changes**:
```bash
# Establish performance baseline
python comprehensive_test.py --password "password" --save-results
```

**After Code Changes**:
```bash
# Validate changes didn't break anything
python comprehensive_test.py --password "password" --debug
```

**When Adding New Features**:
```bash
# Capture protocol behavior first
python enhanced_deep_capture.py --password "password"
# Then implement and validate
python comprehensive_test.py --password "password"
```

## 📊 Understanding Output

### Comprehensive Test Results

**Performance Metrics**:
- Authentication time should be < 3.0s
- Data retrieval should be < 2.0s
- HTTP compatibility issues should have >90% recovery rate
- Data completeness should be >80%

**Key Indicators**:
- `🟢 EXCELLENT` - Client performing optimally
- `🟡 GOOD` - Minor improvements possible
- `🔴 ATTENTION` - Issues requiring investigation

### Deep Capture Analysis

**HAR File**: Import into Chrome DevTools → Network tab
- Look for `/HNAP1/` requests
- Check authentication sequence
- Verify cookie handling
- Compare request timing

**JSON File**: Contains structured data for:
- Request/response correlation
- Cookie timeline analysis
- Storage state changes
- Console error detection

## 🔍 Troubleshooting

### Common Issues

**"No HAR file created"**:
- Playwright may not be installed: `pip install playwright`
- Run: `playwright install chromium`

**"Authentication failed"**:
- Verify password is correct
- Check if modem is accessible at specified host
- Ensure no rate limiting from recent requests

**"HTTP compatibility issues"**:
- This is expected with Arris modems
- Check recovery rate in comprehensive test results
- >90% recovery rate indicates good handling

### Debug Mode

Both tools support verbose debugging:
```bash
python comprehensive_test.py --password "password" --debug
```

This enables detailed HTTP request/response logging and error analysis.

## 🚀 Integration with Development

### Pre-commit Testing
Add to your development workflow:
```bash
# Quick validation before commits
python debug_tools/comprehensive_test.py --password "$MODEM_PASSWORD"
```

### Release Validation
Before releases:
```bash
# Full validation with results export
python debug_tools/comprehensive_test.py --password "$MODEM_PASSWORD" --save-results --debug
```

### Protocol Change Detection
Monthly or after firmware updates:
```bash
# Capture current protocol state
python debug_tools/enhanced_deep_capture.py --password "$MODEM_PASSWORD"
# Compare with previous captures
```

---

## 📝 Notes

- **Security**: Never commit passwords or captured data containing credentials
- **Browser Compatibility**: Deep capture requires Chrome/Chromium via Playwright
- **Performance**: Comprehensive tests take 1-2 minutes to complete fully

These tools represent the culmination of extensive HTTP compatibility debugging and provide the foundation for maintaining long-term compatibility with Arris modem firmware changes.
