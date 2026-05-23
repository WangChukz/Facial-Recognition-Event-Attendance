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
class HNSWMetaRow:
    faiss_id: int
    embedding_id: str
    user_id: str


class HNSWFaceIndex:
    """
    HNSW-based face index with L2-normalized embeddings + IndexHNSWFlat (METRIC_INNER_PRODUCT) 
    => cosine similarity via inner product.
    
    Key differences from FaissFaceIndex:
    - Uses IndexHNSWFlat (HNSW does NOT support IndexIDMap2)
    - HNSW add() only accepts sequential indices (0, 1, 2, ...), not custom IDs
    - Maintains position_to_meta[] list to map vector position → (faiss_id, user_id, embedding_id)
    - HNSW does NOT support deleting vectors
    - Thread-safe with threading.RLock()
    
    Params: M=32, efConstruction=200, efSearch=64
    """

    def __init__(self, index_path: str, meta_path: str, dim: int = 512) -> None:
        self.index_path = index_path
        self.meta_path = meta_path
        self.dim = dim
        self._lock = threading.RLock()
        self._index: faiss.IndexHNSWFlat | None = None
        # position_to_meta[i] = FaissMetaRow corresponding to vector at position i in HNSW
        self._position_to_meta: list[HNSWMetaRow] = []

    def _make_empty(self) -> faiss.IndexHNSWFlat:
        """Create a new empty HNSW index with inner product metric."""
        index = faiss.IndexHNSWFlat(self.dim, 32)  # M=32
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 64
        return index

    def _ensure_index(self) -> faiss.IndexHNSWFlat:
        if self._index is None:
            self._index = self._make_empty()
        return self._index

    def load(self) -> None:
        """Load index and metadata from disk, rebuild position_to_meta mapping."""
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            if os.path.isfile(self.index_path) and os.path.getsize(self.index_path) > 0:
                self._index = faiss.read_index(self.index_path)
                # Verify it's an HNSW index
                if not isinstance(self._index, faiss.IndexHNSWFlat):
                    raise TypeError(f"Expected IndexHNSWFlat, got {type(self._index)}")
                self.dim = int(self._index.d)
            else:
                self._index = self._make_empty()

            # Load metadata from JSON file
            if os.path.isfile(self.meta_path):
                with open(self.meta_path, encoding="utf-8") as f:
                    raw = json.load(f)
                self._position_to_meta = []
                for item in raw.get("position_to_meta", []):
                    self._position_to_meta.append(
                        HNSWMetaRow(
                            faiss_id=item["faiss_id"],
                            embedding_id=item["embedding_id"],
                            user_id=item["user_id"],
                        )
                    )
            else:
                self._position_to_meta = []

    def persist(self) -> None:
        """Save index and metadata to disk."""
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            if self._index is not None:
                faiss.write_index(self._index, self.index_path)

            # Serialize position_to_meta list
            position_list = [
                {
                    "faiss_id": meta.faiss_id,
                    "embedding_id": meta.embedding_id,
                    "user_id": meta.user_id,
                }
                for meta in self._position_to_meta
            ]
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({"position_to_meta": position_list}, f, indent=2)

    def clear_memory(self) -> None:
        """Clear index and metadata from memory."""
        with self._lock:
            self._index = self._make_empty()
            self._position_to_meta = []

    def add_with_id(
        self, 
        embedding: np.ndarray, 
        faiss_id: int, 
        embedding_uuid: uuid.UUID, 
        user_id: uuid.UUID
    ) -> None:
        """
        Add embedding to HNSW index.
        
        HNSW automatically assigns sequential indices (0, 1, 2, ...).
        We track custom faiss_id via position_to_meta[position].
        
        Args:
            embedding: face embedding vector
            faiss_id: custom ID for this embedding
            embedding_uuid: UUID of the embedding record
            user_id: UUID of the user
        """
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        
        with self._lock:
            idx = self._ensure_index()
            if vec.shape[1] != self.dim:
                raise ValueError(f"Embedding dim {vec.shape[1]} != index dim {self.dim}")
            
            # HNSW add() returns the assigned position (sequential)
            # Current position = current ntotal
            position = idx.ntotal
            idx.add(vec)
            
            # Store metadata at this position
            self._position_to_meta.append(
                HNSWMetaRow(
                    faiss_id=faiss_id,
                    embedding_id=str(embedding_uuid),
                    user_id=str(user_id),
                )
            )

    def search(self, embedding: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search for top-k nearest neighbors using cosine similarity (via inner product on normalized vectors).
        
        Returns:
            List of dicts with keys: faiss_id, similarity, user_id, embedding_id
        """
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        
        with self._lock:
            idx = self._ensure_index()
            if idx.ntotal == 0:
                return []
            
            sims, positions = idx.search(vec, min(top_k, idx.ntotal))
        
        out: list[dict[str, Any]] = []
        for sim, pos in zip(sims[0], positions[0]):
            if int(pos) == -1:
                continue
            
            pos_idx = int(pos)
            if pos_idx < 0 or pos_idx >= len(self._position_to_meta):
                continue
            
            meta = self._position_to_meta[pos_idx]
            if not meta:
                continue
            
            out.append(
                {
                    "faiss_id": meta.faiss_id,
                    "similarity": float(sim),
                    "user_id": meta.user_id,
                    "embedding_id": meta.embedding_id,
                }
            )
        return out

    @property
    def total(self) -> int:
        """Return total number of vectors in index."""
        with self._lock:
            if self._index is None:
                return 0
            return int(self._index.ntotal)


# Note: HNSW does NOT support deletion of vectors.
# If vector deletion is needed, consider:
# 1. Marking vectors as deleted in metadata (soft-delete)
# 2. Periodically rebuilding index by excluding deleted vectors
# 3. Using a different index type (e.g., IndexIVFFlat) that supports deletion
