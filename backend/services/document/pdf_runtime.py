"""Runtime helpers for noisy third-party PDF parsers."""

import logging
from contextlib import contextmanager
from typing import Iterator, List, Tuple


_NOISY_PDF_LOGGERS = (
    "pypdf",
    "pypdf._reader",
    "pypdf._page",
    "pypdf.generic._data_structures",
)


@contextmanager
def suppress_pdf_parser_warnings() -> Iterator[None]:
    """Temporarily suppress recoverable parser warnings from malformed PDFs."""
    loggers = [logging.getLogger(name) for name in _NOISY_PDF_LOGGERS]
    previous_levels = [logger.level for logger in loggers]

    try:
        for logger in loggers:
            logger.setLevel(logging.ERROR)
        yield
    finally:
        for logger, level in zip(loggers, previous_levels):
            logger.setLevel(level)


def read_pdf_page_counts(file_path: str) -> Tuple[int, List[int]]:
    """Return total pages and per-page text lengths without noisy pypdf warnings."""
    from pypdf import PdfReader

    with suppress_pdf_parser_warnings():
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PdfReader(pdf_file, strict=False)
            page_char_counts = [
                len(page.extract_text() or "")
                for page in pdf_reader.pages
            ]

    return len(page_char_counts), page_char_counts


def convert_pdf_to_markdown_quiet(opendataloader_pdf, **kwargs):
    """Run opendataloader-pdf without streaming third-party CLI output to logs."""
    return opendataloader_pdf.convert(**kwargs, quiet=True)
