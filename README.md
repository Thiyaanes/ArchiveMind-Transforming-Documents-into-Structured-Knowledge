# ArchiveMind-Transforming Documents into Structured Knowledge

ArchiveMind is an open-source multilingual document digitization and structuring pipeline that transforms books, legacy-language PDFs and scanned documents into structured JSON data for AI model training, RAG systems, digital libraries, search platforms and intelligent applications.

**Unstructured Documents → Extraction → OCR / Encoding Recovery → Structured JSON → Model Training & Applications**

# ArchiveMind

Documents are often created for humans to read, but AI systems and software applications need structured, machine-readable data.

Real-world document collections can contain:

- Unicode text PDFs
- Legacy Tamil / TSCII encoded documents
- Scanned and image-only PDFs
- Different chapter and section formats
- Separate translations or transliterations

ArchiveMind provides a unified pipeline for processing these different document formats and converting their content into structured JSON.

# Architecture


                         ┌───────────────┐
                         │   PDF / Book  │
                         └───────┬───────┘
                                 │
                                 ▼
                      ┌────────────────────┐
                      │ Document Detection │
                      └─────────┬──────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        Unicode PDF         TSCII PDF        Scanned PDF
              │                 │                 │
        Text Extraction   TSCII → Unicode        OCR
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                       Section Detection
                                │
                                ▼
                         Text Cleaning
                                │
                                ▼
                       Translation Sync
                                │
                                ▼
                       Structured JSON
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
             Search        AI Model Training    RAG
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                         Applications

# How to Run
# Clone the repository:

git clone Thiyaanes/ArchiveMind-Transforming-Documents-into-Structured-Knowledge.git


cd ArchiveMind-Transforming-Documents-into-Structured-Knowledge

# Install dependencies:

pip install -r requirements.txt

Or install the dependencies manually:

pip install PyMuPDF open-tamil pytesseract Pillow

# Install Tesseract OCR.

# To install Tesseract

winget install --id UB-Mannheim.TesseractOCR

winget --version

tesseract --version

If that fails with "not recognized," find where it installed (commonly C:\Program Files\Tesseract-OCR) and add it to PATH:

$env:Path += ";C:\Program Files\Tesseract-OCR"

[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\Tesseract-OCR", "Machine")

OCR functionality requires the Tesseract OCR application to be installed on your system.

For Tamil OCR, make sure the Tamil language data (tam) is installed.

# Usage
# Tamil Book
python book_to_json.py book.pdf --output output/book.json --section-regex "பாடல்\s*\d+.*" --lang ta
# English Book
python book_to_json.py book.pdf --output output/book.json --section-regex "^Chapter\s+\d+.*$" --lang en

The --section-regex option allows you to define how chapters, poems, verses, or other sections should be detected.

# Project Structure
book_to_json.py - Main document processing pipeline
requirements.txt - Python dependencies
output/ - Generated structured JSON files
PDF / Book input files - Documents processed by the pipeline
# Features
- Extract text from standard Unicode PDFs
- Process legacy Tamil / TSCII encoded documents
- OCR scanned and image-only PDFs
- Automatically detect sections using regular expressions
- Support Tamil and English documents
- Align translations or transliterations with original content
- Generate structured JSON output
- Generate extraction quality information
- Detect OCR pages and TSCII pages
- Identify empty or suspiciously short sections
- Detect potentially garbled text
- Prepare document data for AI training, RAG, search, and digital libraries
# Structured JSON Output

Example output:

{\
  "id": "sec001",\
  "number": 1,\
  "title": "Introduction",\
  "originalLines": [],\
  "translatedLines": [],\
  "syncedLines": []\
}
# The structured JSON format makes the extracted document content easier to use with:
- AI / LLM training
- RAG systems
- Search engines
- Digital libraries
- Intelligent applications
# Extraction Quality Reports
# ArchiveMind can provide extraction quality information such as:

- Number of OCR pages
- Number of TSCII pages
- Number of plain-text pages
- Total number of detected sections
- Empty sections
- Suspiciously short sections
- Potentially garbled text

For more details, see the comments and documentation in the project files.

If you have any doubt, contact me through thiyaanesv@gmail.com.
