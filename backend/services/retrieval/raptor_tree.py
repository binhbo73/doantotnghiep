from typing import List, Dict, Any, Optional
import logging
import threading
import hashlib
import concurrent.futures
import json

import numpy as np
from django.apps import apps
from django.conf import settings

try:
    from umap import UMAP
except Exception:  # pragma: no cover - optional dependency fallback
    UMAP = None

try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import normalize as sklearn_normalize
    from sklearn.decomposition import PCA
except Exception:  # pragma: no cover - optional dependency fallback
    GaussianMixture = None
    sklearn_normalize = None
    PCA = None

logger = logging.getLogger(__name__)


class RaptorTreeBuilder:
    """Hierarchical RAPTOR tree builder.

    Builds a multi-level tree of:
    - leaf chunks
    - page summaries
    - section summaries
    - document summary
    """

    def __init__(self, embedding_client=None, qdrant_client=None):
        self.DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client

    def _get_exact_page_count(self, document) -> int:
        """Get the parsed page count recorded from the original file metadata."""
        metadata = document.metadata or {}
        # The source of truth should be 'page_count' set in ParsingStage
        page_count = metadata.get('page_count') or metadata.get('pages')
        
        if page_count is not None:
            return int(page_count)
            
        # If not in metadata, try counting unique page_numbers in detail chunks
        unique_pages = document.chunks.filter(is_deleted=False, node_type='detail').values_list('page_number', flat=True).distinct()
        if unique_pages.exists():
            return unique_pages.count()
            
        return 0 # Return 0 instead of 1 to signal "not determined"

    def _is_spreadsheet_document(self, document) -> bool:
        metadata = document.metadata or {}
        file_type = (getattr(document, 'file_type', '') or '').lower()
        mime_type = (getattr(document, 'mime_type', '') or '').lower()
        return (
            file_type in {'xlsx', 'xls', 'csv'}
            or 'spreadsheet' in mime_type
            or mime_type == 'text/csv'
            or bool(metadata.get('spreadsheet'))
        )

    def _should_build_spreadsheet(self, document) -> bool:
        if not getattr(settings, 'RAG_SPREADSHEET_RAPTOR_ENABLED', True):
            return False

        metadata = document.metadata or {}
        spreadsheet = metadata.get('spreadsheet') or {}
        sheet_count = int(
            metadata.get('spreadsheet_sheet_count')
            or spreadsheet.get('sheet_count')
            or self._get_exact_page_count(document)
            or 0
        )
        total_rows = int(
            metadata.get('spreadsheet_total_rows')
            or spreadsheet.get('total_non_empty_rows')
            or 0
        )
        total_chunks = int(
            metadata.get('chunk_count')
            or document.chunks.filter(is_deleted=False, node_type='detail').count()
            or 0
        )

        return (
            sheet_count >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_SHEETS', 3))
            or total_rows >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_ROWS', 200))
            or total_chunks >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_CHUNKS', 12))
        )

    def should_build(self, document) -> bool:
        """Decide whether RAPTOR should be applied to a document."""
        try:
            if self._is_spreadsheet_document(document):
                return self._should_build_spreadsheet(document)

            # Use the global threshold from settings
            threshold = getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3)
            
            page_cnt = self._get_exact_page_count(document)
            if page_cnt >= threshold:
                return True
                
            # Fallback for documents without explicit page count
            total_chunks = document.chunks.filter(is_deleted=False, node_type='detail').count()
            # If we have more than (threshold * 5) chunks, it's likely a long document
            return total_chunks > (threshold * 5)
        except Exception:
            return False

    def _get_cluster_settings(self) -> Dict[str, Any]:
        return {
            'enabled': bool(getattr(settings, 'RAG_RAPTOR_CLUSTERING_ENABLED', True)),
            'max_depth': max(1, int(getattr(settings, 'RAG_RAPTOR_MAX_DEPTH', 4))),
            'min_cluster_size': max(2, int(getattr(settings, 'RAG_RAPTOR_MIN_CLUSTER_SIZE', 4))),
            'max_clusters': max(2, int(getattr(settings, 'RAG_RAPTOR_MAX_CLUSTERS', 8))),
            'umap_neighbors': max(2, int(getattr(settings, 'RAG_RAPTOR_UMAP_NEIGHBORS', 15))),
            'umap_components': max(2, int(getattr(settings, 'RAG_RAPTOR_UMAP_COMPONENTS', 5))),
            'membership_threshold': min(
                0.95,
                max(0.01, float(getattr(settings, 'RAG_RAPTOR_GMM_MEMBERSHIP_THRESHOLD', 0.10))),
            ),
            'max_memberships_per_node': max(
                1,
                int(getattr(settings, 'RAG_RAPTOR_MAX_MEMBERSHIPS_PER_NODE', 3)),
            ),
            'random_state': int(getattr(settings, 'RAG_RAPTOR_RANDOM_STATE', 42)),
        }

    @staticmethod
    def _node_sort_key(node) -> tuple:
        metadata = getattr(node, 'metadata', None) or {}
        page_number = getattr(node, 'page_number', None)
        chunk_index = getattr(node, 'chunk_index', None)

        if page_number is None:
            page_number = metadata.get('page_number')
        if page_number is None:
            page_number = metadata.get('row_start') or metadata.get('sheet_index') or 10**9
        if chunk_index is None:
            chunk_index = metadata.get('chunk_index') or metadata.get('row_number') or 0

        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 10**9

        try:
            chunk_index = int(chunk_index)
        except (TypeError, ValueError):
            chunk_index = 0

        return (page_number, chunk_index, str(getattr(node, 'id', '')))

    def _load_node_embedding(self, node) -> Optional[List[float]]:
        """Load a stored embedding vector for a chunk or summary node."""
        try:
            embeddings_rel = getattr(node, 'embeddings', None)
            if embeddings_rel is not None:
                embedding_obj = embeddings_rel.filter(is_deleted=False).order_by('-created_at').first()
                if embedding_obj and embedding_obj.embedding_vector:
                    vector = embedding_obj.embedding_vector
                    if isinstance(vector, str):
                        vector = json.loads(vector)
                    if hasattr(vector, 'tolist'):
                        vector = vector.tolist()
                    if isinstance(vector, list) and vector:
                        return [float(value) for value in vector]
        except Exception as e:
            logger.debug(f"Failed to load stored embedding for node {getattr(node, 'id', '?')}: {e}")

        if self.embedding_client and getattr(node, 'content', None):
            try:
                embedding = self.embedding_client.create_embedding(node.content)
                if embedding is not None:
                    if hasattr(embedding, 'tolist'):
                        embedding = embedding.tolist()
                    return [float(value) for value in embedding]
            except Exception as e:
                logger.debug(f"Failed to generate fallback embedding for node {getattr(node, 'id', '?')}: {e}")

        return None

    def _cluster_nodes_with_umap_gmm(self, nodes: List[Any]) -> List[List[Any]]:
        """Cluster nodes by embedding similarity using UMAP + GMM.

        Returns a list of ordered node groups. Each group becomes one summary node.
        Falls back to a single ordered group when clustering is unavailable or
        the sample count is too small.
        """
        ordered_nodes = sorted(nodes, key=self._node_sort_key)
        if len(ordered_nodes) <= 1:
            return [ordered_nodes]

        cfg = self._get_cluster_settings()
        if not cfg['enabled']:
            logger.warning("[RAPTOR] Clustering is disabled; skipping RAPTOR tree build")
            return []
        if UMAP is None or GaussianMixture is None or sklearn_normalize is None:
            logger.warning("[RAPTOR] UMAP/GMM dependencies are unavailable; skipping RAPTOR tree build")
            return []

        vectors: List[List[float]] = []
        usable_nodes: List[Any] = []
        for node in ordered_nodes:
            embedding = self._load_node_embedding(node)
            if embedding is None:
                logger.warning(f"[RAPTOR] Missing embedding for node {getattr(node, 'id', '?')}; skipping RAPTOR tree build")
                return []
            vectors.append(embedding)
            usable_nodes.append(node)

        if len(usable_nodes) <= 1:
            return [usable_nodes]
        if len(usable_nodes) < cfg['min_cluster_size']:
            return [usable_nodes]

        matrix = np.asarray(vectors, dtype=np.float32)
        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        matrix = sklearn_normalize(matrix)

        n_samples, n_features = matrix.shape
        if n_samples < 2:
            return [usable_nodes]

        max_cluster_count = min(cfg['max_clusters'], n_samples)
        if n_samples >= cfg['min_cluster_size'] * 2:
            max_cluster_count = max(2, min(max_cluster_count, max(2, n_samples // cfg['min_cluster_size'])))
        else:
            logger.debug(
                "[RAPTOR] Skipping UMAP/GMM clustering: samples=%s min_required=%s",
                n_samples,
                cfg['min_cluster_size'] * 2,
            )
            return [usable_nodes]

        # UMAP spectral initialization asks for n_components + 1 eigenvectors.
        # Keep n_components <= n_samples - 2 so scipy eigsh does not hit k >= N
        # on small page-window sets. Small sets already returned above.
        umap_components = max(2, min(cfg['umap_components'], n_samples - 2, n_features))
        umap_neighbors = max(2, min(cfg['umap_neighbors'], n_samples - 1))

        try:
            reducer = UMAP(
                n_components=umap_components,
                n_neighbors=umap_neighbors,
                min_dist=0.0,
                metric='cosine',
                random_state=cfg['random_state'],
                transform_seed=cfg['random_state'],
                n_jobs=1,
                low_memory=True,
            )
            reduced = reducer.fit_transform(matrix)
        except Exception as e:
            logger.warning(f"[RAPTOR] UMAP reduction failed: {e}")
            # Fallback: use PCA when available to produce a dense reduction.
            if PCA is not None:
                try:
                    pca_components = max(1, min(umap_components, n_samples - 1))
                    pca = PCA(n_components=pca_components)
                    reduced = pca.fit_transform(matrix)
                    logger.info("[RAPTOR] PCA fallback succeeded after UMAP failure")
                except Exception as e2:
                    logger.warning(f"[RAPTOR] PCA fallback also failed; skipping RAPTOR tree build: {e2}")
                    return []
            else:
                logger.warning("[RAPTOR] PCA not available as fallback; skipping RAPTOR tree build")
                return []

        best_labels = None
        best_probs = None
        best_bic = None
        best_k = 1

        for k in range(1, max_cluster_count + 1):
            if k > n_samples:
                break
            try:
                gmm = GaussianMixture(
                    n_components=k,
                    covariance_type='full',
                    random_state=cfg['random_state'],
                    reg_covar=1e-4,
                    n_init=2,
                )
                gmm.fit(reduced)
                bic = gmm.bic(reduced)
                if best_bic is None or bic < best_bic:
                    best_bic = bic
                    best_probs = gmm.predict_proba(reduced)
                    best_labels = np.argmax(best_probs, axis=1)
                    best_k = k
            except Exception as e:
                logger.debug(f"[RAPTOR] GMM fit failed for k={k}: {e}")

        if best_labels is None or best_probs is None:
            return [usable_nodes]

        if best_k == 1 and max_cluster_count >= 2 and n_samples >= cfg['min_cluster_size'] * 2:
            try:
                gmm = GaussianMixture(
                    n_components=2,
                    covariance_type='full',
                    random_state=cfg['random_state'],
                    reg_covar=1e-4,
                    n_init=2,
                )
                gmm.fit(reduced)
                best_probs = gmm.predict_proba(reduced)
                best_labels = np.argmax(best_probs, axis=1)
                best_k = 2
            except Exception as e:
                logger.debug(f"[RAPTOR] Forced 2-way split failed: {e}")

        grouped: Dict[int, List[Any]] = {}
        membership_threshold = float(cfg['membership_threshold'])
        max_memberships = int(cfg['max_memberships_per_node'])
        membership_counts: List[int] = []

        for row_index, node in enumerate(usable_nodes):
            probabilities = best_probs[row_index]
            ranked_labels = [
                int(label)
                for label in np.argsort(probabilities)[::-1]
                if float(probabilities[label]) >= membership_threshold
            ][:max_memberships]

            if not ranked_labels:
                ranked_labels = [int(best_labels[row_index])]

            membership_counts.append(len(ranked_labels))
            for label in ranked_labels:
                grouped.setdefault(label, []).append(node)

        if any(count > 1 for count in membership_counts):
            logger.info(
                "[RAPTOR] Multi-cluster memberships enabled: "
                f"{sum(1 for count in membership_counts if count > 1)}/{len(membership_counts)} "
                f"nodes assigned to multiple clusters "
                f"(threshold={membership_threshold}, max_memberships={max_memberships})"
            )

        ordered_groups = sorted(
            grouped.values(),
            key=lambda group: self._node_sort_key(sorted(group, key=self._node_sort_key)[0]),
        )
        return [sorted(group, key=self._node_sort_key) for group in ordered_groups if group]

    def _create_summary_node(
        self,
        document_id: str,
        children: List[Any],
        level: int,
        cluster_index: int,
        cluster_path: str,
        summary_kind: str = 'cluster_summary',
        cluster_algorithm: str = 'umap_gmm',
    ) -> Optional[Dict[str, Any]]:
        """Create or update a summary node for a cluster of children."""
        if not children:
            return None

        ordered_children = sorted(children, key=self._node_sort_key)
        summary_text = self._compose_summary_text(ordered_children, use_llm=True)
        if not summary_text:
            return None

        first_child = ordered_children[0]
        page_numbers = []
        for child in ordered_children:
            child_page = getattr(child, 'page_number', None)
            if child_page is not None:
                page_numbers.append(child_page)
            child_metadata = getattr(child, 'metadata', None) or {}
            child_page_range = child_metadata.get('page_range')
            if isinstance(child_page_range, list) and len(child_page_range) == 2:
                page_numbers.extend(child_page_range)
        child_ids = [str(getattr(child, 'id', '')) for child in ordered_children]
        cluster_hash = hashlib.md5(
            f"{document_id}:{level}:{cluster_path}:{'|'.join(child_ids)}".encode()
        ).hexdigest()

        summary_metadata: Dict[str, Any] = {
            **self._summary_metadata_for_chunks(ordered_children),
            'raptor_level': level,
            'cluster_level': level,
            'cluster_index': cluster_index,
            'cluster_path': cluster_path,
            'cluster_hash': cluster_hash,
            'cluster_algorithm': cluster_algorithm,
            'summary_kind': summary_kind,
            'child_node_count': len(ordered_children),
            'child_node_ids': child_ids[:50],
        }
        if page_numbers:
            summary_metadata['page_range'] = [min(int(p) for p in page_numbers), max(int(p) for p in page_numbers)]

        summary_chunk, created = self.DocumentChunk.objects.get_or_create(
            document_id=document_id,
            node_type='summary',
            metadata__raptor_level=level,
            metadata__cluster_hash=cluster_hash,
            defaults={
                'content': summary_text[:4000],
                'summary': summary_text[:4000],
                'page_number': getattr(first_child, 'page_number', 1) or 1,
                'chunk_index': getattr(first_child, 'chunk_index', 0) or 0,
                'metadata': summary_metadata,
            },
        )

        summary_chunk.content = summary_text[:4000]
        summary_chunk.summary = summary_text[:4000]
        summary_chunk.page_number = getattr(first_child, 'page_number', 1) or 1
        summary_chunk.chunk_index = getattr(first_child, 'chunk_index', 0) or 0
        summary_chunk.metadata = summary_metadata
        summary_chunk.save()

        for child in ordered_children:
            child_metadata = getattr(child, 'metadata', None) or {}
            parent_ids = list(child_metadata.get('raptor_parent_node_ids') or [])
            summary_id = str(summary_chunk.id)
            if summary_id not in parent_ids:
                parent_ids.append(summary_id)
                child_metadata['raptor_parent_node_ids'] = parent_ids[:20]
                child.metadata = child_metadata
                child.save(update_fields=['metadata'])

            if getattr(child, 'parent_node_id', None) is None:
                child.parent_node = summary_chunk
                child.save(update_fields=['parent_node'])

        self._embed_and_store(summary_chunk)

        return {
            'summary_chunk_id': str(summary_chunk.id),
            'cluster_index': cluster_index,
            'cluster_level': level,
            'cluster_path': cluster_path,
            'summary_kind': summary_kind,
            'child_count': len(ordered_children),
            'page_number': summary_chunk.page_number,
            'created': created,
        }

    def _build_recursive_cluster_tree(
        self,
        document_id: str,
        seed_nodes: List[Any],
        start_level: int = 2,
        max_level: Optional[int] = None,
    ) -> tuple[List[Dict[str, Any]], List[Any]]:
        """Build upper RAPTOR levels from page summaries using recursive clustering."""
        created: List[Dict[str, Any]] = []
        if not seed_nodes:
            return created, []

        current_nodes: List[Any] = sorted(seed_nodes, key=self._node_sort_key)
        cfg = self._get_cluster_settings()
        max_depth = max_level or cfg['max_depth']
        level = start_level
        next_level_nodes: List[Any] = []

        while current_nodes and level <= max_depth:
            clusters = self._cluster_nodes_with_umap_gmm(current_nodes)
            if not clusters:
                break

            next_level_nodes: List[Any] = []
            for cluster_index, cluster_nodes in enumerate(clusters, start=1):
                cluster_path = f"L{level}-C{cluster_index}"
                summary_info = self._create_summary_node(
                    document_id=document_id,
                    children=cluster_nodes,
                    level=level,
                    cluster_index=cluster_index,
                    cluster_path=cluster_path,
                    summary_kind='cluster_summary',
                    cluster_algorithm='umap_gmm',
                )
                if summary_info:
                    created.append(summary_info)
                    summary_node = self.DocumentChunk.objects.get(pk=summary_info['summary_chunk_id'])
                    next_level_nodes.append(summary_node)

            if not next_level_nodes:
                break

            if len(next_level_nodes) == 1:
                break

            current_nodes = next_level_nodes
            level += 1

        return created, next_level_nodes or current_nodes

    def _build_page_window_summaries(
        self,
        document_id: str,
        page_summaries: List[Any],
        window_size: Optional[int] = None,
    ) -> tuple[List[Dict[str, Any]], List[Any]]:
        """Build ordered fixed-size page-window summaries before semantic clustering.

        This gives the tree a stable document-order layer, e.g. pages 1-3,
        4-6, 7-9. RAPTOR clustering is still applied above these windows.
        """
        ordered_pages = sorted(page_summaries or [], key=self._node_sort_key)
        if not ordered_pages:
            return [], []

        window_size = max(
            1,
            int(window_size or getattr(settings, 'RAG_RAPTOR_PAGE_WINDOW_SIZE', 3)),
        )
        created: List[Dict[str, Any]] = []
        window_nodes: List[Any] = []

        for index in range(0, len(ordered_pages), window_size):
            group = ordered_pages[index:index + window_size]
            if not group:
                continue
            start_page = getattr(group[0], 'page_number', 1) or 1
            end_page = getattr(group[-1], 'page_number', start_page) or start_page
            cluster_index = (index // window_size) + 1
            summary_info = self._create_summary_node(
                document_id=document_id,
                children=group,
                level=2,
                cluster_index=cluster_index,
                cluster_path=f"PAGES-{start_page}-{end_page}",
                summary_kind='page_window_summary',
                cluster_algorithm='fixed_page_window',
            )
            if summary_info:
                created.append(summary_info)
                window_nodes.append(self.DocumentChunk.objects.get(pk=summary_info['summary_chunk_id']))

        window_nodes = sorted(window_nodes, key=self._node_sort_key)
        self._link_ordered_summary_nodes(window_nodes)
        return created, window_nodes

    def _link_ordered_summary_nodes(self, nodes: List[Any]) -> None:
        """Link same-level summary nodes in document order for page-to-page traversal."""
        ordered_nodes = sorted(nodes or [], key=self._node_sort_key)
        for index, node in enumerate(ordered_nodes):
            previous = ordered_nodes[index - 1] if index > 0 else None
            next_node = ordered_nodes[index + 1] if index + 1 < len(ordered_nodes) else None
            update_fields = []
            if getattr(node, 'prev_chunk_id', None) != (previous.id if previous else None):
                node.prev_chunk = previous
                update_fields.append('prev_chunk')
            if getattr(node, 'next_chunk_id', None) != (next_node.id if next_node else None):
                node.next_chunk = next_node
                update_fields.append('next_chunk')
            if update_fields:
                node.save(update_fields=update_fields)

    def build_tree(self, document_id: str) -> List[Dict[str, Any]]:
        """Build a page-first RAPTOR tree.

        The stable hierarchy is:
        - detail chunks grouped under page summaries
        - page summaries linked in source order
        - fixed page-window summaries, default 3 pages each, linked in source order
        - upper summaries built by recursive UMAP + GMM clustering over page windows
        - an explicit document summary root for overview questions
        """
        created = []
        try:
            from django.apps import apps
            from django.conf import settings
            Document = apps.get_model('documents', 'Document')
            doc = Document.objects.get(pk=document_id)

            if not self.should_build(doc):
                logger.info(f"Skipping RAPTOR tree building for document {document_id} (below threshold)")
                return []

            page_cnt = self._get_exact_page_count(doc)
            logger.info(f"🏗️ Building RAPTOR tree for document {document_id} ({page_cnt} pages)")

            chunks_qs = doc.chunks.filter(is_deleted=False, node_type='detail').order_by('page_number', 'chunk_index')
            if not chunks_qs.exists():
                logger.info(f"No detail chunks for document {document_id}, skipping RAPTOR")
                return []

            detail_chunks = list(chunks_qs)

            page_groups: Dict[int, List[Any]] = {}
            for chunk in detail_chunks:
                page_groups.setdefault(int(getattr(chunk, 'page_number', None) or 1), []).append(chunk)

            page_created = self._build_page_summaries_parallel(document_id, page_groups)
            created.extend(page_created)

            page_summary_ids = [item['summary_chunk_id'] for item in page_created if item.get('summary_chunk_id')]
            page_summaries = list(
                self.DocumentChunk.objects.filter(
                    id__in=page_summary_ids,
                    is_deleted=False,
                    node_type='summary',
                )
            )
            page_summaries = sorted(page_summaries, key=self._node_sort_key)
            if not page_summaries:
                logger.warning(f"[RAPTOR] No page summaries created for document {document_id}")
                return created

            self._link_ordered_summary_nodes(page_summaries)

            window_created, window_summaries = self._build_page_window_summaries(
                document_id,
                page_summaries,
                window_size=int(getattr(settings, 'RAG_RAPTOR_PAGE_WINDOW_SIZE', 3)),
            )
            created.extend(window_created)

            cfg = self._get_cluster_settings()
            max_depth = max(3, int(cfg.get('max_depth', 4)))
            max_cluster_level = max(3, max_depth - 1)
            if len(window_summaries) > 1:
                cluster_created, root_nodes = self._build_recursive_cluster_tree(
                    document_id,
                    window_summaries,
                    start_level=3,
                    max_level=max_cluster_level,
                )
            else:
                cluster_created, root_nodes = [], window_summaries
            created.extend(cluster_created)

            if root_nodes:
                root_nodes = sorted(root_nodes, key=self._node_sort_key)
                max_child_level = max(
                    int((getattr(node, 'metadata', None) or {}).get('raptor_level') or 1)
                    for node in root_nodes
                )
                document_level = max_child_level + 1
                document_summary = self._create_summary_node(
                    document_id=document_id,
                    children=root_nodes,
                    level=document_level,
                    cluster_index=1,
                    cluster_path='DOCUMENT',
                    summary_kind='document_summary',
                    cluster_algorithm='document_root',
                )
                if document_summary:
                    created.append(document_summary)

            logger.info(
                f"Built page-first RAPTOR tree for document {document_id} "
                f"with {len(created)} summary nodes"
            )
            return created

        except Exception as e:
            logger.error(f"Error building RAPTOR tree for {document_id}: {e}")
            return []

    def _build_page_summaries_parallel(self, document_id: str, page_groups: Dict[int, List[Any]]) -> List[Dict[str, Any]]:
        created = []
        
        def process_page(page, chunks):
            ordered_chunks = sorted(chunks, key=self._node_sort_key)
            summary_text = self._compose_summary_text(ordered_chunks, use_llm=True)
            if not summary_text:
                return None

            # Generate a content hash to identify unique summaries
            content_hash = hashlib.md5(summary_text.encode()).hexdigest()
            child_ids = [str(chunk.id) for chunk in ordered_chunks]
            page_metadata = {
                **self._summary_metadata_for_chunks(ordered_chunks),
                'raptor_level': 1,
                'summary_kind': 'page_summary',
                'page_number': page,
                'page_range': [page, page],
                'child_node_count': len(ordered_chunks),
                'child_chunk_count': len(ordered_chunks),
                'child_node_ids': child_ids[:100],
                'content_hash': content_hash,
            }

            page_summary, created = self.DocumentChunk.objects.get_or_create(
                document_id=document_id,
                page_number=page,
                node_type='summary',
                metadata__summary_kind='page_summary',
                defaults={
                    'content': summary_text[:4000],
                    'summary': summary_text[:4000],
                    'chunk_index': ordered_chunks[0].chunk_index if ordered_chunks else 0,
                    'metadata': page_metadata,
                }
            )

            page_summary.content = summary_text[:4000]
            page_summary.summary = summary_text[:4000]
            page_summary.chunk_index = ordered_chunks[0].chunk_index if ordered_chunks else 0
            page_summary.metadata = page_metadata
            page_summary.save()

            if not created:
                logger.info(f"♻️  [RAPTOR] Page Summary for Page {page} already exists, skipping creation")
            else:
                logger.info(f"✅ [RAPTOR] Created Page Summary for Page {page}")

            for child in ordered_chunks:
                child.parent_node = page_summary
                child.save(update_fields=['parent_node'])

            # Generate embedding and store in Qdrant
            self._embed_and_store(page_summary)
            return {
                'summary_chunk_id': str(page_summary.id),
                'page': page,
                'summary_kind': 'page_summary',
                'child_count': len(ordered_chunks),
            }

        max_workers = max(1, int(getattr(settings, 'RAG_RAPTOR_BUILD_WORKERS', 1)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {executor.submit(process_page, p, c): p for p, c in page_groups.items()}
            for future in concurrent.futures.as_completed(future_to_page):
                res = future.result()
                if res:
                    created.append(res)
                    logger.info(f"✅ [RAPTOR] Finished Page Summary for Page {res['page']}")
        
        return sorted(created, key=lambda x: x['page'])

    def _build_section_summaries_parallel(self, document_id: str, page_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created = []
        if not page_summaries:
            return []

        page_summary_ids = [item['summary_chunk_id'] for item in page_summaries]
        page_summary_objs = list(self.DocumentChunk.objects.filter(id__in=page_summary_ids).order_by('page_number'))

        pages_per_section = 4
        section_groups = [page_summary_objs[i:i + pages_per_section] for i in range(0, len(page_summary_objs), pages_per_section)]

        def process_section(section_index, group):
            section_text = self._compose_summary_text(group, use_llm=True)
            if not section_text:
                return None

            # Level 2 nodes were previously called 'section', changing to 'summary' 
            # with level 2 to avoid confusion with base page sections.
            section_summary, created = self.DocumentChunk.objects.get_or_create(
                document_id=document_id,
                page_number=getattr(group[0], 'page_number', 1),
                node_type='summary',
                metadata__raptor_level=2,
                defaults={
                    'content': section_text[:4000],
                    'summary': section_text[:4000],
                    'chunk_index': getattr(group[0], 'chunk_index', 0),
                    'metadata': {
                        **self._summary_metadata_for_chunks(group),
                        'raptor_level': 2,
                        'child_summary_count': len(group),
                        'page_range': [getattr(group[0], 'page_number', 1), getattr(group[-1], 'page_number', 1)],
                    },
                }
            )

            if not created:
                logger.info(f"♻️  [RAPTOR] Section Summary {section_index} already exists")
            else:
                logger.info(f"✅ [RAPTOR] Created Section Summary {section_index}")

            for page_summary in group:
                page_summary.parent_node = section_summary
                page_summary.save(update_fields=['parent_node'])

            # Generate embedding and store in Qdrant
            self._embed_and_store(section_summary)
            return {
                'section_summary_id': str(section_summary.id),
                'section_index': section_index,
                'child_count': len(group),
                'page_number': section_summary.page_number
            }

        max_workers = max(1, int(getattr(settings, 'RAG_RAPTOR_BUILD_WORKERS', 1)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sec = {executor.submit(process_section, i, g): i for i, g in enumerate(section_groups, 1)}
            for future in concurrent.futures.as_completed(future_to_sec):
                res = future.result()
                if res:
                    created.append(res)
                    logger.info(f"✅ [RAPTOR] Finished Section Summary {res['section_index']}")

        return sorted(created, key=lambda x: x['page_number'])

    def _build_document_summary(self, document_id: str, section_summaries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not section_summaries:
            return None

        summary_ids = [item['section_summary_id'] for item in section_summaries]
        section_objs = list(self.DocumentChunk.objects.filter(id__in=summary_ids).order_by('page_number'))
        document_text = self._compose_summary_text(section_objs, use_llm=True)
        if not document_text:
            return None

        document_summary, created = self.DocumentChunk.objects.get_or_create(
            document_id=document_id,
            node_type='summary',
            metadata__raptor_level=3,
            defaults={
                'content': document_text[:4000],
                'summary': document_text[:4000],
                'page_number': getattr(section_objs[0], 'page_number', 1),
                'chunk_index': getattr(section_objs[0], 'chunk_index', 0),
                'metadata': {
                    **self._summary_metadata_for_chunks(section_objs),
                    'raptor_level': 3,
                    'child_section_count': len(section_objs),
                    'page_range': [getattr(section_objs[0], 'page_number', 1), getattr(section_objs[-1], 'page_number', 1)],
                },
            }
        )

        if not created:
            logger.info(f"♻️  [RAPTOR] Global Document Summary already exists")
        else:
            logger.info(f"✅ [RAPTOR] Created Global Document Summary")

        for section in section_objs:
            section.parent_node = document_summary
            section.save(update_fields=['parent_node'])

        # Generate embedding and store in Qdrant
        self._embed_and_store(document_summary)

        logger.info(
            f"👑 [RAPTOR] Created Global Document Summary (Level 3)\n"
            f"   🆔 ID: {document_summary.id}\n"
            f"   👨‍👦 Parent of {len(section_objs)} sections"
        )

        return {
            'document_summary_id': str(document_summary.id),
            'child_count': len(section_objs),
        }

    def _embed_and_store(self, chunk_obj):
        """Helper to generate embedding and store in Qdrant for RAPTOR nodes."""
        if not self.embedding_client or not self.qdrant_client:
            logger.warning(f"Embedding or Qdrant client missing, skipping vector storage for node {chunk_obj.id}")
            return

        try:
            # 1. Generate embedding
            embedding = self.embedding_client.create_embedding(chunk_obj.content)
            if embedding is None:
                return

            # 2. Store in Qdrant
            doc_obj = chunk_obj.document
            metadata = chunk_obj.metadata or {}
            qdrant_payload = {
                'document_id': str(chunk_obj.document_id),
                'chunk_id': str(chunk_obj.id),
                'chunk_index': chunk_obj.chunk_index,
                'text': chunk_obj.content[:500],
                'text_preview': chunk_obj.content[:500],
                'node_type': chunk_obj.node_type,
                'page_number': chunk_obj.page_number,
                'page_range': metadata.get('page_range'),
                'summary_kind': metadata.get('summary_kind'),
                'raptor_level': metadata.get('raptor_level', 0),
                'parent_node_id': str(chunk_obj.parent_node_id) if chunk_obj.parent_node_id else None,
                'sheet_name': metadata.get('sheet_name'),
                'row_start': metadata.get('row_start'),
                'row_end': metadata.get('row_end'),
                'access_scope': getattr(doc_obj, 'access_scope', 'company'),
                'department_id': str(doc_obj.department_id) if getattr(doc_obj, 'department_id', None) else None,
            }
            
            vector_id = self.qdrant_client.add_embedding(
                embedding=embedding,
                chunk_id=str(chunk_obj.id),
                payload=qdrant_payload
            )
            
            # 3. Update chunk and create DocumentEmbedding
            chunk_obj.vector_id = vector_id
            chunk_obj.save(update_fields=['vector_id'])
            
            DocumentEmbedding = apps.get_model('documents', 'DocumentEmbedding')
            from django.utils import timezone
            import json
            embedding_json = json.dumps(embedding.tolist() if hasattr(embedding, 'tolist') else embedding)
            
            DocumentEmbedding.objects.update_or_create(
                chunk=chunk_obj,
                embedding_model=getattr(self.embedding_client, 'model', 'bge-m3'),
                defaults={
                    'qdrant_vector_id': vector_id,
                    'embedding_vector': embedding_json, # Store for visibility
                    'embedding_dimension': len(embedding),
                    'embedding_computed_at': timezone.now(),
                },
            )
            logger.info(f"Stored RAPTOR node {chunk_obj.id} ({chunk_obj.node_type}) in Qdrant")
        except Exception as e:
            logger.error(f"Failed to embed and store RAPTOR node {chunk_obj.id}: {e}")

    def _compose_summary_text(self, chunks: List[Any], use_llm: bool = False) -> str:
        """Compose summary text from child chunks/summaries.
        
        P1#6: Khi use_llm=True (level >= 2), dung LLM de synthesize summary
        thay vi chi concatenate thuan tuy. Concatenation tao ra chuoi dai cac cau
        roi rac, khong co tinh mach lac. LLM synthesis cho summary chat luong cao hon.
        """
        if self._is_table_chunk_group(chunks):
            return self._compose_table_summary_text(chunks)

        parts = []
        for chunk in chunks:
            summary_text = getattr(chunk, 'summary', None)
            if summary_text:
                parts.append(summary_text)
            elif getattr(chunk, 'content', None):
                parts.append(chunk.content[:400])
        
        combined = ' '.join(parts).strip()
        
        # P1#6: LLM synthesis cho level >= 2 section/document summaries
        if use_llm and len(combined) > 500:
            try:
                synthesized = self._llm_synthesize_summary(combined)
                if synthesized:
                    return synthesized
            except Exception as e:
                logger.warning(f'LLM synthesis failed, using concatenation: {e}')
        
        return combined

    def _is_table_chunk_group(self, chunks: List[Any]) -> bool:
        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', None) or {}
            content = getattr(chunk, 'content', '') or ''
            if metadata.get('content_format') == 'spreadsheet_markdown' or '| Excel row |' in content:
                return True
        return False

    def _summary_metadata_for_chunks(self, chunks: List[Any]) -> Dict[str, Any]:
        sheet_names = []
        row_starts = []
        row_ends = []
        content_formats = set()

        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', None) or {}
            sheet_name = metadata.get('sheet_name')
            if sheet_name and sheet_name not in sheet_names:
                sheet_names.append(sheet_name)
            for key, target in (('row_start', row_starts), ('row_end', row_ends)):
                value = metadata.get(key)
                if value is not None:
                    try:
                        target.append(int(value))
                    except (TypeError, ValueError):
                        pass
            if metadata.get('content_format'):
                content_formats.add(metadata['content_format'])

        summary_metadata: Dict[str, Any] = {}
        if sheet_names:
            summary_metadata['sheet_name'] = sheet_names[0] if len(sheet_names) == 1 else ', '.join(sheet_names[:5])
            summary_metadata['sheet_names'] = sheet_names[:20]
        if row_starts:
            summary_metadata['row_start'] = min(row_starts)
        if row_ends:
            summary_metadata['row_end'] = max(row_ends)
        if content_formats:
            summary_metadata['content_format'] = 'spreadsheet_summary' if 'spreadsheet_markdown' in content_formats else sorted(content_formats)[0]
        return summary_metadata

    def _split_markdown_row(self, line: str) -> List[str]:
        cells = [cell.strip().replace('\\|', '|') for cell in (line or '').strip().strip('|').split('|')]
        return cells

    def _compose_table_summary_text(self, chunks: List[Any]) -> str:
        """Create a deterministic, table-aware summary for spreadsheet chunks."""
        metadata = self._summary_metadata_for_chunks(chunks)
        sheet_label = metadata.get('sheet_name') or 'spreadsheet'
        row_start = metadata.get('row_start')
        row_end = metadata.get('row_end')
        row_label = f"rows {row_start}-{row_end}" if row_start and row_end else "rows unknown"

        columns = []
        row_summaries = []
        for chunk in chunks:
            content = getattr(chunk, 'content', '') or ''
            for line in content.splitlines():
                if not line.startswith('|'):
                    continue
                cells = self._split_markdown_row(line)
                if len(cells) < 2:
                    continue
                if cells[0].lower() == 'excel row':
                    columns = cells
                    continue
                if cells[0].isdigit():
                    values = [cell for cell in cells[1:] if cell]
                    if values:
                        row_summaries.append(f"row {cells[0]}: {'; '.join(values[:6])}")
                if len(row_summaries) >= 10:
                    break
            if len(row_summaries) >= 10:
                break

        column_text = f"Columns: {', '.join(columns)}." if columns else ""
        rows_text = " | ".join(row_summaries[:10])
        summary = (
            f"Spreadsheet summary for sheet {sheet_label}, {row_label}. "
            f"{column_text} Key rows: {rows_text}"
        ).strip()
        return summary[:4000]
    
    def _llm_synthesize_summary(self, text: str) -> str:
        """Goi LLM de synthesize summary tu concatenated child summaries.
        
        Fix: Tang timeout len 300s (tuong thich voi Qwen3-4B tren CPU)
        va giam prompt text xuong 1500 chars de tranh timeout.
        """
        try:
            from services.ai.llama_client import LlamaClient
            
            llama = LlamaClient(timeout=300)
            prompt = (
                "Tong hop cac tom tat sau thanh 1-3 cau tieng Viet, toi da 250 ky tu. "
                "Chi giu y chinh, ten rieng, ngay thang, so lieu, dieu kien va hanh dong quan trong. "
                "Khong suy dien, khong them thong tin ngoai noi dung.\n\n"
                + text[:900] + "\n\n"
                "Tom tat tong hop:"
            )
            summary = llama.complete(
                prompt=prompt,
                max_tokens=96,
                temperature=0.2,
                timeout=300,
            )
            if summary and len(summary.strip()) > 20:
                return summary.strip()[:4000]
        except Exception as e:
            logger.warning(f'LLM synthesis error: {e}')
        return None
