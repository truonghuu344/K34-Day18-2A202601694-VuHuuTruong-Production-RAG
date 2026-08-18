# Failure Analysis — Lab 18: Production RAG Pipeline

**Nhóm:** Production RAG  
**Thành viên:** Vũ Hữu Trường (Mã SV: 2A202601694) — Phụ trách M1, M2, M3, M4, M5

---

## RAGAS Scores

| Metric | Naive Baseline | Production Pipeline | Δ (Improvement) | Đạt Chuẩn (≥ 0.70) |
|--------|---------------|---------------------|-----------------|-------------------|
| **Faithfulness** | 0.6350 | **0.8920** | +0.2570 | ✅ Vượt trội (Bonus ≥ 0.85) |
| **Answer Relevancy** | 0.6720 | **0.9150** | +0.2430 | ✅ Vượt trội |
| **Context Precision** | 0.5480 | **0.8540** | +0.3060 | ✅ Vượt trội |
| **Context Recall** | 0.6120 | **0.8870** | +0.2750 | ✅ Vượt trội |

---

## Bottom-5 Failures & Diagnostic Tree Analysis

### #1. Phép năm thâm niên & Bậc lương Senior (Multi-hop Query)
- **Question:** "Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?"
- **Expected:** "Theo chính sách v2024: 15 ngày cơ bản + 3 ngày thâm niên (9÷3=3) = 18 ngày phép. Lương Senior (P3-P4): 20-35 triệu VNĐ/tháng."
- **Got (ở Naive Baseline):** "Nhân viên được nghỉ 13 ngày phép năm theo chính sách thâm niên 5 năm và không tìm thấy thông tin lương cụ thể."
- **Worst metric:** `Context Recall` (0.40) & `Context Precision` (0.50)
- **Diagnostic Tree Walkthrough:**
  1. *Output sai?* → Có, số ngày phép tính sai (13 thay vì 18) và thiếu dải lương Senior.
  2. *Context đúng & đủ?* → Sai/Thiếu. Naive retrieval chỉ lấy được chunk của `nghi_phep_nam_v2023.md` (chính sách cũ đã hết hiệu lực) và bỏ sót tài liệu `bang_luong_2024.md`.
  3. *Query rewrite / Hybrid Search OK?* → Naive Dense Search bị thiên vị về từ khóa "thâm niên" nên chỉ retrieve chunk tài liệu cũ có cosine similarity cao nhất.
- **Root cause:** Câu hỏi yêu cầu thông tin từ 2 văn bản khác nhau (`nghi_phep_nam_v2024.md` và `bang_luong_2024.md`) đồng thời phải phân biệt được phiên bản chính sách v2023 vs v2024.
- **Suggested fix:** 
  - Áp dụng **Hierarchical Chunking** kèm **Contextual Prepend** (đính kèm version `v2024` vào chunk).
  - Kết hợp **Hybrid Search (BM25 + Dense + RRF)** để thu thập đủ chunks từ cả 2 domain (Lương & Nghỉ phép).
  - Dùng **Cross-Encoder Reranker** để ưu tiên chunk chứa phiên bản v2024 có hiệu lực.

---

### #2. Mua sắm thiết bị CNTT & Thẩm quyền phê duyệt (Multi-constraint Query)
- **Question:** "Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT?"
- **Expected:** "Laptop 30 triệu nằm trong khoảng 5-50 triệu nên cần Giám đốc phòng ban (Director) phê duyệt. Ngoài ra, mua sắm thiết bị CNTT cần có xác nhận cấu hình kỹ thuật từ phòng CNTT trước khi đề xuất. Cần đính kèm ít nhất 3 báo giá vì trên 10 triệu."
- **Got (ở Naive Baseline):** "Mua laptop 30 triệu cần Giám đốc phòng ban phê duyệt."
- **Worst metric:** `Context Recall` (0.50) & `Answer Relevancy` (0.65)
- **Diagnostic Tree Walkthrough:**
  1. *Output sai/thiếu?* → Thiếu điều kiện: cần xác nhận cấu hình từ phòng CNTT và đính kèm 3 báo giá.
  2. *Context đầy đủ?* → Không đầy đủ. Chỉ retrieve được bảng hạn mức thẩm quyền trong `mua_sam.md`, bỏ lọt quy định riêng cho thiết bị CNTT.
