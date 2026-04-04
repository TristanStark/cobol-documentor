from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from src.copy.copy_lookup import CopyLookup

@dataclass
class CopyReplacement:
    old_value: str
    new_value: str
    old_is_pseudotext: bool
    new_is_pseudotext: bool


@dataclass
class ParsedCopyStatement:
    copy_name: str
    replacements: List[CopyReplacement]


def _is_cobol_comment_line(line: str) -> bool:
    """
    COBOL fixed-format:
    colonne 7 = indicateur.
    * / D => commentaire / debug line
    """
    return len(line) >= 7 and line[6] in {"*", "/", "D"}


def _strip_comment_lines_for_parsing(lines: List[str]) -> str:
    """
    Retire uniquement les lignes de commentaire COBOL du buffer COPY
    pour faciliter le parsing, sans impacter le contenu final.
    """
    kept = [line for line in lines if not _is_cobol_comment_line(line)]
    return "".join(kept)


def _tokenize_copy_statement(statement: str) -> List[str]:
    """
    Tokenizer minimal pour COPY ... REPLACING ...

    Gère :
    - pseudo-text COBOL : == ... ==
    - chaînes "..."
    - chaînes '...'
    - mots nus
    - point final

    Exemple :
      COPY X REPLACING ==:A:== BY ==B== OLD BY NEW.
    """
    tokens: List[str] = []
    i = 0
    n = len(statement)

    while i < n:
        ch = statement[i]

        if ch.isspace():
            i += 1
            continue

        # Pseudo-text == ... ==
        if statement.startswith("==", i):
            end = statement.find("==", i + 2)
            if end == -1:
                raise ValueError(f"Pseudo-text non fermé dans COPY statement: {statement!r}")
            tokens.append(statement[i:end + 2])
            i = end + 2
            continue

        # Chaîne double quote
        if ch == '"':
            j = i + 1
            while j < n and statement[j] != '"':
                j += 1
            if j >= n:
                raise ValueError(f'Chaîne " non fermée dans COPY statement: {statement!r}')
            tokens.append(statement[i:j + 1])
            i = j + 1
            continue

        # Chaîne simple quote
        if ch == "'":
            j = i + 1
            while j < n and statement[j] != "'":
                j += 1
            if j >= n:
                raise ValueError(f"Chaîne ' non fermée dans COPY statement: {statement!r}")
            tokens.append(statement[i:j + 1])
            i = j + 1
            continue

        # Point final
        if ch == ".":
            tokens.append(".")
            i += 1
            continue

        # Mot nu
        j = i
        while j < n and (not statement[j].isspace()) and statement[j] != ".":
            j += 1
        tokens.append(statement[i:j])
        i = j

    return tokens


def _decode_copy_operand(token: str) -> tuple[str, bool]:
    """
    Retourne (valeur_sans_delimiteurs, is_pseudotext).
    """
    token = token.strip()

    if token.startswith("==") and token.endswith("==") and len(token) >= 4:
        return token[2:-2], True

    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        return token[1:-1], False

    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1], False

    return token, False


def _parse_copy_statement(statement: str) -> ParsedCopyStatement:
    """
    Parse :
      COPY NOMCOPY.
      COPY NOMCOPY REPLACING OLD BY NEW.
      COPY NOMCOPY REPLACING ==AAA== BY ==BBB== OLD2 BY NEW2.

    Remarque :
    - gestion concrète utile
    - pas de support LEADING / TRAILING
    """
    tokens = _tokenize_copy_statement(statement)

    if not tokens:
        raise ValueError("COPY statement vide.")

    if tokens[0].upper() != "COPY":
        raise ValueError(f"Instruction non COPY: {statement!r}")

    if len(tokens) < 2:
        raise ValueError(f"Nom de copy introuvable: {statement!r}")

    copy_name_raw = tokens[1]
    copy_name, _ = _decode_copy_operand(copy_name_raw)

    replacements: List[CopyReplacement] = []

    i = 2
    if i < len(tokens) and tokens[i].upper() == "REPLACING":
        i += 1

        while i < len(tokens):
            if tokens[i] == ".":
                break

            old_token = tokens[i]
            i += 1

            if i >= len(tokens) or tokens[i].upper() != "BY":
                raise ValueError(
                    f"Clause REPLACING invalide, BY attendu après {old_token!r} dans: {statement!r}"
                )
            i += 1

            if i >= len(tokens):
                raise ValueError(f"Valeur BY manquante dans: {statement!r}")

            new_token = tokens[i]
            i += 1

            old_value, old_is_pseudotext = _decode_copy_operand(old_token)
            new_value, new_is_pseudotext = _decode_copy_operand(new_token)

            replacements.append(
                CopyReplacement(
                    old_value=old_value,
                    new_value=new_value,
                    old_is_pseudotext=old_is_pseudotext,
                    new_is_pseudotext=new_is_pseudotext,
                )
            )

    return ParsedCopyStatement(
        copy_name=copy_name.strip(),
        replacements=replacements,
    )


