"""Các tool và dữ liệu giả lập dành cho Cupid ReAct Agent.

Module cung cấp các hàm quản lý hồ sơ, tìm kiếm và phân tích độ tương thích,
kiểm tra tương tác, ghi nhận phản hồi và đề xuất hoạt động gặp mặt. Các tool
trả về chuỗi JSON theo cùng một schema để Agent có thể xử lý nhất quán.

Dữ liệu trong module hiện được lưu trong bộ nhớ và chỉ phục vụ demo/prototype;
chưa có kết nối cơ sở dữ liệu hoặc dịch vụ thời gian thực.
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
}

MATCH_FEEDBACK = []


def tool_response(
    success: bool,
    data: Any = None,
    error: str | None = None
) -> str:
    """Tạo phản hồi JSON thống nhất cho các tool của Cupid Agent.

        Hàm đóng gói trạng thái thực thi, dữ liệu kết quả và thông báo lỗi vào
        cùng một cấu trúc để ReAct Agent có thể xử lý nhất quán.

        Args:
            success: Cho biết tool thực thi thành công hay thất bại.
            data: Dữ liệu kết quả của tool. Mặc định là ``None``.
            error: Thông báo lỗi khi ``success`` là ``False``. Mặc định là ``None``.

        Returns:
            Chuỗi JSON gồm ba trường ``success``, ``data`` và ``error``.

        Raises:
            TypeError: Nếu ``data`` hoặc ``error`` chứa giá trị không thể tuần tự
                hóa bằng ``json.dumps``.
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
    """Lấy hồ sơ ghép đôi của một người dùng từ cơ sở dữ liệu giả lập.

        Args:
            user_id: Mã định danh duy nhất của người dùng, ví dụ ``"U001"``.

        Returns:
            Chuỗi JSON chuẩn hóa. Khi tìm thấy hồ sơ, trường ``data`` chứa
            ``user_id`` và ``profile``. Khi không tìm thấy, ``success`` là
            ``False`` và trường ``error`` chứa thông báo tương ứng.
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
    """Cập nhật một trường được phép trong hồ sơ người dùng.

        Args:
            user_id: Mã định danh của người dùng cần cập nhật.
            field: Tên trường hồ sơ cần thay đổi. Các trường hợp lệ gồm ``city``,
                ``interests``, ``personality``, ``relationship_goal``,
                ``preferred_age_range``, ``preferred_city`` và ``dealbreakers``.
            value: Giá trị mới được gán cho trường đã chọn.

        Returns:
            Chuỗi JSON chuẩn hóa chứa trường đã cập nhật và giá trị mới. Nếu
            ``user_id`` không tồn tại hoặc ``field`` không được phép, kết quả có
            ``success=False`` và mô tả lỗi trong trường ``error``.

        Notes:
            Hàm thay đổi trực tiếp dữ liệu trong biến toàn cục ``USER_PROFILES``.
            Dữ liệu chỉ tồn tại trong bộ nhớ và sẽ mất khi chương trình kết thúc.
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
    """Trích xuất tiêu chí ghép đôi từ mô tả ngôn ngữ tự nhiên.

        Hàm sử dụng luật so khớp từ khóa để nhận diện sở thích và mục tiêu quan hệ;
        đây không phải là mô hình NLP hoặc lời gọi LLM.

        Args:
            description: Đoạn mô tả tự nhiên chứa các sở thích hoặc mục tiêu quan hệ
                của người dùng.

        Returns:
            Chuỗi JSON chuẩn hóa. Trường ``data`` gồm danh sách ``interests``,
            ``relationship_goal`` được nhận diện và ``original_description``.
            Những thông tin không khớp danh sách từ khóa định sẵn sẽ không được
            trích xuất.
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
    """Kiểm tra tiêu chí loại trừ của người dùng đối với một ứng viên.

        Hàm đối chiếu danh sách ``dealbreakers`` của người tìm kiếm với trường
        ``traits`` của ứng viên.

        Args:
            source_user_id: Mã người dùng đang thực hiện tìm kiếm.
            candidate_user_id: Mã ứng viên cần được kiểm tra.

        Returns:
            Chuỗi JSON chuẩn hóa. Trường ``data.passed`` cho biết ứng viên có vượt
            qua bộ lọc hay không; ``data.violations`` liệt kê các tiêu chí vi phạm.
            Nếu một trong hai hồ sơ không tồn tại, kết quả trả về ``success=False``.

        Notes:
            Nếu hồ sơ ứng viên không có trường ``traits``, hàm coi danh sách đặc
            điểm là rỗng. Với dữ liệu mẫu hiện tại, điều này có thể khiến mọi ứng
            viên vượt qua kiểm tra dealbreaker.
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
    """Tính điểm tương thích giữa hai hồ sơ người dùng.

        Điểm tối đa là 100, gồm: sở thích chung 40 điểm, mục tiêu quan hệ 25 điểm,
        vị trí 20 điểm và độ tuổi 15 điểm. Điểm sở thích sử dụng tỷ lệ giao trên
        hợp của hai tập sở thích.

        Args:
            user_a_id: Mã định danh của người dùng thứ nhất.
            user_b_id: Mã định danh của người dùng thứ hai.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``total_score``, ``maximum_score``,
            ``score_breakdown`` và ``common_interests``. Nếu một hồ sơ không tồn
            tại, kết quả có ``success=False`` và thông báo trong ``error``.

        Notes:
            Điểm vị trí được tính theo góc nhìn của ``user_a_id``: ứng viên nhận
            15 điểm khi thành phố của người B nằm trong ``preferred_city`` của
            người A. Vì vậy kết quả có thể không hoàn toàn đối xứng khi đảo hai ID.
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
    """Tìm và xếp hạng các ứng viên theo điểm tương thích.

        Hàm duyệt các hồ sơ khác trong ``USER_PROFILES``, gọi
        ``calculate_compatibility`` và giữ lại những ứng viên đạt ngưỡng điểm.

        Args:
            user_id: Mã người dùng cần tìm ứng viên phù hợp.
            minimum_score: Điểm tương thích tối thiểu để một ứng viên được giữ lại.
                Mặc định là ``50``.
            limit: Số ứng viên tối đa được trả về. Mặc định là ``5``.

        Returns:
            Chuỗi JSON chuẩn hóa chứa số ứng viên và danh sách đã sắp xếp theo
            ``compatibility_score`` giảm dần. Nếu ``user_id`` không tồn tại,
            kết quả trả về ``success=False``.

        Notes:
            Hàm hiện chưa kiểm tra miền giá trị của ``minimum_score`` và ``limit``.
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
    """Tạo dữ liệu có cấu trúc để giải thích mức độ tương thích.

        Hàm chuyển kết quả chấm điểm thành các nhóm điểm mạnh, khác biệt, sở thích
        chung và khuyến nghị. ReAct Agent có thể dùng dữ liệu này để tạo câu trả
        lời tự nhiên nhưng không nên tự bịa thêm bằng chứng.

        Args:
            user_a_id: Mã định danh của người dùng thứ nhất.
            user_b_id: Mã định danh của người dùng thứ hai.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``compatibility_score``, ``strengths``,
            ``differences``, ``common_interests`` và ``recommendation``. Nếu bước
            tính điểm thất bại, hàm chuyển tiếp nguyên phản hồi lỗi.
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
    """Kiểm tra liệu hai người dùng có cùng đồng ý kết nối hay không.

        Args:
            user_a_id: Mã định danh của người dùng thứ nhất.
            user_b_id: Mã định danh của người dùng thứ hai.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``user_a_interested``,
            ``user_b_interested`` và ``mutual_match``.

        Notes:
            Dữ liệu hiện là mock data trong bộ nhớ và phép tra cứu phụ thuộc vào
            thứ tự cặp ID. Hệ thống thật phải lấy trạng thái đồng thuận từ cơ sở dữ
            liệu và không được để LLM tự suy đoán.
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
    """Tạo gợi ý mở đầu cuộc trò chuyện dựa trên sở thích chung.

        Args:
            user_a_id: Mã người dùng dự kiến gửi lời chào.
            user_b_id: Mã người dùng dự kiến nhận lời chào.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``common_interests`` và danh sách
            ``suggestions``. Nếu không thể phân tích hai hồ sơ, kết quả trả về
            ``success=False`` và thông báo lỗi.
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
    """Kiểm tra tin nhắn bằng bộ luật an toàn dựa trên từ khóa.

        Args:
            message: Nội dung tin nhắn cần kiểm tra trước khi gửi.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``allowed``, ``risk_level``,
            ``detected_patterns`` và hành động ``action`` đề xuất.

        Notes:
            Đây chỉ là bộ lọc chuỗi đơn giản, không phát hiện được cách diễn đạt
            biến thể, ngữ cảnh hoặc ý định ẩn. Không nên sử dụng riêng hàm này như
            một hệ thống kiểm duyệt hoàn chỉnh trong môi trường production.
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
    """Lưu đánh giá của người dùng về một ứng viên vào bộ nhớ tạm.

        Args:
            user_id: Mã người dùng gửi đánh giá.
            candidate_id: Mã ứng viên được đánh giá.
            rating: Điểm nguyên từ 1 đến 5.
            feedback: Nội dung nhận xét bổ sung. Mặc định là chuỗi rỗng.

        Returns:
            Chuỗi JSON chuẩn hóa chứa trạng thái lưu và bản ghi feedback. Nếu
            ``rating`` nằm ngoài khoảng 1–5, kết quả trả về ``success=False``.

        Notes:
            Hàm thêm trực tiếp bản ghi vào biến toàn cục ``MATCH_FEEDBACK`` và
            hiện chưa xác minh sự tồn tại của ``user_id`` hoặc ``candidate_id``.
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
    """Đề xuất hoạt động gặp mặt dựa trên thành phố và sở thích chung.

        Args:
            city: Thành phố dự kiến tổ chức cuộc gặp.
            interests: Danh sách sở thích chung dùng để chọn hoạt động phù hợp.
            budget_level: Mức ngân sách dự kiến, thường là ``"thấp"``,
                ``"trung bình"`` hoặc ``"cao"``. Mặc định là ``"trung bình"``.

        Returns:
            Chuỗi JSON chuẩn hóa chứa thành phố, danh sách ``ideas`` và lưu ý an
            toàn cho lần gặp đầu tiên. Nếu không có sở thích phù hợp với luật định
            sẵn, hàm trả về một gợi ý gặp tại không gian công cộng.
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
    """Tra cứu dữ liệu thời tiết giả lập cho một thành phố được hỗ trợ.

        Args:
            location: Tên thành phố cần tra cứu. Hàm hiện hỗ trợ Hà Nội,
                TP.HCM/Hồ Chí Minh và Đà Nẵng, gồm một số biến thể không dấu.

        Returns:
            Chuỗi JSON chuẩn hóa chứa ``location``, ``temperature``,
            ``condition`` và ``outdoor_suitable``. Nếu địa điểm không được hỗ trợ,
            kết quả trả về ``success=False`` và thông báo trong ``error``.

        Notes:
            Dữ liệu được hard-code để phục vụ demo, không phải thông tin thời tiết
            thời gian thực và không được lấy từ API bên ngoài.
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
