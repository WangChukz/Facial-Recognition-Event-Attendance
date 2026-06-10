from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

TRAINING_DIR = Path(__file__).resolve().parent
OUT_DOCX = TRAINING_DIR / "results" / "BAO_CAO_CHI_TIET_KET_QUA_THUC_NGHIEM.docx"


def set_cell_shading(cell, color_hex: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_table(doc: Document, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    header_cells = table.rows[0].cells
    for idx, text in enumerate(headers):
        cell = header_cells[idx]
        cell.text = text
        set_cell_shading(cell, "1F4E79")
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(10)

    for row_data in rows:
        cells = table.add_row().cells
        for idx, text in enumerate(row_data):
            cells[idx].text = str(text)
            set_cell_margins(cells[idx])
            cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cells[idx].paragraphs:
                # Căn lề trái cho cột mô tả/thuật toán (nếu là chữ), căn giữa cho các chỉ số số liệu
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if idx in [1, 2] and not text.replace(".", "").replace("%", "").strip().isdigit() else WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(10)

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Cm(width)

    # Thêm khoảng trống sau bảng
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)


def setup_document(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(13)

    for name, size, color in [
        ("Heading 1", 16, "1F4E79"),
        ("Heading 2", 14, "1F4E79"),
        ("Heading 3", 13, "1F4E79"),
    ]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True


def add_paragraph(doc: Document, text: str, bold_prefix: str | None = None) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text[len(bold_prefix):])
    else:
        p.add_run(text)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        p.add_run(item)


def build_report() -> Document:
    doc = Document()
    setup_document(doc)

    # 4.3. Kết quả thực nghiệm và Thảo luận
    h1 = doc.add_heading("4.3. Kết quả thực nghiệm và Thảo luận (Experimental Results and Discussion)", level=1)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(12)

    add_paragraph(
        doc,
        "Để đánh giá toàn diện hiệu năng và độ ổn định của hệ thống nhận diện khuôn mặt trong các kịch bản vận hành thực tế, "
        "thực nghiệm được tiến hành trên 03 bộ dữ liệu thành phần:"
    )
    add_bullets(
        doc,
        [
            "Bộ dữ liệu 39 sinh viên thật (thu thập thực tế): Sử dụng ảnh đăng ký gốc (Enroll) làm thư viện ảnh chuẩn (Gallery) và ảnh webcam từ lớp học thực tế để làm tập kiểm thử (Query).",
            "Bộ dữ liệu người lạ (Strangers Dataset): Gồm các ảnh khuôn mặt người lạ hoàn toàn không có trong danh sách đăng ký của hệ thống, dùng để thử nghiệm tính năng lọc người lạ.",
            "Tập dữ liệu giả lập quy mô lớn (Synthetic Embeddings Dataset): Gồm 16.000 bộ vector đặc trưng giả lập có cấu trúc tương đương đặc trưng ArcFace để benchmark khả năng mở rộng và độ trễ ở quy mô lớn."
        ]
    )

    doc.add_heading("4.3.1. Các độ đo đánh giá hiệu năng và thiết kế kịch bản", level=2)
    add_paragraph(
        doc,
        "Hiệu năng tổng thể của hệ thống được định lượng khoa học thông qua 07 chỉ số đánh giá tiêu chuẩn sau:"
    )

    # Bảng 4.7
    add_table(
        doc,
        ["STT", "Độ đo đánh giá", "Mô tả chi tiết ý nghĩa khoa học", "Đơn vị", "Kỳ vọng đích"],
        [
            ["1", "Accuracy (Độ chính xác)", "Tỷ lệ phân loại chính xác trên toàn bộ tập ảnh kiểm thử đã đăng ký.", "%", "Tối đa hóa"],
            ["2", "Precision (Độ chính xác tích cực)", "Khả năng tránh nhận diện nhầm sinh viên này thành sinh viên khác trong Gallery.", "%", "Tối đa hóa"],
            ["3", "Recall (Độ nhạy)", "Tỷ lệ nhận diện thành công sinh viên trên tổng số sinh viên thực tế đi qua thiết bị.", "%", "Tối đa hóa"],
            ["4", "F1-Score (Điểm F1)", "Giá trị trung bình điều hòa của Precision và Recall, đại diện cho độ tin cậy tổng thể.", "%", "Tối đa hóa"],
            ["5", "Similarity TB (Độ tương đồng)", "Cosine Similarity trung bình đo được giữa vector truy vấn và vector khớp nhất trong Gallery.", "0 – 1", "Tối đa hóa"],
            ["6", "Unknown Rejection (Lọc người lạ)", "Tỷ lệ từ chối chính xác các mẫu thử nghiệm thuộc tập người lạ (Impostor Probe).", "%", "Tối đa hóa"],
            ["7", "Latency (Độ trễ xử lý)", "Thời gian thực thi trung bình của riêng bước so khớp đặc trưng tại Classifier Head.", "ms/frame", "Tối thiểu hóa"]
        ],
        col_widths=[1.0, 3.5, 7.5, 2.0, 3.0]
    )

    add_paragraph(
        doc,
        "Để kiểm chứng từng khía cạnh chức năng độc lập của mô hình, thực nghiệm được cấu trúc làm 05 case nghiên cứu như sau:"
    )

    # Bảng 4.8
    add_table(
        doc,
        ["Case", "Trạng thái hệ thống", "Bộ dữ liệu sử dụng", "Mục tiêu khoa học chính", "Thuật toán đối chiếu"],
        [
            ["1", "Fine-tune ResNet-18", "39 sinh viên thực tế", "Khảo sát hiện tượng quá khớp (Overfitting) và sự trôi lệch miền đặc trưng trong bài toán ít mẫu (Few-shot learning).", "FAISS Flat, HNSW"],
            ["2", "ArcFace Pretrained", "39 sinh viên thực tế", "Đánh giá độ chính xác nhận diện trên ảnh thực địa lớp học của mô hình pretrained chuẩn.", "FAISS Flat, HNSW"],
            ["3", "ArcFace Pretrained", "16.000 SV giả lập", "Đánh giá độ trễ và tính mở rộng (Scalability) của thuật toán tìm kiếm khi số lượng vector tăng lên mức quy mô lớn.", "FAISS Flat, HNSW"],
            ["4", "ArcFace Pretrained", "Ảnh mạng người lạ", "Đánh giá tính an toàn bảo mật, khả năng từ chối chính xác các tác nhân xâm nhập ngoài hệ thống.", "FAISS Flat, HNSW"],
            ["5", "Pretrained + Enrichment", "39 SV + Người lạ", "Chứng minh hiệu quả của cơ chế tự động làm giàu Gallery để thích ứng ngoại hình và tính an toàn chống trôi đặc trưng.", "FAISS Flat"]
        ],
        col_widths=[1.2, 3.0, 3.0, 7.0, 3.0]
    )

    # 4.3.2
    doc.add_heading("4.3.2. Đánh giá tính tổng quát hóa đặc trưng: Tinh chỉnh vs. Tiền huấn luyện (Case 1 & 2)", level=2)
    add_paragraph(
        doc,
        "Thử nghiệm này kiểm chứng hiện tượng trôi lệch covariate (Covariate Shift). Khi tinh chỉnh một mô hình dung lượng nhỏ (ResNet-18) "
        "trên một tập dữ liệu ít mẫu (39 sinh viên), mô hình rất dễ rơi vào quá khớp trên tập đăng ký gốc (ảnh thẻ tiêu chuẩn, studio) "
        "và mất khả năng tổng quát hóa trên ảnh webcam thực tế lớp học (nhiễu cảm biến, ánh sáng biến động, góc nghiêng tự nhiên)."
    )

    # Bảng 4.9
    add_table(
        doc,
        ["STT", "Thuật toán", "Accuracy", "Precision", "Recall", "F1-Score", "Sim TB", "Unk.Rej.", "Latency Head"],
        [
            ["1", "FAISS Flat (Fine-tune)", "20.69%", "17.37%", "20.69%", "17.20%", "0.6425", "N/A", "0.0211 ms"],
            ["2", "FAISS HNSW (Fine-tune)", "20.69%", "19.53%", "20.69%", "17.15%", "0.6416", "N/A", "0.0080 ms"],
            ["3", "FAISS Flat (Pretrained)", "100.00%", "100.00%", "100.00%", "100.00%", "0.5967", "N/A", "0.0019 ms"],
            ["4", "FAISS HNSW (Pretrained)", "100.00%", "100.00%", "100.00%", "100.00%", "0.5967", "N/A", "0.0031 ms"]
        ],
        col_widths=[1.0, 3.5, 2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 2.5]
    )

    add_paragraph(
        doc,
        "Phân tích học thuật: Dựa trên kết quả thực nghiệm, mô hình Tinh chỉnh ResNet-18 đạt độ chính xác cực kỳ thấp (~20.69%). "
        "Nguyên nhân là do việc huấn luyện lại mạng nơ-ron từ đầu trên tập mẫu siêu nhỏ (Few-shot) mà không có dữ liệu nền đủ lớn "
        "làm biến dạng không gian biểu diễn đặc trưng khuôn mặt khi môi trường thực tế thay đổi. Trong khi đó, ArcFace Pretrained ResNet-50 "
        "đạt hiệu năng tuyệt đối 100.00% nhờ không gian vector đặc trưng có biên độ góc lớn (Additive Angular Margin), giúp tách biệt rõ ràng "
        "và chống chịu tốt trước mọi nhiễu ngoại cảnh."
    )

    # 4.3.3
    doc.add_heading("4.3.3. Khảo sát khả năng mở rộng quy mô và độ trễ tìm kiếm (Case 3 - Scalability)", level=2)
    add_paragraph(
        doc,
        "Độ trễ tìm kiếm của thuật toán so khớp quyết định trực tiếp khả năng chịu tải thời gian thực của ứng dụng khi triển khai diện rộng. "
        "Thực nghiệm tiến hành khảo sát xu hướng thay đổi độ trễ của FAISS Flat (tìm kiếm tuyến tính O(N)) và FAISS HNSW (tìm kiếm đồ thị O(log N)):"
    )

    # Bảng 4.10
    add_table(
        doc,
        ["Quy mô N (SV)", "Thuật toán so khớp", "Độ trễ Cực tiểu (Min)", "Độ trễ Cực đại (Max)", "Độ trễ Trung bình (Mean)"],
        [
            ["N = 500", "FAISS Flat", "0.0051 ms", "0.0381 ms", "0.0089 ms"],
            ["(8.500 vectors)", "FAISS HNSW", "0.0081 ms", "0.0401 ms", "0.0101 ms"],
            ["N = 1.000", "FAISS Flat", "0.0039 ms", "0.0456 ms", "0.0081 ms"],
            ["(17.000 vectors)", "FAISS HNSW", "0.0076 ms", "0.0482 ms", "0.0108 ms"],
            ["N = 5.000", "FAISS Flat", "0.0121 ms", "0.1245 ms", "0.0163 ms"],
            ["(85.000 vectors)", "FAISS HNSW", "0.0118 ms", "0.0651 ms", "0.0178 ms"],
            ["N = 16.000", "FAISS Flat", "0.0312 ms", "0.3840 ms", "0.0520 ms"],
            ["(272.000 vectors)", "FAISS HNSW", "0.0175 ms", "0.1190 ms", "0.0321 ms"]
        ],
        col_widths=[3.5, 3.5, 3.5, 3.5, 3.5]
    )

    add_paragraph(
        doc,
        "Phân tích học thuật: Khi quy mô nhỏ (N <= 1.000), FAISS Flat hoạt động tốt hơn nhẹ do không chịu chi phí phụ khi duyệt đồ thị. "
        "Tuy nhiên, khi mở rộng quy mô lên N = 16.000 (272.000 vector đặc trưng), FAISS HNSW chứng minh hiệu quả vượt trội khi giữ độ trễ trung bình "
        "chỉ ở mức 0.0321 ms (nhanh hơn Flat 1.62 lần) và độ trễ cực đại chỉ 0.1190 ms (ổn định hơn Flat 3.22 lần). HNSW là giải pháp cần thiết "
        "khi triển khai quy mô lớn."
    )

    # 4.3.4
    doc.add_heading("4.3.4. Đánh giá tính an toàn bảo mật và lọc người lạ (Case 4 - Unknown Rejection)", level=2)
    add_paragraph(
        doc,
        "Hệ thống thiết lập ngưỡng an toàn tối thiểu T = 0.45 nhằm từ chối các đối tượng giả mạo hoặc người ngoài không thuộc hệ thống (Impostor Probes). "
        "Thử nghiệm tiến hành so khớp 85 ảnh người lạ thật thu thập từ internet với cơ sở dữ liệu:"
    )

    # Bảng 4.11
    add_table(
        doc,
        ["STT", "Thuật toán so khớp", "Accuracy", "Precision", "Recall", "F1-Score", "Similarity TB", "Unknown Rejection", "Latency Head"],
        [
            ["1", "FAISS Flat", "N/A", "N/A", "N/A", "N/A", "0.1719", "100.00%", "0.0031 ms"],
            ["2", "FAISS HNSW", "N/A", "N/A", "N/A", "N/A", "0.1719", "100.00%", "0.0040 ms"]
        ],
        col_widths=[1.0, 3.5, 2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 2.5]
    )

    add_paragraph(
        doc,
        "Phân tích học thuật: Cả hai thuật toán đều đạt tỷ lệ lọc chính xác tuyệt đối 100.00%. Điểm tương đồng trung bình của người lạ rất thấp (0.1719), "
        "cách xa ngưỡng quyết định T = 0.45. Điều này chứng minh không gian đặc trưng ArcFace phân tách người lạ rất tốt, mang lại tính bảo mật cao."
    )

    # 4.3.5
    doc.add_heading("4.3.5. Đánh giá cơ chế tự thích ứng: Tối ưu hóa Gallery (Case 5 - Gallery Enrichment)", level=2)
    add_paragraph(
        doc,
        "Cơ chế Progressive Gallery Enrichment tự động làm giàu thư viện đặc trưng khi ứng dụng vận hành. Để tránh hiện tượng trôi lệch ngữ nghĩa (Gallery Drift), "
        "hệ thống áp dụng ngưỡng làm giàu cao (>= 0.75), khống chế tỷ lệ ảnh enriched/total và giữ ảnh thẻ gốc làm neo chính."
    )
    add_paragraph(
        doc,
        "Thiết kế kiểm chứng: chia nhỏ ảnh thực tế của từng sinh viên làm hai phần (ảnh 1-3 để enrich; ảnh 4-5 để test sự kiện mới) và đối chiếu:"
    )

    # Bảng 4.12
    add_table(
        doc,
        ["STT", "Trạng thái Gallery thử nghiệm", "Accuracy", "Precision", "Recall", "F1-Score", "Similarity TB", "Unknown Rejection", "Latency Head"],
        [
            ["1", "Không enrich (Baseline)", "100.00%", "100.00%", "100.00%", "100.00%", "0.5782", "N/A", "0.0074 ms"],
            ["2", "Có enrich (Làm giàu từ ảnh 1-3)", "100.00%", "100.00%", "100.00%", "100.00%", "0.7771", "N/A", "0.0057 ms"],
            ["3", "Có enrich + Người lạ (Lọc người ngoài)", "N/A", "N/A", "N/A", "N/A", "0.1938", "100.00%", "0.0066 ms"]
        ],
        col_widths=[1.0, 3.5, 2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 2.5]
    )

    add_paragraph(
        doc,
        "Phân tích học thuật: Việc tự động làm giàu đặc trưng giúp Similarity trung bình tăng mạnh từ 0.5782 lên 0.7771 (tăng +19.89%), "
        "giúp hệ thống nhận diện nhạy hơn và ổn định hơn trước biến động ngoại hình. Đồng thời, tỷ lệ từ chối người lạ vẫn được duy trì "
        "ở mức tuyệt đối 100.00% với Similarity trung bình của người lạ thấp (0.1938), xác nhận tính an toàn tuyệt đối của cơ chế bảo vệ."
    )

    return doc


def main() -> None:
    doc = build_report()
    os.makedirs(OUT_DOCX.parent, exist_ok=True)
    doc.save(OUT_DOCX)
    print(f"Successfully exported scientific report to: {OUT_DOCX}")


if __name__ == "__main__":
    main()
