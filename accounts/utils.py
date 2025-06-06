from difflib import SequenceMatcher
import re
from .models import CustomUser


def isPasswordSimilar(password, email):
    max_similarity = 0.7
    password = password.lower()
    value_lower = email.lower()
    value_parts = re.split(r"\W+", value_lower) + [value_lower]
    for value_part in value_parts:
        if SequenceMatcher(a=password, b=value_part).quick_ratio() >= max_similarity:
            return True
    return False


def email_address_exists(email):
    return CustomUser.objects.filter(email__iexact=email).exists()
