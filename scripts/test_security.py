from src.core.security import SecurityGuard

def test_security():
    guard = SecurityGuard()
    
    print("🔒 Testing Security Guard...")
    
    # 1. PII Redaction
    text = "Contact me at test@example.com or 555-123-4567."
    redacted = guard.redact_pii(text)
    print(f"Original: {text}")
    print(f"Redacted: {redacted}")
    assert "[EMAIL]" in redacted
    assert "[PHONE]" in redacted
    assert "test@example.com" not in redacted
    
    # 2. Input Sanitization
    bad_input = "Hello world rm -rf /"
    sanitized = guard.sanitize_input(bad_input)
    print(f"Sanitized: {sanitized}")
    assert "[BLOCKED_COMMAND]" in sanitized
    
    # 3. RBAC
    assert guard.check_permission("admin", "user") == True
    assert guard.check_permission("user", "admin") == False
    
    print("✅ All Security Tests Passed.")

if __name__ == "__main__":
    test_security()
