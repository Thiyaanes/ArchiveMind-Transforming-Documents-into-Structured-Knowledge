import argparse
import json
import os
import re
import sys

import fitz  # PyMuPDF

try:
    import tamil  # open-tamil, for TSCII -> Unicode conversion
    HAVE_TAMIL = True
except ImportError:
    HAVE_TAMIL = False

try:
    import pytesseract
    from PIL import Image
    import io
    HAVE_OCR = True
except ImportError:
    HAVE_OCR = False


# ---------------------------------------------------------------------------
# Encoding / extraction helpers
# ---------------------------------------------------------------------------

def page_has_text_layer(page, min_chars=20):
    """Heuristic: does this page have a real extractable text layer,
    or is it just a scanned image?"""
    return len(page.get_text('text').strip()) >= min_chars


def looks_like_tscii(text, sample_size=2000):
    """Heuristic encoding detector.

    TSCII text, when read as normal Unicode, tends to come through as a
    dense run of Latin-1 punctuation/symbol characters rather than actual
    Tamil Unicode codepoints (U+0B80-U+0BFF) or normal English letters.
    We sample the text and score which bucket it falls into.
    """
    sample = text[:sample_size]
    if not sample.strip():
        return False

    tamil_unicode = sum(1 for c in sample if '\u0B80' <= c <= '\u0BFF')
    ascii_letters = sum(1 for c in sample if c.isascii() and c.isalpha())
    total = len(sample)

    tamil_ratio = tamil_unicode / total
    ascii_ratio = ascii_letters / total

    if tamil_ratio > 0.05 or ascii_ratio > 0.3:
        return False

    symbol_noise = sum(1 for c in sample if not c.isspace() and not c.isalnum())
    return (symbol_noise / total) > 0.3


def ocr_page(page, lang='tam+eng'):
    """Rasterize a page and run Tesseract OCR on it."""
    if not HAVE_OCR:
        raise RuntimeError(
            "OCR requested but pytesseract/Pillow are not installed. "
            "Run: pip install pytesseract pillow --break-system-packages "
            "(and ensure the tesseract binary + tamil traineddata are installed)"
        )
    pix = page.get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes('png')))
    return pytesseract.image_to_string(img, lang=lang)


def load_pdf_text(pdf_path, force_ocr=False, ocr_lang='tam+eng', auto_detect=True):
    """Read every page of a PDF, choosing the right extraction path per page:
       OCR -> if no text layer or --ocr forced
       TSCII conversion -> if auto-detected as legacy Tamil encoding
       plain text -> otherwise
    Returns (full_text, stats) where stats reports what happened per page.
    """
    doc = fitz.open(pdf_path)
    pages = []
    stats = {'ocr_pages': 0, 'tscii_pages': 0, 'plain_pages': 0, 'total_pages': len(doc)}

    for page in doc:
        if force_ocr or not page_has_text_layer(page):
            text = ocr_page(page, lang=ocr_lang)
            stats['ocr_pages'] += 1
            pages.append(text)
            continue

        raw_text = page.get_text('text')

        if auto_detect and HAVE_TAMIL and looks_like_tscii(raw_text):
            try:
                b = raw_text.encode('latin1', errors='ignore')
                u = tamil.tscii.convert_to_unicode(b.decode('latin1'))
                stats['tscii_pages'] += 1
                pages.append(u)
                continue
            except Exception:
                pass

        stats['plain_pages'] += 1
        pages.append(raw_text)

    return '\n'.join(pages), stats


def load_translation_file(txt_path, header_pattern):
    """Optional companion translation/transliteration .txt file, parsed
    into a dict keyed by section number. header_pattern needs group(1) as
    the section number and group(2) as an optional title."""
    trans_dict = {}
    if not txt_path or not os.path.exists(txt_path):
        return trans_dict

    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()

    matches = list(re.finditer(header_pattern, text, re.MULTILINE))
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk = text[start:end]
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        trans_dict[num] = {'title': title, 'lines': lines}

    return trans_dict


def clean_line(line, skip_prefixes=(), skip_substrings=()):
    line = line.strip()
    if not line:
        return None
    if any(line.startswith(p) for p in skip_prefixes):
        return None
    if any(s in line for s in skip_substrings):
        return None
    line = re.sub(r'\s*\.{2,}\s*', ' ', line)
    line = re.sub(r'^-+$', '', line).strip()
    return line if line else None


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------

def score_garbled(text, sample_size=500):
    """Rough 0-1 'garbled-ness' score for a chunk of text: higher = more
    likely to still be broken encoding/OCR noise rather than clean text."""
    sample = text[:sample_size]
    if not sample.strip():
        return 0.0
    bad = sum(1 for c in sample if not c.isspace() and not c.isalnum()
              and not ('\u0B80' <= c <= '\u0BFF'))
    return round(bad / len(sample), 3)


