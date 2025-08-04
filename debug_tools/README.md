# Debug Tools

This directory contains specialized tools for protocol analysis, testing, and debugging the Arris modem client. These tools are specifically designed to help maintain compatibility with future Arris firmware changes and detect protocol modifications through comprehensive data capture and analysis.

## 🔧 Available Tools

### [`enhanced_deep_capture.py`](enhanced_deep_capture.py) - Browser Protocol Capture Tool

**Purpose**: Capture complete browser sessions to understand the "ground truth" HNAP protocol implementation using real browser automation.

**Key Features**:
- **Dual Export System**: Creates both HAR files (Chrome DevTools compatible) and structured JSON data
- **Complete Session Recording**: Full login flow, authentication sequence, and all HNAP requests/responses
- **Browser Storage Capture**: Comprehensive timeline of cookies, localStorage, and sessionStorage changes
- **Network Traffic Analysis**: Request timing, sequencing, and header analysis
- **Console Log Recording**: JavaScript errors and debug information capture
- **Playwright Integration**: Uses Chromium automation for authentic browser behavior

**Technical Implementation**:
- Implements comprehensive logging with timestamps for all capture events
- Configurable log levels (INFO, DEBUG) for different analysis needs
- Real-time event listeners for request/response correlation
- Automatic file verification and export validation
- Error handling with screenshot capture on failures

**When to Use**:
- **Firmware Update Analysis**: Establish baseline before/after Arris firmware updates
- **Protocol Reverse Engineering**: Understand authentic browser HNAP implementation
- **Authentication Debugging**: Compare browser vs. client authentication flows
- **New Model Support**: Reverse engineer protocol variations across Arris models
- **Response Format Changes**: Identify what browsers do differently when protocols change

**Usage Examples**:
```bash
# Standard protocol capture session
python enhanced_deep_capture.py --password "your_password"

# Custom modem configuration
python enhanced_deep_capture.py --password "admin_password" --host "192.168.1.1" --username "admin"
```

**Output Files**:
- `deep_capture.har` - HAR file for Chrome DevTools Network tab analysis
- `deep_capture.json` - Structured data for programmatic Python analysis

**Analysis Workflow**:
1. Run capture to establish authentic browser protocol baseline
2. Import HAR file into Chrome DevTools → Network tab for visual analysis
3. Use JSON data for automated comparison scripts and protocol validation
4. Wait 30+ minutes before testing client changes (avoid Arris rate limiting)
5. Compare captures across firmware versions to detect protocol changes

---

### [`hnap_raw_debugger.py`](hnap_raw_debugger.py) - Direct HNAP Protocol Debugger

**Purpose**: Direct authentication and raw HNAP response capture without browser overhead, providing unfiltered access to modem protocol responses.

**Key Features**:
- **Raw Response Capture**: Direct HNAP requests with unprocessed response data
- **Multiple Request Types**: Software info, startup connection, internet registration, and channel data
- **Response Analysis**: JSON structure validation, size analysis, and data type inspection
- **Comparison Mode**: Side-by-side raw vs. parsed data analysis
- **File Export**: Save raw responses to timestamped JSON files
- **Serial Mode Operation**: Reliable sequential requests to avoid overwhelming modems

**Technical Implementation**:
- Comprehensive logging system with configurable levels and timestamps
- Direct integration with ArrisModemStatusClient for authenticated requests
- Response structure analysis with nested key discovery
- Error handling with detailed exception reporting
- Configurable timeouts and retry mechanisms
- Memory-efficient response processing

**HNAP Request Coverage**:
- **Software Information**: Version, model, uptime data
- **Startup Connection**: Boot sequence and connection status
- **Internet Registration**: WAN status and cable registration
- **Channel Information**: Downstream/upstream channel metrics

**When to Use**:
- **Response Format Debugging**: When parsed data doesn't match expectations
- **Vendor Protocol Changes**: Detect raw response format modifications
- **Performance Analysis**: Understand actual response sizes and timing
- **Data Validation**: Verify parsing logic against raw responses
- **Firmware Impact Assessment**: Compare raw responses across firmware versions

**Usage Examples**:
```bash
# Basic raw capture and display
python hnap_raw_debugger.py --password "your_password"

# Verbose logging with file export
python hnap_raw_debugger.py --password "admin_password" --verbose --save-files

# Custom configuration with comparison analysis
python hnap_raw_debugger.py --password "password" --host "192.168.1.1" \
                           --save-files --output-dir "debug_capture" --show-comparison

# Summary-only mode for quick analysis
python hnap_raw_debugger.py --password "password" --summary-only
```

**Output Options**:
- **Console Display**: Formatted JSON responses with structure analysis
- **File Export**: Individual timestamped JSON files per request type
- **Comparison Mode**: Raw vs. parsed data side-by-side analysis
- **Summary Reports**: High-level capture statistics and structure overview

## 🎯 Strategic Use Cases

### Protocol Change Detection System

These tools provide a comprehensive **protocol change detection and analysis system**:

**Phase 1 - Baseline Establishment**:
```bash
# Capture authentic browser behavior
python enhanced_deep_capture.py --password "password"

# Capture raw protocol responses
python hnap_raw_debugger.py --password "password" --save-files --output-dir "baseline"
```

**Phase 2 - Change Detection** (after firmware updates):
```bash
# Re-capture browser behavior
python enhanced_deep_capture.py --password "password"

# Re-capture raw responses
python hnap_raw_debugger.py --password "password" --save-files --output-dir "updated"

# Compare baseline vs. updated captures
```

**Phase 3 - Impact Analysis**:
- Use HAR files in Chrome DevTools to identify request/response changes
- Compare JSON structures to detect format modifications
- Analyze timing changes and new authentication requirements

