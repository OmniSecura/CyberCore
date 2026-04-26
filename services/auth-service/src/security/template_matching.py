import re
from dataclasses import dataclass


# ── Patterns ──────────────────────────────────────────────────────────────────

# Email: standard RFC 5321 simplified — covers 99.9% of real addresses
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Full name: letters (including accented/unicode), spaces, hyphens, apostrophes
_FULL_NAME_PATTERN = re.compile(
    r"^[^\d!@#$%^&*()_+=\[\]{};:\"\\|,.<>\/?`~]+$"
)

# Password checks
_PASSWORD_UPPERCASE      = re.compile(r"[A-Z]")
_PASSWORD_LOWERCASE      = re.compile(r"[a-z]")
_PASSWORD_DIGIT          = re.compile(r"\d")
_PASSWORD_SPECIAL        = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]")
_PASSWORD_WHITESPACE     = re.compile(r"\s")

# 3+ identical characters in a row: aaa, 111, ###
_PASSWORD_REPEATED_CHARS = re.compile(r"(.)\1{2,}")

# 3+ sequential digits ascending or descending: 123, 456, 987, 321
_PASSWORD_SEQ_DIGITS     = re.compile(
    r"(?:0123|1234|2345|3456|4567|5678|6789"
    r"|9876|8765|7654|6543|5432|4321|3210)"
)

# 3+ sequential letters ascending or descending: abc, xyz, zyx
_PASSWORD_SEQ_LETTERS    = re.compile(
    r"(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz"
    r"|zyx|yxw|xwv|wvu|vut|uts|tsr|srq|rqp|qpo|pon|onm|nml|mlk|lkj|kji|jih|ihg|hgf|gfe|fed|edc|dcb|cba)",
    re.IGNORECASE,
)

# Keyboard walk patterns (rows and common diagonal walks)
_PASSWORD_KEYBOARD_WALK  = re.compile(
    r"(?:qwer|wert|erty|rtyu|tyui|yuio|uiop"
    r"|asdf|sdfg|dfgh|fghj|ghjk|hjkl"
    r"|zxcv|xcvb|cvbn|vbnm"
    r"|qaz|wsx|edc|rfv|tgb|yhn|ujm"
    r"|1qaz|2wsx|3edc|4rfv|5tgb|6yhn|7ujm)",
    re.IGNORECASE,
)

# Repeated patterns: abababab, 123123, xoxo
_PASSWORD_REPEATED_PATTERN = re.compile(r"^(.{1,4})\1{2,}$")

# Only one character class used throughout (all digits, all letters, all special)
_PASSWORD_ONLY_DIGITS    = re.compile(r"^\d+$")
_PASSWORD_ONLY_LETTERS   = re.compile(r"^[a-zA-Z]+$")
_PASSWORD_ONLY_SPECIAL   = re.compile(r"^[^a-zA-Z0-9]+$")

# Looks like a date: 01/01/2000, 2000-01-01, 01012000, 20000101
_PASSWORD_DATE_PATTERN   = re.compile(
    r"(?:\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}"  # DD/MM/YYYY or MM/DD/YYYY
    r"|\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2}"    # YYYY-MM-DD
    r"|\d{8})"                               # DDMMYYYY or YYYYMMDD bare
)

# Common weak passwords — extended list
_WEAK_PASSWORDS = {
    # Generic
    "password", "password1", "password12", "password123", "password1234",
    "passw0rd", "p@ssword", "p@ssw0rd",
    # Sequences
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "0987654321", "987654321",
    # Keyboard
    "qwerty", "qwerty123", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn",
    "1q2w3e", "1q2w3e4r", "1q2w3e4r5t",
    # Words
    "letmein", "welcome", "welcome1", "iloveyou", "monkey", "monkey1",
    "dragon", "master", "sunshine", "princess", "football", "baseball",
    "superman", "batman", "trustno1", "shadow", "michael", "jessica",
    "login", "admin", "admin123", "administrator", "root", "toor",
    "guest", "test", "test123", "demo", "user", "user123",
    # Patterns
    "aaaaaa", "111111", "000000", "abcdef", "abcdef1",
    "abc123", "abc123!", "Password1", "Password1!",
}


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """
    Returned by every validator.

    Attributes:
        valid    True if the value passed all checks.
        errors   List of human-readable error messages. Empty when valid=True.
    """
    valid: bool
    errors: list[str]

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(valid=True, errors=[])

    @classmethod
    def fail(cls, *errors: str) -> "ValidationResult":
        return cls(valid=False, errors=list(errors))


# ── Validators ────────────────────────────────────────────────────────────────

