#!/usr/bin/env python3
"""Test if app.utils.credentials module exists"""
try:
    from app.utils.credentials import decrypt_credential_blob
    print("✓ Import successful: app.utils.credentials")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    
    # Try the correct module
    try:
        from app.utils.credential_crypto import decrypt_credential_blob
        print("✓ Alternative import successful: app.utils.credential_crypto")
    except ImportError as e2:
        print(f"✗ Alternative import also failed: {e2}")
