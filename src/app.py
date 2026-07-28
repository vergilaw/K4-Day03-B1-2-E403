"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
Mốc 3: ReAct Agent Loop & Safeguards Integration.
"""

import json
import os
import re
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_SYSTEM_PROMPT,
    MAX_ITERATIONS,
    FORBIDDEN_KEYWORDS,
    SAFE_FALLBACK_MESSAGE,
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Tên tool thay thế mà LLM hay sinh ra do prompt/test case dùng cách gọi khác
# với tên đã đăng ký trong AVAILABLE_TOOLS.
TOOL_ALIASES = {
    "search_matches": "search_candidates",
    "search_profiles": "search_candidates",
    "suggest_date_spot": "suggest_date_ideas",
    "suggest_date_spots": "suggest_date_ideas",
    "get_profile": "get_user_profile",
    "find_user": "find_user_by_name",
}


def build_tool_map():
    """Gộp AVAILABLE_TOOLS với bảng alias thành một bảng tra cứu duy nhất."""
    tool_map = dict(AVAILABLE_TOOLS)
    for alias, target in TOOL_ALIASES.items():
        if alias not in tool_map and target in tool_map:
            tool_map[alias] = tool_map[target]
    return tool_map


def is_provider_error(text: str) -> bool:
    """
    Nhận diện chuỗi lỗi do lớp Provider trả về thay vì nội dung từ LLM.

    providers.py bắt mọi exception và trả về chuỗi dạng
    '[Gemini Exception]: ...' hoặc '[OpenAI Error]: ...'. Nếu không nhận ra,
    vòng lặp ReAct sẽ in nguyên stack lỗi cho người dùng dưới nhãn Final Answer.
    """
    if not isinstance(text, str):
        return False
    return bool(re.match(r"^\s*\[[^\]]*(Exception|Error)[^\]]*\]", text))


def parse_action(text: str):
    """
    Trích xuất tên Action và các tham số từ phản hồi sinh ra của LLM.
    Ví dụ: 'Action: get_user_profile[U001]' -> ('get_user_profile', ['U001'])
           'Action: calculate_compatibility[U001, U002]' -> ('calculate_compatibility', ['U001', 'U002'])

    Pattern 2 (không có tiền tố 'Action:') chỉ được chấp nhận khi tên bắt được
    là một tool có thật. Nếu không, mọi dấu ngoặc đơn trong câu văn xuôi đều bị
    hiểu nhầm thành lời gọi tool — ví dụ 'Nguyễn Hà Zzz (MBTI: XXXX, sống ở Sao
    Hỏa)' từng bị parse thành tool ảo 'Zzz'.
    """
    known_tools = build_tool_map()

    # Pattern 1: Action: tool_name[arg1, arg2] hoặc tool_name(arg1, arg2)
    match = re.search(r"Action:\s*([a-zA-Z0-9_]+)\s*[\[\(](.*?)[\]\)]", text, re.IGNORECASE)

    if not match:
        # Pattern 2: tool_name[arg1, arg2] không có tiền tố Action: —
        # chỉ nhận khi tên trùng một tool đã đăng ký.
        for candidate in re.finditer(r"([a-zA-Z0-9_]+)\s*[\[\(](.*?)[\]\)]", text, re.DOTALL):
            if candidate.group(1).strip() in known_tools:
                match = candidate
                break

        if not match:
            return None, []

    tool_name = match.group(1).strip()
    raw_args = match.group(2).strip()

    if not raw_args:
        args = []
    else:
        # Tách các tham số phân cách bằng dấu phẩy và làm sạch chuỗi
        args = [arg.strip().strip("'\"") for arg in raw_args.split(",")]

    return tool_name, args


def execute_tool_call(tool_name: str, args: list):
    """
    Thực thi công cụ từ AVAILABLE_TOOLS với cơ chế xử lý lỗi và mapping alias.
    """
    tool_map = build_tool_map()

    if tool_name not in tool_map:
        return json.dumps({
            "success": False,
            "error": (
                f"Công cụ '{tool_name}' không có trong AVAILABLE_TOOLS. "
                f"Các công cụ hợp lệ: {sorted(AVAILABLE_TOOLS)}."
            )
        }, ensure_ascii=False)

    func = tool_map[tool_name]
    try:
        # Thực thi hàm với danh sách tham số
        return func(*args)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Lỗi khi thực thi '{tool_name}': {str(e)}"
        }, ensure_ascii=False)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ (Dành cho Mốc 2).
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails (Mốc 3).
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    # 🛡️ 1. GUARDRAIL - Safety Filter: Kiểm tra từ khóa nhạy cảm
    query_lower = user_query.lower()
    for word in FORBIDDEN_KEYWORDS:
        if word.lower() in query_lower:
            print(f"🛡️ GUARDRAIL TRIGGERED: Phát hiện từ khóa nhạy cảm/độc hại '{word}'. Dừng xử lý!")
            print("🏁 Final Answer: Yêu cầu bị ngắt do vi phạm tiêu chuẩn cộng đồng an toàn.")
            return

    conversation_history = f"Question: {user_query}\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Sinh câu trả lời từ LLM với ReAct Prompt
        response_text = provider.generate(conversation_history, system_prompt=REACT_SYSTEM_PROMPT).strip()
        print(f"{response_text}")

        # 🛡️ 3. GUARDRAIL - Provider Failure: không đổ raw stack ra cho người dùng
        if is_provider_error(response_text):
            print(f"\n🛡️ GUARDRAIL TRIGGERED: Lỗi từ LLM Provider, không phải nội dung trả lời. Ngắt an toàn!")
            print(f"🔎 Chi tiết kỹ thuật (dành cho dev): {response_text}")
            print(f"🏁 Final Answer: {SAFE_FALLBACK_MESSAGE}")
            return

        # 2. Kiểm tra nếu LLM đã đưa ra Final Answer
        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            print(f"\n✅ RE-ACT COMPLETE!")
            print(f"🏁 Final Answer: {final_answer}")
            return

        # 3. Trích xuất Action & Tham số
        tool_name, args = parse_action(response_text)

        if not tool_name:
            print("\n⚠️ Không trích xuất được Action hợp lệ. Dùng phản hồi hiện tại làm kết quả.")
            print(f"🏁 Final Answer: {response_text}")
            return

        # 4. Thực thi công cụ
        print(f"🛠️ Action Parsed: {tool_name}{args}")
        obs = execute_tool_call(tool_name, args)
        print(f"👁️ Observation: {obs}")

        # 5. Cập nhật lịch sử suy luận
        conversation_history += f"{response_text}\nObservation: {obs}\n"

    # 🛡️ 2. GUARDRAIL - Infinite Loop Prevention / Max Iterations Exceeded
    print(f"\n🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước mà chưa có Final Answer. Ngắt lặp an toàn!")
    print(f"🏁 Final Answer: {SAFE_FALLBACK_MESSAGE}")


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")

    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")

    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")

    print("==================================================")
    print("📍 MỐC 3: CHẠY TRÊN REACT AGENT LOOP (CÓ TOOL & GUARDRAILS)")
    print("==================================================")

    for test in tests:
        print(f"\n==================================================")
        print(f"📌 Test Case #{test['id']} [{test.get('category', '')}]")
        print(f"🎯 Kỳ vọng: {test.get('expected_behavior', '')}")
        run_react_agent(test["question"], provider)


