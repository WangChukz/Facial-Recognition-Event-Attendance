"""
Case 5 – Progressive Gallery Enrichment Evaluation
====================================================
Đánh giá hiệu quả của chiến lược làm giàu gallery dần dần (progressive
gallery enrichment) cho hệ thống nhận diện khuôn mặt.

3 kịch bản con (chỉ dùng FAISS Flat, KHÔNG dùng SVM / Cosine):
  Sub-case 1: Baseline – gallery chỉ có 1 ảnh enroll / sinh viên
  Sub-case 2: Sau enrichment – gallery += embedding real 1-3
  Sub-case 3: Unknown rejection sau enrichment (random impostor probes)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import cv2
import faiss
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Cấu hình đường dẫn
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Case5_GalleryEnrichment")

# ---------------------------------------------------------------------------
# Import pipeline
# ---------------------------------------------------------------------------
from app.ai_core.pipeline import FacePipeline
from app.ai_core.utils.augmentation import crop_face_with_margin

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------
DATASET_ROOT = Path(r"C:/AI_event/dataset/dataset")
ENROLL_DIR = DATASET_ROOT / "enroll"
REAL_DIR = DATASET_ROOT / "real"
META_PATH = DATASET_ROOT / "metadata.xlsx"
OUTPUT_JSON = Path(current_dir) / "results" / "case5_enrichment_results.json"

RECOGNITION_THRESHOLD = 0.45
UNKNOWN_THRESHOLD = 0.35
ENRICHMENT_THRESHOLD = 0.75

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

# Ánh xạ đặc biệt folder → metadata
SPECIAL_NAME_MAP: dict[str, str] = {
    "phamtrungkien": "nguyentrungkien",
}


# ============================================================================
# Tiện ích
# ============================================================================
def remove_vietnamese_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt, loại khoảng trắng, trả về chữ thường."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", "")
    return text


def normalize_l2(arr: np.ndarray) -> np.ndarray:
    """Chuẩn hoá L2 in-place và trả về mảng float32."""
    arr = np.asarray(arr, dtype=np.float32).copy()
    faiss.normalize_L2(arr)
    return arr


def fmt_pct(val: float | None) -> str:
    return "N/A" if val is None else f"{val:.2f}%"


def fmt_sim(val: float | None) -> str:
    return "N/A" if val is None else f"{val:.4f}"


# ============================================================================
# Đọc metadata & xây class_map
# ============================================================================
def load_metadata() -> dict[str, dict[str, str]]:
    """Trả về dict: clean_name_lower → {student_id, name, class}."""
    if not META_PATH.exists():
        logger.error(f"Không tìm thấy file metadata: {META_PATH}")
        sys.exit(1)

    df = pd.read_excel(META_PATH)
    logger.info(f"Đã nạp metadata: {META_PATH} ({len(df)} sinh viên)")

    meta_map: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        name = str(row.get("Họ và tên", "")).strip()
        clean = remove_vietnamese_diacritics(name).lower()
        meta_map[clean] = {
            "student_id": str(row.get("Mã sinh viên", "")).strip(),
            "name": name,
            "class": str(row.get("Lớp", "")).strip(),
        }
    return meta_map


def build_class_map(meta_map: dict[str, dict[str, str]]) -> dict[str, int]:
    """Ánh xạ clean_name → class_id (0-indexed, sắp xếp ABC)."""
    keys = sorted(meta_map.keys())
    return {k: idx for idx, k in enumerate(keys)}


# ============================================================================
# Trích xuất embedding
# ============================================================================
def extract_embedding(
    pipeline: FacePipeline,
    img: np.ndarray,
) -> np.ndarray | None:
    """Trích embedding 512-dim từ ảnh, trả về None nếu không hợp lệ."""
    faces = pipeline.process_frame_sync(img, use_adaptive_clahe=True)
    v = pipeline.validate_single_face(faces, min_det=0.50, min_face_size=60)
    if v["ok"]:
        return v["face"]["embedding"]
    return None


def load_image(path: str | Path) -> np.ndarray | None:
    """Đọc ảnh hỗ trợ Unicode path (np.fromfile + imdecode)."""
    arr = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


# ============================================================================
# Trích xuất dữ liệu enroll & real
# ============================================================================
def extract_enroll_embeddings(
    pipeline: FacePipeline,
    class_map: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Trả về (embeddings, labels, names) từ thư mục enroll."""
    embs: list[np.ndarray] = []
    labels: list[int] = []
    names: list[str] = []

    enroll_files = [
        f for f in os.listdir(ENROLL_DIR)
        if f.lower().endswith(VALID_EXTENSIONS)
    ]
    logger.info(f"Tìm thấy {len(enroll_files)} file enroll")

    for ef in sorted(enroll_files):
        clean = re.sub(
            r"_enroll\.(jpg|png|jpeg|webp|bmp|JPG)", "", ef, flags=re.IGNORECASE
        ).lower()

        if clean not in class_map:
            logger.warning(f"Enroll '{ef}' (clean='{clean}') không khớp metadata → bỏ qua")
            continue

        img = load_image(ENROLL_DIR / ef)
        if img is None:
            logger.warning(f"Không thể đọc ảnh: {ef}")
            continue

        emb = extract_embedding(pipeline, img)
        if emb is not None:
            embs.append(emb)
            labels.append(class_map[clean])
            names.append(clean)
            logger.info(f"  ✓ Enroll: {clean} (class {class_map[clean]})")
        else:
            logger.warning(f"  ✗ Enroll: {ef} – không phát hiện khuôn mặt hợp lệ")

    X = np.array(embs, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)
    logger.info(f"Tổng embedding enroll: {len(embs)}")
    return X, y, names


