#!/usr/bin/env python3
"""
Script to help find your Supabase JWT Secret.

The JWT secret is needed to validate JWT tokens from Supabase.
You can find it in your Supabase dashboard:

1. Go to: https://app.supabase.com/project/kxgyfwhmcfdfmqrhwkhd/settings/api
2. Look for "JWT Secret" under "JWT Settings"
3. Copy the secret and update it in the .env file

Alternatively, you can decode your JWT tokens to see the payload,
but the secret itself is not stored in the JWT.
"""

import base64
import json

# Example JWT token (anon key)
jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4Z3lmd2htY2ZkZm1xcmh3a2hkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NTI3NTUsImV4cCI6MjA4MjQyODc1NX0.gmnfAD0RpsVUt76vvSXbPJqU-z3M9DLpNSqSC4poHkM"

# Decode JWT (without verification)
parts = jwt_token.split(".")
if len(parts) == 3:
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    
    print("JWT Header:")
    print(json.dumps(header, indent=2))
    print("\nJWT Payload:")
    print(json.dumps(payload, indent=2))
    print("\n" + "="*50)
    print("\nYour Supabase project reference: kxgyfwhmcfdfmqrhwkhd")
    print("\nTo get your JWT Secret:")
    print("1. Go to: https://app.supabase.com/project/kxgyfwhmcfdfmqrhwkhd/settings/api")
    print("2. Scroll to 'JWT Settings'")
    print("3. Copy the 'JWT Secret'")
    print("4. Update SUPABASE_JWT_SECRET in .env file")
    print("\nNote: The JWT secret is NOT the same as your service role key!")
