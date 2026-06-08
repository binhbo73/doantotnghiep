from types import SimpleNamespace
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from services.document_version_service import DocumentVersionService


def chunk(content, index, heading=None, content_hash=None):
    metadata = {}
    if heading:
        metadata['heading_path'] = [heading]
    if content_hash:
        metadata['content_hash'] = content_hash
    return SimpleNamespace(
        id=uuid.uuid4(),
        content=content,
        chunk_index=index,
        metadata=metadata,
    )


class DocumentVersionAlignmentTests(SimpleTestCase):
    def setUp(self):
        self.service = DocumentVersionService()

    def test_exact_content_hash_is_reused(self):
        old = chunk('Điều 1. Phạm vi áp dụng', 0, 'Điều 1', 'same')
        new = chunk('Điều 1. Phạm vi áp dụng', 0, 'Điều 1', 'same')

        matches = self.service._align_chunks([old], [new])

        matched, confidence, method = matches[str(new.id)]
        self.assertEqual(matched.id, old.id)
        self.assertEqual(confidence, 1.0)
        self.assertEqual(method, 'content_hash')

    def test_modified_section_matches_previous_chunk(self):
        old = chunk('Điều 1. Người lao động được nghỉ 10 ngày.', 3, 'Điều 1')
        new = chunk('Điều 1. Người lao động được nghỉ 12 ngày.', 4, 'Điều 1')

        matches = self.service._align_chunks([old], [new])

        matched, confidence, method = matches[str(new.id)]
        self.assertEqual(matched.id, old.id)
        self.assertGreaterEqual(confidence, self.service.MATCH_THRESHOLD)
        self.assertEqual(method, 'section_similarity')

    def test_unrelated_added_chunk_has_no_previous_match(self):
        old = chunk('Điều 1. Quy định về tiền lương.', 0, 'Điều 1')
        new = chunk('Điều 9. Quy định hoàn toàn mới về an toàn dữ liệu.', 20, 'Điều 9')

        matches = self.service._align_chunks([old], [new])

        self.assertNotIn(str(new.id), matches)

    def test_amendment_target_parser_reads_vietnamese_article_refs(self):
        keys = self.service._target_section_keys(
            'Văn bản này sửa đổi ý 2 Điều 1 và bổ sung Điều 2.'
        )

        self.assertEqual(keys, ['dieu:1', 'dieu:2'])

    def test_chunk_matches_target_article_from_heading(self):
        existing = chunk('Điều 1. KPI doanh thu và lợi nhuận có trọng số 30%.', 0, 'Điều 1')

        self.assertTrue(self.service._chunk_matches_target_key(existing, 'dieu:1'))
        self.assertFalse(self.service._chunk_matches_target_key(existing, 'dieu:2'))

    def test_amendment_own_article_number_is_not_a_base_target(self):
        amendment_chunk = chunk(
            'Điều 2. Sửa đổi, bổ sung Điều 4 về KPI tham chiếu.',
            0,
            'Điều 2',
        )
        amendment_chunk.metadata['legal_section_key'] = 'điều:2'

        keys = self.service._amendment_target_section_keys(amendment_chunk)

        self.assertEqual(keys, ['dieu:4'])

    def test_same_number_remains_target_when_repeated_in_directive(self):
        amendment_chunk = chunk(
            'Điều 2. Sửa đổi nội dung Điều 2 như sau.',
            0,
            'Điều 2',
        )
        amendment_chunk.metadata['legal_section_key'] = 'điều:2'

        keys = self.service._amendment_target_section_keys(amendment_chunk)

        self.assertEqual(keys, ['dieu:2'])

    def test_partial_clause_update_does_not_replace_whole_article(self):
        amendment_chunk = chunk(
            'Sửa đổi khoản 4 và khoản 5 Điều 4 như sau.',
            0,
            'Điều 2',
        )

        self.assertFalse(
            self.service._replaces_entire_target_section(amendment_chunk, 'dieu:4')
        )

    def test_explicit_whole_article_update_replaces_article(self):
        amendment_chunk = chunk(
            'Sửa đổi toàn bộ nội dung Điều 4 như sau.',
            0,
            'Điều 1',
        )

        self.assertTrue(
            self.service._replaces_entire_target_section(amendment_chunk, 'dieu:4')
        )

    def test_repeal_replaces_article(self):
        amendment_chunk = chunk('Bãi bỏ Điều 4.', 0, 'Điều 1')

        self.assertTrue(
            self.service._replaces_entire_target_section(amendment_chunk, 'dieu:4')
        )

    @patch.object(DocumentVersionService, '_sync_chunk_lineage_payloads')
    @patch('services.ai.qdrant_client.QdrantClient')
    def test_amendment_qdrant_sync_rebuilds_current_flags_from_effective_chunks(
        self,
        qdrant_cls,
        sync_lineage,
    ):
        qdrant = qdrant_cls.return_value

        self.service._after_amendment_activation(
            previous_id='previous',
            current_id='current',
            inherited_document_ids=['base', 'previous'],
            effective_chunk_ids=['chunk-a', 'chunk-b'],
        )

        qdrant.set_payload_by_filter.assert_any_call(
            {'document_id': ['base', 'previous', 'current']},
            {'is_current': False},
        )
        qdrant.set_payload_by_filter.assert_any_call(
            {'chunk_id': ['chunk-a', 'chunk-b']},
            {'is_current': True},
        )
        sync_lineage.assert_called_once_with(
            qdrant,
            ['base', 'previous', 'current'],
        )

    def test_structured_chunk_is_split_at_each_legal_article(self):
        from services.document.chunker import DocumentChunker

        source = {
            'text': (
                'QUY ĐỊNH CHUNG\n\n'
                'Điều 1. Phạm vi áp dụng\n\nNội dung của Điều 1.\n\n'
                'Điều 2. Trách nhiệm thực hiện\n\nNội dung của Điều 2.'
            ),
            'start_char': 0,
            'end_char': 128,
            'token_count': 40,
            'metadata': {},
            'sequence': 0,
        }

        chunks = DocumentChunker()._split_multi_article_chunks([source])

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]['metadata']['legal_section_key'], 'điều:1')
        self.assertEqual(chunks[1]['metadata']['legal_section_key'], 'điều:2')
        self.assertNotIn('Điều 2.', chunks[0]['text'])

    def test_single_legal_article_chunk_receives_section_key(self):
        from services.document.chunker import DocumentChunker

        source = {
            'text': 'Điều 4. KPI tham chiếu\n\n1. Doanh thu và lợi nhuận: 30%.',
            'metadata': {},
            'sequence': 0,
        }

        chunks = DocumentChunker()._split_multi_article_chunks([source])

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]['metadata']['legal_section_key'], 'điều:4')

    def test_non_legal_chunk_is_unchanged(self):
        from services.document.chunker import DocumentChunker

        source = {
            'text': 'Báo cáo doanh thu tháng 6 gồm số liệu của toàn công ty.',
            'metadata': {'source': 'report'},
            'sequence': 0,
        }

        chunks = DocumentChunker()._split_multi_article_chunks([source])

        self.assertEqual(chunks, [source])

    def test_legal_split_preserves_preamble_and_all_content(self):
        from services.document.chunker import DocumentChunker

        source = {
            'text': (
                'QUY ĐỊNH CHUNG\n\n'
                'Điều 1. Phạm vi áp dụng.\n\n'
                'Điều 2. Trách nhiệm thực hiện.'
            ),
            'metadata': {},
            'sequence': 0,
        }

        chunks = DocumentChunker()._split_multi_article_chunks([source])

        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0]['text'].startswith('QUY ĐỊNH CHUNG'))
        normalized_source = ''.join(source['text'].split())
        normalized_result = ''.join(chunk['text'] for chunk in chunks).replace(' ', '').replace('\n', '')
        self.assertEqual(normalized_result, normalized_source)

    def test_legal_split_is_idempotent(self):
        from services.document.chunker import DocumentChunker

        source = {
            'text': (
                'Điều 1. Phạm vi áp dụng.\n\n'
                'Điều 2. Trách nhiệm thực hiện.'
            ),
            'metadata': {},
            'sequence': 0,
        }
        chunker = DocumentChunker()

        first_pass = chunker._split_multi_article_chunks([source])
        second_pass = chunker._split_multi_article_chunks(first_pass)

        self.assertEqual(
            [(chunk['text'], chunk['metadata']) for chunk in second_pass],
            [(chunk['text'], chunk['metadata']) for chunk in first_pass],
        )

    def test_long_article_continuation_inherits_section_key(self):
        from services.document.chunker import DocumentChunker

        chunks = [
            {
                'text': 'Điều 7. Quy định xử lý dữ liệu.\n\nPhần đầu của Điều 7.',
                'token_start': 0,
                'token_end': 360,
                'metadata': {},
                'sequence': 0,
            },
            {
                'text': 'Phần tiếp theo của cùng Điều 7.',
                'token_start': 288,
                'token_end': 648,
                'metadata': {},
                'sequence': 1,
            },
        ]

        result = DocumentChunker()._split_multi_article_chunks(chunks)

        self.assertEqual(result[1]['metadata']['legal_section_key'], 'điều:7')
        self.assertFalse(result[1]['metadata']['legal_section_boundary'])
        self.assertTrue(result[1]['metadata']['legal_section_continuation'])

    def test_non_overlapping_chunk_does_not_inherit_section_key(self):
        from services.document.chunker import DocumentChunker

        chunks = [
            {
                'text': 'Điều 7. Quy định xử lý dữ liệu.',
                'token_start': 0,
                'token_end': 100,
                'metadata': {},
                'sequence': 0,
            },
            {
                'text': 'PHỤ LỤC\n\nNội dung độc lập.',
                'token_start': 100,
                'token_end': 160,
                'metadata': {},
                'sequence': 1,
            },
        ]

        result = DocumentChunker()._split_multi_article_chunks(chunks)

        self.assertNotIn('legal_section_key', result[1]['metadata'])

    def test_document_overview_query_uses_comprehensive_context(self):
        from services.chat_service import ChatService

        service = object.__new__(ChatService)

        self.assertTrue(service._is_list_style_query('Tóm tắt tổng quan tài liệu này'))