def extract_real_embeddings(
    pipeline: FacePipeline,
    class_map: dict[str, int],
) -> dict[str, list[np.ndarray]]:
    """Trả về dict: clean_name → [embedding_1, embedding_2, ...] từ thư mục real."""
    result: dict[str, list[np.ndarray]] = {}

    real_folders = sorted([
        f for f in os.listdir(REAL_DIR)
        if os.path.isdir(os.path.join(REAL_DIR, f)) and not f.startswith(".")
    ])
    logger.info(f"Tìm thấy {len(real_folders)} thư mục real")

    for folder in real_folders:
        clean = folder.replace("_real", "").lower()
        clean = SPECIAL_NAME_MAP.get(clean, clean)

        if clean not in class_map:
            logger.warning(f"Folder '{folder}' (clean='{clean}') không khớp metadata → bỏ qua")
            continue

        folder_path = REAL_DIR / folder
        img_files = sorted([
            f for f in os.listdir(folder_path)
            if f.lower().endswith(VALID_EXTENSIONS)
        ])

        embs: list[np.ndarray] = []
        for img_file in img_files:
            img = load_image(folder_path / img_file)
            if img is None:
                continue
            emb = extract_embedding(pipeline, img)
            if emb is not None:
                embs.append(emb)

        if embs:
            result[clean] = embs
            logger.info(f"  ✓ Real: {clean} → {len(embs)} embedding(s) (từ {len(img_files)} ảnh)")
        else:
            logger.warning(f"  ✗ Real: {clean} → 0 embedding hợp lệ")

    return result


# ============================================================================
# FAISS matching logic
# ============================================================================
def build_faiss_index(gallery: np.ndarray) -> faiss.IndexFlatIP:
    """Xây dựng FAISS IndexFlatIP từ gallery đã chuẩn hoá L2."""
    index = faiss.IndexFlatIP(512)
    index.add(gallery)
    return index