### Development and Maintenance Workflow

**Before Major Client Changes**:
```bash
# Establish current protocol state
python enhanced_deep_capture.py --password "password"
python hnap_raw_debugger.py --password "password" --save-files
```

**During Development**:
```bash
# Compare client behavior against browser baseline
python hnap_raw_debugger.py --password "password" --show-comparison
```

**After Implementation**:
```bash
# Validate against authentic browser behavior
python enhanced_deep_capture.py --password "password"
```

### Troubleshooting Protocol Issues

**Authentication Problems**:
1. Use `enhanced_deep_capture.py` to see exact browser authentication flow
2. Use `hnap_raw_debugger.py` to test direct authentication
3. Compare request headers and timing between browser and client

**Response Parsing Issues**:
1. Use `hnap_raw_debugger.py --show-comparison` to see raw vs. parsed data
2. Use `--save-files` to export raw responses for detailed analysis
3. Use `--verbose` for detailed request/response logging

## 📊 Understanding Output

### Enhanced Deep Capture Analysis

**HAR File Usage**:
- Import into Chrome DevTools → Network tab
- Filter for `/HNAP1/` requests to see protocol interactions
- Analyze authentication sequence and cookie handling
- Compare request timing and header patterns

**JSON File Structure**:
```json
{
  "timestamp": "ISO timestamp",
  "requests": [/* All captured requests/responses */],
  "cookies": [/* Cookie timeline snapshots */],
  "console": [/* Browser console logs */],
  "storage": [/* localStorage/sessionStorage snapshots */],
  "timing": [/* Request timing analysis */]
}
```

### Raw HNAP Debugger Analysis

**Response Structure Analysis**:
- **Size Metrics**: Character count and byte size analysis
- **JSON Validation**: Structural integrity verification
- **Key Discovery**: Top-level and nested key identification
- **Data Type Analysis**: Value type classification

**Comparison Mode Output**:
- **Parsed Summary**: High-level status information
- **Raw Data Preview**: Unprocessed response content
- **Structure Comparison**: Parsing accuracy verification

## 🔍 Troubleshooting

### Common Issues and Solutions

**"Playwright not installed" Error**:
```bash
pip install playwright
playwright install chromium
```

**"Authentication failed" Errors**:
- Verify password accuracy and modem accessibility
- Check for rate limiting from recent requests (wait 30+ minutes)
- Ensure modem is not in a restricted state

**"HAR file not created" Issues**:
- Verify Playwright Chromium installation
- Check file system permissions in working directory
- Review console output for browser automation errors

**"HTTP compatibility issues" Warnings**:
- This is expected behavior with Arris modems
- Focus on overall capture success rather than individual request failures
- Use verbose logging to identify specific compatibility patterns

### Debug Mode Operation

Enable detailed logging and analysis:
```bash
# Enhanced capture with full debugging
python enhanced_deep_capture.py --password "password" --verbose

# Raw debugger with comprehensive logging
python hnap_raw_debugger.py --password "password" --verbose --show-comparison
```

Debug mode provides:
- **Detailed HTTP request/response logging**
- **Timing analysis for all operations**
- **Error stack traces and recovery information**
- **Browser automation step-by-step logging**

## 🚀 Integration with Development Workflow

### Pre-Development Protocol Analysis
```bash
# Establish current protocol baseline
python enhanced_deep_capture.py --password "$MODEM_PASSWORD"
python hnap_raw_debugger.py --password "$MODEM_PASSWORD" --save-files --output-dir "baseline"
```

### Development Validation
```bash
# Test current implementation against raw responses
python hnap_raw_debugger.py --password "$MODEM_PASSWORD" --show-comparison --verbose
```

### Release Preparation
```bash
# Comprehensive protocol validation
python enhanced_deep_capture.py --password "$MODEM_PASSWORD"
python hnap_raw_debugger.py --password "$MODEM_PASSWORD" --save-files --summary-only
```

### Monthly Protocol Monitoring
```bash
# Automated protocol change detection
python enhanced_deep_capture.py --password "$MODEM_PASSWORD"
python hnap_raw_debugger.py --password "$MODEM_PASSWORD" --save-files --output-dir "monthly_$(date +%Y%m)"
```

## 📈 Performance Considerations

### Optimal Capture Timing
- **Browser Capture**: 2-3 minutes for complete session recording
- **Raw Debugging**: 30-60 seconds for all HNAP request types
- **Rate Limiting**: Wait 30+ minutes between intensive capture sessions

### Resource Usage
- **Enhanced Deep Capture**: Requires Chromium browser automation (higher memory)
- **Raw HNAP Debugger**: Lightweight direct HTTP requests (minimal resources)
- **File Output**: HAR files typically 100KB-1MB, JSON files 10-50KB

### Network Impact
- **Browser Capture**: Mimics normal user browsing patterns
- **Raw Debugging**: Direct protocol requests with configurable delays
- **Modem Compatibility**: Serial mode prevents overwhelming Arris request handling

---

## 📝 Security and Operational Notes

- **Credential Security**: Never commit passwords or captured authentication data
- **Browser Automation**: Enhanced capture requires Chromium via Playwright
- **Protocol Compatibility**: Tools designed for Arris S34 (and likely S33/SB8200) DOCSIS 3.1 modems
- **Data Retention**: Captured files may contain sensitive modem configuration data

These tools represent the culmination of extensive protocol analysis and provide a robust foundation for maintaining long-term compatibility with Arris modem firmware evolution. They enable proactive detection of protocol changes and comprehensive debugging of client-modem communication patterns.
