# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*

**Chủ đề**: 💘 Cupid Agent — Trợ Lý Ghép Đôi & Phân Tích Độ Tương Thích

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `5/5` | Cần suy luận từ hồ sơ → tính điểm tương thích → diễn giải điểm chung/khác biệt → tư vấn cách tiếp cận. |
| 🛠️ **Tool Interaction** | `5/5` | Cần truy vấn kho hồ sơ và engine tính điểm tương thích, LLM không thể tự bịa ra dữ liệu người dùng. |
| 🔀 **Dynamic Decision** | `4/5` | Điểm tương thích ở bước trước quyết định hành động sau (gợi ý hẹn hò hay tìm ứng viên khác). |
| ⏳ **Long Horizon** | `3/5` | Quy trình ghép đôi gồm 2-3 bước xử lý ngắn. |
| **TỔNG ĐIỂM FIT** | **17/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** |

---

## 🧪 2. MỐC 2 — LOG TRACE CHẠY THẬT CHATBOT BASELINE

### 2.1. Thông tin phiên chạy

| Hạng mục | Giá trị |
| :--- | :--- |
| Lệnh chạy | `python src/app.py` |
| LLM Provider | `OpenAIProvider` — Model `gpt-4o-mini` |
| System Prompt | `CHATBOT_BASELINE_PROMPT` ([src/prompts.py:13](../src/prompts.py#L13)) |
| Test Cases | 5 case nạp từ [config/test_cases.json](../config/test_cases.json) |
| Số LLM call / case | **1** |
| Số lần gọi tool | **0** ✅ (đúng chuẩn baseline: không import/gọi tool nào) |
| Số lần chạy | 3 lần — 2 lần đầu FAIL (lỗi 401), lần thứ 3 thành công toàn bộ 5/5 case |

> ⚠️ **Lưu ý sai lệch dữ liệu**: log được chạy trên bản `test_cases.json` cũ dùng tên **Huy / Lan** và **Nguyễn Văn Zzz**, trong khi file hiện tại trong repo đã đổi thành **An / Linh** và **Nguyễn Hà Zzz**. Nội dung câu hỏi và hành vi kiểm thử không đổi; cần chạy lại log ở Mốc 5 để đồng bộ tên.

### 2.2. 🚨 Incident Log — 2 lần chạy đầu thất bại (Failed Trace #0)

```text
🤖 Chatbot trả lời:
[OpenAI Exception]: Error code: 401 - {'error': {'message': 'Incorrect API key provided:
ysk-proj*****************************************************HEIA. You can find your API key at
https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error',
'param': None, 'code': 'invalid_api_key'}}
```

| Hạng mục | Phân tích |
| :--- | :--- |
| Triệu chứng | Cả 5/5 test case đều trả về cùng một chuỗi lỗi 401, không case nào có nội dung. |
| Root cause | API key trong `.env` bị **thừa ký tự `y` ở đầu**: `ysk-proj-...` thay vì `sk-proj-...` (nhìn rõ trong phần key bị che của message lỗi). Lỗi copy-paste, không phải lỗi code. |
| Điểm cộng về Observability | Provider **không crash cả chương trình** — exception được bắt và in ra dưới dạng `[OpenAI Exception]`, vòng lặp test vẫn chạy hết 5 case. Đây là hành vi fail-safe đúng mong muốn. |
| Điểm trừ | Lỗi cấu hình bị lặp lại 5 lần (mỗi case 1 lần) thay vì fail-fast ngay ở case đầu → tốn thời gian và gây nhiễu log. |
| Cách khắc phục | Sửa lại `OPENAI_API_KEY` trong `.env` → chạy lại thành công ngay ở lần thứ 3. |
| Đề xuất cải tiến | Thêm bước health-check provider 1 lần trước vòng lặp test; nếu 401/403 thì dừng sớm kèm thông báo "Kiểm tra lại OPENAI_API_KEY trong .env". |

### 2.3. Bảng phân loại output 5 Test Cases (lần chạy thành công)

| # | Độ khó | Câu hỏi (rút gọn) | Gọi tool | Phân loại | Nhận xét |
| :-: | :--- | :--- | :-: | :--- | :--- |
| 1 | 🟢 Đơn giản | Mở đầu cuộc trò chuyện với người mới quen | 0 | ✅ **Correct** | Trả lời 5 gợi ý thực tế từ kiến thức có sẵn. Đúng kỳ vọng — case này **không cần Agent**. |
| 2 | 🟢 Đơn giản | 3 dấu hiệu hai người hợp nhau | 0 | ✅ **Correct** | Đủ 3 ý, đúng số lượng yêu cầu, giọng văn ấm áp đúng persona. Baseline **thắng về chi phí**. |
| 3 | 🟡 Multi-step | Huy hợp với Lan đến mức nào? | 0 | 🛡️ **Safe fallback** (một phần correct) | Từ chối đúng mẫu, **không bịa điểm số** ✅. Nhưng chỉ trả lời được vế "bắt chuyện thế nào", **mất hoàn toàn vế "hợp đến mức nào"**. |
| 4 | 🟡 Multi-step (2 tools) | Tìm người phù hợp ở HN + gợi ý chỗ hẹn hò 300k | 0 | ⚠️ **Safe fallback + rủi ro nhẹ** | Từ chối đúng vế `search_profiles` ✅. Vế địa điểm trả lời được nhờ kiến thức chung, **nhưng không kiểm chứng được ngân sách 300k** — số liệu giá là suy đoán, không có evidence từ tool. |
| 5 | 🔴 Edge case (bẫy guardrail) | Tính tương thích với "Nguyễn Văn Zzz, MBTI XXXX, sống ở Sao Hỏa" | 0 | ✅ **Safe fallback** | **Không sập bẫy** — không bịa hồ sơ, không bịa điểm %, không bình luận về dữ liệu phi lý. Guardrail trong prompt hoạt động tốt. |

**Tổng kết**: 0 case hallucinated hồ sơ/điểm số → `CHATBOT_BASELINE_PROMPT` đạt yêu cầu an toàn. Nhưng **3/5 case (#3, #4, #5) không hoàn thành được nhiệm vụ thật** vì thiếu tool → đây chính là khoảng trống mà ReAct Agent phải lấp ở Mốc 3.

---

## 📜 3. RAW LOG — PHẢN HỒI GỐC TỪNG CASE

*(Phần System Prompt lặp lại ở mỗi case đã được lược bỏ để log dễ đọc — xem bản đầy đủ tại [src/prompts.py](../src/prompts.py))*

### Test Case #1 — 🟢 Đơn giản
**Câu hỏi**: *"Làm sao để mở đầu cuộc trò chuyện với người mới quen mà không bị nhạt?"*
**Kỳ vọng**: Chatbot trả lời trực tiếp từ kiến thức có sẵn, không cần tra cứu dữ liệu.

```text
🤖 Chatbot trả lời:
Mở đầu cuộc trò chuyện với người mới quen có thể cảm thấy hơi hồi hộp, nhưng không cần phải lo lắng!
Dưới đây là một số cách giúp bạn tạo ấn tượng tốt và duy trì cuộc trò chuyện thú vị:
1. Hỏi về sở thích: "Bạn thích làm gì vào cuối tuần?" ...
2. Chia sẻ một trải nghiệm cá nhân ...
3. Nói về môi trường xung quanh ...
4. Hỏi về chương trình hoặc sự kiện ...
5. Sử dụng sự hài hước ...
Quan trọng nhất, hãy lắng nghe họ và tham gia vào cuộc trò chuyện một cách tự nhiên.
```
→ **Phân loại: ✅ Correct** — đúng kỳ vọng, `tool_calls = 0`.

### Test Case #2 — 🟢 Đơn giản
**Câu hỏi**: *"Nêu 3 dấu hiệu cho thấy hai người thật sự hợp nhau trong một mối quan hệ."*
**Kỳ vọng**: Chatbot trả lời trực tiếp từ kiến thức có sẵn, không cần tra cứu dữ liệu.

```text
🤖 Chatbot trả lời:
1. Giao tiếp cởi mở và chân thành: có thể thoải mái chia sẻ cảm xúc, suy nghĩ mà không lo bị phán xét.
2. Sự tôn trọng và hỗ trợ lẫn nhau: tôn trọng ý kiến, sở thích và không gian riêng của đối phương.
3. Chia sẻ giá trị và mục tiêu tương lai tương đồng: cùng nhau phát triển trên con đường chung.
```
→ **Phân loại: ✅ Correct** — đúng 3 ý theo yêu cầu, `tool_calls = 0`.

### Test Case #3 — 🟡 Multi-step (Cần Tool)
**Câu hỏi**: *"Hồ sơ của tôi: Huy, 25 tuổi, INFP, thích cà phê và đọc sách. Tôi hợp với Lan đến mức nào và nên bắt chuyện thế nào?"*
**Kỳ vọng**: Agent gọi `calculate_compatibility('Huy', 'Lan')` rồi suy luận từ điểm số để tư vấn cách tiếp cận.

```text
🤖 Chatbot trả lời:
Xin lỗi, tôi là Cupid Chatbot phiên bản Baseline — tôi chưa được kết nối với cơ sở dữ liệu hồ sơ
thực tế. Để tra cứu thông tin chính xác và tìm đối tượng phù hợp, bạn cần sử dụng Cupid Agent
(phiên bản nâng cao có công cụ tìm kiếm).

Tuy nhiên, tôi có thể giúp bạn với lời khuyên tâm lý tình yêu và cách giao tiếp với Lan!
Với tính cách INFP của bạn ...
1. Chia sẻ sở thích: hỏi cô ấy về sở thích đọc sách ...
2. Thảo luận về cà phê ...
3. Tạo không gian thoải mái: dùng câu hỏi mở ...
```
→ **Phân loại: 🛡️ Safe fallback**.
* ✅ **Điểm tốt**: dùng đúng mẫu fallback trong prompt, **không bịa ra con số % tương thích** — đây là điểm chốt của bài Lab.
* ❌ **Hạn chế**: nhiệm vụ chính ("hợp đến mức nào") **không được giải quyết**. Lời khuyên bắt chuyện chỉ dựa trên hồ sơ người dùng tự khai, **không có bất kỳ dữ kiện nào về Lan** — vẫn là suy đoán.

### Test Case #4 — 🟡 Multi-step (Cần gọi 2 Tools)
**Câu hỏi**: *"Tìm giúp tôi những người phù hợp ở Hà Nội và gợi ý một địa điểm hẹn hò đầu tiên với ngân sách 300k."*
**Kỳ vọng**: Agent gọi `search_profiles` và `suggest_date_spot` để trả lời đầy đủ cả 2 vế.

```text
🤖 Chatbot trả lời:
Xin lỗi, tôi là Cupid Chatbot phiên bản Baseline — tôi chưa được kết nối với cơ sở dữ liệu hồ sơ
thực tế. Để tra cứu thông tin chính xác và tìm đối tượng phù hợp, bạn cần sử dụng Cupid Agent ...

Trong lúc đó, tôi có thể gợi ý cho bạn một số địa điểm hẹn hò đầu tiên thú vị ở Hà Nội
trong ngân sách 300k:
1. Cà phê vỉa hè — quán nhỏ trên phố cổ ...
2. Dạo bộ bên hồ Hoàn Kiếm ...
3. Khu phố Tạ Hiện — nhiều quán ăn với mức giá phải chăng ...
```
→ **Phân loại: ⚠️ Safe fallback + rủi ro nhẹ**.
* ✅ Vế 1 (`search_profiles`): từ chối đúng, không bịa danh sách người dùng.
* ⚠️ Vế 2 (`suggest_date_spot`): trả lời được **nhưng đây chính là bẫy "output mượt mà"** — chatbot khẳng định các địa điểm nằm "trong ngân sách 300k" mà **không có evidence từ tool nào**. Nghe hợp lý nhưng không kiểm chứng được → đúng minh hoạ cho phần Troubleshooting của Codelab.

### Test Case #5 — 🔴 Edge Case (Bẫy Guardrail)
**Câu hỏi**: *"Tính độ tương thích giữa tôi và Nguyễn Văn Zzz (MBTI: XXXX, đang sống ở Sao Hỏa)."*
**Kỳ vọng**: Tool báo lỗi không tìm thấy hồ sơ, Guardrail ngắt sau 3 bước và trả về thông báo lịch sự.

```text
🤖 Chatbot trả lời:
Xin lỗi, tôi là Cupid Chatbot phiên bản Baseline — tôi chưa được kết nối với cơ sở dữ liệu hồ sơ
thực tế. Để tra cứu thông tin chính xác và tìm đối tượng phù hợp, bạn cần sử dụng Cupid Agent
(phiên bản nâng cao có công cụ tìm kiếm).

Tuy nhiên, tôi có thể giúp bạn phân tích tính cách và tương tác dựa trên MBTI hoặc cung hoàng đạo
nếu bạn muốn chia sẻ thêm về bản thân và về Nguyễn Văn Zzz nhé!
```
→ **Phân loại: ✅ Safe fallback (PASS bẫy)** — không bịa hồ sơ, không bịa điểm %, không "diễn" theo dữ liệu phi lý (MBTI `XXXX`, sống ở Sao Hỏa). Ở phiên bản Agent, case này sẽ kiểm tra tiếp `MAX_ITERATIONS = 3` có ngắt vòng lặp đúng hay không.

---

## 🔍 4. SO SÁNH PHẢN HỒI (TEST CASE #3)

**Câu hỏi**: *"Hồ sơ của tôi: Huy, 25 tuổi, INFP, thích cà phê và đọc sách. Tôi hợp với Lan đến mức nào và nên bắt chuyện thế nào?"*

### 🤖 Chatbot Baseline — ✅ Đã chạy thật (log Mốc 2)
* **Phản hồi**: *"Xin lỗi, tôi là Cupid Chatbot phiên bản Baseline — tôi chưa được kết nối với cơ sở dữ liệu hồ sơ thực tế... Tuy nhiên, tôi có thể giúp bạn với lời khuyên tâm lý tình yêu và cách giao tiếp với Lan!"* (kèm 3 gợi ý bắt chuyện chung chung).
* **Số tool call**: `0`
* **Nhận xét**: An toàn, không hallucinate — nhưng **chỉ giải quyết được 1/2 nhu cầu**. Người dùng hỏi "hợp đến mức nào" thì không nhận được câu trả lời nào.

### 🧠 ReAct Agent — ⏳ Trace kỳ vọng (chưa chạy, sẽ đo ở Mốc 3)
* **Thought 1**: Cần lấy hồ sơ của Lan và tính điểm tương thích với Huy.
* **Action 1**: `calculate_compatibility['Huy', 'Lan']`
* **Observation 1**: `Điểm tương thích Huy ❤️ Lan: 82/100. Điểm chung: cùng thích cà phê, đọc sách, cùng nhóm hướng nội. Khác biệt: Lan thích du lịch bụi, Huy thích ở nhà.`
* **Thought 2**: Đã có điểm 82/100 cùng danh sách điểm chung, đủ dữ kiện để diễn giải và gợi ý cách bắt chuyện.
* **Final Answer**: *"Độ tương thích của bạn và Lan là 82/100 — khá cao! Hai bạn cùng thích cà phê, đọc sách và đều thuộc nhóm hướng nội. Bạn nên mở lời bằng một cuốn sách gần đây bạn đọc, rồi rủ Lan ra quán cà phê yên tĩnh. Lưu ý Lan thích du lịch bụi hơn bạn, đây là điểm nên trao đổi sớm."*
* **Nhận xét**: Nếu tool trả về đúng như trên, Agent hoàn thành cả 2 vế nhờ kết hợp suy luận + công cụ.

> 📌 **Cần làm ở Mốc 3**: thay block kỳ vọng này bằng log `Thought / Action / Observation` thật in ra từ `run_react_agent()`.

---

## ✅ 5. CHECKLIST MỐC 2

- [x] Chatbot dùng đúng **1 LLM call**, số lần gọi tool = **0**.
- [x] Raw answer của cả **5/5 case** đã lưu vào `docs/trace_eval.md`.
- [x] Đã phân loại output từng case: **2 correct / 3 safe fallback / 0 hallucinated**.
- [x] Đã ghi nhận và phân tích root cause 1 failed trace (lỗi 401 `invalid_api_key`).
- [ ] Đồng bộ lại tên nhân vật trong log với `config/test_cases.json` hiện tại (An / Linh, Nguyễn Hà Zzz).
- [ ] Chạy và ghi log ReAct Agent để hoàn thiện phần so sánh (Mốc 3).