def classify_with_faiss(
    index: faiss.IndexFlatIP,
    gallery_labels: np.ndarray,
    query: np.ndarray,
    recognition_threshold: float = RECOGNITION_THRESHOLD,
    unknown_threshold: float = UNKNOWN_THRESHOLD,
) -> tuple[int, float, str]:
    """
    Phân loại 1 query embedding.
    Trả về (predicted_label, similarity, decision).
    decision ∈ {'known', 'unknown', 'uncertain'}
    """
    q = query.reshape(1, -1).astype(np.float32)
    sims, ids = index.search(q, 1)
    sim = float(sims[0, 0])
    idx = int(ids[0, 0])

    if sim >= recognition_threshold:
        return int(gallery_labels[idx]), sim, "known"
    elif sim < unknown_threshold:
        return -1, sim, "unknown"
    else:
        return int(gallery_labels[idx]), sim, "uncertain"


# ============================================================================
# Sub-case 1: Baseline (chỉ enroll)
# ============================================================================
def run_subcase1_baseline(
    enroll_emb: np.ndarray,
    enroll_labels: np.ndarray,
    test_embs: list[np.ndarray],
    test_labels: list[int],
) -> dict[str, Any]:
    """Gallery = chỉ enroll. Test = real 4-5."""
    logger.info("=" * 70)
    logger.info("SUB-CASE 1: Baseline – Gallery chỉ có ảnh enroll")
    logger.info("=" * 70)

    gallery = normalize_l2(enroll_emb)
    index = build_faiss_index(gallery)

    correct = 0
    total = len(test_labels)
    similarities: list[float] = []
    uncertain_count = 0

    t0 = time.perf_counter()
    for emb, true_label in zip(test_embs, test_labels):
        q = normalize_l2(emb.reshape(1, -1))
        pred_label, sim, decision = classify_with_faiss(index, enroll_labels, q)
        similarities.append(sim)

        if decision == "uncertain":
            uncertain_count += 1

        if decision == "known" and pred_label == true_label:
            correct += 1
        elif decision == "uncertain" and pred_label == true_label:
            # Vẫn tính đúng nếu nhãn khớp (nhưng confidence thấp)
            correct += 1

    latency_ms = (time.perf_counter() - t0) / max(total, 1) * 1000
    accuracy = correct / max(total, 1) * 100
    avg_sim = float(np.mean(similarities)) if similarities else 0.0

    result = {
        "subcase": "1_baseline",
        "description": "Gallery = chỉ enroll (1 ảnh/SV)",
        "gallery_size": int(len(enroll_labels)),
        "test_samples": total,
        "accuracy": round(accuracy, 2),
        "avg_similarity": round(avg_sim, 4),
        "uncertain_count": uncertain_count,
        "latency_ms": round(latency_ms, 4),
    }

    logger.info(f"  Gallery size     : {result['gallery_size']}")
    logger.info(f"  Test samples     : {result['test_samples']}")
    logger.info(f"  Accuracy         : {fmt_pct(result['accuracy'])}")
    logger.info(f"  Avg Similarity   : {fmt_sim(result['avg_similarity'])}")
    logger.info(f"  Uncertain count  : {result['uncertain_count']}")
    logger.info(f"  Latency/query    : {result['latency_ms']:.4f} ms")

    return result


