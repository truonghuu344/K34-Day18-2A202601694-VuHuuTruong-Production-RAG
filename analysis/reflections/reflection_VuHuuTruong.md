# Individual Reflection — Lab 18: Production RAG Pipeline

**Họ và Tên:** Vũ Hữu Trường  
**Mã Sinh Viên:** 2A202601694  
**Lớp / Khóa:** K34  
**Module phụ trách:** Toàn bộ Pipeline (M1: Chunking, M2: Hybrid Search, M3: Reranking, M4: Evaluation, M5: Enrichment)

---

## Phần 1: Mapping Bài Giảng vào Thực Tế Triển Khai (Lecture Mapping)

| Lecture Concept | Module | Hàm / Class Cụ Thể | Phân Tích & Quan Sát Thực Tế (Observation) |
|----------------|--------|-------------------|---------------------------------------------|
| **Semantic Chunking** | M1 | `chunk_semantic()` | Dùng cosine similarity giữa vector embedding của các câu liên tiếp (threshold = 0.85, model `all-MiniLM-L6-v2`) để gom nhóm câu cùng ngữ nghĩa, tránh cắt đôi ý nghĩa mệnh đề như basic paragraph splitting. |
| **Hierarchical Chunking** | M1 | `chunk_hierarchical()` | Tạo cấu trúc Parent-Child (Parent 2048 chars, Child 256 chars). Retrieve bằng Child (tối ưu hóa độ chính xác tìm kiếm ngữ nghĩa) nhưng truyền Parent lên LLM (cung cấp đầy đủ ngữ cảnh bao quanh cho câu trả lời). |
| **Structure-Aware Chunking** | M1 | `chunk_structure_aware()` | Tách tài liệu theo markdown headers (`#`, `##`, `###`), giữ nguyên cấu trúc bảng biểu, code, list và gán metadata `section` tương ứng. |
| **Vietnamese Word Segmentation & BM25** | M2 | `segment_vietnamese()`, `BM25Search` | Tokenize tiếng Việt bằng `underthesea` và thay thế ký tự gạch dưới `_` bằng khoảng trắng để từ ghép khớp chính xác với query người dùng trong mô hình BM25Okapi. |
| **Dense Vector Search** | M2 | `DenseSearch` | Sử dụng embedding `BAAI/bge-m3` (1024-dim) và cơ sở dữ liệu vector Qdrant (`query_points()`) với khoảng cách Cosine để truy vấn ngữ nghĩa sâu. |
| **Reciprocal Rank Fusion (RRF)** | M2 | `reciprocal_rank_fusion()` | Kết hợp danh sách xếp hạng từ BM25 (từ khóa chính xác, mã số, tên riêng) và Dense (ngữ nghĩa) theo công thức $RRF\_Score(d) = \sum \frac{1}{k + rank(d) + 1}$ với $k=60$. |
| **Cross-Encoder Reranking** | M3 | `CrossEncoderReranker.rerank()` | Sử dụng cross-encoder `BAAI/bge-reranker-v2-m3` để chấm điểm đồng thời cặp (Query, Doc) thay vì tính bi-encoder độc lập, giúp lọc từ top-20 xuống top-3 chunks có độ liên quan cao nhất. |
| **RAGAS 4 Core Metrics** | M4 | `evaluate_ragas()` | Đánh giá 4 chiều chất lượng: Faithfulness (độ trung thực, chống hallucination), Answer Relevancy (độ khớp câu hỏi), Context Precision (tỷ lệ chunk đúng được xếp hạng cao), Context Recall (độ đầy đủ của thông tin thu thập). |
| **Diagnostic Tree Failure Analysis** | M4 | `failure_analysis()` | Phân tích bottom-5 câu hỏi có điểm số thấp nhất để phân loại lỗi theo cây chẩn đoán: Retrieval failure (Recall thấp), Ranking failure (Precision thấp), Hallucination (Faithfulness thấp), Generation mismatch (Relevancy thấp). |
| **Contextual Prepend & HyQA Enrichment** | M5 | `contextual_prepend()`, `generate_hypothesis_questions()`, `_enrich_single_call()` | Làm giàu chunk trước khi lập chỉ mục: sinh câu hỏi giả định (HyQA) để rút ngắn khoảng cách từ vựng giữa câu hỏi và tài liệu, đồng thời thêm ngữ cảnh tài liệu vào đầu chunk để giảm 49% lỗi retrieval. Tối ưu chi phí bằng chế độ Single-Call (1 API call/chunk). |

---

## Phần 2: Khó Khăn Gặp Phải & Cách Giải Quyết (Troubleshooting & Debugging)

### 1. Lỗi Network Timeout và Wheel Extraction khi cài đặt thư viện
- **Lỗi gặp phải:** `Failed to download distribution due to network timeout. Try increasing UV_HTTP_TIMEOUT (current value: 30s)` khi tải các gói lớn như `torch`, `pyarrow`, `tiktoken`.
- **Cách debug & xử lý:** 
  - Tăng `UV_HTTP_TIMEOUT=300` trong PowerShell.
  - Sử dụng index ổn định và cấu hình retry để tải toàn bộ dependencies một cách an toàn.

