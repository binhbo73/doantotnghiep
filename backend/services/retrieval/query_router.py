from typing import Any, Dict, List
import logging
from django.apps import apps

from .hybrid_retriever import HybridRetriever
from .query_rewriter import QueryRewriter
from .reranker import Reranker
from .raptor_tree import RaptorTreeBuilder

logger = logging.getLogger(__name__)


class QueryRouter:
    """Decides retrieval strategy for incoming queries and returns ranked candidates.

    Simple rules:
    - If query length > 40 words -> consider 'raptor' if document long
    - If query contains keywords ("mã","số","code","id") -> prefer 'sparse' (lexical)
    - Else -> hybrid dense + sparse
    """

    def __init__(self, qdrant_client, embedding_client, llama_client=None):
        self.hybrid = HybridRetriever(qdrant_client=qdrant_client, embedding_client=embedding_client)
        self.reranker = Reranker(llama_client=None)  # Fix A: Disable LLM reranker
        self.raptor = RaptorTreeBuilder()
        self.rewriter = QueryRewriter(llama_client)

    def route(self, query: str, user_context: Dict = None, top_k: int = 5) -> List[Dict]:
        """Quyết định chiến lược retrieval và trả về ranked candidates.

        user_context hỗ trợ 2 keys:
          - 'document_id'  : str  — single doc (cũ, backward compatible)
          - 'document_ids' : List[str] — multi-doc filter (ưu tiên hơn)
        """
        # quick heuristics
        q_words = query.split()
        word_count = len(q_words)
        query_lower = query.lower()

        # Lấy danh sách document IDs để filter (ưu tiên 'document_ids' list)
        document_ids: List[str] = []
        if user_context:
            if user_context.get('document_ids'):
                document_ids = [str(d) for d in user_context['document_ids'] if d]
            elif user_context.get('document_id'):
                document_ids = [str(user_context['document_id'])]

        # Fix: Query expansion disabled for speed - LLM expansion costs 70s on CPU
        # The QueryRewriter is available but only used for simple expansions
        expanded_query = query

        # Step 1: Handle keyword-heavy queries (Lexical/BM25 focus)
        lexical_keywords = ['mã', 'số', 'code', 'id', 'số liệu', 'thông tin', 'danh sách', 'bảng']
        if any(k in query_lower for k in lexical_keywords):
            candidates = self.hybrid.retrieve(
                expanded_query, top_k=top_k, sparse_k=20, document_ids=document_ids
            )

        # Step 2: RAPTOR Logic — dùng khi query dài hoặc document có hierarchical structure
        else:
            # Chỉ thử RAPTOR khi tìm kiếm trong đúng 1 document (nhiều docs → hybrid tốt hơn)
            doc_id = document_ids[0] if len(document_ids) == 1 else None
            use_raptor = False

            if doc_id:
                try:
                    Document = apps.get_model('documents', 'Document')
                    doc = Document.objects.get(pk=doc_id)
                    # Use RAPTOR if document explicitly flagged OR it meets threshold
                    if getattr(doc, 'has_hierarchical_chunks', False) or self.raptor.should_build(doc):
                        use_raptor = True
                except Exception:
                    pass

            # Also use RAPTOR for long queries (>25 words) even without explicit doc_id hint
            if not use_raptor and word_count > 25:
                use_raptor = True

            if use_raptor and doc_id:
                logger.info(f"🚀 Routing query to RAPTOR strategy for document {doc_id}")
                candidates = self._retrieve_via_raptor(query, doc_id, top_k=top_k)
            else:
                # Default to Hybrid search (multi-doc hoặc không có RAPTOR)
                candidates = self.hybrid.retrieve(
                    expanded_query, top_k=top_k, document_ids=document_ids
                )

        # Step 3: Final Rerank for maximum relevance
        ranked = self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)
        return ranked

    def _retrieve_via_raptor(self, query: str, document_id: str, top_k: int = 5) -> List[Dict]:
        """Retrieve using RAPTOR tree: search summary nodes FIRST, then descend to children.
        
        Strategy:
        1. Query summary nodes (node_type='summary') for document
        2. Rank summaries by relevance to query
        3. For top K/2 summaries, retrieve their child chunks
        4. Return merged results with boosted scores from parent summaries
        """
        try:
            from django.apps import apps
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            
            # Step 1: Get all summary nodes for this document
            summary_chunks = DocumentChunk.objects.filter(
                document_id=document_id,
                node_type__in=['summary', 'section'],
                is_deleted=False
            ).order_by('page_number')
            
            if not summary_chunks.exists():
                logger.debug(f"No summary nodes for document {document_id}, falling back to hybrid")
                return self.hybrid.retrieve(query, top_k=top_k)
            
            # Step 2: Generate query embedding
            try:
                query_embedding = self.hybrid.embedding_client.create_embedding(query)
            except Exception as e:
                logger.warning(f"Failed to embed query for RAPTOR: {e}")
                return self.hybrid.retrieve(query, top_k=top_k)
            
            # Step 3: Search Qdrant for summary nodes
            summary_results = self.hybrid.qdrant.search_similar(
                embedding=query_embedding,
                limit=max(2, top_k // 2)
            )
            
            # Filter to only summary nodes in this document
            top_summaries = []
            for vector_id, score, payload in summary_results:
                chunk_id = payload.get('chunk_id')
                if not chunk_id:
                    continue
                try:
                    summary_node = DocumentChunk.objects.get(
                        id=chunk_id,
                        document_id=document_id,
                        node_type='summary',
                        is_deleted=False
                    )
                    top_summaries.append({
                        'node': summary_node,
                        'score': float(score) if score else 0.5,
                        'vector_id': vector_id
                    })
                except DocumentChunk.DoesNotExist:
                    continue
            
            if not top_summaries:
                logger.debug(f"No summary nodes found via Qdrant for document {document_id}")
                return self.hybrid.retrieve(query, top_k=top_k)
            
            logger.debug(f"RAPTOR: Found {len(top_summaries)} summary nodes for document {document_id}")
            
            # Step 4: For each summary, retrieve its children or descendants
            final_candidates = []
            
            for summary_info in top_summaries:
                summary_node = summary_info['node']
                summary_score = summary_info['score']
                node_type = getattr(summary_node, 'node_type', 'summary')
                
                if node_type == 'section':
                    # Retrieve page summaries under section
                    page_summaries = DocumentChunk.objects.filter(
                        parent_node_id=summary_node.id,
                        node_type='summary',
                        is_deleted=False
                    ).order_by('page_number', 'chunk_index')
                    for page_summary in page_summaries[:max(1, top_k // 2)]:
                        child_chunks = DocumentChunk.objects.filter(
                            parent_node_id=page_summary.id,
                            is_deleted=False
                        ).order_by('chunk_index')[:max(1, top_k // 2)]
                        for child in child_chunks:
                            child_score = summary_score * 0.8
                            final_candidates.append({
                                'chunk_id': str(child.id),
                                'document_id': str(document_id),
                                'score': child_score,
                                'source': 'raptor_section_child',
                                'snippet': (child.content or '')[:300],
                                'page': child.page_number,
                                'parent_summary_id': str(page_summary.id)
                            })
                else:
                    # Default: page summary or top-level summary
                    children = DocumentChunk.objects.filter(
                        parent_node_id=summary_node.id,
                        is_deleted=False
                    ).order_by('chunk_index')
                    
                    if children.exists():
                        for child in children[:top_k]:
                            child_score = summary_score * 0.85
                            final_candidates.append({
                                'chunk_id': str(child.id),
                                'document_id': str(document_id),
                                'score': child_score,
                                'source': f'raptor_{node_type}_child',
                                'snippet': (child.content or '')[:300],
                                'page': child.page_number,
                                'parent_summary_id': str(summary_node.id)
                            })
                    else:
                        final_candidates.append({
                            'chunk_id': str(summary_node.id),
                            'document_id': str(document_id),
                            'score': summary_score * 0.9,
                            'source': f'raptor_{node_type}',
                            'snippet': (summary_node.content or '')[:300],
                            'page': summary_node.page_number
                        })
            
            # Sort by score and return top K
            final_candidates = sorted(final_candidates, key=lambda x: x['score'], reverse=True)
            result = final_candidates[:top_k]
            
            # Merge RAPTOR results with hybrid results for better coverage
            hybrid_candidates = self.hybrid.retrieve(query, top_k=top_k)
            
            # Deduplicate by chunk_id
            seen_ids = {c['chunk_id'] for c in result}
            for hc in hybrid_candidates:
                if hc['chunk_id'] not in seen_ids:
                    result.append(hc)
                    seen_ids.add(hc['chunk_id'])
            
            result = sorted(result, key=lambda x: x['score'], reverse=True)[:top_k * 2]
            
            logger.info(
                f"RAPTOR retrieval: {len(result)} results "
                f"({len([c for c in result if 'raptor' in c.get('source', '')])} RAPTOR, "
                f"{len([c for c in result if 'raptor' not in c.get('source', '')])} hybrid)"
            )
            return result
        
        except Exception as e:
            logger.error(f"RAPTOR retrieval failed: {e}", exc_info=True)
            logger.info("Falling back to standard hybrid retrieval")
            return self.hybrid.retrieve(query, top_k=top_k)
