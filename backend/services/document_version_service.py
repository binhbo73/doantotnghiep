"""Document version lifecycle and chunk lineage management."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import uuid
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Tuple

from django.apps import apps
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.exceptions import BusinessLogicError, NotFoundError, PermissionDeniedError, ValidationError
from repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentVersionService:
    """Create, align, activate, and query immutable document versions."""

    MATCH_THRESHOLD = 0.58
    AMENDMENT_DIRECTIVE_PATTERN = re.compile(
        r'\b(?:sua doi|bo sung|bai bo|dinh chinh|thay the|chen them)\b',
        re.IGNORECASE,
    )
    FULL_REPLACEMENT_DIRECTIVE_PATTERN = re.compile(
        r'\b(?:thay the toan bo|toan van|ban hop nhat|ban day du|'
        r'ban hanh lai|duoc thay the boi van ban nay)\b',
        re.IGNORECASE,
    )
    ARTICLE_REF_PATTERN = re.compile(
        r'\b(?P<label>dieu|điều|article|chuong|chương|muc|mục)\s+'
        r'(?P<number>[0-9]+(?:[.\-][0-9a-z]+)*)',
        re.IGNORECASE,
    )
    SECTION_PATTERN = re.compile(
        r'\b(?:dieu|điều|article|chuong|chương|muc|mục|khoan|khoản)\s+'
        r'([0-9]+(?:[.\-][0-9a-z]+)*)',
        re.IGNORECASE,
    )

    def __init__(self):
        self.document_repo = DocumentRepository()

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize('NFKD', value or '')
        without_marks = ''.join(char for char in normalized if not unicodedata.combining(char))
        without_marks = without_marks.replace('đ', 'd').replace('Đ', 'D')
        return re.sub(r'\s+', ' ', without_marks.lower()).strip()

    @classmethod
    def _section_key(cls, chunk) -> str:
        metadata = chunk.metadata or {}
        legal_section_key = metadata.get('legal_section_key')
        if legal_section_key:
            return cls._normalize_text(str(legal_section_key))
        heading_path = metadata.get('heading_path') or []
        if isinstance(heading_path, str):
            heading_path = [heading_path]
        heading_text = ' > '.join(str(item) for item in heading_path if item)
        probe = f"{heading_text} {(chunk.content or '')[:240]}"
        match = cls.SECTION_PATTERN.search(probe)
        if match:
            prefix = cls._normalize_text(match.group(0).split()[0])
            return f"{prefix}:{cls._normalize_text(match.group(1))}"
        return cls._normalize_text(heading_text)

    @staticmethod
    def _content_hash(chunk) -> str:
        metadata_hash = (chunk.metadata or {}).get('content_hash')
        if metadata_hash:
            return str(metadata_hash)
        normalized = re.sub(r'\s+', ' ', chunk.content or '').strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @classmethod
    def _similarity(cls, old_chunk, new_chunk) -> float:
        old_text = cls._normalize_text(old_chunk.content or '')
        new_text = cls._normalize_text(new_chunk.content or '')
        if not old_text or not new_text:
            return 0.0
        content_score = SequenceMatcher(None, old_text[:5000], new_text[:5000]).ratio()
        old_section = cls._section_key(old_chunk)
        new_section = cls._section_key(new_chunk)
        section_bonus = 0.25 if old_section and old_section == new_section else 0.0
        distance = abs(int(old_chunk.chunk_index or 0) - int(new_chunk.chunk_index or 0))
        position_bonus = max(0.0, 0.12 - min(distance, 12) * 0.01)
        return min(1.0, content_score * 0.75 + section_bonus + position_bonus)

    @classmethod
    def _target_section_keys(cls, text: str) -> List[str]:
        """Extract section keys referenced by an amendment/patch document."""
        keys = []
        for match in cls.ARTICLE_REF_PATTERN.finditer(text or ''):
            label = cls._normalize_text(match.group('label'))
            number = cls._normalize_text(match.group('number'))
            key = f"{label}:{number}"
            if key not in keys:
                keys.append(key)
        return keys

    @classmethod
    def _chunk_matches_target_key(cls, chunk, target_key: str) -> bool:
        chunk_key = cls._section_key(chunk)
        if not target_key:
            return False
        if chunk_key and (
            chunk_key == target_key
            or chunk_key.startswith(f"{target_key}.")
            or chunk_key.startswith(f"{target_key}-")
        ):
            return True
        return target_key in cls._target_section_keys(chunk.content or '')

    @classmethod
    def _amendment_target_section_keys(cls, chunk) -> List[str]:
        """Return sections in the base document targeted by an amendment chunk.

        Amendment documents often have their own article numbering, for
        example "Điều 2. Sửa đổi Điều 4". The leading Điều 2 identifies the
        amendment article, not a target in the base document.
        """
        raw_keys = [
            f"{cls._normalize_text(match.group('label'))}:"
            f"{cls._normalize_text(match.group('number'))}"
            for match in cls.ARTICLE_REF_PATTERN.finditer(chunk.content or '')
        ]
        keys = list(dict.fromkeys(raw_keys))
        metadata = chunk.metadata or {}
        own_key = cls._normalize_text(str(metadata.get('legal_section_key') or ''))
        normalized_text = cls._normalize_text(chunk.content or '')
        has_directive = bool(cls.AMENDMENT_DIRECTIVE_PATTERN.search(normalized_text))
        if (
            has_directive
            and own_key
            and len(keys) > 1
            and raw_keys.count(own_key) == 1
        ):
            keys = [key for key in keys if key != own_key]
        return keys

    @classmethod
    def _replaces_entire_target_section(cls, chunk, target_key: str) -> bool:
        """Whether an amendment replaces/removes the whole targeted section."""
        if not target_key or ':' not in target_key:
            return False
        label, number = target_key.split(':', 1)
        if label not in {'dieu', 'article'}:
            return False

        text = cls._normalize_text(chunk.content or '')
        escaped_number = re.escape(number)
        patterns = [
            rf'\bbai bo (?:toan bo )?(?:dieu|article) {escaped_number}\b',
            rf'\bthay the (?:toan bo )?(?:noi dung )?(?:dieu|article) {escaped_number}\b',
            rf'\bsua doi (?:toan bo )?noi dung (?:dieu|article) {escaped_number}\b',
            rf'\b(?:dieu|article) {escaped_number}\b[^.\n]{{0,80}}'
            rf'\bduoc sua doi toan bo\b',
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _classify_update_mode(self, candidate, previous) -> Tuple[str, Dict[str, object]]:
        """Resolve an automatic update after both document versions are chunked."""
        Document = apps.get_model('documents', 'Document')
        DocumentChunk = apps.get_model('documents', 'DocumentChunk')

        old_document_ids = list(Document.objects.filter(
            logical_document_id=candidate.logical_document_id,
            version__lt=candidate.version,
            is_deleted=False,
        ).values_list('id', flat=True))
        old_chunks = list(DocumentChunk.objects.filter(
            document_id__in=old_document_ids,
            node_type='detail',
            is_current=True,
            is_deleted=False,
        ).order_by('chunk_index'))
        new_chunks = list(DocumentChunk.objects.filter(
            document=candidate,
            node_type='detail',
            is_deleted=False,
        ).order_by('chunk_index'))

        new_text = '\n'.join(chunk.content or '' for chunk in new_chunks)
        classification_text = ' '.join([
            new_text,
            candidate.change_summary or '',
            candidate.original_name or '',
        ])
        normalized_text = self._normalize_text(classification_text)
        directive_count = len(self.AMENDMENT_DIRECTIVE_PATTERN.findall(normalized_text))
        full_directive_count = len(
            self.FULL_REPLACEMENT_DIRECTIVE_PATTERN.findall(normalized_text)
        )
        target_keys = set(self._target_section_keys(new_text))
        old_section_keys = {self._section_key(chunk) for chunk in old_chunks}
        new_section_keys = {self._section_key(chunk) for chunk in new_chunks}
        old_section_keys.discard('')
        new_section_keys.discard('')

        old_count = len(old_chunks)
        new_count = len(new_chunks)
        chunk_ratio = new_count / max(1, old_count)
        old_chars = sum(len(chunk.content or '') for chunk in old_chunks)
        new_chars = sum(len(chunk.content or '') for chunk in new_chunks)
        char_ratio = new_chars / max(1, old_chars)
        section_coverage = (
            len(old_section_keys & new_section_keys) / max(1, len(old_section_keys))
        )
        matches = self._align_chunks(old_chunks, new_chunks)
        alignment_coverage = len(matches) / max(1, new_count)

        full_structure = (
            char_ratio >= 0.72
            and chunk_ratio >= 0.65
            and (
                section_coverage >= 0.60
                or alignment_coverage >= 0.65
                or not old_section_keys
            )
        )
        explicit_amendment = bool(directive_count and target_keys)
        compact_patch = char_ratio <= 0.55 or chunk_ratio <= 0.50

        if full_directive_count:
            resolved_mode = 'full'
            confidence = min(0.98, 0.88 + min(full_directive_count, 2) * 0.04)
            reason = 'explicit_full_replacement_directives'
        elif explicit_amendment:
            resolved_mode = 'amendment'
            confidence = min(
                0.99,
                0.82
                + (0.08 if compact_patch else 0.0)
                + min(len(target_keys), 3) * 0.02,
            )
            reason = 'explicit_amendment_directives'
        elif full_structure:
            resolved_mode = 'full'
            confidence = min(
                0.99,
                0.58
                + min(char_ratio, 1.0) * 0.12
                + min(chunk_ratio, 1.0) * 0.10
                + section_coverage * 0.10
                + alignment_coverage * 0.10,
            )
            reason = 'candidate_covers_most_of_effective_document'
        elif compact_patch:
            resolved_mode = 'amendment'
            confidence = min(
                0.99,
                0.68
                + 0.10
                + min(len(target_keys), 3) * 0.02,
            )
            reason = 'candidate_is_substantially_smaller_than_effective_document'
        else:
            # Preserving unaffected chunks is safer than retiring valid content.
            resolved_mode = 'amendment'
            confidence = 0.55
            reason = 'ambiguous_conservative_overlay'

        evidence = {
            'requested_mode': 'auto',
            'resolved_mode': resolved_mode,
            'confidence': round(confidence, 3),
            'reason': reason,
            'old_chunk_count': old_count,
            'new_chunk_count': new_count,
            'chunk_ratio': round(chunk_ratio, 3),
            'char_ratio': round(char_ratio, 3),
            'section_coverage': round(section_coverage, 3),
            'alignment_coverage': round(alignment_coverage, 3),
            'amendment_directive_count': directive_count,
            'full_replacement_directive_count': full_directive_count,
            'target_section_keys': sorted(target_keys),
        }
        return resolved_mode, evidence

    def create_version(
        self,
        *,
        base_document_id: str,
        file,
        user_id: str,
        expected_version_lock: Optional[int] = None,
        change_summary: str = '',
        update_mode: str = 'auto',
    ):
        """Create and dispatch a staging version without disturbing the active version."""
        update_mode = (update_mode or 'auto').strip().lower()
        if update_mode not in {'auto', 'full', 'amendment'}:
            raise ValidationError("update_mode must be 'auto', 'full', or 'amendment'")

        if not self.document_repo.check_user_can_write(base_document_id, user_id):
            raise PermissionDeniedError(f"No write permission on document {base_document_id}")

        Document = apps.get_model('documents', 'Document')
        with transaction.atomic():
            try:
                base = Document.objects.select_for_update().get(
                    id=base_document_id,
                    is_current=True,
                    is_deleted=False,
                )
            except Document.DoesNotExist as exc:
                raise NotFoundError("Current document version not found") from exc

            if expected_version_lock is not None and int(expected_version_lock) != base.version_lock:
                raise ValidationError(
                    f"Document changed concurrently; expected lock {expected_version_lock}, "
                    f"current lock is {base.version_lock}"
                )

            if Document.objects.filter(
                logical_document_id=base.logical_document_id,
                version_state__in=['staging'],
                is_deleted=False,
            ).exists():
                raise BusinessLogicError("Another document version is already being processed")

            from services.document_upload_service import DocumentUploadService

            next_version = (
                Document.objects.filter(logical_document_id=base.logical_document_id)
                .aggregate(max_version=Max('version'))
                .get('max_version') or 0
            ) + 1
            upload_service = DocumentUploadService()
            new_document = upload_service.upload(
                file=file,
                user_id=user_id,
                folder_id=str(base.folder_id) if base.folder_id else None,
                department_id=str(base.department_id) if base.department_id else None,
                access_scope=base.access_scope,
                description=(base.metadata or {}).get('description'),
                tags=[],
                run_processing=False,
                base_document=base,
                change_summary=change_summary,
                version_number=next_version,
                update_mode=update_mode,
            )
            self._clone_tags_and_permissions(base, new_document)

            base.version_lock += 1
            base.save(update_fields=['version_lock', 'updated_at'])

            transaction.on_commit(
                lambda document_id=str(new_document.id): upload_service._dispatch_processing(document_id)
            )
            return new_document

    @staticmethod
    def _clone_tags_and_permissions(base_document, new_document) -> None:
        new_document.tags.set(base_document.tags.all())
        DocumentPermission = apps.get_model('documents', 'DocumentPermission')
        permissions = []
        for permission in base_document.permissions.filter(is_deleted=False):
            permissions.append(DocumentPermission(
                document=new_document,
                subject_type=permission.subject_type,
                subject_id=permission.subject_id,
                permission=permission.permission,
                permission_precedence=permission.permission_precedence,
                is_active=permission.is_active,
                granted_by_id=permission.granted_by_id,
            ))
        if permissions:
            DocumentPermission.objects.bulk_create(permissions)

    def activate_if_ready(self, document_id: str) -> None:
        """Align chunks and atomically switch the current document version."""
        Document = apps.get_model('documents', 'Document')
        DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        ChunkRevisionLink = apps.get_model('documents', 'ChunkRevisionLink')

        document = Document.objects.filter(id=document_id, is_deleted=False).first()
        if not document or not document.previous_version_id:
            return
        if document.status != 'completed':
            return

        with transaction.atomic():
            candidate = Document.objects.select_for_update().get(id=document_id)
            previous = Document.objects.select_for_update().get(id=candidate.previous_version_id)
            if candidate.version_state == 'active' and candidate.is_current:
                return
            if candidate.status != 'completed':
                raise BusinessLogicError("Cannot activate an incomplete document version")

            update_mode = (candidate.metadata or {}).get('update_mode') or 'auto'
            if update_mode == 'auto':
                update_mode, evidence = self._classify_update_mode(candidate, previous)
                candidate.metadata = candidate.metadata or {}
                candidate.metadata['update_mode_requested'] = 'auto'
                candidate.metadata['update_mode'] = update_mode
                candidate.metadata['update_mode_detection'] = evidence
                candidate.save(update_fields=['metadata', 'updated_at'])
                logger.info(
                    "[VERSION_MODE] document=%s resolved=%s confidence=%s reason=%s",
                    candidate.id,
                    update_mode,
                    evidence['confidence'],
                    evidence['reason'],
                )
            if update_mode == 'amendment':
                self._activate_amendment_version(candidate, previous)
                return

            old_document_ids = list(Document.objects.filter(
                logical_document_id=candidate.logical_document_id,
                version__lt=candidate.version,
                is_deleted=False,
            ).values_list('id', flat=True))
            old_chunks = list(DocumentChunk.objects.filter(
                document_id__in=old_document_ids,
                node_type='detail',
                is_current=True,
                is_deleted=False,
            ).order_by('chunk_index'))
            new_chunks = list(DocumentChunk.objects.filter(
                document=candidate,
                node_type='detail',
                is_deleted=False,
            ).order_by('chunk_index'))
            matches = self._align_chunks(old_chunks, new_chunks)

            links = []
            matched_old_ids = set()
            for new_chunk in new_chunks:
                match = matches.get(str(new_chunk.id))
                if match:
                    old_chunk, confidence, method = match
                    same_content = self._content_hash(old_chunk) == self._content_hash(new_chunk)
                    new_chunk.previous_version_chunk = old_chunk
                    new_chunk.lineage_id = old_chunk.lineage_id or old_chunk.id
                    new_chunk.change_type = 'unchanged' if same_content else 'modified'
                    matched_old_ids.add(old_chunk.id)
                    links.append(ChunkRevisionLink(
                        from_chunk=old_chunk,
                        to_chunk=new_chunk,
                        relation='unchanged' if same_content else 'replaces',
                        confidence=confidence,
                        match_method=method,
                    ))
                else:
                    new_chunk.change_type = 'added'
                new_chunk.is_current = True

            for old_chunk in old_chunks:
                old_chunk.is_current = False
                if old_chunk.id not in matched_old_ids:
                    old_chunk.change_type = 'removed'

            if new_chunks:
                DocumentChunk.objects.bulk_update(
                    new_chunks,
                    ['previous_version_chunk', 'lineage_id', 'change_type', 'is_current', 'updated_at'],
                )
            if old_chunks:
                DocumentChunk.objects.bulk_update(
                    old_chunks,
                    ['change_type', 'is_current', 'updated_at'],
                )
            if links:
                ChunkRevisionLink.objects.bulk_create(links, ignore_conflicts=True)

            now = timezone.now()
            DocumentChunk.objects.filter(
                document_id__in=old_document_ids,
                is_deleted=False,
            ).update(is_current=False, updated_at=now)
            DocumentChunk.objects.filter(
                document=candidate,
                is_deleted=False,
            ).update(is_current=True, updated_at=now)

            previous.is_current = False
            previous.version_state = 'superseded'
            previous.valid_to = now
            previous.save(update_fields=['is_current', 'version_state', 'valid_to', 'updated_at'])

            candidate.is_current = True
            candidate.version_state = 'active'
            candidate.valid_from = now
            candidate.valid_to = None
            candidate.metadata = candidate.metadata or {}
            candidate.metadata['version_activated_at'] = now.isoformat()
            candidate.metadata['version_diff'] = {
                'previous_document_id': str(previous.id),
                'unchanged': sum(1 for chunk in new_chunks if chunk.change_type == 'unchanged'),
                'modified': sum(1 for chunk in new_chunks if chunk.change_type == 'modified'),
                'added': sum(1 for chunk in new_chunks if chunk.change_type == 'added'),
                'removed': sum(1 for chunk in old_chunks if chunk.change_type == 'removed'),
            }
            candidate.save(update_fields=[
                'is_current', 'version_state', 'valid_from', 'valid_to', 'metadata', 'updated_at',
            ])

            transaction.on_commit(
                lambda: self._after_activation(
                    previous_id=str(previous.id),
                    current_id=str(candidate.id),
                    previous_ids=[str(doc_id) for doc_id in old_document_ids],
                )
            )

    def _activate_amendment_version(self, candidate, previous) -> None:
        """Activate a patch/amendment version without replacing the whole base.

        The candidate document contains only amendment text. Unaffected chunks
        from the previous version stay current and remain searchable as the
        inherited effective text. Chunks referenced by the amendment are retired
        and linked via previous_version_chunk.
        """
        Document = apps.get_model('documents', 'Document')
        DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        ChunkRevisionLink = apps.get_model('documents', 'ChunkRevisionLink')

        old_document_ids = list(Document.objects.filter(
            logical_document_id=candidate.logical_document_id,
            version__lt=candidate.version,
            is_deleted=False,
        ).values_list('id', flat=True))
        old_chunks = list(DocumentChunk.objects.filter(
            document_id__in=old_document_ids,
            node_type='detail',
            is_current=True,
            is_deleted=False,
        ).order_by('chunk_index'))
        new_chunks = list(DocumentChunk.objects.filter(
            document=candidate,
            node_type='detail',
            is_deleted=False,
        ).order_by('chunk_index'))

        links = []
        retired_old_ids = set()
        for new_chunk in new_chunks:
            target_keys = self._amendment_target_section_keys(new_chunk)
            target_old_chunks = []
            for target_key in target_keys:
                for old_chunk in old_chunks:
                    if old_chunk.id in retired_old_ids:
                        continue
                    if old_chunk in target_old_chunks:
                        continue
                    if self._chunk_matches_target_key(old_chunk, target_key):
                        target_old_chunks.append(old_chunk)

            if not target_old_chunks:
                matches = self._align_chunks(old_chunks, [new_chunk])
                match = matches.get(str(new_chunk.id))
                if match:
                    target_old_chunks = [match[0]]

            if target_old_chunks:
                primary_old = target_old_chunks[0]
                new_chunk.previous_version_chunk = primary_old
                new_chunk.lineage_id = primary_old.lineage_id or primary_old.id
                new_chunk.change_type = 'modified'
                for target_old in target_old_chunks:
                    old_section_keys = self._target_section_keys(target_old.content or '')
                    old_heading_keys = {
                        f"{self._normalize_text(match.group('label'))}:"
                        f"{self._normalize_text(match.group('number'))}"
                        for match in re.finditer(
                            r'(?im)^\s*(?P<label>dieu|điều|article)\s+'
                            r'(?P<number>[0-9]+(?:[.\-][0-9a-z]+)*)',
                            target_old.content or '',
                        )
                    }
                    primary_old_key = self._section_key(target_old)
                    can_retire_old = (
                        self._replaces_entire_target_section(new_chunk, primary_old_key)
                        and (
                            (
                                len(old_heading_keys) <= 1
                                and primary_old_key in target_keys
                            )
                            or (
                                bool(old_heading_keys)
                                and old_heading_keys.issubset(set(target_keys))
                            )
                            or (
                                not old_heading_keys
                                and (
                                    not old_section_keys
                                    or set(old_section_keys).issubset(set(target_keys))
                                    or len(old_section_keys) == 1
                                )
                            )
                        )
                    )
                    if can_retire_old:
                        retired_old_ids.add(target_old.id)
                    links.append(ChunkRevisionLink(
                        from_chunk=target_old,
                        to_chunk=new_chunk,
                        relation='replaces' if can_retire_old else 'references',
                        confidence=0.88 if target_keys else 0.60,
                        match_method='amendment_target' if target_keys else 'amendment_similarity',
                    ))
            else:
                new_chunk.change_type = 'added'
            new_chunk.is_current = True

        if new_chunks:
            DocumentChunk.objects.bulk_update(
                new_chunks,
                ['previous_version_chunk', 'lineage_id', 'change_type', 'is_current', 'updated_at'],
            )

        if retired_old_ids:
            DocumentChunk.objects.filter(id__in=retired_old_ids).update(
                is_current=False,
                change_type='removed',
                updated_at=timezone.now(),
            )

        # Keep all unaffected previous chunks current. They are inherited by the
        # amendment version's effective view.
        DocumentChunk.objects.filter(
            document=previous,
            is_deleted=False,
        ).exclude(id__in=retired_old_ids).update(is_current=True, updated_at=timezone.now())
        DocumentChunk.objects.filter(
            document=candidate,
            is_deleted=False,
        ).update(is_current=True, updated_at=timezone.now())

        if links:
            ChunkRevisionLink.objects.bulk_create(links, ignore_conflicts=True)

        now = timezone.now()
        previous.is_current = False
        previous.version_state = 'superseded'
        previous.valid_to = now
        previous.save(update_fields=['is_current', 'version_state', 'valid_to', 'updated_at'])

        candidate.is_current = True
        candidate.version_state = 'active'
        candidate.valid_from = now
        candidate.valid_to = None
        candidate.metadata = candidate.metadata or {}
        candidate.metadata['version_activated_at'] = now.isoformat()
        candidate.metadata['effective_document_mode'] = 'overlay'
        candidate.metadata['version_diff'] = {
            'previous_document_id': str(previous.id),
            'update_mode': 'amendment',
            'modified': sum(1 for chunk in new_chunks if chunk.change_type == 'modified'),
            'added': sum(1 for chunk in new_chunks if chunk.change_type == 'added'),
            'retired': len(retired_old_ids),
            'inherited': max(0, len(old_chunks) - len(retired_old_ids)),
        }
        candidate.save(update_fields=[
            'is_current', 'version_state', 'valid_from', 'valid_to', 'metadata', 'updated_at',
        ])

        effective_chunk_ids = list(DocumentChunk.objects.filter(
            document_id__in=[*old_document_ids, candidate.id],
            node_type='detail',
            is_current=True,
            is_deleted=False,
        ).values_list('id', flat=True))
        transaction.on_commit(
            lambda: self._after_amendment_activation(
                previous_id=str(previous.id),
                current_id=str(candidate.id),
                inherited_document_ids=[str(doc_id) for doc_id in old_document_ids],
                effective_chunk_ids=[str(chunk_id) for chunk_id in effective_chunk_ids],
            )
        )

    def mark_failed(self, document_id: str) -> None:
        Document = apps.get_model('documents', 'Document')
        Document.objects.filter(
            id=document_id,
            previous_version_id__isnull=False,
            is_current=False,
        ).update(version_state='failed', updated_at=timezone.now())

    def _after_activation(
        self,
        *,
        previous_id: str,
        current_id: str,
        previous_ids: Optional[List[str]] = None,
    ) -> None:
        try:
            from services.ai.qdrant_client import QdrantClient
            qdrant = QdrantClient()
            qdrant.set_payload_by_filter(
                {'document_id': previous_ids or [previous_id]},
                {'is_current': False},
            )
            qdrant.set_payload_by_filter({'document_id': current_id}, {'is_current': True})
            self._sync_chunk_lineage_payloads(
                qdrant,
                [*(previous_ids or [previous_id]), current_id],
            )
        except Exception as exc:
            logger.warning("Qdrant version payload sync failed: %s", exc, exc_info=True)

        try:
            cache.clear()
        except Exception:
            logger.warning("Retrieval cache invalidation failed", exc_info=True)

    def _after_amendment_activation(
        self,
        *,
        previous_id: str,
        current_id: str,
        inherited_document_ids: Optional[List[str]] = None,
        effective_chunk_ids: Optional[List[str]] = None,
    ) -> None:
        try:
            from services.ai.qdrant_client import QdrantClient
            qdrant = QdrantClient()
            all_document_ids = list(inherited_document_ids or [previous_id])
            all_document_ids.append(current_id)
            qdrant.set_payload_by_filter(
                {'document_id': all_document_ids},
                {'is_current': False},
            )
            effective_chunk_ids = effective_chunk_ids or []
            if effective_chunk_ids:
                qdrant.set_payload_by_filter(
                    {'chunk_id': effective_chunk_ids},
                    {'is_current': True},
                )
            self._sync_chunk_lineage_payloads(qdrant, all_document_ids)
        except Exception as exc:
            logger.warning("Qdrant amendment payload sync failed: %s", exc, exc_info=True)

        try:
            cache.clear()
        except Exception:
            logger.warning("Retrieval cache invalidation failed", exc_info=True)

    @staticmethod
    def _sync_chunk_lineage_payloads(qdrant, document_ids: List[str]) -> None:
        """Mirror authoritative chunk lineage fields into Qdrant payloads."""
        DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        chunks = DocumentChunk.objects.select_related('document').filter(
            document_id__in=document_ids,
            node_type='detail',
            is_deleted=False,
        ).only(
            'id',
            'previous_version_chunk_id',
            'lineage_id',
            'change_type',
            'is_current',
            'document__logical_document_id',
            'document__version',
            'document__version_state',
            'document__metadata',
        )
        failed = 0
        for chunk in chunks.iterator(chunk_size=200):
            document_metadata = chunk.document.metadata or {}
            ok = qdrant.set_payload_by_filter(
                {'chunk_id': str(chunk.id)},
                {
                    'previous_chunk_id': (
                        str(chunk.previous_version_chunk_id)
                        if chunk.previous_version_chunk_id
                        else None
                    ),
                    'lineage_id': str(chunk.lineage_id),
                    'change_type': chunk.change_type,
                    'is_current': chunk.is_current,
                    'logical_document_id': str(chunk.document.logical_document_id),
                    'version_number': chunk.document.version,
                    'version_state': chunk.document.version_state,
                    'update_mode': document_metadata.get('update_mode') or 'full',
                    'effective_document_mode': document_metadata.get('effective_document_mode'),
                },
            )
            if not ok:
                failed += 1
        if failed:
            logger.warning(
                "Qdrant chunk lineage payload sync failed for %s chunk(s)",
                failed,
            )

    def _align_chunks(self, old_chunks: Iterable, new_chunks: Iterable) -> Dict[str, Tuple[object, float, str]]:
        old_chunks = list(old_chunks)
        new_chunks = list(new_chunks)
        matches: Dict[str, Tuple[object, float, str]] = {}
        used_old_ids = set()

        old_by_hash: Dict[str, List] = {}
        old_by_section: Dict[str, List] = {}
        for old_chunk in old_chunks:
            old_by_hash.setdefault(self._content_hash(old_chunk), []).append(old_chunk)
            section_key = self._section_key(old_chunk)
            if section_key:
                old_by_section.setdefault(section_key, []).append(old_chunk)

        for new_chunk in new_chunks:
            exact = next(
                (chunk for chunk in old_by_hash.get(self._content_hash(new_chunk), []) if chunk.id not in used_old_ids),
                None,
            )
            if exact:
                matches[str(new_chunk.id)] = (exact, 1.0, 'content_hash')
                used_old_ids.add(exact.id)

        for new_chunk in new_chunks:
            if str(new_chunk.id) in matches:
                continue
            section_candidates = [
                chunk for chunk in old_by_section.get(self._section_key(new_chunk), [])
                if chunk.id not in used_old_ids
            ]
            candidates = section_candidates or [
                chunk for chunk in old_chunks
                if chunk.id not in used_old_ids
                and abs(int(chunk.chunk_index or 0) - int(new_chunk.chunk_index or 0)) <= 8
            ]
            scored = sorted(
                ((self._similarity(old_chunk, new_chunk), old_chunk) for old_chunk in candidates),
                key=lambda item: item[0],
                reverse=True,
            )
            if scored and scored[0][0] >= self.MATCH_THRESHOLD:
                confidence, old_chunk = scored[0]
                method = 'section_similarity' if section_candidates else 'position_similarity'
                matches[str(new_chunk.id)] = (old_chunk, confidence, method)
                used_old_ids.add(old_chunk.id)
        return matches

    @staticmethod
    def list_versions(document_id: str):
        Document = apps.get_model('documents', 'Document')
        document = Document.objects.filter(id=document_id, is_deleted=False).first()
        if not document:
            raise NotFoundError("Document not found")
        return Document.objects.filter(
            logical_document_id=document.logical_document_id,
            is_deleted=False,
        ).order_by('-version')
