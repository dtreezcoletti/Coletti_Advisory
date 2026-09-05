from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CandidateStatement:
    candidate_id: str
    text: str
    locator: str
    extraction_method: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractionResult:
    filename: str
    extraction_method: str
    candidates: tuple[CandidateStatement, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "extraction_method": self.extraction_method,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": list(self.warnings),
        }


def _candidate_id(locator: str, text: str) -> str:
    digest = hashlib.sha256(f"{locator}\x00{text}".encode("utf-8")).hexdigest()[:12].upper()
    return f"CAND-{digest}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _segments(text: str) -> Iterable[str]:
    """Yield conservative record-derived segments without interpreting them."""
    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if len(line) < 3:
            continue
        if len(line) <= 240:
            yield line
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            cleaned = _clean_text(sentence)
            if len(cleaned) >= 3:
                yield cleaned


def _dedupe(candidates: Iterable[CandidateStatement], max_candidates: int) -> tuple[CandidateStatement, ...]:
    seen: set[str] = set()
    output: list[CandidateStatement] = []
    for candidate in candidates:
        normalized = _clean_text(candidate.text).casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(candidate)
        if len(output) >= max_candidates:
            break
    return tuple(output)


def _text_candidates(text: str, *, method: str, locator_prefix: str = "line") -> list[CandidateStatement]:
    output: list[CandidateStatement] = []
    for index, segment in enumerate(_segments(text), start=1):
        locator = f"{locator_prefix} {index}"
        output.append(
            CandidateStatement(
                candidate_id=_candidate_id(locator, segment),
                text=segment,
                locator=locator,
                extraction_method=method,
            )
        )
    return output


def _extract_pdf(data: bytes) -> tuple[list[CandidateStatement], list[str]]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    candidates: list[CandidateStatement] = []
    warnings: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            warnings.append(f"Page {page_number} contained no extractable text; scanned/image-only pages require OCR or manual review.")
            continue
        for segment_index, segment in enumerate(_segments(text), start=1):
            locator = f"page {page_number} · segment {segment_index}"
            candidates.append(
                CandidateStatement(
                    candidate_id=_candidate_id(locator, segment),
                    text=segment,
                    locator=locator,
                    extraction_method="pypdf-text",
                )
            )
    return candidates, warnings


def _extract_csv(data: bytes) -> list[CandidateStatement]:
    text = data.decode("utf-8-sig")
    rows = csv.reader(io.StringIO(text))
    candidates: list[CandidateStatement] = []
    for row_number, row in enumerate(rows, start=1):
        values = [_clean_text(value) for value in row]
        if not any(values):
            continue
        statement = " | ".join(values)
        locator = f"row {row_number}"
        candidates.append(
            CandidateStatement(
                candidate_id=_candidate_id(locator, statement),
                text=statement,
                locator=locator,
                extraction_method="csv-row",
            )
        )
    return candidates


def _flatten_json(value, path: str = "$" ) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _flatten_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _flatten_json(child, f"{path}[{index}]")
    else:
        yield path, json.dumps(value, ensure_ascii=False, default=str)


def _extract_json(data: bytes) -> list[CandidateStatement]:
    parsed = json.loads(data.decode("utf-8-sig"))
    candidates: list[CandidateStatement] = []
    for path, rendered in _flatten_json(parsed):
        statement = f"{path} = {rendered}"
        candidates.append(
            CandidateStatement(
                candidate_id=_candidate_id(path, statement),
                text=statement,
                locator=path,
                extraction_method="json-path",
            )
        )
    return candidates


def extract_candidate_statements(filename: str, data: bytes, *, max_candidates: int = 100) -> ExtractionResult:
    """Extract source-derived candidate statements without promoting them to Core propositions.

    Extraction is intentionally deterministic. Candidates remain review-only until an authorized
    human explicitly promotes selected statements to source-linked propositions.
    """
    if not data:
        raise ValueError("Cannot extract an empty document")

    suffix = Path(filename).suffix.lower()
    warnings: list[str] = []

    try:
        if suffix == ".pdf":
            candidates, pdf_warnings = _extract_pdf(data)
            warnings.extend(pdf_warnings)
            method = "pypdf-text"
        elif suffix == ".csv":
            candidates = _extract_csv(data)
            method = "csv-row"
        elif suffix == ".json":
            candidates = _extract_json(data)
            method = "json-path"
        elif suffix in {".txt", ".md", ".log", ".tsv", ".xml", ".html", ".htm"}:
            text = data.decode("utf-8-sig", errors="replace")
            candidates = _text_candidates(text, method="plain-text")
            method = "plain-text"
        else:
            candidates = []
            method = "unsupported"
            warnings.append(
                f"{suffix or 'This file type'} is registered as a source but does not yet have a deterministic text extractor."
            )
    except Exception as exc:
        candidates = []
        method = "extraction-error"
        warnings.append(f"Text extraction failed ({exc.__class__.__name__}); the source remains registered and requires manual review.")

    deduped = _dedupe(candidates, max_candidates=max_candidates)
    if not deduped and not warnings:
        warnings.append("No reviewable text statements were extracted from this source.")

    return ExtractionResult(
        filename=filename,
        extraction_method=method,
        candidates=deduped,
        warnings=tuple(warnings),
    )
