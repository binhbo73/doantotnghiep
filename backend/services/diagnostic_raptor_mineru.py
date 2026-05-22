"""
RAPTOR + Mineru + DocumentChunk Diagnostic Script
==================================================

Purpose: Validate that Mineru metadata is being properly captured in DocumentChunks
and that RAPTOR tree is being built correctly.

Usage:
    from django.core.management import execute_from_command_line
    from services.diagnostic_raptor_mineru import run_diagnostic
    
    run_diagnostic(document_id="doc-uuid-123")
"""

import logging
from typing import Dict, Any, List, Optional
from django.apps import apps

logger = logging.getLogger(__name__)


def run_diagnostic(document_id: str = None) -> Dict[str, Any]:
    """
    Run full diagnostic on a document to validate pipeline.
    
    Args:
        document_id: Optional specific document ID to check. If None, check last 5 docs.
    
    Returns:
        Diagnostic report dict
    """
    Document = apps.get_model('documents', 'Document')
    DocumentChunk = apps.get_model('documents', 'DocumentChunk')
    
    report = {
        'timestamp': None,
        'documents_checked': [],
        'total_issues': 0,
        'warnings': [],
        'successes': [],
    }
    
    from datetime import datetime
    report['timestamp'] = datetime.now().isoformat()
    
    # Get documents to check
    if document_id:
        try:
            docs = [Document.objects.get(pk=document_id)]
        except Document.DoesNotExist:
            return {
                **report,
                'error': f'Document {document_id} not found',
            }
    else:
        # Check last 5 completed documents
        docs = Document.objects.filter(
            status='completed',
            is_deleted=False
        ).order_by('-updated_at')[:5]
    
    for doc in docs:
        doc_report = _check_document(doc, DocumentChunk)
        report['documents_checked'].append(doc_report)
        report['total_issues'] += doc_report['issues']
        report['warnings'].extend(doc_report['warnings'])
        report['successes'].extend(doc_report['successes'])
    
    return report