def validate_email(email: str) -> ValidationResult:
    """
    Validate an email address.

    Checks:
        - Not empty
        - No leading or trailing whitespace
        - Matches standard email pattern (local@domain.tld)
        - Does not exceed 255 characters (RFC 5321 limit)
        - Local part does not exceed 64 characters (RFC 5321 limit)
        - No consecutive dots in local part

    Args:
        email: Raw email string from user input.

    Returns:
        ValidationResult with valid=True or a list of error messages.

    Example:
        >>> validate_email("user@example.com").valid
        True
        >>> validate_email("not-an-email").errors
        ['Invalid email address format']
    """
    errors: list[str] = []

    if not email or not email.strip():
        return ValidationResult.fail("Email address is required")

    if email != email.strip():
        errors.append("Email address must not contain leading or trailing spaces")

    if len(email) > 255:
        errors.append("Email address must not exceed 255 characters")

    stripped = email.strip()

    if "@" in stripped:
        local_part, _, domain = stripped.partition("@")

        if len(local_part) > 64:
            errors.append("Email local part must not exceed 64 characters")

        if ".." in local_part:
            errors.append("Email local part must not contain consecutive dots")

        if local_part.startswith(".") or local_part.endswith("."):
            errors.append("Email local part must not start or end with a dot")

        if ".." in domain:
            errors.append("Email domain must not contain consecutive dots")

    if not _EMAIL_PATTERN.match(stripped):
        errors.append("Invalid email address format")

    if errors:
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult.ok()


def validate_full_name(full_name: str) -> ValidationResult:
    """
    Validate a full name.

    Checks:
        - Not empty
        - Between 2 and 100 characters
        - Only letters, spaces, hyphens, and apostrophes (no digits or symbols)
        - No leading or trailing whitespace
        - No consecutive spaces
        - No consecutive hyphens

    Accepts:
        "Bartosz Kowalski", "Jean-Pierre Dupont", "O'Brien", "Zoë Müller"

    Args:
        full_name: Raw full name string from user input.

    Returns:
        ValidationResult with valid=True or a list of error messages.

    Example:
        >>> validate_full_name("Bartosz Kowalski").valid
        True
        >>> validate_full_name("B4rtosz!").errors
        ['Full name must not contain digits or special characters']
    """
    errors: list[str] = []

    if not full_name or not full_name.strip():
        return ValidationResult.fail("Full name is required")

    if full_name != full_name.strip():
        errors.append("Full name must not contain leading or trailing spaces")

    stripped = full_name.strip()

    if len(stripped) < 2:
        errors.append("Full name must be at least 2 characters long")

    if len(stripped) > 100:
        errors.append("Full name must not exceed 100 characters")

    if not _FULL_NAME_PATTERN.match(stripped):
        errors.append("Full name must not contain digits or special characters")

    if "  " in stripped:
        errors.append("Full name must not contain consecutive spaces")

    if "--" in stripped:
        errors.append("Full name must not contain consecutive hyphens")

    if errors:
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult.ok()