class AmendmentOverlayScopeTests(TestCase):
    def test_current_amendment_scope_expands_all_ancestors(self):
        from apps.documents.models import Document
        from services.chat_service import ChatService

        logical_id = uuid.uuid4()
        base = Document.objects.create(
            filename='policy-v1.md',
            original_name='policy-v1.md',
            storage_path='policy-v1.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            version=1,
            is_current=False,
            version_state='superseded',
            metadata={'update_mode': 'full'},
        )
        amendment_v2 = Document.objects.create(
            filename='policy-v2.md',
            original_name='policy-v2.md',
            storage_path='policy-v2.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            previous_version=base,
            version=2,
            is_current=False,
            version_state='superseded',
            metadata={'update_mode': 'amendment', 'effective_document_mode': 'overlay'},
        )
        amendment_v3 = Document.objects.create(
            filename='policy-v3.md',
            original_name='policy-v3.md',
            storage_path='policy-v3.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            previous_version=amendment_v2,
            version=3,
            is_current=True,
            version_state='active',
            metadata={'update_mode': 'amendment', 'effective_document_mode': 'overlay'},
        )

        service = object.__new__(ChatService)
        resolved = service._resolve_document_ids(
            user_id=0,
            conversation_id=None,
            document_ids=[str(amendment_v3.id)],
            folder_ids=[],
        )

        self.assertEqual(resolved[0], str(amendment_v3.id))
        self.assertIn(str(amendment_v2.id), resolved)
        self.assertIn(str(base.id), resolved)

    def test_history_scope_expands_full_replacement_ancestors(self):
        from apps.documents.models import Document
        from services.chat_service import ChatService

        logical_id = uuid.uuid4()
        base = Document.objects.create(
            filename='policy-v1.md',
            original_name='policy-v1.md',
            storage_path='policy-v1.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            version=1,
            is_current=False,
            version_state='superseded',
            metadata={'update_mode': 'full'},
        )
        current = Document.objects.create(
            filename='policy-v2.md',
            original_name='policy-v2.md',
            storage_path='policy-v2.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            previous_version=base,
            version=2,
            is_current=True,
            version_state='active',
            metadata={'update_mode': 'full'},
        )

        service = object.__new__(ChatService)
        resolved = service._expand_previous_version_scope([str(current.id)])

        self.assertEqual(resolved[0], str(current.id))
        self.assertIn(str(base.id), resolved)

    def test_effective_revision_link_pairs_base_and_partial_amendment(self):
        from apps.documents.models import ChunkRevisionLink, Document, DocumentChunk
        from services.chat_service import ChatService

        logical_id = uuid.uuid4()
        base = Document.objects.create(
            filename='policy-v1.md',
            original_name='policy-v1.md',
            storage_path='policy-v1.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            version=1,
            is_current=False,
            version_state='superseded',
            metadata={'update_mode': 'full'},
        )
        amendment = Document.objects.create(
            filename='policy-v2.md',
            original_name='policy-v2.md',
            storage_path='policy-v2.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            previous_version=base,
            version=2,
            is_current=True,
            version_state='active',
            metadata={'update_mode': 'amendment', 'effective_document_mode': 'overlay'},
        )
        base_chunk = DocumentChunk.objects.create(
            document=base,
            content='Điều 4. KPI gồm các khoản 1 đến 5.',
            chunk_index=0,
            is_current=True,
            metadata={'legal_section_key': 'điều:4'},
        )
        amendment_chunk = DocumentChunk.objects.create(
            document=amendment,
            content='Bổ sung khoản 6 Điều 4: Chuyển đổi số 10%.',
            chunk_index=0,
            is_current=True,
            previous_version_chunk=base_chunk,
            lineage_id=base_chunk.lineage_id,
            change_type='modified',
            metadata={'legal_section_key': 'điều:1'},
        )
        ChunkRevisionLink.objects.create(
            from_chunk=base_chunk,
            to_chunk=amendment_chunk,
            relation='references',
            confidence=0.88,
            match_method='amendment_target',
        )

        service = object.__new__(ChatService)
        expanded = service._expand_candidates_with_effective_revision_links(
            [{
                'chunk_id': str(base_chunk.id),
                'document_id': str(base.id),
                'score': 0.9,
                'source': 'bm25',
                'snippet': base_chunk.content,
            }],
            [str(base.id), str(amendment.id)],
        )

        self.assertEqual(len(expanded), 2)
        linked = next(item for item in expanded if item['chunk_id'] == str(amendment_chunk.id))
        self.assertEqual(linked['source'], 'effective_revision_link')
        self.assertEqual(linked['revision_relation'], 'references')