# ============================================================================
# Sub-case 2: Sau enrichment
# ============================================================================
def run_subcase2_enriched(
    enroll_emb: np.ndarray,
    enroll_labels: np.ndarray,
    enrich_embs: list[np.ndarray],
    enrich_labels: list[int],
    test_embs: list[np.ndarray],
    test_labels: list[int],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """Gallery = enroll + enrichment (real 1-3 với threshold 0.75)."""
    logger.info("=" * 70)
    logger.info("SUB-CASE 2: Sau Enrichment – Gallery += real 1-3")
    logger.info("=" * 70)

    # Bước 1: Xây gallery baseline (enroll)
    gallery_base = normalize_l2(enroll_emb)
    index_base = build_faiss_index(gallery_base)

    # Bước 2: Mô phỏng enrichment – chỉ thêm nếu similarity >= threshold
    enriched_embs: list[np.ndarray] = []
    enriched_labels: list[int] = []
    accepted = 0
    rejected = 0

    for emb, label in zip(enrich_embs, enrich_labels):
        q = normalize_l2(emb.reshape(1, -1))
        sims, ids = index_base.search(q, 1)
        sim = float(sims[0, 0])

        if sim >= ENRICHMENT_THRESHOLD:
            enriched_embs.append(emb)
            enriched_labels.append(label)
            accepted += 1
        else:
            rejected += 1

    logger.info(f"  Enrichment: accepted={accepted}, rejected={rejected} "
                f"(threshold={ENRICHMENT_THRESHOLD})")

    # Bước 3: Ghép gallery
    if enriched_embs:
        enriched_arr = normalize_l2(np.array(enriched_embs, dtype=np.float32))
        gallery_full = np.vstack([gallery_base, enriched_arr])
        labels_full = np.concatenate([
            enroll_labels,
            np.array(enriched_labels, dtype=np.int32),
        ])
    else:
        gallery_full = gallery_base.copy()
        labels_full = enroll_labels.copy()

    index_full = build_faiss_index(gallery_full)

    # Bước 4: Đánh giá trên cùng tập test
    correct = 0
    total = len(test_labels)
    similarities: list[float] = []
    uncertain_count = 0

    t0 = time.perf_counter()
    for emb, true_label in zip(test_embs, test_labels):
        q = normalize_l2(emb.reshape(1, -1))
        pred_label, sim, decision = classify_with_faiss(index_full, labels_full, q)
        similarities.append(sim)

        if decision == "uncertain":
            uncertain_count += 1

        if decision == "known" and pred_label == true_label:
            correct += 1
        elif decision == "uncertain" and pred_label == true_label:
            correct += 1

    latency_ms = (time.perf_counter() - t0) / max(total, 1) * 1000
    accuracy = correct / max(total, 1) * 100
    avg_sim = float(np.mean(similarities)) if similarities else 0.0

    result = {
        "subcase": "2_enriched",
        "description": f"Gallery = enroll + enrichment (threshold={ENRICHMENT_THRESHOLD})",
        "gallery_size": int(len(labels_full)),
        "enriched_added": accepted,
        "enriched_rejected": rejected,
        "test_samples": total,
        "accuracy": round(accuracy, 2),
        "avg_similarity": round(avg_sim, 4),
        "uncertain_count": uncertain_count,
        "latency_ms": round(latency_ms, 4),
    }

    logger.info(f"  Gallery size     : {result['gallery_size']} (enroll={len(enroll_labels)} + enriched={accepted})")
    logger.info(f"  Test samples     : {result['test_samples']}")
    logger.info(f"  Accuracy         : {fmt_pct(result['accuracy'])}")
    logger.info(f"  Avg Similarity   : {fmt_sim(result['avg_similarity'])}")
    logger.info(f"  Uncertain count  : {result['uncertain_count']}")
    logger.info(f"  Latency/query    : {result['latency_ms']:.4f} ms")

    return result, gallery_full, labels_full


# ============================================================================
# Sub-case 3: Unknown Rejection sau enrichment
# ============================================================================
def run_subcase3_unknown_rejection(
    gallery: np.ndarray,
    gallery_labels: np.ndarray,
) -> dict[str, Any]:
    """Test unknown rejection bằng random impostor probes."""
    logger.info("=" * 70)
    logger.info("SUB-CASE 3: Unknown Rejection sau Enrichment")
    logger.info("=" * 70)

    # Sinh 100 random impostor embeddings (unit-norm 512-dim)
    rng = np.random.default_rng(42)
    n_impostors = 100
    raw = rng.standard_normal((n_impostors, 512)).astype(np.float32)
    impostors = normalize_l2(raw)

    logger.info(f"  Đã sinh {n_impostors} impostor vectors ngẫu nhiên (unit-norm 512-dim)")

    index = build_faiss_index(gallery)

    correctly_rejected = 0
    false_accepts = 0
    uncertain_count = 0
    similarities: list[float] = []

    t0 = time.perf_counter()
    for i in range(n_impostors):
        q = impostors[i].reshape(1, -1)
        _, sim, decision = classify_with_faiss(index, gallery_labels, q)
        similarities.append(sim)

        if decision == "unknown":
            correctly_rejected += 1
        elif decision == "known":
            false_accepts += 1
        else:
            uncertain_count += 1

    latency_ms = (time.perf_counter() - t0) / n_impostors * 1000
    rejection_rate = correctly_rejected / n_impostors * 100
    avg_sim = float(np.mean(similarities))

    result = {
        "subcase": "3_unknown_rejection",
        "description": "Unknown Rejection sau enrichment (100 random impostor probes)",
        "gallery_size": int(len(gallery_labels)),
        "impostor_count": n_impostors,
        "correctly_rejected": correctly_rejected,
        "false_accepts": false_accepts,
        "uncertain_count": uncertain_count,
        "rejection_rate": round(rejection_rate, 2),
        "avg_similarity": round(avg_sim, 4),
        "latency_ms": round(latency_ms, 4),
    }

    logger.info(f"  Gallery size        : {result['gallery_size']}")
    logger.info(f"  Impostor probes     : {n_impostors}")
    logger.info(f"  Correctly rejected  : {correctly_rejected}")
    logger.info(f"  False accepts       : {false_accepts}")
    logger.info(f"  Uncertain           : {uncertain_count}")
    logger.info(f"  Rejection Rate      : {fmt_pct(result['rejection_rate'])}")
    logger.info(f"  Avg Sim (impostor)  : {fmt_sim(result['avg_similarity'])}")

    return result


# ============================================================================
# In bảng tổng hợp
# ============================================================================
def print_comparison_table(r1: dict, r2: dict, r3: dict) -> None:
    """In bảng so sánh 3 sub-case."""
    print("\n" + "=" * 100)
    print("         BẢNG TỔNG HỢP – CASE 5: PROGRESSIVE GALLERY ENRICHMENT")
    print("=" * 100)

    header = (
        f"{'Sub-case':<45} | {'Gallery':>8} | {'Accuracy':>10} | "
        f"{'Avg Sim':>8} | {'Uncertain':>9} | {'Unk.Rej.':>9}"
    )
    print(header)
    print("-" * 100)

    # Row 1 - Baseline
    print(
        f"{'1. Baseline (chỉ enroll)':<45} | "
        f"{r1['gallery_size']:>8} | "
        f"{fmt_pct(r1['accuracy']):>10} | "
        f"{fmt_sim(r1['avg_similarity']):>8} | "
        f"{r1['uncertain_count']:>9} | "
        f"{'N/A':>9}"
    )

    # Row 2 - Enriched
    print(
        f"{'2. Sau Enrichment (enroll + real 1-3)':<45} | "
        f"{r2['gallery_size']:>8} | "
        f"{fmt_pct(r2['accuracy']):>10} | "
        f"{fmt_sim(r2['avg_similarity']):>8} | "
        f"{r2['uncertain_count']:>9} | "
        f"{'N/A':>9}"
    )

    # Row 3 - Unknown rejection
    print(
        f"{'3. Unknown Rejection (impostor probes)':<45} | "
        f"{r3['gallery_size']:>8} | "
        f"{'N/A':>10} | "
        f"{fmt_sim(r3['avg_similarity']):>8} | "
        f"{r3['uncertain_count']:>9} | "
        f"{fmt_pct(r3['rejection_rate']):>9}"
    )

    print("=" * 100)

    # Phân tích delta
    print("\n" + "-" * 60)
    print("  PHÂN TÍCH LỢI ÍCH CỦA ENRICHMENT")
    print("-" * 60)

    sim_delta = r2["avg_similarity"] - r1["avg_similarity"]
    unc_delta = r1["uncertain_count"] - r2["uncertain_count"]
    acc_delta = r2["accuracy"] - r1["accuracy"]

    print(f"  • Gallery size tăng  : {r1['gallery_size']} → {r2['gallery_size']} "
          f"(+{r2['gallery_size'] - r1['gallery_size']} embeddings)")
    print(f"  • Accuracy           : {fmt_pct(r1['accuracy'])} → {fmt_pct(r2['accuracy'])} "
          f"(Δ = {acc_delta:+.2f}%)")
    print(f"  • Avg Similarity     : {fmt_sim(r1['avg_similarity'])} → {fmt_sim(r2['avg_similarity'])} "
          f"(Δ = {sim_delta:+.4f})")
    print(f"  • Uncertain giảm    : {r1['uncertain_count']} → {r2['uncertain_count']} "
          f"(giảm {unc_delta})")
    print(f"  • Unknown Rejection  : {fmt_pct(r3['rejection_rate'])} "
          f"({r3['correctly_rejected']}/{r3['impostor_count']} impostor bị từ chối đúng)")

    print()
    print("  KẾT LUẬN:")
    if sim_delta > 0:
        print("  ✅ Enrichment giúp TĂNG Average Similarity – hệ thống nhận diện")
        print("     tự tin hơn khi gặp khuôn mặt đã biết.")
    else:
        print("  ⚠️ Average Similarity không tăng – cần kiểm tra chất lượng ảnh enrichment.")

    if unc_delta > 0:
        print(f"  ✅ Số lượng dự đoán 'uncertain' GIẢM {unc_delta} trường hợp – ")
        print("     enrichment giúp giảm vùng xám giữa known/unknown.")
    elif unc_delta == 0:
        print("  ℹ️ Số lượng uncertain không thay đổi.")
    else:
        print("  ⚠️ Số lượng uncertain tăng – cần kiểm tra lại pipeline enrichment.")

    if r3["rejection_rate"] >= 90:
        print(f"  ✅ Unknown Rejection Rate = {fmt_pct(r3['rejection_rate'])} – ")
        print("     hệ thống từ chối người lạ rất tốt sau enrichment.")
    elif r3["rejection_rate"] >= 70:
        print(f"  ⚠️ Unknown Rejection Rate = {fmt_pct(r3['rejection_rate'])} – ")
        print("     mức chấp nhận được nhưng có thể cải thiện.")
    else:
        print(f"  ❌ Unknown Rejection Rate = {fmt_pct(r3['rejection_rate'])} – ")
        print("     cần điều chỉnh threshold hoặc chất lượng gallery.")

    print()


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU ĐÁNH GIÁ CASE 5: PROGRESSIVE GALLERY ENRICHMENT")
    logger.info("=" * 70)
    logger.info(f"Recognition threshold  : {RECOGNITION_THRESHOLD}")
    logger.info(f"Unknown threshold      : {UNKNOWN_THRESHOLD}")
    logger.info(f"Enrichment threshold   : {ENRICHMENT_THRESHOLD}")

    # ------------------------------------------------------------------
    # 1. Đọc metadata & xây bảng ánh xạ
    # ------------------------------------------------------------------
    meta_map = load_metadata()
    class_map = build_class_map(meta_map)
    logger.info(f"Số sinh viên trong metadata: {len(class_map)}")

    # ------------------------------------------------------------------
    # 2. Khởi tạo pipeline
    # ------------------------------------------------------------------
    logger.info("Đang khởi tạo FacePipeline (InsightFace ArcFace)...")
    pipeline = FacePipeline()

    # ------------------------------------------------------------------
    # 3. Trích xuất embedding enroll
    # ------------------------------------------------------------------
    logger.info("\n--- TRÍCH XUẤT EMBEDDING ENROLL ---")
    enroll_emb, enroll_labels, enroll_names = extract_enroll_embeddings(pipeline, class_map)

    if len(enroll_emb) == 0:
        logger.error("Không có embedding enroll nào → dừng.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Trích xuất embedding real & chia nhóm enrichment / test
    # ------------------------------------------------------------------
    logger.info("\n--- TRÍCH XUẤT EMBEDDING REAL ---")
    real_dict = extract_real_embeddings(pipeline, class_map)

    # Chia: real 1-3 → enrichment, real 4-5 → test
    enrich_embs: list[np.ndarray] = []
    enrich_labels: list[int] = []
    test_embs: list[np.ndarray] = []
    test_labels: list[int] = []

    for name, embs in real_dict.items():
        class_id = class_map[name]
        n = len(embs)

        if n < 2:
            # Nếu chỉ có 1 ảnh → dùng cho test, không enrichment
            test_embs.extend(embs)
            test_labels.extend([class_id] * len(embs))
            logger.info(f"  {name}: chỉ có {n} ảnh → toàn bộ dùng cho test")
            continue

        # Chia: tối đa 3 ảnh đầu cho enrichment, phần còn lại cho test
        split_idx = min(3, n - 1)  # Đảm bảo ít nhất 1 ảnh cho test
        enrich_embs.extend(embs[:split_idx])
        enrich_labels.extend([class_id] * split_idx)
        test_embs.extend(embs[split_idx:])
        test_labels.extend([class_id] * (n - split_idx))

    logger.info(f"\nTổng hợp chia dữ liệu:")
    logger.info(f"  Enroll embeddings     : {len(enroll_emb)}")
    logger.info(f"  Enrichment embeddings : {len(enrich_embs)} (real 1-3)")
    logger.info(f"  Test embeddings       : {len(test_embs)} (real 4-5)")

    if len(test_embs) == 0:
        logger.error("Không có ảnh test nào → dừng.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 5. Chạy 3 Sub-cases
    # ------------------------------------------------------------------
    r1 = run_subcase1_baseline(enroll_emb, enroll_labels, test_embs, test_labels)

    r2, enriched_gallery, enriched_labels_arr = run_subcase2_enriched(
        enroll_emb, enroll_labels,
        enrich_embs, enrich_labels,
        test_embs, test_labels,
    )

    r3 = run_subcase3_unknown_rejection(enriched_gallery, enriched_labels_arr)

    # ------------------------------------------------------------------
    # 6. In bảng so sánh & phân tích
    # ------------------------------------------------------------------
    print_comparison_table(r1, r2, r3)

    # ------------------------------------------------------------------
    # 7. Lưu kết quả JSON
    # ------------------------------------------------------------------
    output = {
        "experiment": "Case 5 – Progressive Gallery Enrichment",
        "thresholds": {
            "recognition": RECOGNITION_THRESHOLD,
            "unknown": UNKNOWN_THRESHOLD,
            "enrichment": ENRICHMENT_THRESHOLD,
        },
        "results": {
            "subcase_1_baseline": r1,
            "subcase_2_enriched": r2,
            "subcase_3_unknown_rejection": r3,
        },
        "delta_analysis": {
            "accuracy_delta": round(r2["accuracy"] - r1["accuracy"], 2),
            "similarity_delta": round(r2["avg_similarity"] - r1["avg_similarity"], 4),
            "uncertain_reduction": r1["uncertain_count"] - r2["uncertain_count"],
            "gallery_growth": r2["gallery_size"] - r1["gallery_size"],
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\nĐã lưu kết quả tại: {OUTPUT_JSON}")
    logger.info("HOÀN TẤT ĐÁNH GIÁ CASE 5.")


if __name__ == "__main__":
    main()
