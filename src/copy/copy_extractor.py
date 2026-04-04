from __future__ import annotations

import re
from pathlib import Path


def extract_copy_names(file_path: str) -> list[str]:
    """
    Ouvre un programme COBOL et retourne la liste des noms de COPY référencés.

    Gère notamment :
    - COPY MA-COPY.
    - COPY "MA-COPY".
    - COPY 'MA-COPY'.
    - COPY MA-COPY REPLACING ...
    - instructions sur plusieurs lignes

    Ignore :
    - les lignes de commentaires COBOL classiques (* en colonne 7)
    - les doublons
    """

    path = Path(file_path)
    content = path.read_text(encoding="utf-8", errors="ignore")

    cleaned_lines: list[str] = []

    for line in content.splitlines():
        # Ignore les lignes trop courtes
        if len(line) >= 7:
            indicator = line[6]
            # Commentaire COBOL classique : '*' en colonne 7
            if indicator == "*":
                continue

        cleaned_lines.append(line)

    cleaned_content = "\n".join(cleaned_lines)

    # Regex :
    # - cherche le mot-clé COPY
    # - récupère soit un nom nu, soit un nom entre quotes
    # - s'arrête avant le point final ou REPLACING
    pattern = re.compile(
        r"""
        \bCOPY\s+
        (?:
            "([^"]+)"        |   # COPY "XXX"
            '([^']+)'        |   # COPY 'XXX'
            ([A-Z0-9_-]+)        # COPY XXX
        )
        (?=
            \s+REPLACING\b   |   # avant REPLACING
            \s*\.            |   # avant point final
            \s*$                 # ou fin de ligne / contenu
        )
        """,
        re.IGNORECASE | re.VERBOSE | re.MULTILINE,
    )

    copies: list[str] = []
    seen: set[str] = set()

    for match in pattern.finditer(cleaned_content):
        copy_name = match.group(1) or match.group(2) or match.group(3)
        if copy_name:
            normalized = copy_name.strip()
            if normalized not in seen:
                seen.add(normalized)
                copies.append(normalized)

    return copies