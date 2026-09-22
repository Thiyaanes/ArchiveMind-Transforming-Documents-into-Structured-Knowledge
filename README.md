# ArchiveMind-Transforming Documents into Structured Knowledge
ArchiveMind is an open-source multilingual document digitization and structuring pipeline that transforms books, legacy-language PDFs, and scanned documents into structured JSON data for AI model training, RAG systems, digital libraries, search platforms, and intelligent applications.

Unstructured Documents → Extraction → OCR / Encoding Recovery → Structured JSON → Model Training & Applications

# ArchiveMind

Documents are often created for humans to read, but AI systems and software applications need structured, machine-readable data.

Real-world document collections can contain:

 Unicode text PDFs
 Legacy Tamil / TSCII encoded documents
 Scanned and image-only PDFs
 Different chapter and section formats
 Separate translations or transliterations

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
# Installation
1. Clone the repository
git clone https://github.com/Thiyaanes/ArchiveMind-Transforming-Documents-into-Structured-Knowledge.git
cd ArchiveMind-Transforming-Documents-into-Structured-Knowledge
2. Install Python dependencies
pip install -r requirements.txt

Or install the dependencies manually:

pip install PyMuPDF open-tamil pytesseract Pillow
3. OCR Setup

OCR functionality requires the Tesseract OCR application to be installed on your system.

For Tamil OCR, the appropriate Tamil language data (tam) must also be installed.

For Tamil Book
python book_to_json.py book.pdf --output output/book.json --section-regex "பாடல்\s*\d+.*" --lang ta

For English Book
python book_to_json.py book.pdf --output output/book.json --section-regex "^Chapter\s+\d+.*$" --lang en

 if u have any doubt contact me through thiyaanesv@gmail.com
