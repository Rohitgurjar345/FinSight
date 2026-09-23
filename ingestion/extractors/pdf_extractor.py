import pandas as pd


def extract(filepath: str) -> pd.DataFrame:
    """Extracts tables from a text-layer PDF bank statement.
    Scanned/image PDFs are not supported yet (would need OCR — no sample
    scanned PDF was available to build/test against).
    """
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError(
            "pdfplumber not installed. Run: pip install pdfplumber"
        ) from e

    rows = []
    header = None
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table:
                    continue
                if header is None:
                    header = table[0]
                    rows.extend(table[1:])
                else:
                    # skip repeated header rows on later pages
                    rows.extend(table[1:] if table[0] == header else table)

    if header is None:
        raise ValueError(f"No extractable table found in {filepath}. "
                          f"If this is a scanned image PDF, OCR is required (not yet supported).")
    return pd.DataFrame(rows, columns=header)
