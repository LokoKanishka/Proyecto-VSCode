import re
from typing import Optional

class SecurityGuard:
    """
    Handles security checks, input sanitization, and PII redaction.
    """
    def __init__(self):
        # Regex patterns for PII
        self.pii_patterns = {
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "PHONE": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        }
        
        # Simple bad words list (mock)
        self.bad_words = ["rm -rf", ":(){:|:&};:"] 

    def sanitize_input(self, text: str) -> str:
        """
        Sanitizes user input to prevent injection or malicious commands.
        Very basic implementation for now.
        """
        for bad in self.bad_words:
            if bad in text:
                return "[BLOCKED_COMMAND]"
        return text

    def redact_pii(self, text: str) -> str:
        """
        Redacts PII from text using Regex.
        Returns the redacted text.
        """
        redacted_text = text
        for pii_type, pattern in self.pii_patterns.items():
            redacted_text = re.sub(pattern, f"[{pii_type}]", redacted_text)
        return redacted_text

    def check_permission(self, user_role: str, required_role: str) -> bool:
        """
        Checks if user_role satisfies required_role.
        Hierarchy: admin > user > guest
        """
        hierarchy = {"admin": 3, "user": 2, "guest": 1}
        
        u_level = hierarchy.get(user_role, 0)
        r_level = hierarchy.get(required_role, 0)
        
        return u_level >= r_level
