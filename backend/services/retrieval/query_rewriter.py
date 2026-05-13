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
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryRewriter:
    """LLM-based query rewriting for better retrieval recall."""
    
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
        
    def expand(self, query: str) -> List[str]:
        """Expand a user query into multiple clearer versions.
        
        Args:
            query: Raw user query
            
        Returns:
            List of expanded query strings (includes original)
        """
        if not self.enabled or not self.llama:
            return [query]
        
        # Skip expansion for very short or very long queries
        q_words = query.split()
        if len(q_words) > 30 or len(query) < 5:
            return [query]
        
        # Skip if query already has specific keywords
        skip_keywords = ['ma ', 'so ', 'id ', 'code ']
        if any(query.lower().startswith(k) for k in skip_keywords):
            return [query]
        
        try:
            prompt = self.EXPANSION_PROMPT.format(query=query)
            response = self.llama.complete(
                prompt=prompt,
                max_tokens=self.MAX_EXPANSION_TOKENS,
                temperature=self.EXPANSION_TEMPERATURE,
            )
            
            if not response:
                return [query]
            
            # Parse expanded queries from response
            expansions = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and len(line) > 4:
                    # Remove numbering if present
                    if line[0].isdigit():
                        line = line.split('. ', 1)[-1] if '. ' in line else line
                        line = line.split(') ', 1)[-1] if ') ' in line else line
                    expansions.append(line)
            
            if not expansions:
                return [query]
            
            # Limit and add original
            expansions = expansions[:self.max_expansions]
            if query not in expansions:
                expansions = [query] + expansions
            
            logger.debug(
                f"Query expanded: '{query[:50]}' -> {len(expansions)} versions"
            )
            return expansions[:self.max_expansions + 1]
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}, using original")
            return [query]
    
    def expand_and_combine(self, query: str, separator: str = ' ') -> str:
        """Expand query and combine into a single search string.
        
        Dung cho BM25 search - gop tat ca expanded queries thanh 1 string.
        """
        expanded = self.expand(query)
        if len(expanded) == 1:
            return query
        return separator.join(expanded[:self.max_expansions])
