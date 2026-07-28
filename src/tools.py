"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.
"""

"""
Cupid Agent Tool Registry
Các công cụ mà ReAct Agent có thể sử dụng để tìm kiếm,
phân tích và hỗ trợ kết nối người dùng.
"""

import json
from typing import Any


# =========================================================
# MOCK DATABASE
# =========================================================

USER_PROFILES = {
    "U001": {
        "name": "Minh",
        "age": 22,
        "city": "Hà Nội",
        "interests": ["đọc sách", "công nghệ", "cà phê", "du lịch"],
        "personality": ["hướng nội", "điềm tĩnh", "tò mò"],
        "relationship_goal": "nghiêm túc",
        "preferred_age_range": [20, 25],
        "preferred_city": ["Hà Nội"],
        "dealbreakers": ["hút thuốc"],
    },
    "U002": {
        "name": "Lan",
        "age": 21,
        "city": "Hà Nội",
        "interests": ["đọc sách", "nhiếp ảnh", "cà phê", "du lịch"],
        "personality": ["cởi mở", "điềm tĩnh", "sáng tạo"],
        "relationship_goal": "nghiêm túc",
        "preferred_age_range": [21, 26],
        "preferred_city": ["Hà Nội"],
        "dealbreakers": [],
    },
    "U003": {
        "name": "An",
        "age": 24,
        "city": "Đà Nẵng",
        "interests": ["thể thao", "du lịch", "âm nhạc"],
        "personality": ["năng động", "hướng ngoại"],
        "relationship_goal": "kết bạn",
        "preferred_age_range": [20, 26],
        "preferred_city": ["Đà Nẵng", "TP.HCM"],
        "dealbreakers": [],
    },
}

MATCH_FEEDBACK = []


def tool_response(
    success: bool,
    data: Any = None,
    error: str | None = None
) -> str:
    """
    Chuẩn hóa kết quả trả về của mọi tool.
    """
    return json.dumps(
        {
            "success": success,
            "data": data,
            "error": error,
        },
        ensure_ascii=False,
    )


# =========================================================
# PROFILE TOOLS
# =========================================================

def get_user_profile(user_id: str) -> str:
    """
    Lấy hồ sơ của một người dùng.

    Args:
        user_id: Mã định danh người dùng, ví dụ U001.

    Returns:
        Chuỗi JSON chứa thông tin hồ sơ.
    """
    profile = USER_PROFILES.get(user_id)

    if profile is None:
        return tool_response(
            success=False,
            error=f"Không tìm thấy người dùng '{user_id}'.",
        )

    return tool_response(
        success=True,
        data={
            "user_id": user_id,
            "profile": profile,
        },
    )


def update_user_profile(
    user_id: str,
    field: str,
    value: Any,
) -> str:
    """
    Cập nhật một trường trong hồ sơ người dùng.

    Args:
        user_id: Mã người dùng.
        field: Tên trường cần cập nhật.
        value: Giá trị mới.

    Returns:
        Kết quả cập nhật dưới dạng JSON.
    """
    if user_id not in USER_PROFILES:
        return tool_response(
            success=False,
            error=f"Không tìm thấy người dùng '{user_id}'.",
        )

    allowed_fields = {
        "city",
        "interests",
        "personality",
        "relationship_goal",
        "preferred_age_range",
        "preferred_city",
        "dealbreakers",
    }

    if field not in allowed_fields:
        return tool_response(
            success=False,
            error=f"Không được phép cập nhật trường '{field}'.",
        )

    USER_PROFILES[user_id][field] = value

    return tool_response(
        success=True,
        data={
            "user_id": user_id,
            "updated_field": field,
            "new_value": value,
        },
    )


def extract_preferences(description: str) -> str:
    """
    Trích xuất tiêu chí ghép đôi từ mô tả tự nhiên.

    Đây là phiên bản rule-based đơn giản. Trong hệ thống thật,
    có thể sử dụng LLM để tạo structured output.

    Args:
        description: Mô tả của người dùng.

    Returns:
        Các tiêu chí được trích xuất.
    """
    text = description.lower()

    interests = []
    known_interests = [
        "đọc sách",
        "du lịch",
        "công nghệ",
        "thể thao",
        "âm nhạc",
        "cà phê",
        "nhiếp ảnh",
        "nấu ăn",
    ]

    for interest in known_interests:
        if interest in text:
            interests.append(interest)

    relationship_goal = None

    if "nghiêm túc" in text or "lâu dài" in text:
        relationship_goal = "nghiêm túc"
    elif "kết bạn" in text:
        relationship_goal = "kết bạn"

    return tool_response(
        success=True,
        data={
            "interests": interests,
            "relationship_goal": relationship_goal,
            "original_description": description,
        },
    )


# =========================================================
# MATCHING TOOLS
# =========================================================

def check_dealbreakers(
    source_user_id: str,
    candidate_user_id: str,
) -> str:
    """
    Kiểm tra các tiêu chí không thể chấp nhận giữa hai hồ sơ.

    Args:
        source_user_id: Người đang tìm kiếm.
        candidate_user_id: Ứng viên được đánh giá.

    Returns:
        Kết quả kiểm tra dealbreaker.
    """
    source = USER_PROFILES.get(source_user_id)
    candidate = USER_PROFILES.get(candidate_user_id)

    if source is None or candidate is None:
        return tool_response(
            success=False,
            error="Không tìm thấy một trong hai hồ sơ.",
        )

    violations = []

    source_dealbreakers = source.get("dealbreakers", [])
    candidate_traits = candidate.get("traits", [])

    for dealbreaker in source_dealbreakers:
        if dealbreaker in candidate_traits:
            violations.append(dealbreaker)

    return tool_response(
        success=True,
        data={
            "passed": len(violations) == 0,
            "violations": violations,
        },
    )


def calculate_compatibility(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """
    Tính điểm tương thích giữa hai người dùng.

    Công thức minh họa:
    - Sở thích chung: 40 điểm
    - Mục tiêu quan hệ: 25 điểm
    - Thành phố phù hợp: 20 điểm
    - Độ tuổi phù hợp: 15 điểm

    Args:
        user_a_id: Mã người dùng thứ nhất.
        user_b_id: Mã người dùng thứ hai.

    Returns:
        Tổng điểm và điểm theo từng tiêu chí.
    """
    user_a = USER_PROFILES.get(user_a_id)
    user_b = USER_PROFILES.get(user_b_id)

    if user_a is None or user_b is None:
        return tool_response(
            success=False,
            error="Không tìm thấy một trong hai hồ sơ.",
        )

    # 1. Điểm sở thích
    interests_a = set(user_a.get("interests", []))
    interests_b = set(user_b.get("interests", []))
    common_interests = interests_a.intersection(interests_b)
    all_interests = interests_a.union(interests_b)

    interest_ratio = (
        len(common_interests) / len(all_interests)
        if all_interests
        else 0
    )
    interest_score = round(interest_ratio * 40, 2)

    # 2. Mục tiêu mối quan hệ
    same_goal = (
        user_a.get("relationship_goal")
        == user_b.get("relationship_goal")
    )
    goal_score = 25 if same_goal else 0

    # 3. Vị trí
    location_score = 0

    if user_a.get("city") == user_b.get("city"):
        location_score = 20
    elif user_b.get("city") in user_a.get("preferred_city", []):
        location_score = 15

    # 4. Độ tuổi
    age_score = 0

    preferred_age_a = user_a.get("preferred_age_range", [])
    preferred_age_b = user_b.get("preferred_age_range", [])

    b_matches_a = (
        len(preferred_age_a) == 2
        and preferred_age_a[0] <= user_b["age"] <= preferred_age_a[1]
    )

    a_matches_b = (
        len(preferred_age_b) == 2
        and preferred_age_b[0] <= user_a["age"] <= preferred_age_b[1]
    )

    if b_matches_a and a_matches_b:
        age_score = 15
    elif b_matches_a or a_matches_b:
        age_score = 7.5

    total_score = round(
        interest_score
        + goal_score
        + location_score
        + age_score,
        2,
    )

    return tool_response(
        success=True,
        data={
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "total_score": total_score,
            "maximum_score": 100,
            "score_breakdown": {
                "shared_interests": interest_score,
                "relationship_goal": goal_score,
                "location": location_score,
                "age_preference": age_score,
            },
            "common_interests": sorted(common_interests),
        },
    )


def search_candidates(
    user_id: str,
    minimum_score: float = 50,
    limit: int = 5,
) -> str:
    """
    Tìm các ứng viên có điểm tương thích cao nhất.

    Args:
        user_id: Người dùng cần tìm ứng viên.
        minimum_score: Điểm tương thích tối thiểu.
        limit: Số ứng viên tối đa.

    Returns:
        Danh sách ứng viên được sắp xếp theo điểm giảm dần.
    """
    if user_id not in USER_PROFILES:
        return tool_response(
            success=False,
            error=f"Không tìm thấy người dùng '{user_id}'.",
        )

    candidates = []

    for candidate_id in USER_PROFILES:
        if candidate_id == user_id:
            continue

        raw_result = calculate_compatibility(
            user_a_id=user_id,
            user_b_id=candidate_id,
        )
        result = json.loads(raw_result)

        if not result["success"]:
            continue

        score = result["data"]["total_score"]

        if score >= minimum_score:
            candidate_profile = USER_PROFILES[candidate_id]

            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "display_name": candidate_profile["name"],
                    "city": candidate_profile["city"],
                    "compatibility_score": score,
                    "common_interests": result["data"][
                        "common_interests"
                    ],
                }
            )

    candidates.sort(
        key=lambda item: item["compatibility_score"],
        reverse=True,
    )

    return tool_response(
        success=True,
        data={
            "user_id": user_id,
            "candidate_count": len(candidates[:limit]),
            "candidates": candidates[:limit],
        },
    )


def explain_compatibility(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """
    Tạo dữ liệu giải thích mức độ tương thích.

    Tool chỉ trả về các bằng chứng có cấu trúc.
    Agent sử dụng dữ liệu này để tạo câu trả lời tự nhiên.

    Args:
        user_a_id: Người dùng thứ nhất.
        user_b_id: Người dùng thứ hai.

    Returns:
        Điểm mạnh, khác biệt và khuyến nghị.
    """
    raw_result = calculate_compatibility(user_a_id, user_b_id)
    result = json.loads(raw_result)

    if not result["success"]:
        return raw_result

    data = result["data"]
    breakdown = data["score_breakdown"]

    strengths = []
    differences = []

    if breakdown["shared_interests"] >= 20:
        strengths.append(
            "Hai người có nhiều sở thích chung."
        )
    elif data["common_interests"]:
        strengths.append(
            "Hai người có một số chủ đề chung để bắt đầu trò chuyện."
        )
    else:
        differences.append(
            "Hai người hiện chưa có nhiều sở thích được ghi nhận giống nhau."
        )

    if breakdown["relationship_goal"] == 25:
        strengths.append(
            "Hai người có cùng mục tiêu về mối quan hệ."
        )
    else:
        differences.append(
            "Mục tiêu mối quan hệ hiện tại chưa hoàn toàn giống nhau."
        )

    if breakdown["location"] == 20:
        strengths.append(
            "Hai người đang sống cùng thành phố."
        )
    elif breakdown["location"] > 0:
        strengths.append(
            "Địa điểm của ứng viên nằm trong khu vực được ưu tiên."
        )
    else:
        differences.append(
            "Khoảng cách địa lý có thể là một yếu tố cần cân nhắc."
        )

    return tool_response(
        success=True,
        data={
            "compatibility_score": data["total_score"],
            "strengths": strengths,
            "differences": differences,
            "common_interests": data["common_interests"],
            "recommendation": (
                "Có thể bắt đầu bằng một cuộc trò chuyện ngắn."
                if data["total_score"] >= 60
                else "Nên tìm hiểu thêm trước khi đưa ra quyết định."
            ),
        },
    )


# =========================================================
# INTERACTION TOOLS
# =========================================================

def check_mutual_interest(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """
    Kiểm tra hai bên đã đồng ý kết nối hay chưa.

    Trong phiên bản thật, dữ liệu này phải được lấy từ database
    và không được suy đoán bởi LLM.
    """
    # Mock data
    interest_data = {
        ("U001", "U002"): {
            "user_a_interested": True,
            "user_b_interested": True,
        }
    }

    result = interest_data.get(
        (user_a_id, user_b_id),
        {
            "user_a_interested": False,
            "user_b_interested": False,
        },
    )

    return tool_response(
        success=True,
        data={
            **result,
            "mutual_match": (
                result["user_a_interested"]
                and result["user_b_interested"]
            ),
        },
    )


def generate_icebreaker(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """
    Tạo dữ liệu cho câu mở đầu dựa trên sở thích chung.

    Args:
        user_a_id: Người gửi lời chào.
        user_b_id: Người nhận lời chào.

    Returns:
        Các gợi ý bắt đầu cuộc trò chuyện.
    """
    match_result = json.loads(
        calculate_compatibility(user_a_id, user_b_id)
    )

    if not match_result["success"]:
        return tool_response(
            success=False,
            error="Không thể phân tích hai hồ sơ.",
        )

    common_interests = match_result["data"]["common_interests"]

    if not common_interests:
        suggestions = [
            "Cuối tuần bạn thường thích làm gì?",
            "Gần đây bạn có trải nghiệm nào thú vị không?",
        ]
    else:
        topic = common_interests[0]
        suggestions = [
            f"Mình thấy chúng ta đều thích {topic}. "
            f"Bạn bắt đầu quan tâm đến sở thích này từ khi nào?",
            f"Nếu chọn một trải nghiệm liên quan đến {topic}, "
            f"bạn muốn thử điều gì nhất?",
        ]

    return tool_response(
        success=True,
        data={
            "common_interests": common_interests,
            "suggestions": suggestions,
        },
    )


def moderate_message(message: str) -> str:
    """
    Kiểm tra an toàn cơ bản cho tin nhắn.

    Args:
        message: Nội dung cần kiểm tra.

    Returns:
        Kết quả cho phép, cảnh báo hoặc chặn.
    """
    text = message.lower()

    blocked_patterns = [
        "gửi địa chỉ nhà",
        "gửi mật khẩu",
        "chuyển tiền cho tôi",
        "gửi mã otp",
        "đe dọa",
    ]

    detected = [
        pattern
        for pattern in blocked_patterns
        if pattern in text
    ]

    if detected:
        return tool_response(
            success=True,
            data={
                "allowed": False,
                "risk_level": "high",
                "detected_patterns": detected,
                "action": "block",
            },
        )

    return tool_response(
        success=True,
        data={
            "allowed": True,
            "risk_level": "low",
            "detected_patterns": [],
            "action": "allow",
        },
    )


def record_match_feedback(
    user_id: str,
    candidate_id: str,
    rating: int,
    feedback: str = "",
) -> str:
    """
    Lưu đánh giá của người dùng về một ứng viên.

    Args:
        user_id: Người đưa ra đánh giá.
        candidate_id: Ứng viên được đánh giá.
        rating: Điểm từ 1 đến 5.
        feedback: Nhận xét bổ sung.

    Returns:
        Kết quả lưu feedback.
    """
    if rating < 1 or rating > 5:
        return tool_response(
            success=False,
            error="Rating phải nằm trong khoảng từ 1 đến 5.",
        )

    feedback_record = {
        "user_id": user_id,
        "candidate_id": candidate_id,
        "rating": rating,
        "feedback": feedback,
    }

    MATCH_FEEDBACK.append(feedback_record)

    return tool_response(
        success=True,
        data={
            "saved": True,
            "feedback_record": feedback_record,
        },
    )


# =========================================================
# DATE PLANNING TOOLS
# =========================================================

def suggest_date_ideas(
    city: str,
    interests: list[str],
    budget_level: str = "trung bình",
) -> str:
    """
    Đề xuất hoạt động gặp mặt tại một thành phố.

    Args:
        city: Thành phố tổ chức cuộc gặp.
        interests: Sở thích chung.
        budget_level: thấp, trung bình hoặc cao.

    Returns:
        Danh sách hoạt động đề xuất.
    """
    ideas = []

    if "cà phê" in interests:
        ideas.append(
            {
                "activity": "Gặp tại một quán cà phê yên tĩnh",
                "city": city,
                "budget_level": "thấp",
            }
        )

    if "đọc sách" in interests:
        ideas.append(
            {
                "activity": "Tham quan hiệu sách hoặc phố sách",
                "city": city,
                "budget_level": "thấp",
            }
        )

    if "nhiếp ảnh" in interests:
        ideas.append(
            {
                "activity": "Đi bộ và chụp ảnh tại khu vực trung tâm",
                "city": city,
                "budget_level": "thấp",
            }
        )

    if "du lịch" in interests:
        ideas.append(
            {
                "activity": "Tham quan một địa điểm văn hóa trong thành phố",
                "city": city,
                "budget_level": "trung bình",
            }
        )

    if not ideas:
        ideas.append(
            {
                "activity": "Gặp tại không gian công cộng đông người",
                "city": city,
                "budget_level": budget_level,
            }
        )

    return tool_response(
        success=True,
        data={
            "city": city,
            "ideas": ideas,
            "safety_note": (
                "Lần gặp đầu tiên nên diễn ra tại địa điểm công cộng."
            ),
        },
    )


def get_weather(location: str) -> str:
    """
    Tra cứu thời tiết hiện tại của một thành phố.
    """
    loc_lower = location.lower()

    if "hà nội" in loc_lower or "ha noi" in loc_lower:
        weather = {
            "temperature": "28°C",
            "condition": "Nắng nhẹ",
            "outdoor_suitable": True,
        }
    elif (
        "hồ chí minh" in loc_lower
        or "tp.hcm" in loc_lower
        or "hcm" in loc_lower
    ):
        weather = {
            "temperature": "33°C",
            "condition": "Nắng nóng, có mây",
            "outdoor_suitable": False,
        }
    elif "đà nẵng" in loc_lower or "da nang" in loc_lower:
        weather = {
            "temperature": "30°C",
            "condition": "Gió nhẹ",
            "outdoor_suitable": True,
        }
    else:
        return tool_response(
            success=False,
            error=f"Không có dữ liệu cho '{location}'.",
        )

    return tool_response(
        success=True,
        data={
            "location": location,
            **weather,
        },
    )


# =========================================================
# TOOL REGISTRY
# =========================================================

AVAILABLE_TOOLS = {
    # Profile
    "get_user_profile": get_user_profile,
    "update_user_profile": update_user_profile,
    "extract_preferences": extract_preferences,

    # Matching
    "search_candidates": search_candidates,
    "calculate_compatibility": calculate_compatibility,
    "explain_compatibility": explain_compatibility,
    "check_dealbreakers": check_dealbreakers,

    # Interaction
    "check_mutual_interest": check_mutual_interest,
    "generate_icebreaker": generate_icebreaker,
    "moderate_message": moderate_message,
    "record_match_feedback": record_match_feedback,

    # Date planning
    "suggest_date_ideas": suggest_date_ideas,
    "get_weather": get_weather,
}