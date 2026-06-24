"""
Custom Password Validators for enhanced security
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UppercaseValidator:
    """
    Validates that the password contains at least one uppercase letter.
    """
    def __init__(self, min_count=1):
        self.min_count = min_count

    def validate(self, password, user=None):
        uppercase_count = sum(1 for c in password if c.isupper())
        if uppercase_count < self.min_count:
            raise ValidationError(
                _("This password must contain at least %(min_count)d uppercase letter%(min_count)s."),
                code='password_no_upper',
                params={'min_count': self.min_count},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least %(min_count)d uppercase letter%(min_count)s."
            % {'min_count': self.min_count}
        )


class SpecialCharValidator:
    """
    Validates that the password contains at least one special character.
    """
    def __init__(self, min_count=1):
        self.min_count = min_count
        # Special characters that are allowed
        self.special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?')

    def validate(self, password, user=None):
        special_count = sum(1 for c in password if c in self.special_chars)
        if special_count < self.min_count:
            raise ValidationError(
                _("This password must contain at least %(min_count)d special character%(min_count)s."),
                code='password_no_special',
                params={'min_count': self.min_count},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least %(min_count)d special character%(min_count)s "
            "(e.g., !@#$%^&*)."
            % {'min_count': self.min_count}
        )


class MinimumLengthValidator:
    """
    Enhanced minimum length validator with configurable minimum length.
    """
    def __init__(self, min_length=12):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("This password is too short. It must contain at least %(min_length)d characters."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least %(min_length)d characters."
            % {'min_length': self.min_length}
        )


class CommonPasswordValidator:
    """
    Validates that the password is not a commonly used password.
    Extends Django's built-in validator with additional checks.
    """
    # Top 100 most common passwords (abbreviated list)
    COMMON_PASSWORDS = {
        'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey',
        '1234567', 'letmein', 'trustno1', 'dragon', 'baseball', 'iloveyou',
        'master', 'sunshine', 'ashley', 'bailey', 'passw0rd', 'shadow',
        '123123', '654321', 'superman', 'qazwsx', 'michael', 'football',
        'password1', 'password123', 'welcome', 'welcome1', 'admin',
    }

    def validate(self, password, user=None):
        if password.lower() in self.COMMON_PASSWORDS:
            raise ValidationError(
                _("This password is too common."),
                code='password_too_common',
            )

    def get_help_text(self):
        return _("Your password can't be a commonly used password.")
