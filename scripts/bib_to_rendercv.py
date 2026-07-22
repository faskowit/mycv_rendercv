#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BEGIN_MARKER = "    # BEGIN GENERATED BIBLIOGRAPHY"
END_MARKER = "    # END GENERATED BIBLIOGRAPHY"

# Defaults for this CV. Forks can override the owner name from the command line;
# adjust the classification constants below only when their publication taxonomy
# differs from the four RenderCV sections produced by this script.
DEFAULT_OWNER_LAST_NAME = "faskowitz"
PREPRINT_JOURNALS = {"biorxiv", "bioarxiv", "arxiv"}
POSTER_INCLUDE_KEYWORD = "firstauth"


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]
    index: int


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def latex_to_unicode(text: str) -> str:
    special_replacements = {
        r"\ss": "ß",
        r"\ae": "æ",
        r"\AE": "Æ",
        r"\oe": "œ",
        r"\OE": "Œ",
        r"\o": "ø",
        r"\O": "Ø",
        r"\aa": "å",
        r"\AA": "Å",
        r"\l": "ł",
        r"\L": "Ł",
    }
    for source, target in special_replacements.items():
        text = text.replace(source, target)

    combining_marks = {
        "'": "\u0301",
        "`": "\u0300",
        "^": "\u0302",
        '"': "\u0308",
        "~": "\u0303",
        "=": "\u0304",
        ".": "\u0307",
        "c": "\u0327",
        "v": "\u030C",
        "u": "\u0306",
        "H": "\u030B",
        "k": "\u0328",
    }

    def replace_braced_accent(match: re.Match[str]) -> str:
        accent = match.group(1)
        character = match.group(2)
        return unicodedata.normalize("NFC", character + combining_marks[accent])

    accent_pattern = r"\{?\\([`'\"^~=.cvuHk])\{?([A-Za-z])\}?\}?"
    text = re.sub(accent_pattern, replace_braced_accent, text)
    text = text.replace("{", "").replace("}", "")
    return normalize_whitespace(text)


def strip_comment_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines)


def find_matching_delimiter(text: str, start: int, opener: str, closer: str) -> tuple[str, int]:
    depth = 1
    index = start
    in_quotes = False
    escaped = False
    while index < len(text):
        char = text[index]
        if char == '"' and not escaped:
            in_quotes = not in_quotes
        elif not in_quotes:
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return text[start:index], index + 1
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
        index += 1
    raise ValueError("Unbalanced BibTeX delimiters")


def find_matching_quote(text: str, start: int) -> tuple[str, int]:
    index = start
    escaped = False
    while index < len(text):
        char = text[index]
        if char == '"' and not escaped:
            return text[start:index], index + 1
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
        index += 1
    raise ValueError("Unbalanced quoted BibTeX value")


def split_top_level(text: str, delimiter: str, maxsplit: int = 1) -> list[str]:
    parts: list[str] = []
    depth = 0
    in_quotes = False
    escaped = False
    current: list[str] = []
    for char in text:
        if char == '"' and not escaped:
            in_quotes = not in_quotes
        elif not in_quotes:
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(depth - 1, 0)
            elif char == delimiter and depth == 0 and (maxsplit <= 0 or len(parts) < maxsplit):
                parts.append("".join(current))
                current = []
                escaped = False
                continue
        current.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    parts.append("".join(current))
    return parts


def parse_bib_value(text: str, start: int) -> tuple[str, int]:
    parts: list[str] = []
    index = start

    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break

        char = text[index]
        if char == "{":
            part, index = find_matching_delimiter(text, index + 1, "{", "}")
        elif char == '"':
            part, index = find_matching_quote(text, index + 1)
        else:
            end = index
            while end < len(text) and text[end] not in ",#\n\r":
                end += 1
            part = text[index:end]
            index = end
        parts.append(part)

        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == "#":
            index += 1
            continue
        break

    cleaned = latex_to_unicode("".join(parts))
    return cleaned, index


def parse_bibtex(text: str) -> list[BibEntry]:
    text = strip_comment_lines(text)
    entries: list[BibEntry] = []
    pattern = re.compile(r"@([A-Za-z]+)\s*([({])")
    cursor = 0
    entry_index = 0

    while True:
        match = pattern.search(text, cursor)
        if not match:
            break

        entry_type = match.group(1).lower()
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        body, cursor = find_matching_delimiter(text, match.end(), opener, closer)
        key_and_fields = split_top_level(body, ",", maxsplit=1)
        if len(key_and_fields) != 2:
            continue

        key = normalize_whitespace(key_and_fields[0])
        field_block = key_and_fields[1]
        fields: dict[str, str] = {}
        position = 0
        while position < len(field_block):
            while position < len(field_block) and field_block[position] in " \t\r\n,":
                position += 1
            if position >= len(field_block):
                break

            name_end = position
            while name_end < len(field_block) and field_block[name_end] not in "= \t\r\n":
                name_end += 1
            field_name = field_block[position:name_end].strip().lower()
            position = name_end

            while position < len(field_block) and field_block[position].isspace():
                position += 1
            if position >= len(field_block) or field_block[position] != "=":
                break
            position += 1

            field_value, position = parse_bib_value(field_block, position)
            if field_name:
                fields[field_name] = field_value

            while position < len(field_block) and field_block[position] not in ",\n":
                if field_block[position].isspace():
                    position += 1
                else:
                    break
            if position < len(field_block) and field_block[position] == ",":
                position += 1

        entries.append(BibEntry(entry_type=entry_type, key=key, fields=fields, index=entry_index))
        entry_index += 1

    return entries


