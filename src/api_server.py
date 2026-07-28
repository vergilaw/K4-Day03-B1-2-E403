"""
🌐 WEB API SERVER (Role 4 - UI Integration)
Flask server expose các endpoint để giao diện web gọi vào ReAct Agent và Baseline Chatbot.
"""

import json
import os
import sys
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Đảm bảo import được các module trong cùng thư mục src/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# UTF-8 cho Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tools import AVAILABLE_TOOLS
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_SYSTEM_PROMPT,
    MAX_ITERATIONS,
    FORBIDDEN_KEYWORDS,
    SAFE_FALLBACK_MESSAGE,
)
from providers import get_llm_provider
from app import (
    load_test_cases,
    parse_action,
    execute_tool_call,
    is_provider_error,
)

load_dotenv()

# ─── Flask App Setup ─────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Cho phép frontend HTML gọi từ file:// hoặc cổng khác

# Thư mục gốc của project (một cấp trên src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(BASE_DIR, "ui")

# ─── Provider (khởi tạo 1 lần) ───────────────────────────────────────────────
provider = get_llm_provider()
model_name = getattr(provider, "model_name", "Offline Mock Mode")
provider_class = provider.__class__.__name__


# ─── Helper: ReAct Agent (có trace log trả về) ───────────────────────────────

def run_react_agent_api(user_query: str):
    """
    Chạy vòng lặp ReAct Agent và trả về dict chứa:
    - final_answer: câu trả lời cuối cùng
    - trace: danh sách các bước Thought / Action / Observation
    - guardrail_triggered: cờ báo phanh an toàn bị kích hoạt
    """
    trace = []

    # Guardrail 1: Safety Filter
    query_lower = user_query.lower()
    for word in FORBIDDEN_KEYWORDS:
        if word.lower() in query_lower:
            return {
                "final_answer": "🛡️ Yêu cầu bị từ chối do vi phạm tiêu chuẩn cộng đồng an toàn.",
                "trace": [{"type": "guardrail", "content": f"Phát hiện từ khóa nhạy cảm: '{word}'"}],
                "guardrail_triggered": True,
            }

    conversation_history = f"Question: {user_query}\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        response_text = provider.generate(conversation_history, system_prompt=REACT_SYSTEM_PROMPT).strip()

        # Guardrail 3: Provider Error
        if is_provider_error(response_text):
            trace.append({"type": "guardrail", "content": f"Lỗi Provider: {response_text}"})
            return {
                "final_answer": SAFE_FALLBACK_MESSAGE,
                "trace": trace,
                "guardrail_triggered": True,
            }

        # Tách Thought / Action / Final Answer ra khỏi response
        thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)", response_text, re.DOTALL)
        thought_text = thought_match.group(1).strip() if thought_match else ""
        if thought_text:
            trace.append({"type": "thought", "content": thought_text})

        # Kiểm tra Final Answer
        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            trace.append({"type": "final_answer", "content": final_answer})
            return {
                "final_answer": final_answer,
                "trace": trace,
                "guardrail_triggered": False,
            }

        # Trích xuất Action
        tool_name, args = parse_action(response_text)
        if not tool_name:
            trace.append({"type": "final_answer", "content": response_text})
            return {
                "final_answer": response_text,
                "trace": trace,
                "guardrail_triggered": False,
            }

        trace.append({"type": "action", "content": f"{tool_name}({', '.join(args)})"})

        # Thực thi Tool
        obs = execute_tool_call(tool_name, args)
        trace.append({"type": "observation", "content": obs})

        # Cập nhật lịch sử
        conversation_history += f"{response_text}\nObservation: {obs}\n"

    # Guardrail 2: Max Iterations
    trace.append({"type": "guardrail", "content": f"Đã đạt giới hạn {MAX_ITERATIONS} bước."})
    return {
        "final_answer": SAFE_FALLBACK_MESSAGE,
        "trace": trace,
        "guardrail_triggered": True,
    }


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def api_status():
    """Kiểm tra trạng thái server và provider"""
    return jsonify({
        "status": "ok",
        "provider": provider_class,
        "model": model_name,
        "tools_count": len(AVAILABLE_TOOLS),
        "max_iterations": MAX_ITERATIONS,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """ReAct Agent endpoint — chính của Mốc 3"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Thiếu trường 'message' trong body"}), 400

    user_query = data["message"].strip()
    if not user_query:
        return jsonify({"error": "Câu hỏi không được để trống"}), 400

    result = run_react_agent_api(user_query)
    return jsonify(result)


@app.route("/api/baseline", methods=["POST"])
def api_baseline():
    """Baseline Chatbot endpoint — Mốc 2 so sánh"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Thiếu trường 'message' trong body"}), 400

    user_query = data["message"].strip()
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    return jsonify({"response": response})


@app.route("/api/test-cases", methods=["GET"])
def api_test_cases():
    """Trả về bộ test cases của Role 1"""
    try:
        tests = load_test_cases()
        return jsonify(tests)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Serve UI ─────────────────────────────────────────────────────────────────

@app.route("/")
def serve_ui():
    return send_from_directory(UI_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(UI_DIR, filename)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("💘 CUPID AGENT — WEB UI SERVER")
    print("=" * 55)
    print(f"🔌 Provider : {provider_class} (Model: {model_name})")
    print(f"🛠️  Tools    : {len(AVAILABLE_TOOLS)} công cụ")
    print(f"🌐 Mở trình duyệt tại: http://localhost:5000")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=False)
