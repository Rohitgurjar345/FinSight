def _has_enough_signal(t) -> bool:
    """A zero amount is usually a parsing artifact from a missing/malformed
    value, not a real $0 transaction — and a blank/"nan" narration gives no
    identifying text either. Without a real date, real narration, and a
    non-zero amount, there isn't enough signal to safely call two rows
    duplicates; wrongly dropping real transactions is worse than leaving a
    few uncertain "duplicates" in."""
    narration = (t.raw_narration or "").strip().lower()
    return bool(t.date) and narration not in ("", "nan", "none") and t.amount != 0


def dedupe(transactions: list) -> list:
    """Removes transactions with a duplicate transaction_id (same date, raw
    narration, amount, and source file — catches re-uploaded/overlapping
    statement periods within a single file). Rows with insufficient
    identifying signal (see _has_enough_signal) are always kept rather than
    risked as false-positive collapses."""
    seen = set()
    result = []
    for t in transactions:
        if not _has_enough_signal(t):
            result.append(t)
            continue
        if t.transaction_id in seen:
            continue
        seen.add(t.transaction_id)
        result.append(t)
    return result


def dedupe_cross_file(transactions: list) -> list:
    """For multi-file uploads: catches the same transaction appearing in
    TWO DIFFERENT files (e.g. overlapping statement periods across two
    uploads), which per-file transaction_id can't catch since it includes
    source_file in its hash. Matches on (date, raw_narration, amount) only,
    keeps the first occurrence (by list order). Same signal guard as
    dedupe() — see _has_enough_signal."""
    seen = set()
    result = []
    for t in transactions:
        if not _has_enough_signal(t):
            result.append(t)
            continue
        narration = (t.raw_narration or "").strip().lower()
        content_key = (t.date, narration, round(t.amount, 2))
        if content_key in seen:
            continue
        seen.add(content_key)
        result.append(t)
    return result