def month_to_number(value: str | None) -> int:
    if not value:
        return 0
    value = value.strip().lower()
    if value.isdigit():
        return int(value)
    mapping = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }
    return mapping.get(value, 0)


def sort_entries(entries: list[BibEntry]) -> list[BibEntry]:
    def sort_key(entry: BibEntry) -> tuple[int, int, int]:
        year_text = entry.fields.get("year", "0")
        year = int(year_text) if year_text.isdigit() else 0
        month = month_to_number(entry.fields.get("month"))
        return (year, month, entry.index)

    return sorted(entries, key=sort_key, reverse=True)


def classify_publication(entry: BibEntry) -> str | None:
    journal = entry.fields.get("journal", "").strip().lower()
    if entry.entry_type == "inproceedings":
        return "Peer-Reviewed Conference Proceedings"
    if journal in PREPRINT_JOURNALS:
        return "Preprints"
    if entry.entry_type == "article":
        return "Journal Articles"
    return None


def has_keyword(entry: BibEntry, keyword: str) -> bool:
    keywords = entry.fields.get("keywords", "")
    return keyword.lower() in {part.strip().lower() for part in keywords.split(",") if part.strip()}


def split_authors(author_text: str, owner_last_name: str) -> list[str]:
    authors = [normalize_whitespace(part) for part in re.split(r"\s+and\s+", author_text) if part.strip()]
    formatted: list[str] = []
    for author in authors:
        author = author.replace("*", "").strip()
        author = author.replace("{...}", "...").replace("others", "et al.")
        if "," in author:
            parts = [normalize_whitespace(part) for part in author.split(",")]
            if len(parts) == 2:
                last, first = parts
                author = f"{first} {last}".strip()
            elif len(parts) >= 3:
                last, suffix, first = parts[0], parts[1], parts[2]
                author = f"{first} {suffix} {last}".strip()
        author = normalize_whitespace(author)
        if owner_last_name and owner_last_name.casefold() in author.casefold():
            author = f"**{author}**"
        formatted.append(author)
    return formatted


def build_date(entry: BibEntry) -> int | str | None:
    year = entry.fields.get("year")
    if not year:
        return None
    month = month_to_number(entry.fields.get("month"))
    if month:
        return f"{year}-{month:02d}"
    if year.isdigit():
        return int(year)
    return year


def clean_pages(pages: str | None) -> str | None:
    if not pages:
        return None
    return pages.replace("--", "-")


def build_journal(entry: BibEntry, section_name: str) -> str | None:
    if section_name == "Peer-Reviewed Conference Proceedings":
        parts = [entry.fields.get("booktitle")]
        organization = entry.fields.get("organization") or entry.fields.get("publisher")
        if organization:
            parts.append(organization)
        details = []
        volume = entry.fields.get("volume")
        pages = clean_pages(entry.fields.get("pages"))
        if volume:
            details.append(f"Vol. {volume}")
        if pages:
            details.append(f"pp. {pages}")
        if details:
            parts.append(", ".join(details))
        return "; ".join(part for part in parts if part)
    if section_name == "Conference Posters (first-author only)":
        return entry.fields.get("note") or entry.fields.get("booktitle")

    journal = entry.fields.get("journal")
    if not journal:
        return None

    details: list[str] = []
    volume = entry.fields.get("volume")
    number = entry.fields.get("number")
    pages = clean_pages(entry.fields.get("pages"))
    if volume and number:
        details.append(f"{volume}({number})")
    elif volume:
        details.append(volume)
    if pages and section_name == "Journal Articles":
        details.append(pages)
    if details:
        return f"{journal} {' '.join(details)}"
    return journal


def build_url(entry: BibEntry) -> str | None:
    url = entry.fields.get("url")
    if url:
        return url
    doi = entry.fields.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    return None


