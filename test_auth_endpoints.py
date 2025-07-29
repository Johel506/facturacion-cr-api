#!/usr/bin/env python3
"""
Test script for authentication endpoints - Task 10.1
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8001/api/v1"

# Load tenant credentials
with open("tenant_info.json", "r") as f:
    tenant_info = json.load(f)

API_KEY = tenant_info["api_key"]

def test_validate_api_key():
    """Test API key validation endpoint"""
    print("🔑 Testing API Key Validation")
    print("-" * 40)
    
    # Test with X-API-Key header
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.post(
            f"{API_BASE}/auth/validate-key",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Key validation successful!")
            print(f"Tenant: {data['data']['tenant']['nombre_empresa']}")
            print(f"Plan: {data['data']['tenant']['plan']}")
            print(f"Active: {data['data']['tenant']['activo']}")
            print(f"Has Certificate: {data['data']['tenant']['tiene_certificado']}")
            return True
        else:
            print(f"❌ Validation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_generate_jwt_token():
    """Test JWT token generation"""
    print("\n🎫 Testing JWT Token Generation")
    print("-" * 40)
    
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.post(
            f"{API_BASE}/auth/token",
            headers=headers,
            json={"expires_minutes": 60},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ JWT token generated successfully!")
            token = data['data']['access_token']
            print(f"Token type: {data['data']['token_type']}")
            print(f"Expires in: {data['data']['expires_in']} seconds")
            print(f"Token (first 50 chars): {token[:50]}...")
            return token
        else:
            print(f"❌ Token generation failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_validate_jwt_token(token):
    """Test JWT token validation"""
    print("\n🔍 Testing JWT Token Validation")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{API_BASE}/auth/token/validate",
            params={"token": token},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ JWT token validation successful!")
            print(f"Tenant: {data['data']['tenant']['nombre_empresa']}")
            print(f"Token payload keys: {list(data['data']['token_payload'].keys())}")
            return True
        else:
            print(f"❌ Token validation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_rate_limit_status():
    """Test rate limit status endpoint"""
    print("\n📊 Testing Rate Limit Status")
    print("-" * 40)
    
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.get(
            f"{API_BASE}/auth/limits",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Rate limit status retrieved!")
            
            monthly = data['data']['monthly_limits']
            print(f"Monthly limit: {monthly['limit']}")
            print(f"Used: {monthly['used']}")
            print(f"Remaining: {monthly['remaining']}")
            print(f"Usage: {monthly['usage_percent']}%")
            
            status = data['data']['status']
            print(f"Can create documents: {status['can_create_documents']}")
            print(f"Certificate valid: {status['certificate_valid']}")
            
            return True
        else:
            print(f"❌ Rate limit status failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_current_user_info():
    """Test current user info endpoint"""
    print("\n👤 Testing Current User Info")
    print("-" * 40)
    
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.get(
            f"{API_BASE}/auth/me",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ User info retrieved!")
            
            tenant = data['data']['tenant']
            print(f"Company: {tenant['nombre_empresa']}")
            print(f"Email: {tenant['email_contacto']}")
            print(f"Plan: {tenant['plan']}")
            
            permissions = data['data']['permissions']
            print(f"Can create documents: {permissions['can_create_documents']}")
            
            features = data['data']['plan_features']
            print(f"Plan features: {len(features)} features")
            
            return True
        else:
            print(f"❌ User info failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_auth_health():
    """Test auth service health check"""
    print("\n🏥 Testing Auth Service Health")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{API_BASE}/auth/health",
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Auth service is healthy!")
            print(f"Service: {data['data']['service']}")
            print(f"Status: {data['data']['status']}")
            print(f"Features: {', '.join(data['data']['features'])}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_invalid_api_key():
    """Test with invalid API key"""
    print("\n🚫 Testing Invalid API Key")
    print("-" * 40)
    
    headers = {"X-API-Key": "invalid_key_12345"}
    
    try:
        response = requests.post(
            f"{API_BASE}/auth/validate-key",
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Invalid API key correctly rejected!")
            data = response.json()
            error_code = data.get('error', {}).get('code', 'UNKNOWN')
            print(f"Error code: {error_code}")
            return True
        else:
            print(f"❌ Expected 401, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all authentication endpoint tests"""
    print("🧪 TESTING AUTHENTICATION ENDPOINTS - TASK 10.1")
    print("=" * 60)
    
    results = []
    
    # Test 1: API key validation
    results.append(("API Key Validation", test_validate_api_key()))
    
    # Test 2: JWT token generation
    token = test_generate_jwt_token()
    results.append(("JWT Token Generation", token is not None))
    
    # Test 3: JWT token validation (if token was generated)
    if token:
        results.append(("JWT Token Validation", test_validate_jwt_token(token)))
    
    # Test 4: Rate limit status
    results.append(("Rate Limit Status", test_rate_limit_status()))
    
    # Test 5: Current user info
    results.append(("Current User Info", test_current_user_info()))
    
    # Test 6: Auth service health
    results.append(("Auth Service Health", test_auth_health()))
    
    # Test 7: Invalid API key handling
    results.append(("Invalid API Key", test_invalid_api_key()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("-" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
    
    print("-" * 60)
    print(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL AUTHENTICATION ENDPOINTS WORKING!")
        print("✅ Task 10.1 - Authentication and security endpoints COMPLETED")
        return True
    else:
        print(f"\n⚠️ {total - passed} tests failed - check server logs")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)