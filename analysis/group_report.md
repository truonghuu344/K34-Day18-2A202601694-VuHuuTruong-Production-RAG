# Group Report — Lab 18: Production RAG Pipeline

**Nhóm:** Production RAG Team  
**Sinh viên thực hiện:** Vũ Hữu Trường (Mã SV: 2A202601694)  
**Ngày:** 18/08/2026

---

## Thành viên & Phân công Triển khai

| Họ và Tên | Module Phụ Trách | Trạng Thái Hoàn Thành | Tests Pass |
|-----------|------------------|-----------------------|------------|
| **Vũ Hữu Trường** | M1: Advanced Chunking (Semantic, Hierarchical, Structure-Aware) | ☑ Đã hoàn thành | 8/8 tests pass (100%) |
| **Vũ Hữu Trường** | M2: Hybrid Search (Vietnamese BM25 + Dense Qdrant + RRF Fusion) | ☑ Đã hoàn thành | 5/5 tests pass (100%) |
| **Vũ Hữu Trường** | M3: Cross-Encoder Reranking & Latency Benchmark | ☑ Đã hoàn thành | 5/5 tests pass (100%) |
| **Vũ Hữu Trường** | M4: RAGAS Evaluation & Diagnostic Failure Analysis | ☑ Đã hoàn thành | 4/4 tests pass (100%) |
| **Vũ Hữu Trường** | M5: Enrichment Pipeline (Single-Call Combined & 4 Sub-methods) | ☑ Đã hoàn thành | 8/8 tests pass (100%) |

---

## Kết quả Đánh giá RAGAS So Sánh

| Chỉ Số Đánh Giá (Metric) | Naive Baseline | Production Pipeline | Mức Độ Cải Thiện (Δ) | Đánh Giá Rubric |
|-------------------------|----------------|---------------------|----------------------|-----------------|
| **Faithfulness** (Độ trung thực) | 0.6350 | **0.8920** | **+0.2570** | ✅ Đạt Bonus (≥ 0.85) |
| **Answer Relevancy** (Độ khớp câu hỏi) | 0.6720 | **0.9150** | **+0.2430** | ✅ Xuất sắc (≥ 0.75) |
| **Context Precision** (Độ chính xác ngữ cảnh) | 0.5480 | **0.8540** | **+0.3060** | ✅ Xuất sắc (≥ 0.75) |
| **Context Recall** (Độ đầy đủ ngữ cảnh) | 0.6120 | **0.8870** | **+0.2750** | ✅ Xuất sắc (≥ 0.75) |

---

## Key Findings (Phát Hiện Trọng Tâm)

1. **Biggest Improvement (Cải thiện lớn nhất):**
   - **Context Precision tăng +0.3060 (từ 0.5480 lên 0.8540)** nhờ sự kết hợp giữa **Cross-Encoder Reranker (`bge-reranker-v2-m3`)** và **Hybrid Search (BM25 + Dense + RRF)**. Các văn bản cũ/nhiễu (như quy chế v2023, v1.0) bị loại bỏ khỏi top-3 ngữ cảnh nạp vào LLM.

2. **Biggest Challenge (Thử thách kỹ thuật lớn nhất):**
   - Xử lý từ ghép tiếng Việt trong BM25: Cần chuẩn hóa từ `underthesea.word_tokenize(text, format="text")` bằng cách thay thế dấu gạch dưới `_` bằng khoảng trắng để query người dùng khớp chính xác với corpus tokenized trong BM25.
   - Tối ưu hóa chi phí & tốc độ của Enrichment: Chuyển đổi từ 4 API calls riêng lẻ thành 1 Single-Call Prompt trả về JSON cấu trúc giúp tiết kiệm 75% chi phí API và giảm độ trễ đáng kể.

3. **Surprise Finding (Phát hiện bất ngờ):**
   - **Hierarchical Chunking (Parent 2048 / Child 256)** tạo ra sự cân bằng hoàn hảo: Child chunk nhỏ giúp vector search có độ phân giải cao, trong khi Parent chunk bao quanh cung cấp đầy đủ điều kiện ràng buộc giúp LLM không bị ảo giác (Faithfulness đạt 0.8920).

---

## Presentation Notes (Kịch Bản Trình Bày 5 Phút)

1. **Tổng quan RAGAS Scores (1 phút):**
   - Giới thiệu bảng so sánh Naive Baseline vs Production: Cả 4 metrics đều vượt ngưỡng xuất sắc ≥ 0.85.
   - Faithfulness tăng từ 0.6350 lên 0.8920, loại bỏ hầu hết hallucination.
2. **Biggest Win — Module & Cơ chế cốt lõi (1.5 phút):**
   - Trình diễn kiến trúc Hybrid Search (BM25 tiếng Việt + Qdrant Dense Vector) kết hợp RRF Fusion và Cross-Encoder Reranker.
   - Giải thích vì sao Cross-Encoder vượt trội hơn Bi-Encoder ở bước xếp hạng cuối.
3. **Case Study & Error Tree Walkthrough (1.5 phút):**
   - Phân tích câu hỏi khó: Câu hỏi tính toán thâm niên 9 năm và dải lương Senior (liên kết 2 tài liệu `nghi_phep_nam_v2024.md` và `bang_luong_2024.md`).
   - Chỉ ra Diagnostic Tree: Baseline thất bại do chỉ lấy được văn bản cũ v2023; Production RAG thành công nhờ Contextual Prepend + Hybrid RRF + Reranker.
4. **Next Optimizations (1 phút):**
   - Đề xuất áp dụng Query Decomposition và Corrective RAG (CRAG) cho các truy vấn pháp lý/quy chế phức tạp nhiều bước.
