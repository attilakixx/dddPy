# dddPy
DDD file reader written in Python for VU and driver tachograph files.

## Functions
- Open `.ddd` and `.DDD` files with a Tkinter GUI (file picker + auto-open).
- Detect file type (driver card vs vehicle unit) and show a Summary tab.
- Validate VU parts and driver-card EF parts (valid/invalid/missing).
- Show key card identification/licence data for driver cards.
- Display events, faults, overspeeding, and activity timelines (daily blocks).
- Render driver/co-driver activity headers (insert/withdraw info).
- Show country codes for all NationNumeric values.

## Screenshot
![dddPy screenshot](<Screenshot from 2025-12-29 21-34-35.png>)

## Installation
### Run from source (Linux/Windows)
1. Install Python 3.
2. From the project folder:
   - Install deps: `python3 -m pip install -r requirements-build.txt`
   - Run the app: `python3 app.py`

### Build a standalone app
- The build scripts bootstrap a local `.venv-build` and install build deps.
- Linux: run `./build_linux.sh` and use `dist/dddPy`
- Windows: run `build_windows.bat` and use `dist\\dddPy.exe`

## Known limitations
- VU validation checks structure only; signature verification is not implemented.
- Gen2 driver-card certificates (ECC) are not verified yet.
- Some record types are parsed minimally; unknown fields may be skipped or shown raw.

## Roadmap
1. Complete parsing coverage
   - Decode remaining record types and fields per spec (VU + driver card).
   - Match the PDF output for all tables.
2. Add export formats
   - JSON for raw structured data.
   - CSV summaries for common reports (activities, events, faults).
3. Strengthen validation
   - VU signature verification.
   - Gen2 (ECC) certificate verification.
4. Testing and validation
   - Unit tests for low-level parsers and record decoding.
   - Golden tests against the sample `.ddd` files.
5. CLI tooling
   - Batch parsing and export from the command line.
