"""
Case 4 - Benchmark khả năng mở rộng (Scalability) của FAISS Flat vs HNSW
=========================================================================
So sánh thời gian xây dựng index và độ trễ tìm kiếm trên dữ liệu giả lập
ở nhiều quy mô: N = 1000, 4000, 8000, 16000 sinh viên.

Dữ liệu đầu vào:
  - enroll_embeddings.npy  (16000, 512) — embedding đăng ký
  - real_embeddings.npy    (80000, 512) — embedding webcam thực tế
  - metadata.json          — thông tin nhãn

Không đo accuracy vì dữ liệu là synthetic (giả lập).
"""

import sys
import os
import json
import time
import logging
from pathlib import Path

import numpy as np
import faiss

# ---------------------------------------------------------------------------
# UTF-8 encoding cho Windows console
# ---------------------------------------------------------------------------
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Case4_Scalability")

# ---------------------------------------------------------------------------
# Đường dẫn dữ liệu
# ---------------------------------------------------------------------------
FAKE_ROOT = Path(
    r"C:\AI_event\DATA_FAKE-20260608T190448Z-3-001"
    r"\DATA_FAKE\dataset_fake\dataset_fake"
)
ENROLL_PATH = FAKE_ROOT / "enroll_embeddings.npy"
REAL_PATH = FAKE_ROOT / "real_embeddings.npy"
META_PATH = FAKE_ROOT / "metadata.json"

TRAINING_DIR = Path(__file__).resolve().parent
RESULT_PATH = TRAINING_DIR / "results" / "case4_scalability_results.json"

# ---------------------------------------------------------------------------
# Tham số thí nghiệm
# ---------------------------------------------------------------------------
SCALES = [1000, 4000, 8000, 16000]
NUM_QUERIES = 500
HNSW_M = 32
HNSW_EF_CONSTRUCTION = 200
HNSW_EF_SEARCH = 64
DIM = 512
RNG_SEED = 42


# ---------------------------------------------------------------------------
# Hàm tiện ích
# ---------------------------------------------------------------------------
def normalize_l2(x: np.ndarray) -> np.ndarray:
    """Chuẩn hoá L2 từng vector (dùng cho Inner Product search)."""
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)  # tránh chia cho 0
    return x / norms


def build_flat_index(gallery: np.ndarray) -> tuple:
    """Xây dựng FAISS IndexFlatIP và trả về (index, build_time_ms)."""
    t0 = time.perf_counter()
    index = faiss.IndexFlatIP(gallery.shape[1])
    index.add(gallery)
    build_ms = (time.perf_counter() - t0) * 1000
    return index, build_ms


def build_hnsw_index(gallery: np.ndarray) -> tuple:
    """Xây dựng FAISS IndexHNSWFlat và trả về (index, build_time_ms)."""
    t0 = time.perf_counter()
    index = faiss.IndexHNSWFlat(gallery.shape[1], HNSW_M)
    index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
    index.hnsw.efSearch = HNSW_EF_SEARCH
    index.add(gallery)
    build_ms = (time.perf_counter() - t0) * 1000
    return index, build_ms


def measure_search_latency(index, queries: np.ndarray, top_k: int = 1) -> float:
    """Đo độ trễ trung bình mỗi query (ms/query)."""
    t0 = time.perf_counter()
    index.search(queries, top_k)
    total_s = time.perf_counter() - t0
    return (total_s / len(queries)) * 1000