def _replace_cobol_word(content: str, old: str, new: str) -> str:
    """
    Remplacement d'un mot COBOL isolé.
    Frontières COBOL simples : lettres, chiffres, tiret.
    """
    pattern = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(old)}(?![A-Za-z0-9-])")
    return pattern.sub(new, content)


def _apply_replacements_to_copy_content(
    copy_content: str,
    replacements: List[CopyReplacement]
) -> str:
    """
    Applique les remplacements sur le contenu brut de la copy.

    Règles concrètes :
    - pseudo-text ==...== : remplacement littéral exact, partout dans le contenu
    - mot simple : remplacement sur frontière de mot COBOL
    - chaîne quoted : traitée comme littérale simple
    """
    result = copy_content

    for repl in replacements:
        if repl.old_is_pseudotext:
            result = result.replace(repl.old_value, repl.new_value)
        else:
            result = _replace_cobol_word(result, repl.old_value, repl.new_value)

    return result


def expand_program_with_copies(file_path: str) -> List[str]:
    """
    Lit un programme COBOL et remplace chaque instruction COPY par le contenu
    réel du copybook correspondant, en gérant REPLACING.

    - conserve les commentaires
    - supporte COPY multi-lignes
    - pas de récursivité
    - renvoie la liste finale des lignes
    - écrit aussi un fichier temporaire
    """
    source_path = Path(file_path)
    program_lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

    output_lines: List[str] = []
    statement_buffer: List[str] = []
    in_copy_statement = False

    for line in program_lines:
        if not in_copy_statement:
            if _is_cobol_comment_line(line):
                output_lines.append(line)
                continue

            if re.match(r"^\s*COPY\b", line, re.IGNORECASE):
                in_copy_statement = True
                statement_buffer = [line]

                if "." in line:
                    parsed = _parse_copy_statement(_strip_comment_lines_for_parsing(statement_buffer))
                    copy_path = CopyLookup.lookup_copy(parsed.copy_name)

                    copy_content = Path(copy_path).read_text(encoding="utf-8", errors="ignore")
                    expanded_content = _apply_replacements_to_copy_content(
                        copy_content=copy_content,
                        replacements=parsed.replacements,
                    )

                    output_lines.extend(expanded_content.splitlines(keepends=True))
                    statement_buffer = []
                    in_copy_statement = False
            else:
                output_lines.append(line)
        else:
            statement_buffer.append(line)

            if "." in line:
                parsed = _parse_copy_statement(_strip_comment_lines_for_parsing(statement_buffer))
                copy_path = CopyLookup.lookup_copy(parsed.copy_name)

                copy_content = Path(copy_path).read_text(encoding="utf-8", errors="ignore")
                expanded_content = _apply_replacements_to_copy_content(
                    copy_content=copy_content,
                    replacements=parsed.replacements,
                )

                output_lines.extend(expanded_content.splitlines(keepends=True))
                statement_buffer = []
                in_copy_statement = False

    # Si le fichier se termine au milieu d'un COPY incomplet, on le garde tel quel.
    if statement_buffer:
        output_lines.extend(statement_buffer)

    return output_lines