"""
Query Rewriter
==============
P2#10: LLM-based query rewriting/expansion de cai thien recall.

Van de: User thuong hoi bang query ngan, mo ho, thieu context:
- "no hoat dong the nao" -> khong ro "no" la gi
- "cho toi biet ve cai do" -> thieu thong tin cu the
- "loi roi, sua di" -> thieu ngu canh

Giai phap: Dung LLM nhe de:
1. Mo rong query ngan (query expansion)
2. Giai quyet coreference
3. Sinh multiple query variants de search da mat

Su dung:
    rewriter = QueryRewriter(llama_client)
    expanded_queries = rewriter.expand("no hoat dong the nao")
    # -> ["cach thuc hoat dong cua he thong X", "quy trinh van hanh X"]
"""

import logging
import re
import unicodedata
from typing import List, Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryRewriter:
    """LLM-based query rewriting for better retrieval recall."""

    FOLLOW_UP_MARKERS = (
        'xem kĩ', 'xem kỹ', 'xem lại', 'như trên', 'như đã nói', 'ở trên',
        'ở đây', 'chỗ này', 'phần này', 'phần đó', 'đoạn này', 'đoạn đó',
        'cái này', 'cái đó', 'nó', 'đó', 'đây', 'tiếp theo', 'theo đó',
        'trang', 'mục', 'phần', 'mục lục', 'bảng', 'hình', 'đã hỏi',
    )

    HISTORY_STOPWORDS = {
        'cho', 'toi', 'tôi', 'ban', 'bạn', 'hay', 'hãy', 'vui', 'long', 'lòng',
        'cam', 'cảm', 'giup', 'giúp', 'xem', 'khi', 'kĩ', 'kỹ', 'lai', 'lại',
        'cua', 'của', 'va', 'và', 'la', 'là', 'cac', 'các', 'nhung', 'những',
        'mot', 'một', 'noi', 'nội', 'dung', 'phan', 'phần', 'trong', 'tren',
        'trên', 'duoi', 'dưới', 'nay', 'này', 'do', 'đó', 'day', 'đây', 'tai',
        'tài', 'lieu', 'liệu', 'trang', 'muc', 'mục', 'file', 'van', 'vấn',
        'de', 'đề', 'thong', 'thông', 'tin', 've', 'về', 'gi', 'gì',
    }
    
    EXPANSION_PROMPT = (
        "Ban la tro ly giup cai thien cau hoi tim kiem tai lieu. "
        "Nguoi dung da hoi: '{query}'\n\n"
        "Hay viet lai cau hoi nay thanh 1-3 phien ban ro rang, cu the hon "
        "(bang tieng Viet), bo sung ngu canh neu cau hoi qua ngan hoac mo ho. "
        "Chi tra ve cac cau hoi da duoc viet lai, moi cau mot dong. "
        "Khong giai thich gi them.\n\n"
        "Cac phien ban:"
    )
    
    MAX_EXPANSIONS = 3
    MAX_EXPANSION_TOKENS = 128
    EXPANSION_TEMPERATURE = 0.3
    
    def __init__(self, llama_client=None, max_expansions: int = None):
        self.llama = llama_client
        self.max_expansions = max_expansions or self.MAX_EXPANSIONS
        self.enabled = getattr(settings, 'QUERY_REWRITE_ENABLED', True)
        self.llm_enabled = self.enabled and getattr(settings, 'QUERY_REWRITE_LLM_ENABLED', True)
        
    def expand(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        force_llm: bool = False,
    ) -> List[str]:
        """Expand a user query into multiple clearer versions.
        
        Args:
            query: Raw user query
            
        Returns:
            List of expanded query strings (includes original)
        """
        query = (query or '').strip()
        if not query:
            return []

        if not self.enabled:
            return [query]

        variants = [query]

        if self.llama and (self.llm_enabled or force_llm):
            # Keep the legacy LLM path available, but only when we do not
            # already have a better history-aware rewrite.
            q_words = query.split()
            if len(q_words) <= 30 and len(query) >= 5:
                skip_keywords = ['ma ', 'so ', 'id ', 'code ']
                if not any(query.lower().startswith(k) for k in skip_keywords):
                    try:
                        prompt = self.EXPANSION_PROMPT.format(query=query)
                        response = self.llama.complete(
                            prompt=prompt,
                            max_tokens=self.MAX_EXPANSION_TOKENS,
                            temperature=self.EXPANSION_TEMPERATURE,
                        )

                        if response:
                            expansions = []
                            for line in response.strip().split('\n'):
                                line = line.strip()
                                if line and len(line) > 4:
                                    if line[0].isdigit():
                                        line = line.split('. ', 1)[-1] if '. ' in line else line
                                        line = line.split(') ', 1)[-1] if ') ' in line else line
                                    expansions.append(line)

                            for item in expansions[:self.max_expansions]:
                                if item and item not in variants:
                                    variants.append(item)
                    except Exception as e:
                        logger.debug(f"Query expansion failed, falling back to deterministic rewrite: {e}")

        history_rewrite = self._rewrite_with_history(query, conversation_history)
        if history_rewrite and history_rewrite not in variants:
            variants.append(history_rewrite)

        if self._looks_like_follow_up(query, conversation_history) and conversation_history:
            history_focus = self._extract_history_focus(conversation_history)
            if history_focus:
                merged = self._merge_query_and_history(query, history_focus)
                if merged not in variants:
                    variants.append(merged)

        deduped = []
        seen = set()
        for item in variants:
            normalized = self._normalize_text(item)
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(item.strip())

        return deduped[: self.max_expansions + 1]

    def resolve(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        force_llm: bool = False,
    ) -> str:
        """Return the single best search query for retrieval."""
        variants = self.expand(query, conversation_history=conversation_history, force_llm=force_llm)
        if not variants:
            return query
        if len(variants) == 1:
            return variants[0]
        return self._choose_best_variant(query, variants)

    def _rewrite_with_history(self, query: str, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """Create a safer standalone search query using the recent conversation."""
        if not conversation_history:
            return ''

        previous_user = self._get_previous_user_message(conversation_history)
        previous_assistant = self._get_previous_assistant_message(conversation_history)
        seed_text = previous_user or previous_assistant
        if not seed_text:
            return ''

        if not self._looks_like_follow_up(query, conversation_history):
            return ''

        focus_terms = self._extract_focus_terms(seed_text)
        if not focus_terms:
            return ''

        combined = self._merge_query_and_history(query, ' '.join(focus_terms))
        return combined if combined and combined != query else ''

    def _looks_like_follow_up(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> bool:
        text = self._normalize_text(query)
        if not text:
            return False

        if any(marker in text for marker in self.FOLLOW_UP_MARKERS):
            return True

        words = [w for w in re.findall(r'\w+', text) if len(w) >= 3]
        if len(words) <= 6 and conversation_history:
            previous_user = self._get_previous_user_message(conversation_history)
            if previous_user:
                return True

        return False

    def _get_previous_user_message(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        if not conversation_history:
            return ''
        user_messages = [
            (msg.get('content') or '').strip()
            for msg in conversation_history
            if msg.get('role') == 'user' and (msg.get('content') or '').strip()
        ]
        if len(user_messages) >= 2:
            return user_messages[-2]
        if len(user_messages) == 1:
            return user_messages[0]
        return ''

    def _get_previous_assistant_message(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        if not conversation_history:
            return ''
        assistant_messages = [
            (msg.get('content') or '').strip()
            for msg in conversation_history
            if msg.get('role') == 'assistant' and (msg.get('content') or '').strip()
        ]
        return assistant_messages[-1] if assistant_messages else ''

    def _extract_history_focus(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        previous_user = self._get_previous_user_message(conversation_history)
        previous_assistant = self._get_previous_assistant_message(conversation_history)
        seed_text = previous_user or previous_assistant
        focus_terms = self._extract_focus_terms(seed_text)
        return ' '.join(focus_terms)

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize('NFD', (text or '').lower())
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    def _extract_focus_terms(self, text: str, max_terms: int = 8) -> List[str]:
        normalized = self._normalize_text(text)
        tokens = re.findall(r'\w+', normalized)
        focus_terms: List[str] = []
        seen = set()
        for token in tokens:
            if len(token) < 3 or token in self.HISTORY_STOPWORDS:
                continue
            if token not in seen:
                seen.add(token)
                focus_terms.append(token)
            if len(focus_terms) >= max_terms:
                break
        return focus_terms

    def _merge_query_and_history(self, query: str, history_text: str) -> str:
        query_text = (query or '').strip()
        history_terms = ' '.join(self._extract_focus_terms(history_text, max_terms=10))
        if not query_text:
            return history_terms
        if not history_terms:
            return query_text

        query_normalized = self._normalize_text(query_text)
        if history_terms in query_normalized:
            return query_text

        merged = f"{query_text} {history_terms}".strip()
        return re.sub(r'\s+', ' ', merged)

    def _choose_best_variant(self, query: str, variants: List[str]) -> str:
        """Prefer the most explicit query variant for retrieval."""
        query_terms = set(self._extract_focus_terms(query, max_terms=16))
        best_variant = variants[0]
        best_score = -1
        for variant in variants:
            terms = set(self._extract_focus_terms(variant, max_terms=16))
            overlap = len(query_terms & terms)
            score = overlap * 2 + len(terms)
            if len(variant) > len(query) and overlap > 0:
                score += 2
            if score > best_score:
                best_score = score
                best_variant = variant
        return best_variant

    def generate_hypothetical_answer(self, query: str, max_tokens: int = 128, force_llm: bool = False) -> str:
        """HyDE: generate a short hypothetical answer, then embed it for dense search.

        Instead of searching with the raw query embedding (which may be far from
        document embeddings), we ask the LLM to write a short hypothetical answer,
        then embed THAT. The hypothetical answer's embedding is closer to real
        document embeddings, dramatically improving dense retrieval recall.

        Only used for analytical/comparative queries where the answer format
        is predictable (NOT for factual lookups).
        """
        if not self.llama or not self.enabled:
            return ''
        if not force_llm and not getattr(settings, 'RAG_HYDE_ENABLED', True):
            return ''

        hyde_prompt = (
            "Ban la tro ly AI. Hay viet mot doan van ngan (3-5 cau) tra loi cau hoi sau "
            "dua tren kien thuc chung cua ban. Day chi la cau tra loi gia dinh de giup "
            "tim kiem tai lieu tot hon, khong can chinh xac 100%.\n\n"
            f"Cau hoi: {query}\n\n"
            "Cau tra loi gia dinh (ngan gon):"
        )

        try:
            response = self.llama.complete(
                prompt=hyde_prompt,
                max_tokens=max_tokens,
                temperature=0.4,
            )
            if response and len(response.strip()) > 20:
                logger.debug(f"[HYDE] Generated hypothetical answer for '{query[:40]}...'")
                return response.strip()
        except Exception as e:
            logger.debug(f"[HYDE] Failed: {e}")

        return ''

    def decompose_complex_query(self, query: str, force_llm: bool = False) -> List[str]:
        """Multi-hop: decompose a complex query into simpler sub-queries.

        For queries like "Compare A and B" or "What are causes AND effects of X",
        splitting into sub-queries and retrieving for each independently gives
        much better coverage than retrieving for the combined query.
        """
        if not self.llama or not self.enabled:
            return []
        if not force_llm and not getattr(settings, 'RAG_QUERY_DECOMPOSITION_ENABLED', True):
            return []

        decompose_prompt = (
            "Ban la tro ly phan tich cau hoi. Neu cau hoi duoi day la cau hoi PHUC HOP "
            "(yeu cau so sanh, liet ke nhieu y, hoac co nhieu phan doc lap), hay tach no "
            "thanh 2-3 cau hoi con doc lap, moi cau mot dong.\n"
            "Neu cau hoi DON GIAN (1 y chinh), hay tra ve 'SIMPLE'.\n\n"
            f"Cau hoi: {query}\n\n"
            "Ket qua:"
        )

        try:
            response = self.llama.complete(
                prompt=decompose_prompt,
                max_tokens=128,
                temperature=0.2,
            )
            if not response or 'SIMPLE' in response.upper():
                return []

            sub_queries = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and len(line) > 5 and 'SIMPLE' not in line.upper():
                    # Remove numbering
                    if line[0].isdigit():
                        line = line.split('. ', 1)[-1] if '. ' in line else line
                    sub_queries.append(line)

            if sub_queries:
                logger.debug(
                    f"[DECOMPOSE] '{query[:40]}...' -> {len(sub_queries)} sub-queries"
                )
                return sub_queries[:3]
        except Exception as e:
            logger.debug(f"[DECOMPOSE] Failed: {e}")

        return []

    def extract_page_hints(self, query: str) -> Dict[str, Any]:
        """Extract page number and position hints from the query.

        Returns dict with:
        - 'page_numbers': list of int page numbers found
        - 'position': 'end'/'start'/'middle'/None
        - 'has_page_ref': bool
        """
        result: Dict[str, Any] = {
            'page_numbers': [],
            'position': None,
            'has_page_ref': False,
        }

        normalized = self._normalize_text(query)

        # Extract page numbers: "trang 25", "trang số 25", "page 25"
        page_patterns = [
            r'\btrang\s*(?:so\s*)?(\d+)\b',
            r'\bpage\s*(\d+)\b',
            r'\bp\.?\s*(\d+)\b',
        ]
        for pattern in page_patterns:
            for match in re.finditer(pattern, normalized):
                num = int(match.group(1))
                if num not in result['page_numbers']:
                    result['page_numbers'].append(num)
                    result['has_page_ref'] = True

        # Detect position hints
        if any(m in normalized for m in ('cuoi file', 'cuoi tai lieu', 'cuoi cung',
                                           'phan cuoi', 'doan cuoi', 'cuoi trang',
                                           'cuối file', 'cuối tài liệu', 'cuối cùng',
                                           'phần cuối', 'đoạn cuối', 'cuối trang')):
            result['position'] = 'end'
        elif any(m in normalized for m in ('dau file', 'dau tai lieu', 'phan dau',
                                             'doan dau', 'dau trang', 'mo dau',
                                             'đầu file', 'đầu tài liệu', 'phần đầu')):
            result['position'] = 'start'

        return result

    def expand_and_combine(self, query: str, separator: str = ' ') -> str:
        """Expand query and combine into a single search string.
        
        Dung cho BM25 search - gop tat ca expanded queries thanh 1 string.
        """
        expanded = self.expand(query)
        if len(expanded) == 1:
            return query
        return separator.join(expanded[:self.max_expansions])
