import re
from django.core.exceptions import ValidationError


def get_policy_for_user(user=None):
    """Resolve PasswordPolicy from user's first admin/active membership tenant."""
    from apps.accounts.models import PasswordPolicy

    if user is None or not getattr(user, "is_authenticated", False):
        return PasswordPolicy()
    membership = (
        user.memberships.filter(is_active=True).select_related("tenant").order_by("id").first()
        if hasattr(user, "memberships")
        else None
    )
    if membership:
        policy, _ = PasswordPolicy.objects.get_or_create(tenant=membership.tenant)
        return policy
    return PasswordPolicy()


class ComplexityValidator:
    def validate(self, password, user=None):
        policy = get_policy_for_user(user)
        if len(password) < policy.min_length:
            raise ValidationError(
                f"Password must be at least {policy.min_length} characters.",
                code="password_too_short",
            )
        if policy.require_upper and not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain an uppercase letter.", code="password_no_upper")
        if policy.require_lower and not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain a lowercase letter.", code="password_no_lower")
        if policy.require_digit and not re.search(r"\d", password):
            raise ValidationError("Password must contain a digit.", code="password_no_digit")
        if policy.require_special and not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError("Password must contain a special character.", code="password_no_special")

    def get_help_text(self):
        return "Password must meet tenant password policy (length and complexity)."