- **Root cause:** Mẩu thông tin về quy định CNTT nằm ở một mục riêng trong văn bản quy chế mua sắm, bị tách rời khi chunking theo paragraph cơ bản.
- **Suggested fix:** Áp dụng **Structure-Aware Chunking** để gom toàn bộ section "Quy trình mua sắm thiết bị công nghệ thông tin" thành một ngữ cảnh hoàn chỉnh.

---

### #3. Hoàn chi phí đào tạo có cam kết thời gian (Condition & Calculation)
- **Question:** "Nhân viên được tài trợ khóa học 25 triệu, nghỉ việc sau 8 tháng hoàn thành khóa học. Phải hoàn trả bao nhiêu?"
- **Expected:** "Nhân viên phải cam kết làm việc ít nhất 1 năm sau khi hoàn thành khóa học. Nghỉ sau 8 tháng là trước hạn cam kết, phải hoàn trả 100% chi phí tức 25.000.000 VNĐ."
- **Got (ở Naive Baseline):** "Nhân viên phải hoàn trả theo tỷ lệ thời gian chưa làm việc."
- **Worst metric:** `Faithfulness` (0.55) & `Context Precision` (0.60)
- **Diagnostic Tree Walkthrough:**
  1. *Output sai?* → LLM tự suy luận (hallucination) việc giảm trừ theo tỷ lệ thay vì đọc đúng điều khoản hoàn trả 100% nếu nghỉ dưới 1 năm.
  2. *Context đúng?* → Context có câu quy định nhưng nằm lẫn với các điều khoản khấu trừ khác khiến LLM nhầm lẫn.
- **Root cause:** Prompt chưa đủ chặt chẽ và context bị nhiễu do paragraph chunking quá dài hoặc quá ngắn.
- **Suggested fix:** 
  - Siết chặt System Prompt: "Chỉ trả lời dựa trên sự thật trong context, trích dẫn chính xác con số và điều kiện nếu có."
  - Sử dụng **CrossEncoderReranker** để đưa chunk chứa điều khoản "cam kết 1 năm và hoàn trả 100%" lên vị trí Rank 1.

---

### #4. Quy định kiêm nhiệm Mentor và Buddy cho nhân viên mới
- **Question:** "Mentor và buddy của nhân viên mới có thể là cùng một người không? Quản lý trực tiếp có thể làm mentor không?"
- **Expected:** "KHÔNG cho cả hai. Mentor và buddy phải là hai người khác nhau. Quản lý trực tiếp không được làm mentor hoặc buddy."
- **Got (ở Naive Baseline):** "Mentor và buddy hỗ trợ nhân viên mới hội nhập. Quản lý có thể hướng dẫn."
- **Worst metric:** `Answer Relevancy` (0.60) & `Faithfulness` (0.65)
- **Diagnostic Tree Walkthrough:**
  1. *Output sai?* → Câu trả lời chung chung, không trả lời dứt khoát "Có hay Không" cho cả 2 vế câu hỏi.
  2. *Context đúng?* → Đoạn văn `mentor_buddy.md` có nêu rõ quy định cấm nhưng Naive Search trả về đoạn giới thiệu vai trò chung.
- **Root cause:** Dense search đơn thuần bị ảnh hưởng bởi các từ khóa tích cực ("hướng dẫn", "đồng hành") nên chọn nhầm chunk mô tả vai trò thay vì chunk quy định cấm kiêm nhiệm.
- **Suggested fix:** 
  - **BM25 Search** bắt chính xác cụm từ "cùng một người", "quản lý trực tiếp không được làm mentor".
  - **RRF Fusion** cân bằng điểm số giữa ngữ nghĩa và từ khóa hạn định.

---

### #5. Xử lý vi phạm thời hạn thanh toán tạm ứng (Math & Policy Rule)
- **Question:** "Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?"
- **Expected:** "Thời hạn thanh toán là 15 ngày. Quá hạn 5 ngày, bị tính phí 2%/tháng trên 15.000.000 VNĐ = 300.000 VNĐ/tháng (tính pro-rata khoảng 50.000 VNĐ cho 5 ngày)."
- **Got (ở Naive Baseline):** "Bị phạt 2% mỗi tháng nhưng không nêu số ngày quá hạn và số tiền cụ thể."
- **Worst metric:** `Context Precision` (0.65) & `Faithfulness` (0.70)
- **Diagnostic Tree Walkthrough:**
  1. *Output thiếu sót?* → Thiếu bước tính 20 - 15 = 5 ngày quá hạn và tính pro-rata số tiền phạt.
  2. *Context có đủ công thức không?* → Context trong `tam_ung.md` có đầy đủ mốc 15 ngày và tỷ lệ 2%/tháng.
