# Hướng dẫn thực nghiệm Đánh giá Hiệu năng Nhận diện Khuôn mặt (FAISS Flat & HNSW) — Đề tài Học viện Ngân hàng

Thư mục này chứa các kịch bản kiểm thử, đánh giá hiệu năng (Offline Benchmark) của hệ thống nhận diện khuôn mặt điểm danh sử dụng các chỉ mục **FAISS Flat** và **FAISS HNSW** (đã loại bỏ Cosine Similarity và SVM theo yêu cầu nghiệp vụ để tập trung vào các giải pháp tìm kiếm vector mật độ cao hiệu năng lớn).

---

## 📂 1. Chuẩn bị Dữ liệu đầu vào

Hệ thống sử dụng tập dữ liệu thực tế tại thư mục `c:\AI_event\dataset\dataset` để đánh giá:
- `enroll/`: Chứa 39 ảnh đăng ký của 39 sinh viên Học viện Ngân hàng (dạng `TênSinhViên_enroll.jpg`).
- `real/`: Chứa 39 thư mục sinh viên (dạng `TênSinhViên_real/`), mỗi thư mục chứa khoảng 5-6 ảnh thực tế chụp tại cổng điểm danh để làm tập test.
- `metadata.xlsx`: File danh sách sinh viên khớp giữa Mã sinh viên, Họ và tên, Lớp.

Ngoài ra, tập dữ liệu lớn giả lập (Synthetic Dataset) với 16.000 sinh viên tại `C:\AI_event\DATA_FAKE...` được sử dụng để đánh giá khả năng mở rộng (Scalability Benchmark).

---

## ⚡ 2. Các Kịch Bản Kiểm Thử (Case 1, 2, 4, 5)

Chúng ta tiến hành chạy kiểm thử theo các kịch bản sau:

### Case 1: Đánh giá mô hình ArcFace Pretrained (ResNet-50) + FAISS Flat / HNSW
Đánh giá độ chính xác nhận diện trên 39 sinh viên thực tế bằng mô hình pre-trained gốc.

### Case 2: Đánh giá mô hình Fine-tuned (ResNet-18 ArcFace) + FAISS Flat / HNSW
So sánh độ chính xác và độ trễ của mô hình tự huấn luyện (fine-tuned) trên tập dữ liệu trường học so với mô hình pre-trained gốc để chứng minh ảnh hưởng của "Domain Gap" và "Few-shot Learning".

### Case 4: Benchmark Khả năng Mở rộng (Scalability Benchmark)
Đo lường độ trễ tìm kiếm (Search Latency) và thời gian dựng chỉ mục (Index Build Time) của **FAISS Flat** vs **HNSW** khi số lượng sinh viên tăng dần: $N = 1.000, 4.000, 8.000, 16.000$ sinh viên giả lập.

### Case 5: Tự động Làm giàu Thư viện Ảnh (Progressive Gallery Enrichment)
Đánh giá hiệu quả của cơ chế tự động thêm ảnh chất lượng cao vào Gallery khi điểm danh thành công:
- **Trước Enrichment**: Thư viện chỉ có 1 ảnh đăng ký gốc (baseline).
- **Sau Enrichment**: Thư viện tự động cập nhật các ảnh điểm danh đạt ngưỡng tin cậy cao ($\ge 0.75$).
- **Đánh giá Unknown Rejection**: Đo lường khả năng loại bỏ người lạ sau khi thư viện được cập nhật.

---

## 🚀 3. Hướng dẫn Chạy Kiểm thử & Sinh Báo cáo

Mở PowerShell tại thư mục dự án và kích hoạt môi trường ảo:
```powershell
cd c:\AI_event\AI_Project_2526\backend
.venv\Scripts\activate
```

Chạy lần lượt các bước kiểm thử để cập nhật dữ liệu:

### Bước 1: Trích xuất Embedding và chạy đối chứng 4 luồng chính
Chạy đánh giá Case 1 & Case 2 trên tập dữ liệu thực tế, sinh file cache embedding cho các bước sau:
```powershell
$env:PYTHONIOENCODING='utf-8'
python training/evaluate_all_8_pipelines.py
```

### Bước 2: Chạy đối sánh chi tiết Case 1 & Case 2
Chạy kịch bản đối sánh trực tiếp độ chính xác giữa FAISS Flat và HNSW:
```powershell
python training/evaluate_comparison.py
```

### Bước 3: Benchmark hiệu năng mở rộng (Case 4)
Chạy kiểm thử đo độ trễ tìm kiếm với quy mô từ 1k đến 16k sinh viên:
```powershell
python training/case4_scalability_benchmark.py
```

### Bước 4: Kiểm thử Gallery Enrichment (Case 5)
Chạy mô phỏng quá trình tự động cập nhật thư viện ảnh và đánh giá Unknown Rejection:
```powershell
python training/case5_gallery_enrichment.py
```

### Bước 5: Tổng hợp và Xuất báo cáo
Chạy script tổng hợp kết quả của tất cả các case vào báo cáo Markdown và cập nhật file dữ liệu kết quả:
```powershell
python training/generate_final_scenario_report.py
```

---

## 🎯 4. Các tệp kết quả sinh ra
- `training/results/FINAL_SCENARIO_REPORT.md`: Báo cáo kết quả tổng hợp bằng Markdown.
- `training/results/final_scenario_results.json`: Tệp kết quả dạng JSON để vẽ biểu đồ hoặc import tự động.
- `training/results/BAO_CAO_THUC_NGHIEM_5_CASE_NHAN_DIEN_KHUON_MAT.docx`: Báo cáo Word học thuật phục vụ nghiệm thu đề tài.
