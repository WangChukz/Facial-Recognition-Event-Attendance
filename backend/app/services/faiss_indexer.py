from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any

import faiss
import numpy as np


@dataclass
class FaissMetaRow:
    faiss_id: int
    embedding_id: str
    user_id: str


class FaissFaceIndex:
    """
    L2-normalized embeddings + IndexFlatIP (+ IDMap) => inner-product similarity score.
    """

    def __init__(self, index_path: str, meta_path: str, dim: int = 512) -> None:
        self.index_path = index_path
        self.meta_path = meta_path
        self.dim = dim
        self._lock = threading.RLock()
        self._base: faiss.Index | None = None
        self._index: faiss.IndexIDMap2 | None = None
        self._meta: dict[int, FaissMetaRow] = {}

    def _make_empty(self) -> faiss.IndexIDMap2:
        base = faiss.IndexFlatIP(self.dim)
        return faiss.IndexIDMap2(base)

    def _ensure_index(self) -> faiss.IndexIDMap2:
        if self._index is None:
            self._index = self._make_empty()
        return self._index

    def load(self) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            if os.path.isfile(self.index_path) and os.path.getsize(self.index_path) > 0:
                self._index = faiss.read_index(self.index_path)
                self.dim = int(faiss.downcast_index(self._index.index).d)
            else:
                self._index = self._make_empty()
            if os.path.isfile(self.meta_path):
                with open(self.meta_path, encoding="utf-8") as f:
                    raw = json.load(f)
                self._meta = {}
                for k, v in raw.get("rows", {}).items():
                    fid = int(k)
                    self._meta[fid] = FaissMetaRow(
                        faiss_id=fid,
                        embedding_id=v["embedding_id"],
                        user_id=v["user_id"],
                    )
            else:
                self._meta = {}

    def persist(self) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            if self._index is not None:
                faiss.write_index(self._index, self.index_path)
            rows = {str(k): {"embedding_id": v.embedding_id, "user_id": v.user_id} for k, v in self._meta.items()}
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({"rows": rows}, f, indent=2)

    def clear_memory(self) -> None:
        with self._lock:
            self._index = self._make_empty()
            self._meta = {}

    def add_with_id(self, embedding: np.ndarray, faiss_id: int, embedding_uuid: uuid.UUID, user_id: uuid.UUID) -> None:
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        ids = np.array([faiss_id], dtype=np.int64)
        with self._lock:
            idx = self._ensure_index()
            if vec.shape[1] != self.dim:
                raise ValueError(f"Embedding dim {vec.shape[1]} != index dim {self.dim}")
            idx.add_with_ids(vec, ids)
            self._meta[faiss_id] = FaissMetaRow(
                faiss_id=faiss_id,
                embedding_id=str(embedding_uuid),
                user_id=str(user_id),
            )

    def search(self, embedding: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        with self._lock:
            idx = self._ensure_index()
            if idx.ntotal == 0:
                return []
            sims, ids = idx.search(vec, min(top_k, idx.ntotal))
        out: list[dict[str, Any]] = []
        for sim, fid in zip(sims[0], ids[0]):
            if int(fid) == -1:
                continue
            meta = self._meta.get(int(fid))
            if not meta:
                continue
            out.append(
                {
                    "faiss_id": int(fid),
                    "similarity": float(sim),
                    "user_id": meta.user_id,
                    "embedding_id": meta.embedding_id,
                }
            )
        return out

    @property
    def total(self) -> int:
        with self._lock:
            if self._index is None:
                return 0
            return int(self._index.ntotal)
