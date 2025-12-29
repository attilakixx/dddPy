# dddPy
DDD file reader written in Python for VU and driver tachograph files.

## Roadmap
1. Study file formats and requirements
   - Read EU 799/2016 and ISO 16844 series (card/VU data, file structure, data types).
   - Identify mandatory data elements for VU vs driver card files and any version differences.
2. Collect and label sample data
   - Use sample `.ddd` files from `hidden/` and tag them as VU or driver.
   - Capture expected outputs for a few files to use as golden references.
3. Build a binary parsing core
   - Implement a byte reader with helpers for BCD, bitfields, timestamps, and fixed-length strings.
   - Parse the file header and detect file type/version.
   - Implement block/record decoding per spec and map them to structured Python objects.
4. Validate and harden parsing
   - Add integrity checks required by the spec (lengths, checksums/CRC if present).
   - Make parsing resilient to partial or unknown records with clear error reporting.
5. Create a normalized data model
   - Define shared classes/structures for drivers, vehicles, activities, events, faults, and calibration.
   - Normalize VU and driver outputs into the same schema for easy UI and export.
6. Add export formats
   - JSON for raw structured data.
   - CSV summaries for common reports (activities, events, faults).
7. Build a simple GUI
   - Tkinter-based file picker and summary view.
   - Tabs or tree view for major record groups (identification, activities, events, faults).
   - Export buttons (JSON/CSV).
8. Testing and validation
   - Unit tests for low-level parsers and record decoding.
   - Golden tests against the sample `.ddd` files.
9. Packaging
   - Provide a CLI entry point for batch parsing.
   - Bundle the GUI as a standalone app (optional: PyInstaller).
