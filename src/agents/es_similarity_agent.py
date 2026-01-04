import os
import glob
from pathlib import Path
from typing import List, Dict, Optional, Any

from difflib import SequenceMatcher, unified_diff

from src.utils.file_utils import read_jsonl_file

try:
    from elasticsearch import Elasticsearch
except Exception:
    Elasticsearch = None  # Optional dependency; fallback to local search


class ESSimilarityAgent:
    """Agent for searching similar test cases in Elasticsearch and diffing results.

    Fallbacks to local JSONL `es_docs` artifacts when ES is not configured.
    """

    def __init__(self,
                 es_host: Optional[str] = None,
                 es_index: Optional[str] = None,
                 es_api_key: Optional[str] = None,
                 es_username: Optional[str] = None,
                 es_password: Optional[str] = None,
                 default_docs_dir: Optional[str] = None,
                 project_name: Optional[str] = None):
        self.es_host = es_host or os.getenv("ES_HOST")
        self.es_index = es_index or os.getenv("ES_INDEX")
        self.es_api_key = es_api_key or os.getenv("ES_API_KEY")
        self.es_username = es_username or os.getenv("ES_USERNAME")
        self.es_password = es_password or os.getenv("ES_PASSWORD")
        self.project_name = project_name
        self.default_docs_dir = default_docs_dir or str(Path(__file__).parent.parent.parent / "outputs" / "testcases")

        self.client = None
        if self.es_host and Elasticsearch:
            try:
                if self.es_api_key:
                    self.client = Elasticsearch(hosts=[self.es_host], api_key=self.es_api_key)
                elif self.es_username and self.es_password:
                    self.client = Elasticsearch(hosts=[self.es_host], basic_auth=(self.es_username, self.es_password))
                else:
                    self.client = Elasticsearch(hosts=[self.es_host])
            except Exception:
                # If client construction fails, fallback will be used
                self.client = None

    # ---------------------- Public API ----------------------
    def search_similar(self,
                       query_text: Optional[str] = None,
                       case_id: Optional[str] = None,
                       top_k: int = 5) -> Dict[str, Any]:
        """Search similar cases by `query_text` or an existing `case_id`.

        Returns a dict with `query`, `results` (list of hits with scores), and `diffs` per result.
        """
        if not query_text and not case_id:
            raise ValueError("either query_text or case_id must be provided")

        if self.client and self.es_index:
            hits = self._search_es(query_text=query_text, case_id=case_id, top_k=top_k)
            base_doc = self._get_base_doc_es(case_id) if case_id else {"title": query_text or "", "steps": "", "expected_result": ""}
        else:
            docs = self._load_local_es_docs()
            base_doc = self._find_local_doc_by_id(docs, case_id) if case_id else {"title": query_text or "", "steps": "", "expected_result": ""}
            hits = self._search_local(docs, query_text=query_text, base_doc=base_doc, top_k=top_k)

        # Build diffs
        diffs = []
        for h in hits:
            diffs.append({
                "case_id": h.get("case_id"),
                "title_similarity": self._text_similarity(base_doc.get("title", ""), h.get("title", "")),
                "steps_similarity": self._text_similarity(base_doc.get("steps", ""), h.get("steps", "")),
                "expected_similarity": self._text_similarity(base_doc.get("expected_result", ""), h.get("expected_result", "")),
                "title_diff": self._diff_text(base_doc.get("title", ""), h.get("title", "")),
                "steps_diff": self._diff_text(base_doc.get("steps", ""), h.get("steps", "")),
                "expected_diff": self._diff_text(base_doc.get("expected_result", ""), h.get("expected_result", "")),
                "score": h.get("_score"),
                "title": h.get("title"),
            })

        return {
            "query": query_text or case_id,
            "results": hits,
            "diffs": diffs,
        }

    # ---------------------- ES helpers ----------------------
    def _search_es(self, query_text: Optional[str], case_id: Optional[str], top_k: int) -> List[Dict[str, Any]]:
        assert self.client is not None and self.es_index is not None

        if case_id:
            body = {
                "query": {
                    "more_like_this": {
                        "fields": ["title", "steps", "expected_result"],
                        "like": [{"_id": case_id}],
                        "min_term_freq": 1,
                        "min_doc_freq": 1,
                    }
                }
            }
        else:
            body = {
                "query": {
                    "multi_match": {
                        "query": query_text,
                        "fields": ["title^2", "steps", "expected_result"],
                        "type": "most_fields"
                    }
                }
            }

        res = self.client.search(index=self.es_index, body=body, size=top_k)
        hits = []
        for hit in res.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            src["_score"] = hit.get("_score")
            hits.append(src)
        return hits

    def _get_base_doc_es(self, case_id: str) -> Dict[str, Any]:
        try:
            doc = self.client.get(index=self.es_index, id=case_id)
            return doc.get("_source", {})
        except Exception:
            return {}

    # ---------------------- Local helpers ----------------------
    def _load_local_es_docs(self) -> List[Dict[str, Any]]:
        pattern = "*es_docs_*.jsonl"
        base_dir = Path(self.default_docs_dir)
        if self.project_name:
            pattern = f"{self.project_name}_es_docs_*.jsonl"
        files = sorted(glob.glob(str(base_dir / pattern)))
        if not files:
            raise FileNotFoundError(f"No local es_docs JSONL found under {base_dir} with pattern {pattern}")
        return read_jsonl_file(files[-1])

    def _find_local_doc_by_id(self, docs: List[Dict[str, Any]], case_id: Optional[str]) -> Dict[str, Any]:
        if not case_id:
            return {}
        for d in docs:
            if d.get("case_id") == case_id:
                return d
        return {}

    def _search_local(self,
                       docs: List[Dict[str, Any]],
                       query_text: Optional[str],
                       base_doc: Dict[str, Any],
                       top_k: int) -> List[Dict[str, Any]]:
        scored: List[Dict[str, Any]] = []
        for d in docs:
            title_sim = self._text_similarity((query_text or base_doc.get("title", "")), d.get("title", ""))
            steps_sim = self._text_similarity(base_doc.get("steps", ""), d.get("steps", ""))
            expected_sim = self._text_similarity(base_doc.get("expected_result", ""), d.get("expected_result", ""))
            score = (2 * title_sim + steps_sim + expected_sim) / 4.0
            dd = d.copy()
            dd["_score"] = round(score, 4)
            scored.append(dd)
        scored.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return scored[:top_k]

    # ---------------------- Text utils ----------------------
    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        return round(SequenceMatcher(None, a or "", b or "").ratio(), 4)

    @staticmethod
    def _diff_text(a: str, b: str) -> List[str]:
        a_lines = (a or "").splitlines()
        b_lines = (b or "").splitlines()
        return list(unified_diff(a_lines, b_lines, lineterm=""))