class AutomaticUpdateModeTests(TestCase):
    def _document(self, logical_id, version, *, current, previous=None):
        from apps.documents.models import Document

        return Document.objects.create(
            filename=f'policy-v{version}.md',
            original_name=f'policy-v{version}.md',
            storage_path=f'policy-v{version}.md',
            file_type='md',
            file_size=100,
            status='completed',
            logical_document_id=logical_id,
            previous_version=previous,
            version=version,
            is_current=current,
            version_state='active' if current else 'staging',
            metadata={'update_mode': 'auto'},
        )

    @staticmethod
    def _add_chunks(document, contents, *, current):
        from apps.documents.models import DocumentChunk

        for index, content in enumerate(contents):
            DocumentChunk.objects.create(
                document=document,
                content=content,
                chunk_index=index,
                node_type='detail',
                is_current=current,
                metadata={'heading_path': [f'Điều {index + 1}']},
            )

    def test_auto_detects_partial_amendment(self):
        logical_id = uuid.uuid4()
        base = self._document(logical_id, 1, current=True)
        candidate = self._document(logical_id, 2, current=False, previous=base)
        self._add_chunks(
            base,
            [f'Điều {index}. Nội dung quy định hiện hành số {index}.' for index in range(1, 6)],
            current=True,
        )
        self._add_chunks(
            candidate,
            ['Văn bản này sửa đổi ý 2 Điều 1 thành mức KPI mới là 35%.'],
            current=False,
        )

        mode, evidence = DocumentVersionService()._classify_update_mode(candidate, base)

        self.assertEqual(mode, 'amendment')
        self.assertEqual(evidence['reason'], 'explicit_amendment_directives')
        self.assertIn('dieu:1', evidence['target_section_keys'])

    def test_auto_detects_full_replacement(self):
        logical_id = uuid.uuid4()
        base = self._document(logical_id, 1, current=True)
        candidate = self._document(logical_id, 2, current=False, previous=base)
        old_contents = [
            f'Điều {index}. Nội dung quy định hiện hành số {index} áp dụng cho toàn công ty.'
            for index in range(1, 6)
        ]
        new_contents = [
            f'Điều {index}. Nội dung quy định cập nhật số {index} áp dụng cho toàn công ty.'
            for index in range(1, 6)
        ]
        self._add_chunks(base, old_contents, current=True)
        self._add_chunks(candidate, new_contents, current=False)

        mode, evidence = DocumentVersionService()._classify_update_mode(candidate, base)

        self.assertEqual(mode, 'full')
        self.assertEqual(evidence['reason'], 'candidate_covers_most_of_effective_document')
        self.assertGreaterEqual(evidence['section_coverage'], 0.6)
