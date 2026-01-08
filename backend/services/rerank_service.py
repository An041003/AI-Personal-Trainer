from __future__ import annotations

from typing import Any, Dict, List, Optional
import os


class RerankService:
    """
    Service để rerank các candidates dựa trên query.
    Hỗ trợ nhiều provider: cohere, jina, hoặc có thể mở rộng thêm.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        top_n: int = 20,
    ) -> None:
        self.provider = (provider or os.getenv("RERANK_PROVIDER", "cohere")).lower()
        self.api_key = api_key or os.getenv("COHERE_API_KEY") or os.getenv("RERANK_API_KEY")
        self.model = model or os.getenv("RERANK_MODEL", "rerank-english-v3.0")
        self.top_n = top_n

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates dựa trên query.

        Args:
            query: Query string để rerank
            candidates: List các candidates với format:
                {
                    "id": int,
                    "title": str,
                    "muscle_groups": List[str],
                    "score": float,
                    ...
                }
            top_n: Số lượng kết quả trả về sau rerank (mặc định dùng self.top_n)

        Returns:
            List candidates đã được rerank và sắp xếp theo relevance score
        """
        if not query or not candidates:
            return candidates

        top_n = top_n or self.top_n

        if self.provider == "cohere":
            return self._cohere_rerank(query, candidates, top_n)
        elif self.provider == "jina":
            return self._jina_rerank(query, candidates, top_n)
        elif self.provider == "none" or not self.api_key:
            # Fallback: không rerank, chỉ sort theo score hiện tại
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]
        else:
            raise ValueError(f"Unsupported RERANK_PROVIDER={self.provider}")

    def _cohere_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """Rerank sử dụng Cohere API"""
        if not self.api_key:
            print("[RERANK] Cohere API key không có, skip rerank")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]

        try:
            import cohere

            client = cohere.Client(api_key=self.api_key)

            # Chuẩn bị documents từ candidates
            documents = []
            for c in candidates:
                title = c.get("title", "")
                muscles = c.get("muscle_groups", [])
                muscle_str = ", ".join(map(str, muscles)) if muscles else ""
                doc_text = f"{title}"
                if muscle_str:
                    doc_text += f" - {muscle_str}"
                documents.append(doc_text)

            # Gọi Cohere rerank API
            response = client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=min(top_n, len(candidates)),
            )

            # Map lại kết quả với candidates gốc
            reranked = []
            for result in response.results:
                idx = result.index
                if 0 <= idx < len(candidates):
                    candidate = candidates[idx].copy()
                    # Cập nhật score với relevance score từ Cohere
                    candidate["rerank_score"] = float(result.relevance_score)
                    candidate["original_score"] = candidate.get("score", 0.0)
                    candidate["score"] = float(result.relevance_score)
                    reranked.append(candidate)

            print(f"[RERANK] Cohere rerank: {len(candidates)} -> {len(reranked)} candidates")
            return reranked

        except ImportError:
            print("[RERANK] Cohere package chưa được cài đặt, skip rerank")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]
        except Exception as e:
            print(f"[RERANK] Cohere rerank error: {e}, fallback to original order")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]

    def _jina_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        """Rerank sử dụng Jina API"""
        if not self.api_key:
            print("[RERANK] Jina API key không có, skip rerank")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]

        try:
            import requests

            # Chuẩn bị documents
            documents = []
            for c in candidates:
                title = c.get("title", "")
                muscles = c.get("muscle_groups", [])
                muscle_str = ", ".join(map(str, muscles)) if muscles else ""
                doc_text = f"{title}"
                if muscle_str:
                    doc_text += f" - {muscle_str}"
                documents.append(doc_text)

            # Gọi Jina rerank API
            url = "https://api.jina.ai/v1/rerank"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(candidates)),
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Map lại kết quả
            reranked = []
            if "results" in data:
                for result in data["results"]:
                    idx = result.get("index", -1)
                    if 0 <= idx < len(candidates):
                        candidate = candidates[idx].copy()
                        candidate["rerank_score"] = float(result.get("relevance_score", 0.0))
                        candidate["original_score"] = candidate.get("score", 0.0)
                        candidate["score"] = float(result.get("relevance_score", 0.0))
                        reranked.append(candidate)

            print(f"[RERANK] Jina rerank: {len(candidates)} -> {len(reranked)} candidates")
            return reranked

        except ImportError:
            print("[RERANK] requests package chưa được cài đặt, skip rerank")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]
        except Exception as e:
            print(f"[RERANK] Jina rerank error: {e}, fallback to original order")
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]


def get_rerank_service() -> RerankService:
    """Factory function để tạo RerankService instance"""
    return RerankService()