def build_quality_report(records, extraction_stats):
    total = len(records)
    empty_sections = [r['number'] for r in records if not r['originalLines']]
    short_sections = [r['number'] for r in records if 0 < len(r['originalLines']) < 2]
    garbled_scores = [score_garbled(' '.join(r['originalLines'])) for r in records if r['originalLines']]
    avg_garbled = round(sum(garbled_scores) / len(garbled_scores), 3) if garbled_scores else 0.0

    return {
        'extraction': extraction_stats,
        'sections_total': total,
        'sections_empty': empty_sections,
        'sections_suspiciously_short': short_sections,
        'avg_garbled_score': avg_garbled,
        'note': 'garbled_score closer to 1.0 means the text likely still has encoding/OCR noise',
    }


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_book_to_json(
    pdf_path,
    output_path,
    section_header_regex,
    lang='ta',
    force_ocr=False,
    ocr_lang=None,
    auto_detect_encoding=True,
    translation_txt_path=None,
    translation_header_regex=None,
    skip_prefixes=(),
    skip_substrings=(),
    extra_fields=None,
    report_path=None,
):
    print(f"Reading PDF: {pdf_path}")
    default_ocr_lang = 'tam+eng' if lang == 'ta' else 'eng'
    full_text, extraction_stats = load_pdf_text(
        pdf_path,
        force_ocr=force_ocr,
        ocr_lang=ocr_lang or default_ocr_lang,
        auto_detect=auto_detect_encoding,
    )
    print(f"Extraction stats: {extraction_stats}")

    headers = list(re.finditer(section_header_regex, full_text, re.MULTILINE))
    print(f"Found {len(headers)} sections.")
    if not headers:
        print("WARNING: no sections matched -- check --section-regex against the extracted text.")

    trans_dict = {}
    if translation_txt_path and translation_header_regex:
        trans_dict = load_translation_file(translation_txt_path, translation_header_regex)
        print(f"Loaded {len(trans_dict)} translation entries.")

    records = []
    for i, m in enumerate(headers):
        section_num = i + 1
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(full_text)
        chunk = full_text[start:end]

        lines = []
        for raw_line in chunk.split('\n'):
            cleaned = clean_line(raw_line, skip_prefixes, skip_substrings)
            if cleaned:
                lines.append(cleaned)

        title = lines[0] if lines else f"Section {section_num}"
        trans_entry = trans_dict.get(section_num, {})
        translated_lines = trans_entry.get('lines', [])

        synced = []
        max_len = max(len(lines), len(translated_lines)) if translated_lines else len(lines)
        for idx in range(max_len):
            synced.append({
                'index': idx,
                'originalText': lines[idx] if idx < len(lines) else '',
                'translation': translated_lines[idx] if idx < len(translated_lines) else '',
            })

        record = {
            'id': f'sec{section_num:03d}',
            'number': section_num,
            'title': title,
            'translatedTitle': trans_entry.get('title', ''),
            'originalLines': lines,
            'translatedLines': translated_lines,
            'syncedLines': synced,
        }
        if extra_fields:
            record.update(extra_fields)
        records.append(record)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(records)} records to '{output_path}'")

    report = build_quality_report(records, extraction_stats)
    if report_path:
        os.makedirs(os.path.dirname(report_path) or '.', exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote quality report to '{report_path}'")
    else:
        print("Quality report:", json.dumps(report, indent=2, ensure_ascii=False))

    return records, report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert a Tamil/English book PDF into structured JSON, "
                    "with automatic OCR fallback for scanned pages and "
                    "automatic TSCII legacy-encoding detection."
    )
    parser.add_argument('pdf_path', help="Path to the source PDF")
    parser.add_argument('--output', '-o', required=True, help="Path to write output JSON")
    parser.add_argument('--section-regex', required=True,
                         help="Regex matching the start of each section/chapter/poem header")
    parser.add_argument('--lang', choices=['ta', 'en'], default='ta',
                         help="Primary language of the book (affects OCR language pack default)")
    parser.add_argument('--ocr', action='store_true',
                         help="Force OCR on every page, even if a text layer exists")
    parser.add_argument('--ocr-lang', default=None,
                         help="Tesseract language code(s), e.g. 'tam', 'eng', 'tam+eng'")
    parser.add_argument('--no-auto-detect', action='store_true',
                         help="Disable automatic TSCII encoding detection")
    parser.add_argument('--translation-txt', default=None,
                         help="Optional companion translation/transliteration .txt file")
    parser.add_argument('--translation-regex', default=None,
                         help="Header regex for the translation file (needs 2 capture groups: number, title)")
    parser.add_argument('--skip-prefixes', nargs='*', default=[],
                         help="Lines starting with any of these strings are dropped")
    parser.add_argument('--skip-substrings', nargs='*', default=[],
                         help="Lines containing any of these strings are dropped")
    parser.add_argument('--report', default=None,
                         help="Path to write a JSON quality report (defaults to printing to stdout)")

    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"ERROR: PDF not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    convert_book_to_json(
        pdf_path=args.pdf_path,
        output_path=args.output,
        section_header_regex=args.section_regex,
        lang=args.lang,
        force_ocr=args.ocr,
        ocr_lang=args.ocr_lang,
        auto_detect_encoding=not args.no_auto_detect,
        translation_txt_path=args.translation_txt,
        translation_header_regex=args.translation_regex,
        skip_prefixes=tuple(args.skip_prefixes),
        skip_substrings=tuple(args.skip_substrings),
        extra_fields={'language': args.lang},
        report_path=args.report,
    )


if __name__ == '__main__':
    main()