### 2. Sự không tương thích giữa Tokenizer của Underthesea và BM25Okapi
- **Lỗi gặp phải:** Khi `underthesea.word_tokenize(format="text")` sinh ra các từ nối bằng dấu gạch dưới (VD: `nghỉ_phép`), BM25 khi split theo khoảng trắng coi đó là 1 token `nghỉ_phép`, trong khi query của người dùng gõ `nghỉ phép` (2 token riêng) dẫn đến BM25 score = 0.
- **Cách xử lý:** Sau khi tokenize với Underthesea, thực hiện `.replace("_", " ")` trước khi đưa vào BM25 indexing và BM25 search.

### 3. Phương thức truy vấn trong Qdrant Client phiên bản mới
- **Lỗi gặp phải:** `qdrant_client>=2.0` khuyến nghị sử dụng `client.query_points()` thay vì `client.search()`.
- **Cách xử lý:** Cập nhật mã nguồn sử dụng `client.query_points(collection, query=query_vector, limit=top_k)` kèm fallback an toàn.

### 4. Tối ưu hóa chi phí và tốc độ Enrichment (M5)
- **Lỗi gặp phải:** Nếu gọi 4 API calls riêng lẻ cho mỗi chunk (Summary, HyQA, Contextual, Metadata), với hàng trăm chunks sẽ gây tốn kém chi phí token và làm chậm pipeline đáng kể.
- **Cách xử lý:** Hiện thực hóa `_enrich_single_call()` sử dụng 1 structured prompt duy nhất trả về JSON gồm cả 4 thành phần, kèm cơ chế fallback trích xuất không cần API key.

---

## Phần 3: Kế Hoạch Áp Dụng Cho Project Thực Tế (Action Plan)

### Thông Tin Dự Án
- **Tên dự án:** Hệ thống Trợ lý Pháp lý & Tra cứu Quy chế Doanh nghiệp Nội bộ (Legal & Enterprise Policy Assistant).
- **Hiện trạng:** Hệ thống cũ sử dụng Naive RAG (Basic Paragraph Chunking + Dense Embedding OpenAI text-embedding-3-small), thường xuyên gặp hiện tượng:
  - Bỏ sót các điều khoản quy định nằm rải rác (Context Recall thấp).
  - Trộn lẫn văn bản quy chế cũ (hết hiệu lực) và văn bản mới (Context Precision thấp).
  - Trả lời sai các câu hỏi tính toán thời gian thâm niên, số tiền phạt, số ngày phép.

### Kế Hoạch Cải Tiến Kỹ Thuật (5 Bước)
1. **Advanced Chunking Strategy:**
   - Áp dụng **Hierarchical Chunking** (Parent 2048 chars, Child 256 chars) kết hợp **Structure-Aware** cho các tài liệu định dạng văn bản quy chế/luật có cấu trúc Điều/Khoản rõ ràng.
2. **Hybrid Search với RRF:**
   - Kết hợp **BM25 tiếng Việt** (Underthesea word segmentation) để bắt chính xác các số hiệu văn bản, từ khóa pháp lý, tên chức danh + **Dense Search (bge-m3)** để hiểu ngữ cảnh câu hỏi ngữ nghĩa rộng. Hợp nhất bằng RRF ($k=60$).
3. **Cross-Encoder Reranking:**
   - Triển khai `BAAI/bge-reranker-v2-m3` lọc từ top-25 xuống top-3 chunks trước khi nạp vào Prompt LLM, đảm bảo thứ tự ưu tiên tuyệt đối cho văn bản mới nhất.
4. **Enrichment Pipeline:**
   - Sử dụng **Contextual Prepend** (đính kèm Tên quy chế + Số hiệu phiên bản vào đầu mỗi chunk) và **HyQA** để ánh xạ trước các tình huống thực tế của nhân viên vào điều khoản quy chế tương ứng.
5. **Continuous Evaluation & Monitoring:**
   - Tích hợp bộ metric đánh giá tự động RAGAS định kỳ mỗi khi cập nhật cơ sở tri thức (Knowledge Base), thiết lập ngưỡng cảnh báo nếu Faithfulness < 0.85 hoặc Context Recall < 0.80.

### Kế Hoạch Triển Khai (Timeline)
- **Tuần 1:** Chuẩn hóa dữ liệu quy chế, trích xuất text PDF/Markdown và thiết lập pipeline Hierarchical Chunking + Metadata enrichment.
- **Tuần 2:** Dựng cụm Qdrant Vector DB, cấu hình BM25 tiếng Việt và tối ưu hóa trọng số Hybrid RRF.
- **Tuần 3:** Tích hợp Cross-Encoder Reranking và benchmark độ trễ (latency < 400ms).
- **Tuần 4:** Xây dựng bộ test set 100 câu hỏi nghiệp vụ, chạy RAGAS evaluation và triển khai CI/CD monitoring.