def entry_to_reversed_numbered_entry(
    section_name: str, entry: BibEntry, owner_last_name: str
) -> dict[str, object]:
    title = entry.fields.get("title", entry.key)
    authors = ", ".join(split_authors(entry.fields.get("author", ""), owner_last_name))
    date = build_date(entry)
    journal = build_journal(entry, section_name)
    url = build_url(entry)
    metadata = f"*{journal}*" if journal else ""
    if date:
        metadata = f"{metadata} ({date})" if metadata else str(date)

    title_line = f"**{title}**"
    if url:
        title_line += f" [link]({url})"

    lines = [title_line]
    if authors:
        lines.append(authors)
    if metadata:
        lines.append(metadata)

    return {"reversed_number": " #linebreak() ".join(lines)}


def yaml_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return yaml_quote(value)
    return str(value)


def render_mapping(mapping: dict[str, object], indent: int) -> list[str]:
    lines: list[str] = []
    for key, value in mapping.items():
        prefix = " " * indent
        if isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.extend(render_mapping(item, indent + 6))
                else:
                    lines.append(f"{prefix}  - {render_scalar(item)}")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(render_mapping(value, indent + 2))
        else:
            lines.append(f"{prefix}{key}: {render_scalar(value)}")
    return lines


def render_section(section_name: str, entries: list[dict[str, object]]) -> list[str]:
    lines = [f"    {section_name}:"]
    for entry in entries:
        first = True
        for key, value in entry.items():
            if first:
                if isinstance(value, list):
                    lines.append(f"      - {key}:")
                    for item in value:
                        lines.append(f"          - {render_scalar(item)}")
                else:
                    lines.append(f"      - {key}: {render_scalar(value)}")
                first = False
                continue

            if isinstance(value, list):
                lines.append(f"        {key}:")
                for item in value:
                    lines.append(f"          - {render_scalar(item)}")
            else:
                lines.append(f"        {key}: {render_scalar(value)}")
    if not entries:
        lines.append('      - reversed_number: "No entries yet"')
    return lines


def render_generated_block(
    publication_entries: list[BibEntry],
    poster_entries: list[BibEntry],
    owner_last_name: str,
) -> str:
    section_map: dict[str, list[dict[str, object]]] = {
        "Preprints": [],
        "Journal Articles": [],
        "Peer-Reviewed Conference Proceedings": [],
        "Conference Posters (first-author only)": [],
    }

    for entry in sort_entries(publication_entries):
        section_name = classify_publication(entry)
        if section_name:
            section_map[section_name].append(
                entry_to_reversed_numbered_entry(section_name, entry, owner_last_name)
            )

    for entry in sort_entries(poster_entries):
        if has_keyword(entry, POSTER_INCLUDE_KEYWORD):
            section_name = "Conference Posters (first-author only)"
            section_map[section_name].append(
                entry_to_reversed_numbered_entry(section_name, entry, owner_last_name)
            )

    lines = [
        BEGIN_MARKER,
        "    # Generated by scripts/bib_to_rendercv.py. Edit the .bib files, then rerun the script.",
    ]
    for section_name in (
        "Preprints",
        "Journal Articles",
        "Peer-Reviewed Conference Proceedings",
        "Conference Posters (first-author only)",
    ):
        lines.extend(render_section(section_name, section_map[section_name]))
    lines.append(END_MARKER)
    return "\n".join(lines)


def replace_generated_block(yaml_text: str, generated_block: str) -> str:
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    if not pattern.search(yaml_text):
        raise ValueError("Could not find generated bibliography markers in the YAML file.")
    return pattern.sub(generated_block, yaml_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert BibTeX entries into RenderCV publication sections."
    )
    parser.add_argument(
        "--yaml",
        default=REPOSITORY_ROOT / "Joshua_Faskowitz_CV.yaml",
        help="RenderCV YAML file to update.",
    )
    parser.add_argument(
        "--publications-bib",
        default=REPOSITORY_ROOT / "bibliography/pubs.bib",
        help="BibTeX file containing journal articles, preprints, and proceedings.",
    )
    parser.add_argument(
        "--posters-bib",
        default=REPOSITORY_ROOT / "bibliography/posters.bib",
        help="BibTeX file containing posters and talks.",
    )
    parser.add_argument(
        "--owner-last-name",
        default=DEFAULT_OWNER_LAST_NAME,
        help=(
            "Last name to bold in publication author lists "
            f"(default: {DEFAULT_OWNER_LAST_NAME})."
        ),
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the updated YAML to stdout instead of writing it back to disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    yaml_path = Path(args.yaml)
    publications_bib_path = Path(args.publications_bib)
    posters_bib_path = Path(args.posters_bib)

    yaml_text = yaml_path.read_text()
    publication_entries = parse_bibtex(publications_bib_path.read_text())
    poster_entries = parse_bibtex(posters_bib_path.read_text())

    generated_block = render_generated_block(
        publication_entries, poster_entries, args.owner_last_name
    )
    updated_yaml = replace_generated_block(yaml_text, generated_block)

    if args.stdout:
        sys.stdout.write(updated_yaml)
    else:
        yaml_path.write_text(updated_yaml)
        print(
            f"Updated {yaml_path} using {publications_bib_path} and {posters_bib_path}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
