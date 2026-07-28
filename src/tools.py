"""Các tool an toàn và dữ liệu giả lập dành cho Cupid ReAct Agent.

Mọi tool được đăng ký trong ``AVAILABLE_TOOLS`` đều trả về chuỗi JSON theo
schema thống nhất::

    {
        "success": bool,
        "data": object | null,
        "error": str | null
    }

Các lỗi đầu vào dự kiến được kiểm tra trực tiếp. Mọi exception không lường
trước được chặn bởi ``safe_tool`` để Agent nhận được thông báo lỗi thay vì
làm dừng chương trình.

Dữ liệu trong module chỉ phục vụ demo/prototype, được lưu trong bộ nhớ và
không phải dữ liệu thời gian thực.
"""

from __future__ import annotations

import json
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


# =========================================================
# MOCK DATABASE
# =========================================================

USER_PROFILES: dict[str, dict[str, Any]] = {
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
}

MATCH_FEEDBACK: list[dict[str, Any]] = []


# =========================================================
# ERROR-HANDLING HELPERS
# =========================================================

def tool_response(
    success: bool,
    data: Any = None,
    error: str | None = None,
) -> str:
    """Tạo chuỗi JSON phản hồi thống nhất và không làm crash chương trình.

    Args:
        success: Trạng thái thực thi của tool.
        data: Dữ liệu trả về khi tool thành công.
        error: Thông báo lỗi khi tool thất bại.

    Returns:
        Chuỗi JSON luôn chứa ``success``, ``data`` và ``error``.

    Notes:
        ``default=str`` chuyển các object không hỗ trợ JSON sang chuỗi. Nếu
        vẫn gặp lỗi, ví dụ dữ liệu chứa tham chiếu vòng, hàm trả về một phản
        hồi lỗi tối giản chỉ gồm các kiểu dữ liệu JSON an toàn.
    """
    try:
        if not isinstance(success, bool):
            return json.dumps(
                {
                    "success": False,
                    "data": None,
                    "error": "Tham số 'success' phải có kiểu bool.",
                },
                ensure_ascii=False,
            )

        if error is not None and not isinstance(error, str):
            error = str(error)

        return json.dumps(
            {
                "success": success,
                "data": data,
                "error": error,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        # Dữ liệu cố định bên dưới chỉ chứa primitive nên json.dumps không
        # thể thất bại trong điều kiện hoạt động Python bình thường.
        return json.dumps(
            {
                "success": False,
                "data": None,
                "error": (
                    "Không thể tạo phản hồi JSON: "
                    f"{type(exc).__name__}: {exc}"
                ),
            },
            ensure_ascii=False,
        )


def safe_tool(func: Callable[P, str]) -> Callable[P, str]:
    """Bọc tool để chuyển mọi exception chưa xử lý thành chuỗi JSON lỗi.

    Args:
        func: Hàm tool cần được bảo vệ.

    Returns:
        Hàm wrapper có cùng metadata, luôn trả về chuỗi JSON.

    Notes:
        Decorator là lớp bảo vệ cuối cùng. Các tool vẫn nên tự kiểm tra dữ
        liệu đầu vào để trả về thông báo cụ thể và dễ hiểu hơn.
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            result = func(*args, **kwargs)
            if not isinstance(result, str):
                return tool_response(
                    success=False,
                    error=(
                        f"Tool '{func.__name__}' trả về kiểu "
                        f"{type(result).__name__}, yêu cầu kiểu str."
                    ),
                )
            return result
        except Exception as exc:
            return tool_response(
                success=False,
                error=(
                    f"Lỗi khi thực thi tool '{func.__name__}': "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    return wrapper


def _validate_non_empty_string(value: Any, field_name: str) -> str | None:
    """Trả về thông báo lỗi nếu giá trị không phải chuỗi có nội dung."""
    if not isinstance(value, str):
        return f"'{field_name}' phải có kiểu str."
    if not value.strip():
        return f"'{field_name}' không được để trống."
    return None


def _validate_string_list(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = True,
) -> str | None:
    """Trả về thông báo lỗi nếu giá trị không phải danh sách chuỗi hợp lệ."""
    if not isinstance(value, list):
        return f"'{field_name}' phải là list[str]."
    if not allow_empty and not value:
        return f"'{field_name}' không được là danh sách rỗng."
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return f"Mọi phần tử trong '{field_name}' phải là chuỗi không rỗng."
    return None


def _parse_tool_response(raw_result: Any, source_tool: str) -> tuple[dict[str, Any] | None, str | None]:
    """Phân tích phản hồi nội bộ của một tool mà không để lỗi JSON lan ra."""
    if not isinstance(raw_result, str):
        return None, f"Tool '{source_tool}' không trả về chuỗi."

    try:
        parsed = json.loads(raw_result)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, (
            f"Phản hồi từ tool '{source_tool}' không phải JSON hợp lệ: "
            f"{type(exc).__name__}: {exc}"
        )

    if not isinstance(parsed, dict):
        return None, f"Phản hồi từ tool '{source_tool}' phải là JSON object."

    if not isinstance(parsed.get("success"), bool):
        return None, (
            f"Phản hồi từ tool '{source_tool}' thiếu trường 'success' kiểu bool."
        )

    return parsed, None


def _validate_matching_profile(
    profile: Any,
    user_id: str,
) -> str | None:
    """Kiểm tra các trường tối thiểu cần thiết để tính độ tương thích."""
    if not isinstance(profile, dict):
        return f"Hồ sơ '{user_id}' phải là dict."

    error = _validate_string_list(profile.get("interests"), "interests")
    if error:
        return f"Hồ sơ '{user_id}' không hợp lệ: {error}"

    error = _validate_non_empty_string(profile.get("city"), "city")
    if error:
        return f"Hồ sơ '{user_id}' không hợp lệ: {error}"

    error = _validate_string_list(profile.get("preferred_city"), "preferred_city")
    if error:
        return f"Hồ sơ '{user_id}' không hợp lệ: {error}"

    age = profile.get("age")
    if isinstance(age, bool) or not isinstance(age, (int, float)):
        return f"Hồ sơ '{user_id}' không hợp lệ: 'age' phải là số."
    if age < 0:
        return f"Hồ sơ '{user_id}' không hợp lệ: 'age' không được âm."

    age_range = profile.get("preferred_age_range")
    if not isinstance(age_range, (list, tuple)) or len(age_range) != 2:
        return (
            f"Hồ sơ '{user_id}' không hợp lệ: 'preferred_age_range' "
            "phải gồm đúng hai giá trị."
        )

    min_age, max_age = age_range
    if (
        isinstance(min_age, bool)
        or isinstance(max_age, bool)
        or not isinstance(min_age, (int, float))
        or not isinstance(max_age, (int, float))
    ):
        return (
            f"Hồ sơ '{user_id}' không hợp lệ: khoảng tuổi phải chứa các số."
        )
    if min_age < 0 or max_age < 0 or min_age > max_age:
        return (
            f"Hồ sơ '{user_id}' không hợp lệ: khoảng tuổi phải thỏa "
            "0 <= min_age <= max_age."
        )

    goal = profile.get("relationship_goal")
    if goal is not None and not isinstance(goal, str):
        return (
            f"Hồ sơ '{user_id}' không hợp lệ: "
            "'relationship_goal' phải là str hoặc None."
        )

    return None


# =========================================================
# PROFILE TOOLS
# =========================================================

@safe_tool
def get_user_profile(user_id: str) -> str:
    """Lấy hồ sơ ghép đôi của một người dùng."""
    error = _validate_non_empty_string(user_id, "user_id")
    if error:
        return tool_response(False, error=error)

    profile = USER_PROFILES.get(user_id.strip())
    if profile is None:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{user_id.strip()}'.",
        )

    if not isinstance(profile, dict):
        return tool_response(
            False,
            error=f"Dữ liệu hồ sơ '{user_id.strip()}' bị hỏng.",
        )

    return tool_response(
        True,
        data={
            "user_id": user_id.strip(),
            "profile": profile,
        },
    )


@safe_tool
def update_user_profile(
    user_id: str,
    field: str,
    value: Any,
) -> str:
    """Cập nhật một trường được phép trong hồ sơ người dùng."""
    error = _validate_non_empty_string(user_id, "user_id")
    if error:
        return tool_response(False, error=error)

    error = _validate_non_empty_string(field, "field")
    if error:
        return tool_response(False, error=error)

    normalized_user_id = user_id.strip()
    normalized_field = field.strip()

    if normalized_user_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_user_id}'.",
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

    if normalized_field not in allowed_fields:
        return tool_response(
            False,
            error=(
                f"Không được phép cập nhật trường '{normalized_field}'. "
                f"Các trường hợp lệ: {sorted(allowed_fields)}."
            ),
        )

    if normalized_field in {
        "interests",
        "personality",
        "preferred_city",
        "dealbreakers",
    }:
        error = _validate_string_list(value, normalized_field)
        if error:
            return tool_response(False, error=error)

    elif normalized_field in {"city", "relationship_goal"}:
        error = _validate_non_empty_string(value, normalized_field)
        if error:
            return tool_response(False, error=error)
        value = value.strip()

    elif normalized_field == "preferred_age_range":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return tool_response(
                False,
                error="'preferred_age_range' phải gồm đúng hai giá trị.",
            )
        min_age, max_age = value
        if (
            isinstance(min_age, bool)
            or isinstance(max_age, bool)
            or not isinstance(min_age, (int, float))
            or not isinstance(max_age, (int, float))
        ):
            return tool_response(
                False,
                error="'preferred_age_range' chỉ được chứa số.",
            )
        if min_age < 0 or max_age < 0 or min_age > max_age:
            return tool_response(
                False,
                error=(
                    "'preferred_age_range' phải thỏa "
                    "0 <= min_age <= max_age."
                ),
            )
        value = [min_age, max_age]

    USER_PROFILES[normalized_user_id][normalized_field] = value

    return tool_response(
        True,
        data={
            "user_id": normalized_user_id,
            "updated_field": normalized_field,
            "new_value": value,
        },
    )


@safe_tool
def extract_preferences(description: str) -> str:
    """Trích xuất sở thích và mục tiêu quan hệ bằng luật từ khóa."""
    error = _validate_non_empty_string(description, "description")
    if error:
        return tool_response(False, error=error)

    normalized_description = description.strip()
    text = normalized_description.lower()

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
    interests = [
        interest for interest in known_interests if interest in text
    ]

    relationship_goal = None
    if "nghiêm túc" in text or "lâu dài" in text:
        relationship_goal = "nghiêm túc"
    elif "kết bạn" in text:
        relationship_goal = "kết bạn"

    return tool_response(
        True,
        data={
            "interests": interests,
            "relationship_goal": relationship_goal,
            "original_description": normalized_description,
        },
    )


# =========================================================
# MATCHING TOOLS
# =========================================================

@safe_tool
def check_dealbreakers(
    source_user_id: str,
    candidate_user_id: str,
) -> str:
    """Kiểm tra tiêu chí loại trừ của người dùng đối với một ứng viên."""
    for field_name, value in (
        ("source_user_id", source_user_id),
        ("candidate_user_id", candidate_user_id),
    ):
        error = _validate_non_empty_string(value, field_name)
        if error:
            return tool_response(False, error=error)

    source_id = source_user_id.strip()
    candidate_id = candidate_user_id.strip()

    source = USER_PROFILES.get(source_id)
    candidate = USER_PROFILES.get(candidate_id)

    if source is None:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng nguồn '{source_id}'.",
        )
    if candidate is None:
        return tool_response(
            False,
            error=f"Không tìm thấy ứng viên '{candidate_id}'.",
        )
    if not isinstance(source, dict) or not isinstance(candidate, dict):
        return tool_response(False, error="Một trong hai hồ sơ bị hỏng.")

    source_dealbreakers = source.get("dealbreakers", [])
    candidate_traits = candidate.get("traits", [])

    error = _validate_string_list(source_dealbreakers, "dealbreakers")
    if error:
        return tool_response(
            False,
            error=f"Hồ sơ '{source_id}' không hợp lệ: {error}",
        )

    error = _validate_string_list(candidate_traits, "traits")
    if error:
        return tool_response(
            False,
            error=f"Hồ sơ '{candidate_id}' không hợp lệ: {error}",
        )

    candidate_trait_set = {trait.casefold() for trait in candidate_traits}
    violations = [
        dealbreaker
        for dealbreaker in source_dealbreakers
        if dealbreaker.casefold() in candidate_trait_set
    ]

    return tool_response(
        True,
        data={
            "passed": len(violations) == 0,
            "violations": violations,
        },
    )


@safe_tool
def calculate_compatibility(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """Tính điểm tương thích giữa hai hồ sơ người dùng."""
    for field_name, value in (
        ("user_a_id", user_a_id),
        ("user_b_id", user_b_id),
    ):
        error = _validate_non_empty_string(value, field_name)
        if error:
            return tool_response(False, error=error)

    normalized_a_id = user_a_id.strip()
    normalized_b_id = user_b_id.strip()

    if normalized_a_id == normalized_b_id:
        return tool_response(
            False,
            error="Không thể tính độ tương thích của một người với chính họ.",
        )

    user_a = USER_PROFILES.get(normalized_a_id)
    user_b = USER_PROFILES.get(normalized_b_id)

    if user_a is None:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_a_id}'.",
        )
    if user_b is None:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_b_id}'.",
        )

    profile_error = _validate_matching_profile(user_a, normalized_a_id)
    if profile_error:
        return tool_response(False, error=profile_error)

    profile_error = _validate_matching_profile(user_b, normalized_b_id)
    if profile_error:
        return tool_response(False, error=profile_error)

    interests_a = set(user_a["interests"])
    interests_b = set(user_b["interests"])
    common_interests = interests_a.intersection(interests_b)
    all_interests = interests_a.union(interests_b)

    interest_ratio = (
        len(common_interests) / len(all_interests)
        if all_interests
        else 0.0
    )
    interest_score = round(interest_ratio * 40, 2)

    same_goal = (
        user_a.get("relationship_goal")
        == user_b.get("relationship_goal")
        and user_a.get("relationship_goal") is not None
    )
    goal_score = 25 if same_goal else 0

    location_score = 0
    if user_a["city"] == user_b["city"]:
        location_score = 20
    elif user_b["city"] in user_a["preferred_city"]:
        location_score = 15

    preferred_age_a = user_a["preferred_age_range"]
    preferred_age_b = user_b["preferred_age_range"]

    b_matches_a = (
        preferred_age_a[0] <= user_b["age"] <= preferred_age_a[1]
    )
    a_matches_b = (
        preferred_age_b[0] <= user_a["age"] <= preferred_age_b[1]
    )

    if b_matches_a and a_matches_b:
        age_score = 15
    elif b_matches_a or a_matches_b:
        age_score = 7.5
    else:
        age_score = 0

    total_score = round(
        interest_score + goal_score + location_score + age_score,
        2,
    )

    return tool_response(
        True,
        data={
            "user_a_id": normalized_a_id,
            "user_b_id": normalized_b_id,
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


@safe_tool
def search_candidates(
    user_id: str,
    minimum_score: float = 50,
    limit: int = 5,
) -> str:
    """Tìm và xếp hạng ứng viên theo điểm tương thích."""
    error = _validate_non_empty_string(user_id, "user_id")
    if error:
        return tool_response(False, error=error)

    if (
        isinstance(minimum_score, bool)
        or not isinstance(minimum_score, (int, float))
    ):
        return tool_response(
            False,
            error="'minimum_score' phải là số từ 0 đến 100.",
        )
    if not 0 <= minimum_score <= 100:
        return tool_response(
            False,
            error="'minimum_score' phải nằm trong khoảng 0–100.",
        )

    if isinstance(limit, bool) or not isinstance(limit, int):
        return tool_response(
            False,
            error="'limit' phải là số nguyên dương.",
        )
    if limit <= 0:
        return tool_response(
            False,
            error="'limit' phải lớn hơn 0.",
        )

    normalized_user_id = user_id.strip()
    if normalized_user_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_user_id}'.",
        )

    candidates: list[dict[str, Any]] = []
    skipped_candidates: list[dict[str, str]] = []

    # Duyệt trên snapshot để tránh RuntimeError nếu dictionary bị thay đổi
    # đồng thời bởi luồng khác.
    for candidate_id, candidate_profile in list(USER_PROFILES.items()):
        if candidate_id == normalized_user_id:
            continue

        raw_result = calculate_compatibility(
            user_a_id=normalized_user_id,
            user_b_id=candidate_id,
        )
        result, parse_error = _parse_tool_response(
            raw_result,
            "calculate_compatibility",
        )

        if parse_error:
            skipped_candidates.append(
                {"candidate_id": candidate_id, "reason": parse_error}
            )
            continue

        if result is None or not result["success"]:
            skipped_candidates.append(
                {
                    "candidate_id": candidate_id,
                    "reason": str(
                        (result or {}).get("error")
                        or "Không thể tính điểm tương thích."
                    ),
                }
            )
            continue

        data = result.get("data")
        if not isinstance(data, dict):
            skipped_candidates.append(
                {
                    "candidate_id": candidate_id,
                    "reason": "Kết quả tính điểm thiếu trường data hợp lệ.",
                }
            )
            continue

        score = data.get("total_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            skipped_candidates.append(
                {
                    "candidate_id": candidate_id,
                    "reason": "Điểm tương thích không phải là số.",
                }
            )
            continue

        if score >= minimum_score:
            if not isinstance(candidate_profile, dict):
                skipped_candidates.append(
                    {
                        "candidate_id": candidate_id,
                        "reason": "Hồ sơ ứng viên bị hỏng.",
                    }
                )
                continue

            display_name = candidate_profile.get("name")
            city = candidate_profile.get("city")
            common_interests = data.get("common_interests", [])

            if not isinstance(display_name, str) or not display_name.strip():
                display_name = candidate_id
            if not isinstance(city, str):
                city = "Không xác định"
            if not isinstance(common_interests, list):
                common_interests = []

            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "display_name": display_name,
                    "city": city,
                    "compatibility_score": score,
                    "common_interests": common_interests,
                }
            )

    candidates.sort(
        key=lambda item: item["compatibility_score"],
        reverse=True,
    )
    selected_candidates = candidates[:limit]

    return tool_response(
        True,
        data={
            "user_id": normalized_user_id,
            "candidate_count": len(selected_candidates),
            "candidates": selected_candidates,
            "skipped_candidates": skipped_candidates,
        },
    )


@safe_tool
def explain_compatibility(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """Giải thích điểm mạnh và khác biệt giữa hai hồ sơ."""
    raw_result = calculate_compatibility(user_a_id, user_b_id)
    result, parse_error = _parse_tool_response(
        raw_result,
        "calculate_compatibility",
    )

    if parse_error:
        return tool_response(False, error=parse_error)
    if result is None:
        return tool_response(False, error="Không nhận được kết quả tính điểm.")
    if not result["success"]:
        return tool_response(
            False,
            error=str(result.get("error") or "Không thể tính độ tương thích."),
        )

    data = result.get("data")
    if not isinstance(data, dict):
        return tool_response(
            False,
            error="Kết quả tính điểm thiếu trường 'data' hợp lệ.",
        )

    breakdown = data.get("score_breakdown")
    common_interests = data.get("common_interests")
    total_score = data.get("total_score")

    if not isinstance(breakdown, dict):
        return tool_response(
            False,
            error="Kết quả tính điểm thiếu 'score_breakdown'.",
        )
    if not isinstance(common_interests, list):
        return tool_response(
            False,
            error="Kết quả tính điểm có 'common_interests' không hợp lệ.",
        )
    if isinstance(total_score, bool) or not isinstance(
        total_score,
        (int, float),
    ):
        return tool_response(
            False,
            error="Kết quả tính điểm có 'total_score' không hợp lệ.",
        )

    shared_score = breakdown.get("shared_interests")
    goal_score = breakdown.get("relationship_goal")
    location_score = breakdown.get("location")

    for field_name, value in (
        ("shared_interests", shared_score),
        ("relationship_goal", goal_score),
        ("location", location_score),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return tool_response(
                False,
                error=f"Điểm thành phần '{field_name}' không hợp lệ.",
            )

    strengths: list[str] = []
    differences: list[str] = []

    if shared_score >= 20:
        strengths.append("Hai người có nhiều sở thích chung.")
    elif common_interests:
        strengths.append(
            "Hai người có một số chủ đề chung để bắt đầu trò chuyện."
        )
    else:
        differences.append(
            "Hai người hiện chưa có nhiều sở thích được ghi nhận giống nhau."
        )

    if goal_score == 25:
        strengths.append("Hai người có cùng mục tiêu về mối quan hệ.")
    else:
        differences.append(
            "Mục tiêu mối quan hệ hiện tại chưa hoàn toàn giống nhau."
        )

    if location_score == 20:
        strengths.append("Hai người đang sống cùng thành phố.")
    elif location_score > 0:
        strengths.append(
            "Địa điểm của ứng viên nằm trong khu vực được ưu tiên."
        )
    else:
        differences.append(
            "Khoảng cách địa lý có thể là một yếu tố cần cân nhắc."
        )

    return tool_response(
        True,
        data={
            "compatibility_score": total_score,
            "strengths": strengths,
            "differences": differences,
            "common_interests": common_interests,
            "recommendation": (
                "Có thể bắt đầu bằng một cuộc trò chuyện ngắn."
                if total_score >= 60
                else "Nên tìm hiểu thêm trước khi đưa ra quyết định."
            ),
        },
    )


# =========================================================
# INTERACTION TOOLS
# =========================================================

@safe_tool
def check_mutual_interest(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """Kiểm tra hai người dùng có cùng đồng ý kết nối hay không."""
    for field_name, value in (
        ("user_a_id", user_a_id),
        ("user_b_id", user_b_id),
    ):
        error = _validate_non_empty_string(value, field_name)
        if error:
            return tool_response(False, error=error)

    normalized_a_id = user_a_id.strip()
    normalized_b_id = user_b_id.strip()

    if normalized_a_id == normalized_b_id:
        return tool_response(
            False,
            error="Không thể kiểm tra kết nối của một người với chính họ.",
        )
    if normalized_a_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_a_id}'.",
        )
    if normalized_b_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_b_id}'.",
        )

    interest_data = {
        ("U001", "U002"): {
            "user_a_interested": True,
            "user_b_interested": True,
        }
    }

    result = interest_data.get(
        (normalized_a_id, normalized_b_id),
        {
            "user_a_interested": False,
            "user_b_interested": False,
        },
    )

    if not isinstance(result, dict):
        return tool_response(False, error="Dữ liệu đồng thuận bị hỏng.")

    a_interested = result.get("user_a_interested")
    b_interested = result.get("user_b_interested")

    if not isinstance(a_interested, bool) or not isinstance(
        b_interested,
        bool,
    ):
        return tool_response(
            False,
            error="Trạng thái đồng thuận phải có kiểu bool.",
        )

    return tool_response(
        True,
        data={
            "user_a_interested": a_interested,
            "user_b_interested": b_interested,
            "mutual_match": a_interested and b_interested,
        },
    )


@safe_tool
def generate_icebreaker(
    user_a_id: str,
    user_b_id: str,
) -> str:
    """Tạo gợi ý mở đầu dựa trên sở thích chung."""
    raw_result = calculate_compatibility(user_a_id, user_b_id)
    match_result, parse_error = _parse_tool_response(
        raw_result,
        "calculate_compatibility",
    )

    if parse_error:
        return tool_response(False, error=parse_error)
    if match_result is None:
        return tool_response(False, error="Không nhận được kết quả phân tích.")
    if not match_result["success"]:
        return tool_response(
            False,
            error=str(
                match_result.get("error")
                or "Không thể phân tích hai hồ sơ."
            ),
        )

    data = match_result.get("data")
    if not isinstance(data, dict):
        return tool_response(
            False,
            error="Kết quả phân tích thiếu trường 'data' hợp lệ.",
        )

    common_interests = data.get("common_interests")
    if not isinstance(common_interests, list) or any(
        not isinstance(item, str) for item in common_interests
    ):
        return tool_response(
            False,
            error="Danh sách sở thích chung không hợp lệ.",
        )

    if not common_interests:
        suggestions = [
            "Cuối tuần bạn thường thích làm gì?",
            "Gần đây bạn có trải nghiệm nào thú vị không?",
        ]
    else:
        topic = common_interests[0]
        suggestions = [
            (
                f"Mình thấy chúng ta đều thích {topic}. "
                "Bạn bắt đầu quan tâm đến sở thích này từ khi nào?"
            ),
            (
                f"Nếu chọn một trải nghiệm liên quan đến {topic}, "
                "bạn muốn thử điều gì nhất?"
            ),
        ]

    return tool_response(
        True,
        data={
            "common_interests": common_interests,
            "suggestions": suggestions,
        },
    )


@safe_tool
def moderate_message(message: str) -> str:
    """Kiểm tra an toàn cơ bản cho tin nhắn bằng luật từ khóa."""
    error = _validate_non_empty_string(message, "message")
    if error:
        return tool_response(False, error=error)

    normalized_message = message.strip()
    if len(normalized_message) > 5000:
        return tool_response(
            False,
            error="'message' không được dài quá 5000 ký tự.",
        )

    text = normalized_message.lower()
    blocked_patterns = [
        "gửi địa chỉ nhà",
        "gửi mật khẩu",
        "chuyển tiền cho tôi",
        "gửi mã otp",
        "đe dọa",
    ]

    detected = [
        pattern for pattern in blocked_patterns if pattern in text
    ]

    if detected:
        return tool_response(
            True,
            data={
                "allowed": False,
                "risk_level": "high",
                "detected_patterns": detected,
                "action": "block",
            },
        )

    return tool_response(
        True,
        data={
            "allowed": True,
            "risk_level": "low",
            "detected_patterns": [],
            "action": "allow",
        },
    )


@safe_tool
def record_match_feedback(
    user_id: str,
    candidate_id: str,
    rating: int,
    feedback: str = "",
) -> str:
    """Kiểm tra và lưu đánh giá của người dùng về một ứng viên."""
    for field_name, value in (
        ("user_id", user_id),
        ("candidate_id", candidate_id),
    ):
        error = _validate_non_empty_string(value, field_name)
        if error:
            return tool_response(False, error=error)

    normalized_user_id = user_id.strip()
    normalized_candidate_id = candidate_id.strip()

    if normalized_user_id == normalized_candidate_id:
        return tool_response(
            False,
            error="Người dùng không thể tự đánh giá chính mình.",
        )
    if normalized_user_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy người dùng '{normalized_user_id}'.",
        )
    if normalized_candidate_id not in USER_PROFILES:
        return tool_response(
            False,
            error=f"Không tìm thấy ứng viên '{normalized_candidate_id}'.",
        )

    if isinstance(rating, bool) or not isinstance(rating, int):
        return tool_response(
            False,
            error="'rating' phải là số nguyên từ 1 đến 5.",
        )
    if not 1 <= rating <= 5:
        return tool_response(
            False,
            error="'rating' phải nằm trong khoảng từ 1 đến 5.",
        )

    if not isinstance(feedback, str):
        return tool_response(False, error="'feedback' phải có kiểu str.")
    if len(feedback) > 2000:
        return tool_response(
            False,
            error="'feedback' không được dài quá 2000 ký tự.",
        )

    feedback_record = {
        "user_id": normalized_user_id,
        "candidate_id": normalized_candidate_id,
        "rating": rating,
        "feedback": feedback.strip(),
    }
    MATCH_FEEDBACK.append(feedback_record)

    return tool_response(
        True,
        data={
            "saved": True,
            "feedback_record": feedback_record,
        },
    )


# =========================================================
# DATE PLANNING TOOLS
# =========================================================

@safe_tool
def suggest_date_ideas(
    city: str,
    interests: list[str],
    budget_level: str = "trung bình",
) -> str:
    """Đề xuất hoạt động gặp mặt theo thành phố và sở thích."""
    error = _validate_non_empty_string(city, "city")
    if error:
        return tool_response(False, error=error)

    error = _validate_string_list(interests, "interests")
    if error:
        return tool_response(False, error=error)

    error = _validate_non_empty_string(budget_level, "budget_level")
    if error:
        return tool_response(False, error=error)

    normalized_city = city.strip()
    normalized_interests = {
        interest.strip().casefold() for interest in interests
    }
    normalized_budget = budget_level.strip().casefold()
    allowed_budgets = {"thấp", "trung bình", "cao"}

    if normalized_budget not in allowed_budgets:
        return tool_response(
            False,
            error=(
                "'budget_level' phải là một trong các giá trị: "
                "'thấp', 'trung bình', 'cao'."
            ),
        )

    ideas: list[dict[str, str]] = []

    if "cà phê" in normalized_interests:
        ideas.append(
            {
                "activity": "Gặp tại một quán cà phê yên tĩnh",
                "city": normalized_city,
                "budget_level": "thấp",
            }
        )

    if "đọc sách" in normalized_interests:
        ideas.append(
            {
                "activity": "Tham quan hiệu sách hoặc phố sách",
                "city": normalized_city,
                "budget_level": "thấp",
            }
        )

    if "nhiếp ảnh" in normalized_interests:
        ideas.append(
            {
                "activity": "Đi bộ và chụp ảnh tại khu vực trung tâm",
                "city": normalized_city,
                "budget_level": "thấp",
            }
        )

    if "du lịch" in normalized_interests:
        ideas.append(
            {
                "activity": (
                    "Tham quan một địa điểm văn hóa trong thành phố"
                ),
                "city": normalized_city,
                "budget_level": "trung bình",
            }
        )

    if not ideas:
        ideas.append(
            {
                "activity": "Gặp tại không gian công cộng đông người",
                "city": normalized_city,
                "budget_level": normalized_budget,
            }
        )

    return tool_response(
        True,
        data={
            "city": normalized_city,
            "ideas": ideas,
            "safety_note": (
                "Lần gặp đầu tiên nên diễn ra tại địa điểm công cộng."
            ),
        },
    )


@safe_tool
def get_weather(location: str) -> str:
    """Tra cứu dữ liệu thời tiết giả lập cho thành phố được hỗ trợ."""
    error = _validate_non_empty_string(location, "location")
    if error:
        return tool_response(False, error=error)

    normalized_location = location.strip()
    loc_lower = normalized_location.lower()

    if "hà nội" in loc_lower or "ha noi" in loc_lower:
        weather = {
            "temperature": "28°C",
            "condition": "Nắng nhẹ",
            "outdoor_suitable": True,
        }
    elif (
        "hồ chí minh" in loc_lower
        or "ho chi minh" in loc_lower
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
            False,
            error=f"Không có dữ liệu cho '{normalized_location}'.",
        )

    return tool_response(
        True,
        data={
            "location": normalized_location,
            **weather,
        },
    )


# =========================================================
# TOOL REGISTRY
# =========================================================

AVAILABLE_TOOLS: dict[str, Callable[..., str]] = {
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