# ---------------------------------------------------------------------------
# Chương trình chính
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 80)
    logger.info("  CASE 4 — BENCHMARK KHẢ NĂNG MỞ RỘNG: FAISS FLAT vs HNSW")
    logger.info("=" * 80)

    # ------------------------------------------------------------------
    # 1. Kiểm tra và tải dữ liệu
    # ------------------------------------------------------------------
    for p, desc in [
        (ENROLL_PATH, "enroll_embeddings.npy"),
        (REAL_PATH, "real_embeddings.npy"),
        (META_PATH, "metadata.json"),
    ]:
        if not p.exists():
            logger.error(f"Không tìm thấy tệp {desc}: {p}")
            sys.exit(1)

    logger.info(f"Đang tải embedding đăng ký từ: {ENROLL_PATH}")
    enroll_raw = np.load(str(ENROLL_PATH), mmap_mode="r").astype(np.float32)
    logger.info(f"  → Shape: {enroll_raw.shape}")

    logger.info(f"Đang tải embedding webcam thực tế từ: {REAL_PATH}")
    real_raw = np.load(str(REAL_PATH), mmap_mode="r").astype(np.float32)
    logger.info(f"  → Shape: {real_raw.shape}")

    with open(META_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    logger.info(f"Đã tải metadata ({len(metadata) if isinstance(metadata, (list, dict)) else '?'} mục)")

    # Chuẩn hoá L2 toàn bộ
    logger.info("Đang chuẩn hoá L2 toàn bộ embedding...")
    enroll_norm = normalize_l2(enroll_raw[:max(SCALES)].copy())
    real_norm = normalize_l2(real_raw.copy())

    # Chọn 500 query ngẫu nhiên từ tập real
    rng = np.random.RandomState(RNG_SEED)
    query_ids = rng.choice(len(real_norm), size=min(NUM_QUERIES, len(real_norm)), replace=False)
    queries = real_norm[query_ids].copy()
    logger.info(f"Đã chọn {len(queries)} query ngẫu nhiên từ tập real (seed={RNG_SEED})")

    # ------------------------------------------------------------------
    # 2. Chạy benchmark ở từng quy mô
    # ------------------------------------------------------------------
    results = []

    for n in SCALES:
        logger.info("-" * 60)
        logger.info(f"▶ Quy mô N = {n:,} sinh viên")
        gallery = enroll_norm[:n]

        # --- FAISS Flat ---
        flat_index, flat_build_ms = build_flat_index(gallery)
        flat_latency = measure_search_latency(flat_index, queries)
        logger.info(
            f"  [FlatIP]  Build: {flat_build_ms:>10.2f} ms | "
            f"Search: {flat_latency:>8.4f} ms/query"
        )

        # --- HNSW ---
        hnsw_index, hnsw_build_ms = build_hnsw_index(gallery)
        hnsw_latency = measure_search_latency(hnsw_index, queries)
        logger.info(
            f"  [HNSW ]  Build: {hnsw_build_ms:>10.2f} ms | "
            f"Search: {hnsw_latency:>8.4f} ms/query"
        )

        speedup = flat_latency / hnsw_latency if hnsw_latency > 0 else float("inf")
        logger.info(f"  → HNSW nhanh hơn Flat: {speedup:.2f}x (search)")

        results.append(
            {
                "N": n,
                "flat_build_ms": round(flat_build_ms, 2),
                "flat_search_ms_per_query": round(flat_latency, 4),
                "hnsw_build_ms": round(hnsw_build_ms, 2),
                "hnsw_search_ms_per_query": round(hnsw_latency, 4),
                "hnsw_speedup_vs_flat": round(speedup, 2),
            }
        )

        # Giải phóng bộ nhớ
        del flat_index, hnsw_index

    # ------------------------------------------------------------------
    # 3. In bảng kết quả đẹp
    # ------------------------------------------------------------------
    print("\n")
    title = "BẢNG KẾT QUẢ BENCHMARK KHẢ NĂNG MỞ RỘNG — FAISS FLAT vs HNSW"
    print("╔" + "═" * 96 + "╗")
    print(f"║{title:^96}║")
    print("╠" + "═" * 96 + "╣")

    sub = f"  Queries: {NUM_QUERIES} | HNSW: M={HNSW_M}, efConstruction={HNSW_EF_CONSTRUCTION}, efSearch={HNSW_EF_SEARCH}"
    print(f"║{sub:<96}║")
    print("╠" + "═" * 12 + "╦" + "═" * 20 + "╦" + "═" * 20 + "╦" + "═" * 20 + "╦" + "═" * 20 + "╣")

    hdr = (
        f"║{'N (SV)':^12}║"
        f"{'Flat Build(ms)':^20}║"
        f"{'Flat Search(ms)':^20}║"
        f"{'HNSW Build(ms)':^20}║"
        f"{'HNSW Search(ms)':^20}║"
    )
    print(hdr)
    print("╠" + "═" * 12 + "╬" + "═" * 20 + "╬" + "═" * 20 + "╬" + "═" * 20 + "╬" + "═" * 20 + "╣")

    for r in results:
        row = (
            f"║{r['N']:>10,}  ║"
            f"{r['flat_build_ms']:>18.2f}  ║"
            f"{r['flat_search_ms_per_query']:>18.4f}  ║"
            f"{r['hnsw_build_ms']:>18.2f}  ║"
            f"{r['hnsw_search_ms_per_query']:>18.4f}  ║"
        )
        print(row)

    print("╚" + "═" * 12 + "╩" + "═" * 20 + "╩" + "═" * 20 + "╩" + "═" * 20 + "╩" + "═" * 20 + "╝")

    # Bảng speedup
    print()
    print("╔" + "═" * 56 + "╗")
    print(f"║{'TỈ LỆ SPEEDUP HNSW vs FLAT (Search Latency)':^56}║")
    print("╠" + "═" * 12 + "╦" + "═" * 20 + "╦" + "═" * 20 + "╣")
    print(f"║{'N (SV)':^12}║{'HNSW Speedup':^20}║{'Đánh giá':^20}║")
    print("╠" + "═" * 12 + "╬" + "═" * 20 + "╬" + "═" * 20 + "╣")

    for r in results:
        sp = r["hnsw_speedup_vs_flat"]
        if sp >= 5:
            verdict = "✅ Rất tốt"
        elif sp >= 2:
            verdict = "✅ Tốt"
        elif sp >= 1:
            verdict = "⚠️ Ngang bằng"
        else:
            verdict = "❌ Chậm hơn"
        print(f"║{r['N']:>10,}  ║{sp:>17.2f}x  ║{verdict:^20}║")

    print("╚" + "═" * 12 + "╩" + "═" * 20 + "╩" + "═" * 20 + "╝")

    # ------------------------------------------------------------------
    # 4. Phân tích xu hướng
    # ------------------------------------------------------------------
    print("\n")
    print("=" * 80)
    print("  PHÂN TÍCH KHẢ NĂNG MỞ RỘNG (SCALABILITY ANALYSIS)")
    print("=" * 80)

    # Tính tỉ lệ tăng latency khi N tăng
    flat_latencies = [r["flat_search_ms_per_query"] for r in results]
    hnsw_latencies = [r["hnsw_search_ms_per_query"] for r in results]
    scales = [r["N"] for r in results]

    print("\n📊 Xu hướng độ trễ tìm kiếm khi quy mô tăng:")
    print("-" * 60)
    for i in range(1, len(results)):
        n_ratio = scales[i] / scales[0]
        flat_ratio = flat_latencies[i] / flat_latencies[0] if flat_latencies[0] > 0 else 0
        hnsw_ratio = hnsw_latencies[i] / hnsw_latencies[0] if hnsw_latencies[0] > 0 else 0
        print(
            f"  N: {scales[0]:>5,} → {scales[i]:>6,} "
            f"(×{n_ratio:.0f})  |  "
            f"Flat: ×{flat_ratio:.2f}  |  "
            f"HNSW: ×{hnsw_ratio:.2f}"
        )

    # Tính hệ số tuyến tính (linear fit) cho Flat
    if len(scales) >= 2:
        flat_coef = np.polyfit(scales, flat_latencies, 1)
        hnsw_coef = np.polyfit(scales, hnsw_latencies, 1)

        print(f"\n📐 Hồi quy tuyến tính (Linear Regression):")
        print(f"  • FAISS Flat:  latency ≈ {flat_coef[0]:.6f} × N + {flat_coef[1]:.4f} ms")
        print(f"  • HNSW:        latency ≈ {hnsw_coef[0]:.6f} × N + {hnsw_coef[1]:.4f} ms")
        print(f"  • Hệ số góc Flat / HNSW = {abs(flat_coef[0] / hnsw_coef[0]):.1f}x"
              if abs(hnsw_coef[0]) > 1e-10
              else f"  • Hệ số góc HNSW ≈ 0 (gần như không đổi)")

    # Kết luận
    flat_growth = flat_latencies[-1] / flat_latencies[0] if flat_latencies[0] > 0 else 0
    hnsw_growth = hnsw_latencies[-1] / hnsw_latencies[0] if hnsw_latencies[0] > 0 else 0

    print(f"\n🔍 KẾT LUẬN:")
    print(f"  ┌─────────────────────────────────────────────────────────────────┐")
    print(f"  │ • FAISS Flat: Độ trễ tăng ×{flat_growth:.2f} khi N tăng "
          f"từ {scales[0]:,} → {scales[-1]:,}")
    print(f"  │   → Tăng tuyến tính (O(N)) — brute-force quét toàn bộ        │")
    print(f"  │                                                                │")
    print(f"  │ • HNSW:       Độ trễ tăng ×{hnsw_growth:.2f} khi N tăng "
          f"từ {scales[0]:,} → {scales[-1]:,}")
    print(f"  │   → Gần như không đổi (O(log N)) — đồ thị tìm kiếm xấp xỉ   │")
    print(f"  │                                                                │")

    final_speedup = results[-1]["hnsw_speedup_vs_flat"]
    print(f"  │ • Ở quy mô N={scales[-1]:,}: HNSW nhanh hơn {final_speedup:.1f}x "
          f"so với Flat          │")
    print(f"  │ • HNSW là lựa chọn tối ưu khi mở rộng hệ thống > 10k SV     │")
    print(f"  └─────────────────────────────────────────────────────────────────┘")

    # ------------------------------------------------------------------
    # 5. Lưu kết quả JSON
    # ------------------------------------------------------------------
    output = {
        "experiment": "Case 4 — Scalability Benchmark: FAISS Flat vs HNSW",
        "parameters": {
            "scales": SCALES,
            "num_queries": NUM_QUERIES,
            "hnsw_M": HNSW_M,
            "hnsw_efConstruction": HNSW_EF_CONSTRUCTION,
            "hnsw_efSearch": HNSW_EF_SEARCH,
            "dimension": DIM,
            "seed": RNG_SEED,
        },
        "results": results,
        "analysis": {
            "flat_latency_growth": f"×{flat_growth:.2f} (N: {scales[0]:,} → {scales[-1]:,})",
            "hnsw_latency_growth": f"×{hnsw_growth:.2f} (N: {scales[0]:,} → {scales[-1]:,})",
            "conclusion": (
                f"FAISS Flat tăng tuyến tính O(N), "
                f"HNSW gần như không đổi O(log N). "
                f"Ở N={scales[-1]:,}, HNSW nhanh hơn {final_speedup:.1f}x."
            ),
        },
    }

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    logger.info(f"Đã lưu kết quả benchmark tại: {RESULT_PATH}")

    logger.info("=" * 80)
    logger.info("  HOÀN TẤT BENCHMARK CASE 4 — KHẢ NĂNG MỞ RỘNG")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
