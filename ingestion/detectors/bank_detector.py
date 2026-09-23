from ingestion.parsers.hdfc_parser import HDFCParser
from ingestion.parsers.icici_parser import ICICIParser
from ingestion.parsers.sbi_parser import SBIParser
from ingestion.parsers.generic_parser import GenericParser

# Order matters: check named banks first, generic is the always-true fallback
_PARSERS = [HDFCParser(), ICICIParser(), SBIParser(), GenericParser()]


def detect_parser(df):
    """Returns the first parser whose column fingerprint matches."""
    for parser in _PARSERS:
        if parser.matches(df):
            return parser
    return _PARSERS[-1]  # unreachable since GenericParser always matches