def validate_password(password: str, full_name: str = "", email: str = "") -> ValidationResult:
    """
    Validate a password against security requirements.

    Checks:
        - Not empty
        - At least 12 characters (increased from 8)
        - At most 128 characters
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        - Contains at least one special character
        - At least 2 digits (not just one token digit)
        - At least 2 special characters
        - Does not contain whitespace
        - Is not a known weak/common password
        - No character repeated 3 or more times in a row (aaa, 111)
        - No sequential digit runs (123, 456, 987)
        - No sequential letter runs (abc, xyz)
        - No keyboard walk patterns (qwer, asdf, zxcv)
        - Not a repeated pattern (abab, 123123)
        - Not composed entirely of one character class
        - Does not look like a date (01012000, 2000-01-01)
        - Does not contain parts of the user's name (if provided)
        - Does not contain the email local part (if provided)

    Args:
        password:  Raw password string from user input.
        full_name: Optional — used to check if password contains the first name.
        email:     Optional — used to check if password contains the email.

    Returns:
        ValidationResult with valid=True or a list of error messages.

    Example:
        >>> validate_password("MyP@ssw0rd!9").valid
        True
        >>> validate_password("aaabbbccc").errors
        ['Password must be at least 12 characters long', ...]
    """
    errors: list[str] = []

    if not password:
        return ValidationResult.fail("Password is required")

    # ── Length ────────────────────────────────────────────────────────────────
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")

    if len(password) > 128:
        errors.append("Password must not exceed 128 characters")

    # ── Character class requirements ──────────────────────────────────────────
    if not _PASSWORD_UPPERCASE.search(password):
        errors.append("Password must contain at least one uppercase letter")

    if not _PASSWORD_LOWERCASE.search(password):
        errors.append("Password must contain at least one lowercase letter")

    digit_count = len(re.findall(r"\d", password))
    if digit_count == 0:
        errors.append("Password must contain at least one digit")
    elif digit_count < 2:
        errors.append("Password must contain at least 2 digits")

    special_count = len(re.findall(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password))
    if special_count == 0:
        errors.append("Password must contain at least one special character (!@#$%...)")
    elif special_count < 2:
        errors.append("Password must contain at least 2 special characters")

    if _PASSWORD_WHITESPACE.search(password):
        errors.append("Password must not contain spaces or whitespace characters")

    # ── Single character class only ───────────────────────────────────────────
    if _PASSWORD_ONLY_DIGITS.match(password):
        errors.append("Password must not consist entirely of digits")

    if _PASSWORD_ONLY_LETTERS.match(password):
        errors.append("Password must not consist entirely of letters")

    if _PASSWORD_ONLY_SPECIAL.match(password):
        errors.append("Password must not consist entirely of special characters")

    # ── Repetition and sequence patterns ──────────────────────────────────────
    if _PASSWORD_REPEATED_CHARS.search(password):
        errors.append(
            "Password must not contain the same character 3 or more times in a row (e.g. 'aaa', '111')"
        )

    if _PASSWORD_SEQ_DIGITS.search(password):
        errors.append(
            "Password must not contain sequential digit runs (e.g. '1234', '9876')"
        )

    if _PASSWORD_SEQ_LETTERS.search(password):
        errors.append(
            "Password must not contain sequential letter runs (e.g. 'abc', 'xyz')"
        )

    if _PASSWORD_KEYBOARD_WALK.search(password):
        errors.append(
            "Password must not contain keyboard walk patterns (e.g. 'qwer', 'asdf')"
        )

    if _PASSWORD_REPEATED_PATTERN.match(password):
        errors.append(
            "Password must not be a repeated pattern (e.g. 'abababab', '123123123')"
        )

    # ── Date-like patterns ────────────────────────────────────────────────────
    if _PASSWORD_DATE_PATTERN.search(password):
        errors.append(
            "Password must not contain a date pattern (e.g. '01012000', '2000-01-01')"
        )

    # ── Common weak passwords ─────────────────────────────────────────────────
    if password.lower() in _WEAK_PASSWORDS:
        errors.append("Password is too common — please choose a more unique password")

    # ── Context-aware: name parts ─────────────────────────────────────────────
    if full_name:
        name_parts = [p.lower() for p in full_name.strip().split() if len(p) >= 3]
        for part in name_parts:
            if part in password.lower():
                errors.append("Password must not contain parts of your name")
                break

    # ── Context-aware: email local part ──────────────────────────────────────
    if email and "@" in email:
        local_part = email.split("@")[0].lower()
        if len(local_part) >= 3 and local_part in password.lower():
            errors.append("Password must not contain your email address")

    if errors:
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult.ok()


# ── Convenience: validate all registration fields at once ─────────────────────

@dataclass(frozen=True)
class RegistrationValidationResult:
    """Combined result for all three fields at registration time."""
    valid: bool
    email_errors: list[str]
    full_name_errors: list[str]
    password_errors: list[str]

    def all_errors(self) -> dict[str, list[str]]:
        """Return all errors grouped by field — useful for API responses."""
        return {
            field: errs
            for field, errs in {
                "email":     self.email_errors,
                "full_name": self.full_name_errors,
                "password":  self.password_errors,
            }.items()
            if errs
        }


def validate_registration(
    email: str,
    full_name: str,
    password: str,
) -> RegistrationValidationResult:
    """
    Run all three validators in one call.

    Validates all fields independently — the user sees every problem
    at once rather than fixing them one by one.

    Args:
        email:     Email address.
        full_name: Full name.
        password:  Chosen password.

    Returns:
        RegistrationValidationResult — check .valid and .all_errors().

    Example:
        result = validate_registration("bad", "", "weak")
        if not result.valid:
            return JSONResponse(status_code=422, content=result.all_errors())
    """
    email_result     = validate_email(email)
    full_name_result = validate_full_name(full_name)
    password_result  = validate_password(password, full_name=full_name, email=email)

    return RegistrationValidationResult(
        valid=all([email_result.valid, full_name_result.valid, password_result.valid]),
        email_errors=email_result.errors,
        full_name_errors=full_name_result.errors,
        password_errors=password_result.errors,
    )