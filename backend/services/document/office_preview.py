"""Office document preview helpers.

The original Office file remains the source of truth for download/storage.  These
helpers create a cached PDF preview so browsers can display Word documents
locally and the ingestion pipeline can align chunks to the same pages shown in
the preview.
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from django.conf import settings

from core.exceptions import DocumentProcessingError


OFFICE_PREVIEW_EXTENSIONS = {'.doc', '.docx', '.odt', '.rtf'}


def is_office_preview_supported(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in OFFICE_PREVIEW_EXTENSIONS


def get_pdf_preview_path(source_path: str) -> str:
    source_path = os.path.abspath(source_path)
    stat = os.stat(source_path)
    key_input = f"{source_path}:{stat.st_size}:{stat.st_mtime_ns}"
    cache_key = hashlib.sha256(key_input.encode('utf-8')).hexdigest()[:32]
    cache_dir = os.path.join(str(settings.MEDIA_ROOT), 'document_previews', 'pdf')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{cache_key}.pdf")


def convert_office_to_pdf(source_path: str, timeout: int = 120) -> str:
    """Convert an Office document to cached PDF using local LibreOffice."""
    source_path = os.path.abspath(source_path)
    if not os.path.exists(source_path):
        raise DocumentProcessingError(f"Office file not found: {source_path}")

    if not is_office_preview_supported(source_path):
        raise DocumentProcessingError(f"PDF preview is not supported for {Path(source_path).suffix}")

    preview_path = get_pdf_preview_path(source_path)
    if os.path.exists(preview_path) and os.path.getsize(preview_path) > 0:
        return preview_path

    with tempfile.TemporaryDirectory() as temp_dir:
        user_profile = Path(temp_dir) / 'lo-profile'
        user_profile.mkdir(parents=True, exist_ok=True)
        command = [
            'soffice',
            '--headless',
            '--nologo',
            '--nofirststartwizard',
            f'-env:UserInstallation=file:///{user_profile.as_posix()}',
            '--convert-to',
            'pdf',
            '--outdir',
            temp_dir,
            source_path,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise DocumentProcessingError(
                'LibreOffice is not installed in the backend container.'
            ) from exc

        if result.returncode != 0:
            message = (result.stderr or result.stdout or '').strip()
            raise DocumentProcessingError(f"Failed to convert Office preview to PDF: {message}")

        output_pdf = _find_converted_pdf(temp_dir, source_path)
        if not output_pdf:
            raise DocumentProcessingError('Office conversion completed but no PDF output was found')

        shutil.move(output_pdf, preview_path)
        return preview_path


def _find_converted_pdf(temp_dir: str, source_path: str) -> Optional[str]:
    expected = os.path.join(temp_dir, f"{Path(source_path).stem}.pdf")
    if os.path.exists(expected):
        return expected

    candidates = [
        os.path.join(temp_dir, name)
        for name in os.listdir(temp_dir)
        if name.lower().endswith('.pdf')
    ]
    return candidates[0] if candidates else None