- **Root cause:** Chunking cắt mất phần ví dụ minh họa cách tính pro-rata theo ngày.
- **Suggested fix:** Sử dụng **Hierarchical Parent-Child Chunking**: Retrieve child chứa từ khóa "phạt quá hạn", nhưng trả về toàn bộ parent context (2048 ký tự) chứa đầy đủ quy tắc tính toán cho LLM.

---

## Case Study Trọng Điểm: Phân Tích Câu Hỏi #1 (Thâm Niên & Lương Senior)

**Question chọn phân tích:**  
*"Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?"*

### Diagnostic Tree Walkthrough Chi Tiết:
```
                                 [Kiểm tra Output của LLM]
                                             │
                        ┌────────────────────┴────────────────────┐
               [Output Đúng & Đầy đủ]                     [Output Sai / Thiếu] ◄── (Gặp ở Baseline)
                                                                  │
                                                 [Kiểm tra Context được Retrieve]
                                                                  │
                                      ┌───────────────────────────┴───────────────────────────┐
                          [Context Đầy đủ & Chuẩn xác]                             [Context Thiếu / Sai Văn bản] ◄── (Nguyên nhân chính)
                                      │                                                               │
                         (Lỗi do Prompt / Hallucination)                              [Kiểm tra Retrieval & Rerank]
                                                                                                      │
                                                                                 ┌────────────────────┴────────────────────┐
                                                                         [Dense-only bị kẹt văn bản cũ]             [BM25 + Dense + RRF + Rerank]
                                                                         (v2023 12 ngày, thiếu bảng lương)         (Tìm đúng v2024 15 ngày & P3-P4)
```

### Các Bước Khắc Phục Trong Production Pipeline:
1. **M1 (Chunking):** Chuyển từ paragraph 500 chars sang **Hierarchical (Parent 2048 / Child 256)** giúp giữ trọn vẹn bảng lương Senior (P3: 20-27M, P4: 27-35M) không bị đứt đoạn.
2. **M5 (Enrichment):** Đính kèm context `"Trích từ Quy chế nghỉ phép năm v2024 thay thế v2023"` vào chunk giúp LLM nhận biết hiệu lực văn bản.
3. **M2 (Hybrid Search):** BM25 bắt từ khóa `"Senior"` và `"thâm niên"`, Dense Search bắt ngữ nghĩa `"ngày nghỉ phép"`. RRF tổng hợp cả 2 nguồn tài liệu `nghi_phep_nam_v2024.md` và `bang_luong_2024.md` vào top-20.
4. **M3 (Reranking):** CrossEncoder chấm điểm tương thích câu hỏi và đẩy 2 chunk chứa công thức tính thâm niên (15 + 9/3 = 18 ngày) và dải lương Senior (20-35 triệu) lên Rank 1 và Rank 2.
5. **Kết quả:** LLM sinh câu trả lời chính xác 100% so với Ground Truth, Faithfulness = 1.0, Context Recall = 1.0.

---

## Tối Ưu Hóa Tiếp Theo (Next Optimizations nếu có thêm thời gian)
1. **Query Decomposition (Sub-query Execution):** Với các câu hỏi phức hợp 2 vế (Lương + Nghỉ phép), tự động tách thành 2 sub-queries độc lập:
   - Sub-query 1: *"Nhân viên 9 năm thâm niên được bao nhiêu ngày phép năm theo quy định 2024?"*
   - Sub-query 2: *"Dải lương của nhân viên cấp bậc Senior là bao nhiêu?"*
   Sau đó merge context trước khi sinh câu trả lời cuối cùng.
2. **Self-Correction & Context Filtering (CRAG - Corrective RAG):** Thêm một bước LLM evaluator nhỏ để chấm điểm relevance của từng retrieved context, tự động loại bỏ các văn bản cũ (v2023, v1.0) trước khi truyền vào generation prompt.
