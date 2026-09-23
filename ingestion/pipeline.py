import os
from ingestion.extractors import csv_extractor, excel_extractor, pdf_extractor
from ingestion.detectors.bank_detector import detect_parser
from ingestion.cleaning.narration_cleaner import clean as clean_narration
from ingestion.cleaning.deduplicator import dedupe, dedupe_cross_file

_EXTRACTORS = {
    ".csv": (csv_extractor.extract, "csv"),
    ".xlsx": (excel_extractor.extract, "xlsx"),
    ".xls": (excel_extractor.extract, "xlsx"),
    ".pdf": (pdf_extractor.extract, "pdf"),
}


def run(filepath: str) -> list:
    """Single-file pipeline: detect format -> extract -> detect bank -> parse -> clean -> dedupe."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _EXTRACTORS:
        raise ValueError(f"Unsupported file format: {ext}")

    extract_fn, source_format = _EXTRACTORS[ext]
    df = extract_fn(filepath)

    parser = detect_parser(df)
    source_file = os.path.basename(filepath)
    transactions = parser.parse(df, source_file, source_format)

    for t in transactions:
        t.clean_narration = clean_narration(t.raw_narration)

    transactions = dedupe(transactions)
    return transactions


def run_batch(filepaths: list) -> dict:
    """Multi-file upload pipeline: runs each file through the single-file
    pipeline independently (so one bad file doesn't abort the whole batch),
    merges results, then applies cross-file dedup for overlapping statement
    periods uploaded as separate files.

    Returns:
        {
            "transactions": [...],       # merged, cross-file-deduped
            "per_file_counts": {filename: count, ...},
            "files_processed": int,
            "files_failed": int,
            "errors": [{"file": ..., "error": ...}, ...],
            "duplicates_removed_cross_file": int,
        }
    """
    all_transactions = []
    per_file_counts = {}
    errors = []

    for filepath in filepaths:
        filename = os.path.basename(filepath)
        try:
            txns = run(filepath)
            all_transactions.extend(txns)
            per_file_counts[filename] = len(txns)
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})
            per_file_counts[filename] = 0

    before = len(all_transactions)
    deduped = dedupe_cross_file(all_transactions)

    return {
        "transactions": deduped,
        "per_file_counts": per_file_counts,
        "files_processed": len(filepaths) - len(errors),
        "files_failed": len(errors),
        "errors": errors,
        "duplicates_removed_cross_file": before - len(deduped),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 -m ingestion.pipeline <file1> [file2] [file3] ...")
        sys.exit(1)

    if len(sys.argv) == 2:
        txns = run(sys.argv[1])
        print(f"Parsed {len(txns)} transactions, bank={txns[0].bank if txns else 'N/A'}")
        for t in txns[:3]:
            print(t.to_dict())
    else:
        result = run_batch(sys.argv[1:])
        print(f"Files processed: {result['files_processed']}, failed: {result['files_failed']}")
        print(f"Per-file counts: {result['per_file_counts']}")
        print(f"Cross-file duplicates removed: {result['duplicates_removed_cross_file']}")
        print(f"Total merged transactions: {len(result['transactions'])}")
        if result["errors"]:
            print(f"Errors: {result['errors']}")

