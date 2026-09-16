"""Text normalization utilities — accent-insensitive search."""

import unicodedata


def strip_accents(text: str) -> str:
    """Remove accents/diacritics: 'Saída' → 'Saida', 'Império' → 'Imperio'."""
    if not text:
        return text
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))
