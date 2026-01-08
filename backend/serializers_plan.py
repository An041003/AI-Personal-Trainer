from rest_framework import serializers

TRAINING_DAY_CHOICES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_TRAINING_DAY_ORDER = {d: i for i, d in enumerate(TRAINING_DAY_CHOICES)}

# chấp nhận input "Mon", "monday", "TUE", ... rồi canonicalize về "mon"..."sun"
_TRAINING_DAY_ALIASES = {
    "mon": "mon",
    "monday": "mon",
    "tue": "tue",
    "tues": "tue",
    "tuesday": "tue",
    "wed": "wed",
    "weds": "wed",
    "wednesday": "wed",
    "thu": "thu",
    "thur": "thu",
    "thurs": "thu",
    "thursday": "thu",
    "fri": "fri",
    "friday": "fri",
    "sat": "sat",
    "saturday": "sat",
    "sun": "sun",
    "sunday": "sun",
}


def _default_training_days(days_per_week: int) -> list[str]:
    """
    Default lịch theo days_per_week (calendar-aware tối thiểu).
    Có thể thay/upgrade sau, nhưng phải deterministic.
    """
    if days_per_week <= 0:
        return []
    if days_per_week == 1:
        return ["mon"]
    if days_per_week == 2:
        return ["mon", "thu"]
    if days_per_week == 3:
        return ["mon", "wed", "fri"]
    if days_per_week == 4:
        return ["mon", "tue", "thu", "fri"]
    if days_per_week == 5:
        return ["mon", "tue", "wed", "fri", "sat"]
    if days_per_week == 6:
        return ["mon", "tue", "wed", "thu", "fri", "sat"]
    return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _canon_day(v: str) -> str:
    if v is None:
        raise serializers.ValidationError("training_days chứa phần tử rỗng.")
    key = str(v).strip().lower()
    if not key:
        raise serializers.ValidationError("training_days chứa phần tử rỗng.")
    out = _TRAINING_DAY_ALIASES.get(key)
    if out is None:
        raise serializers.ValidationError(
            f"training_day không hợp lệ: {v}. Allowed: {', '.join(TRAINING_DAY_CHOICES)}"
        )
    return out


class WorkoutPlanGenerateSerializer(serializers.Serializer):
    # Bước 0 input tối thiểu
    goal_text = serializers.CharField(allow_blank=False, trim_whitespace=True)

    days_per_week = serializers.IntegerField(min_value=1, max_value=7)
    session_minutes = serializers.IntegerField(min_value=10, max_value=240)

    # NEW: FE có thể gửi training_days; nếu không gửi -> BE tự sinh default theo days_per_week
    training_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )


    # Optional profile signals
    sex = serializers.ChoiceField(choices=["male", "female"], required=False)
    height = serializers.FloatField(required=False)  # cm
    weight = serializers.FloatField(required=False)  # kg
    waist = serializers.FloatField(required=False)  # cm
    hip = serializers.FloatField(required=False)  # cm
    chest = serializers.FloatField(required=False)  # cm

    experience = serializers.ChoiceField(
        choices=["beginner", "intermediate", "advanced"],
        required=False,
    )

    # CSV string, ví dụ: "dumbbell, pullup_bar"
    equipment = serializers.CharField(required=False, allow_blank=True, default="")

    # để plan ổn định nếu bạn muốn
    seed = serializers.IntegerField(required=False)

    def validate(self, attrs):
        days_per_week = int(attrs.get("days_per_week") or 0)

        raw_days = attrs.get("training_days", None)

        # Nếu FE không gửi (hoặc gửi rỗng) -> default
        if not raw_days:
            attrs["training_days"] = _default_training_days(days_per_week)
            return attrs

        # Canonicalize + validate unique + validate length = days_per_week
        canon = [_canon_day(x) for x in raw_days]

        if len(set(canon)) != len(canon):
            raise serializers.ValidationError(
                {"training_days": "training_days phải là danh sách unique (không trùng ngày)."}
            )

        if len(canon) != days_per_week:
            raise serializers.ValidationError(
                {
                    "training_days": f"Số ngày đã chọn ({len(canon)}) phải đúng bằng days_per_week ({days_per_week})."
                }
            )

        # Sort theo thứ tự tuần để deterministic (optional nhưng rất hữu ích cho pipeline + cache)
        canon_sorted = sorted(canon, key=lambda d: _TRAINING_DAY_ORDER[d])
        attrs["training_days"] = canon_sorted
        return attrs
