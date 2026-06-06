# Hướng dẫn huấn luyện Bộ Phân Lớp Sinh Viên (SVM Classifier Head) — Đề tài Học viện Ngân hàng

Mục này chứa kịch bản huấn luyện offline bộ phân lớp **SVM (Support Vector Machine) RBF Kernel** để nhận diện danh tính của 40 sinh viên thuộc Học viện Ngân hàng từ một bức ảnh chân dung đơn lẻ (được tăng cường).

---

## 📂 1. Chuẩn bị Dữ liệu đầu vào

Các bạn hãy tạo một thư mục dữ liệu tại bất cứ đâu (mặc định khuyến nghị là `c:\AI_event\dataset_students`) và tổ chức các thư mục sinh viên bên trong đúng theo quy chuẩn dưới đây:

```text
c:\AI_event\dataset_students\
├── SV001_NguyenVanA\
│   ├── image_01.jpg
│   ├── image_02.jpg
│   ├── image_03.jpg
│   ├── image_04.jpg
│   └── image_05.jpg
├── SV002_TranThiB\
│   ├── image_01.png
│   └── ...
└── SV040_LeVanC\
    └── ...
```

> [!IMPORTANT]
> - Tên thư mục con nên có cấu trúc dạng: `[MãSinhViên]_[HọTênViếtLiền]` (Ví dụ: `SV001_NguyenVanA`). Hệ thống sẽ tự động tách chuỗi này để trích xuất Mã Sinh Viên (`SV001`) và Tên Sinh Viên (`NguyenVanA`) hiển thị lên màn hình điểm danh.
> - Mỗi sinh viên nên có ít nhất **5 ảnh gốc** chụp rõ mặt, đủ các góc thẳng, hơi nghiêng nhẹ, ánh sáng rõ ràng.

---

## ⚡ 2. Hướng dẫn Chạy Huấn luyện

### Bước 1: Kích hoạt Môi trường ảo (Virtual Environment)
Mở cửa sổ dòng lệnh (Terminal / PowerShell) và di chuyển vào thư mục dự án `backend`, sau đó kích hoạt môi trường ảo:

```powershell
cd c:\AI_event\AI_Project_2526\backend
.venv\Scripts\activate
```

### Bước 2: Chạy Script Huấn luyện
Để chạy huấn luyện với đường dẫn dữ liệu mặc định (`c:\AI_event\dataset_students`), chỉ cần chạy:

```powershell
python training/train_svm.py
```

Nếu tập dữ liệu của bạn nằm ở một thư mục khác, hãy truyền tham số `--data_dir`:

```powershell
python training/train_svm.py --data_dir "D:/Data/NganHangStudents"
```

### Quá trình hoạt động của Script:
1.  **Quét Dữ Liệu**: Tự động duyệt qua toàn bộ 40 thư mục sinh viên.
2.  **Tăng Cường Ảnh (Augmentation)**: Tự động nhân bản 5 ảnh gốc của mỗi bạn thành **~100 ảnh biến thể** khác nhau về góc nghiêng (Geometric) và độ tương phản ánh sáng (Photometric).
3.  **Trích Xuất Vector**: Dùng mô hình ArcFace InsightFace để chuyển hóa 4.000 ảnh biến thể thành các vector đặc trưng 512 chiều.
4.  **Huấn Luyện Model**: Huấn luyện một bộ phân lớp SVM (RBF kernel) học cách phân tách 40 lớp sinh viên trên không gian vector.
5.  **Lưu kết quả**:
    -   Lưu file model học máy tại: `backend/app/models/student_svm_classifier.pkl`
    -   Lưu file map nhãn tại: `backend/app/models/label_encoder.json`

---

## 🎯 3. Điểm cộng Nghiên cứu Khoa học (Học thuật)

Trong cuốn báo cáo bảo vệ đề tài, các bạn nên đưa các chỉ số đánh giá mà script huấn luyện in ra màn hình khi hoàn thành:
1.  **Độ chính xác tập kiểm thử độc lập (Test set accuracy)**: Chứng minh khả năng nhận diện chính xác các bức ảnh chưa từng thấy trong quá trình học.
2.  **Chỉ số F1-Score & Precision**: Thể hiện hiệu năng cân bằng trên tất cả 40 sinh viên.
3.  **Tốc độ suy luận (Latency)**: Chứng minh rằng bộ phân lớp SVM xử lý chỉ mất **$< 1ms$** trên CPU, giúp hệ thống điểm danh siêu tốc tại các cổng ra vào.
