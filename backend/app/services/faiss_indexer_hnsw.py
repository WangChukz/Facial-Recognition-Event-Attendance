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
    """
    Lớp dữ liệu lưu trữ siêu dữ liệu (metadata) của một vector trong chỉ mục HNSW.
    
    Thuộc tính:
        faiss_id (int): ID số nguyên tự tăng trong cơ sở dữ liệu dùng để liên kết ngược.
        embedding_id (str): Mã UUID định danh duy nhất của bản ghi vector đặc trưng.
        user_id (str): Mã UUID của người dùng sở hữu khuôn mặt này.
    """
    faiss_id: int
    embedding_id: str
    user_id: str


class HNSWFaceIndex:
    """
    Bộ chỉ mục khuôn mặt sử dụng thuật toán HNSW (Hierarchical Navigable Small World) của thư viện FAISS.
    - Sử dụng độ đo khoảng cách tích vô hướng (METRIC_INNER_PRODUCT) trên các vector đã chuẩn hóa L2
      để tính toán trực tiếp độ tương đồng Cosine (Cosine Similarity).
      
    Sự khác biệt quan trọng so với FaissFaceIndex thông thường:
    - Sử dụng IndexHNSWFlat thay vì IndexIDMap (HNSW không hỗ trợ gắn ID tùy ý khi thêm vector trực tiếp).
    - HNSW yêu cầu chỉ số vector tự tăng liên tục (0, 1, 2, ...). Vì thế, hệ thống duy trì danh sách
      `position_to_meta` để tự ánh xạ: vị trí vật lý trong chỉ mục -> thông tin định danh thực tế.
    - HNSW mặc định KHÔNG hỗ trợ việc xóa vector đơn lẻ.
    - Đảm bảo an toàn đa luồng bằng cơ chế khóa threading.RLock().
    """

    def __init__(self, index_path: str, meta_path: str, dim: int = 512) -> None:
        """
        Khởi tạo bộ chỉ mục HNSW.

        Tham số:
            index_path (str): Đường dẫn lưu trữ file chỉ mục HNSW (.bin hoặc .index).
            meta_path (str): Đường dẫn lưu trữ file siêu dữ liệu JSON chứa ánh xạ vị trí sang ID người dùng.
            dim (int): Số chiều của vector khuôn mặt (mặc định là 512 chiều của mô hình ArcFace).
        """
        self.index_path = index_path
        self.meta_path = meta_path
        self.dim = dim
        self._lock = threading.RLock() # Khóa chống xung đột truy cập đa luồng
        self._index: faiss.IndexHNSWFlat | None = None
        # Danh sách ánh xạ: vị trí i trong mảng -> thông tin người dùng tương ứng
        self._position_to_meta: list[HNSWMetaRow] = []

    def _make_empty(self) -> faiss.IndexHNSWFlat:
        """
        Khởi tạo một đồ thị HNSW rỗng với các cấu hình tối ưu.
        
        Các cấu hình HNSW:
            - M = 32: Số lượng liên kết tối đa của mỗi node đồ thị tới các node lân cận trong quá trình dựng.
                     Màng lưới càng dày (M lớn) thì tìm kiếm càng chính xác nhưng tốn RAM hơn.
            - efConstruction = 200: Số lượng liên kết ứng viên được đánh giá trong quá trình xây dựng đồ thị.
                                  Giá trị càng cao độ chính xác càng tăng nhưng xây dựng chỉ mục chậm hơn.
            - efSearch = 64: Số lượng liên kết ứng viên được đánh giá trong quá trình tìm kiếm truy vấn.
                            Giá trị càng cao tìm kiếm càng chính xác, bù lại thời gian tìm kiếm tăng nhẹ.
        """
        index = faiss.IndexHNSWFlat(self.dim, 32)  # M=32, độ đo mặc định là METRIC_INNER_PRODUCT
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 64
        return index

    def _ensure_index(self) -> faiss.IndexHNSWFlat:
        """Đảm bảo đối tượng Index luôn tồn tại (khởi tạo rỗng nếu chưa có)."""
        if self._index is None:
            self._index = self._make_empty()
        return self._index

    def load(self) -> None:
        """Tải chỉ mục HNSW và siêu dữ liệu từ ổ đĩa lên bộ nhớ RAM."""
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            # 1. Đọc file chỉ mục HNSW từ đĩa
            if os.path.isfile(self.index_path) and os.path.getsize(self.index_path) > 0:
                self._index = faiss.read_index(self.index_path)
                if not isinstance(self._index, faiss.IndexHNSWFlat):
                    raise TypeError(f"Yêu cầu định dạng IndexHNSWFlat, nhận được {type(self._index)}")
                self.dim = int(self._index.d)
            else:
                self._index = self._make_empty()

            # 2. Đọc file JSON lưu trữ siêu dữ liệu ánh xạ vị trí
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
        """Ghi chỉ mục HNSW và siêu dữ liệu ánh xạ hiện tại từ RAM xuống ổ đĩa cứng."""
        with self._lock:
            os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
            # 1. Ghi tệp chỉ mục nhị phân FAISS
            if self._index is not None:
                faiss.write_index(self._index, self.index_path)

            # 2. Ghi tệp siêu dữ liệu ánh xạ dưới dạng JSON
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
        """Giải phóng toàn bộ chỉ mục và siêu dữ liệu ánh xạ khỏi bộ nhớ RAM."""
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
        Thêm một vector khuôn mặt mới vào đồ thị HNSW.
        Do HNSW gán nhãn vị trí tự tăng (0, 1, 2...), hàm này sẽ lưu thông tin ánh xạ tương ứng vào danh sách siêu dữ liệu.
        
        Tham số:
            embedding (np.ndarray): Vector đặc trưng khuôn mặt (512 chiều).
            faiss_id (int): Mã định danh số nguyên tự tăng của bản ghi trong cơ sở dữ liệu.
            embedding_uuid (uuid.UUID): UUID định danh duy nhất của đặc trưng khuôn mặt.
            user_id (uuid.UUID): UUID của sinh viên sở hữu khuôn mặt này.
        """
        # Chuẩn hóa vector đầu vào trước khi thêm
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        
        with self._lock:
            idx = self._ensure_index()
            if vec.shape[1] != self.dim:
                raise ValueError(f"Số chiều vector thêm vào {vec.shape[1]} không khớp cấu hình {self.dim}")
            
            # Vị trí lưu trữ trong HNSW chính bằng tổng số lượng phần tử hiện tại
            position = idx.ntotal
            idx.add(vec)
            
            # Lưu siêu dữ liệu ứng với vị trí vừa thêm
            self._position_to_meta.append(
                HNSWMetaRow(
                    faiss_id=faiss_id,
                    embedding_id=str(embedding_uuid),
                    user_id=str(user_id),
                )
            )

    def search(self, embedding: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Tìm kiếm Top-k khuôn mặt có khoảng cách gần nhất trong đồ thị HNSW.
        
        Tham số:
            embedding (np.ndarray): Vector đặc trưng khuôn mặt cần đối khớp.
            top_k (int): Số lượng kết quả gần nhất cần lấy ra (mặc định lấy 5 kết quả).
            
        Trả về:
            list[dict[str, Any]]: Danh sách kết quả tìm được, mỗi phần tử gồm:
                - faiss_id (int): ID số nguyên tự tăng của bản ghi.
                - similarity (float): Độ tương đồng Cosine (0.0 đến 1.0).
                - user_id (str): UUID người dùng.
                - embedding_id (str): UUID của đặc trưng khuôn mặt.
        """
        # Chuẩn hóa vector truy vấn
        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)
        
        with self._lock:
            idx = self._ensure_index()
            if idx.ntotal == 0:
                return []
            
            # Truy vấn tìm kiếm trên đồ thị HNSW nhị phân
            sims, positions = idx.search(vec, min(top_k, idx.ntotal))
        
        out: list[dict[str, Any]] = []
        for sim, pos in zip(sims[0], positions[0]):
            if int(pos) == -1: # Không tìm thấy kết quả phù hợp
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
        """Trả về tổng số lượng vector đặc trưng đang lưu trữ trong chỉ mục."""
        with self._lock:
            if self._index is None:
                return 0
            return int(self._index.ntotal)



# Note: HNSW does NOT support deletion of vectors.
# If vector deletion is needed, consider:
# 1. Marking vectors as deleted in metadata (soft-delete)
# 2. Periodically rebuilding index by excluding deleted vectors
# 3. Using a different index type (e.g., IndexIVFFlat) that supports deletion