def _check_document(doc, DocumentChunk) -> Dict[str, Any]:
    """
    Check a single document for RAPTOR + Mineru compliance.
    """
    doc_id = str(doc.id)
    doc_report = {
        'document_id': doc_id,
        'filename': doc.original_name,
        'status': doc.status,
        'file_type': doc.file_type,
        'issues': 0,
        'warnings': [],
        'successes': [],
        'chunk_analysis': {},
        'raptor_analysis': {},
    }
    
    # ========== Chunk Analysis ==========
    detail_chunks = DocumentChunk.objects.filter(
        document_id=doc_id,
        node_type='detail',
        is_deleted=False
    )
    summary_chunks = DocumentChunk.objects.filter(
        document_id=doc_id,
        node_type='summary',
        is_deleted=False
    )
    
    total_chunks = detail_chunks.count() + summary_chunks.count()
    doc_report['chunk_analysis']['total_chunks'] = total_chunks
    doc_report['chunk_analysis']['detail_chunks'] = detail_chunks.count()
    doc_report['chunk_analysis']['summary_chunks'] = summary_chunks.count()
    
    if not detail_chunks.exists():
        doc_report['warnings'].append("❌ No detail chunks found")
        doc_report['issues'] += 1
    else:
        doc_report['successes'].append(f"✅ Found {detail_chunks.count()} detail chunks")
    
    # ========== Mineru Metadata Check ==========
    mineru_metadata_fields = [
        'block_type',
        'heading_path',
        'bbox',
        'reading_order_start',
        'parse_backend',
    ]
    
    chunks_with_metadata = 0
    chunks_with_structured = 0
    metadata_coverage = {field: 0 for field in mineru_metadata_fields}
    
    for chunk in detail_chunks[:20]:  # Check first 20 chunks
        meta = chunk.metadata or {}
        if meta:
            chunks_with_metadata += 1
        
        if meta.get('structured_chunk') or meta.get('parse_backend'):
            chunks_with_structured += 1
        
        for field in mineru_metadata_fields:
            if field in meta and meta[field]:
                metadata_coverage[field] += 1
    
    checked_count = min(20, detail_chunks.count())
    if checked_count > 0:
        doc_report['chunk_analysis']['metadata_coverage'] = {
            field: f"{(coverage/checked_count*100):.1f}%"
            for field, coverage in metadata_coverage.items()
        }
        doc_report['chunk_analysis']['structured_chunk_ratio'] = (
            f"{(chunks_with_structured/checked_count*100):.1f}%"
        )
        
        if chunks_with_structured > 0:
            doc_report['successes'].append(
                f"✅ {chunks_with_structured}/{checked_count} chunks have Mineru metadata"
            )
        else:
            doc_report['warnings'].append(
                "⚠️  No chunks have Mineru structured metadata - may be using plain text chunking"
            )
            doc_report['issues'] += 1
    
    # ========== RAPTOR Analysis ==========
    doc_meta = doc.metadata or {}
    doc_report['raptor_analysis']['raptor_ready'] = doc_meta.get('raptor_ready', False)
    doc_report['raptor_analysis']['raptor_status'] = doc_meta.get('raptor_status', 'unknown')
    doc_report['raptor_analysis']['raptor_node_count'] = doc_meta.get('raptor_node_count', 0)
    doc_report['raptor_analysis']['has_hierarchical_chunks'] = doc.has_hierarchical_chunks
    
    if summary_chunks.exists():
        doc_report['successes'].append(
            f"✅ RAPTOR tree created: {summary_chunks.count()} summary nodes"
        )
        
        # Check if summaries are vectorized
        vectorized = summary_chunks.filter(vector_id__isnull=False).count()
        if vectorized > 0:
            doc_report['successes'].append(
                f"✅ {vectorized}/{summary_chunks.count()} summary nodes vectorized"
            )
        else:
            doc_report['warnings'].append(
                "⚠️  Summary nodes created but not vectorized (RAPTOR retrieval won't work)"
            )
            doc_report['issues'] += 1
    else:
        if doc_meta.get('page_count', 1) < 3:
            doc_report['successes'].append(
                f"ℹ️  RAPTOR skipped: document is {doc_meta.get('page_count', 1)} pages "
                f"(threshold: 3)"
            )
        else:
            doc_report['warnings'].append(
                f"⚠️  RAPTOR not built for {doc_meta.get('page_count', 1)}-page document"
            )
            doc_report['issues'] += 1
    
    # ========== Page Distribution Check ==========
    page_distribution = {}
    for chunk in detail_chunks:
        p = chunk.page_number or 1
        page_distribution[p] = page_distribution.get(p, 0) + 1
    
    if page_distribution:
        doc_report['chunk_analysis']['page_distribution'] = page_distribution
        doc_report['successes'].append(
            f"✅ Chunks distributed across {len(page_distribution)} pages"
        )
    
    # ========== Hierarchy Check ==========
    chunks_with_parent = detail_chunks.filter(parent_node__isnull=False).count()
    if chunks_with_parent > 0:
        doc_report['successes'].append(
            f"✅ {chunks_with_parent} chunks have parent nodes (hierarchical)"
        )
    else:
        if summary_chunks.exists():
            doc_report['warnings'].append(
                "⚠️  Summary nodes exist but detail chunks don't have parents (incorrect hierarchy)"
            )
            doc_report['issues'] += 1
    
    return doc_report


def print_diagnostic_report(report: Dict[str, Any]) -> None:
    """Pretty-print diagnostic report."""
    print("\n" + "="*80)
    print("RAPTOR + MINERU + DOCUMENTCHUNK DIAGNOSTIC REPORT")
    print("="*80)
    print(f"Timestamp: {report.get('timestamp')}")
    print(f"Total Issues: {report['total_issues']}")
    print()
    
    for doc_report in report['documents_checked']:
        print(f"\n📄 Document: {doc_report['filename']}")
        print(f"   ID: {doc_report['document_id']}")
        print(f"   Status: {doc_report['status']} | File Type: {doc_report['file_type']}")
        
        print("\n   📊 Chunk Analysis:")
        for key, val in doc_report['chunk_analysis'].items():
            if isinstance(val, dict):
                print(f"      {key}:")
                for k2, v2 in val.items():
                    print(f"         {k2}: {v2}")
            else:
                print(f"      {key}: {val}")
        
        print("\n   🌳 RAPTOR Analysis:")
        for key, val in doc_report['raptor_analysis'].items():
            print(f"      {key}: {val}")
        
        if doc_report['successes']:
            print("\n   ✅ Successes:")
            for msg in doc_report['successes']:
                print(f"      {msg}")
        
        if doc_report['warnings']:
            print("\n   ⚠️  Warnings:")
            for msg in doc_report['warnings']:
                print(f"      {msg}")
        
        print(f"\n   Issues: {doc_report['issues']}")
    
    print("\n" + "="*80)
    print(f"Total Issues Found: {report['total_issues']}")
    if report['total_issues'] == 0:
        print("✅ All checks passed!")
    print("="*80)


# CLI Integration
if __name__ == '__main__':
    import sys
    doc_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Setup Django
    import django
    django.setup()
    
    report = run_diagnostic(doc_id)
    print_diagnostic_report(report)
