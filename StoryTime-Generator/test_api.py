#!/usr/bin/env python3
"""
Test GitHub Models API connectivity
Verifies that your GITHUB_TOKEN is valid and can access the API
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")

print("=" * 60)
print("🧪 GitHub Models API Connectivity Test")
print("=" * 60)

# Check token
print("\n1️⃣  Checking GitHub Token...")
if not GITHUB_TOKEN:
    print("   ❌ GITHUB_TOKEN not found in .env file")
    exit(1)

if GITHUB_TOKEN == "your_github_token_here":
    print("   ❌ GITHUB_TOKEN is still a placeholder")
    print("   Please replace it with your actual token")
    exit(1)

print(f"   ✓ Token found: {GITHUB_TOKEN[:20]}...")

# Check endpoint
print("\n2️⃣  Checking API Endpoint...")
print(f"   Endpoint: {API_ENDPOINT}")
print(f"   Model: {MODEL_NAME}")

# Try to initialize LLM
print("\n3️⃣  Initializing ChatOpenAI...")
try:
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.7,
        base_url=API_ENDPOINT,
        api_key=GITHUB_TOKEN
    )
    print("   ✓ LLM initialized successfully")
except Exception as e:
    print(f"   ❌ Failed to initialize LLM: {e}")
    exit(1)

# Test API call
print("\n4️⃣  Testing API Call...")
try:
    response = llm.invoke([HumanMessage(content="Say 'hello'.")])
    print("   ✓ API call successful!")
    print(f"\n   Response: {response.content}")
except Exception as e:
    print(f"   ❌ API call failed: {e}")
    print("\n   Possible issues:")
    print("   - Token is invalid or expired")
    print("   - Token doesn't have GitHub Models API access")
    print("   - API endpoint is unreachable")
    print("\n   💡 Solution:")
    print("   1. Create a new GitHub token at: https://github.com/settings/tokens")
    print("   2. Ensure the token has access to GitHub Models API")
    print("   3. Update your .env file with the new token")
    exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed! Your API is configured correctly.")
print("=" * 60)
print("\nYou can now run: python app.py")
