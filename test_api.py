#!/usr/bin/env python3
"""
KTP Detection API Test Script
=============================

Script untuk testing API endpoints
"""

import requests
import json
import sys
import os
from pathlib import Path

class KTPAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
    def test_health(self):
        """Test health endpoint"""
        print("🔍 Testing health endpoint...")
        try:
            response = requests.get(f"{self.api_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_gemini_connection(self):
        """Test Gemini connection"""
        print("🔍 Testing Gemini connection...")
        try:
            response = requests.post(f"{self.api_url}/test-gemini")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Gemini test: {data['message']}")
                return data['gemini_connected']
            else:
                print(f"❌ Gemini test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Gemini test error: {e}")
            return False
    
    def test_database_init(self):
        """Test database initialization"""
        print("🔍 Testing database initialization...")
        try:
            response = requests.post(f"{self.api_url}/init-database")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Database init: {data['message']}")
                return True
            else:
                print(f"❌ Database init failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Database init error: {e}")
            return False
    
    def test_ktp_upload(self, image_path):
        """Test KTP upload endpoint"""
        print(f"🔍 Testing KTP upload with: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return False
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.api_url}/verify-ktp", files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ KTP upload successful")
                print(f"   Valid KTP: {data['is_valid_ktp']}")
                print(f"   Confidence: {data['confidence_score']:.2f}")
                
                if data['is_valid_ktp'] and data['extracted_data']:
                    print(f"   NIK: {data['extracted_data'].get('nik', 'N/A')}")
                    print(f"   Nama: {data['extracted_data'].get('nama', 'N/A')}")
                
                return True
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                print(f"❌ KTP upload failed: {response.status_code}")
                print(f"   Error: {error_data}")
                return False
                
        except Exception as e:
            print(f"❌ KTP upload error: {e}")
            return False
    
    def test_search_endpoint(self):
        """Test search endpoint"""
        print("🔍 Testing search endpoint...")
        try:
            # Test search with empty criteria (should fail)
            search_data = {"limit": 5, "offset": 0}
            response = requests.post(f"{self.api_url}/search-ktp", json=search_data)
            
            if response.status_code == 400:
                print("✅ Search validation working (empty criteria rejected)")
                return True
            else:
                print(f"❌ Search validation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Search test error: {e}")
            return False
    
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        print("🔍 Testing stats endpoint...")
        try:
            response = requests.get(f"{self.api_url}/stats")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Stats endpoint working")
                print(f"   Total processed: {data.get('total_processed', 0)}")
                return True
            else:
                print(f"❌ Stats endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Stats test error: {e}")
            return False
    
    def run_all_tests(self, image_path=None):
        """Run all tests"""
        print("🚀 Starting KTP Detection API Tests")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health),
            ("Gemini Connection", self.test_gemini_connection),
            ("Database Init", self.test_database_init),
            ("Search Endpoint", self.test_search_endpoint),
            ("Stats Endpoint", self.test_stats_endpoint),
        ]
        
        # Add KTP upload test if image provided
        if image_path:
            tests.append(("KTP Upload", lambda: self.test_ktp_upload(image_path)))
        
        results = []
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            result = test_func()
            results.append((test_name, result))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nPassed: {passed}/{len(results)} tests")
        
        if passed == len(results):
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️ Some tests failed. Check the logs above.")
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test KTP Detection API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--image", help="Path to test KTP image")
    
    args = parser.parse_args()
    
    tester = KTPAPITester(args.url)
    
    print(f"Testing API at: {args.url}")
    
    # Run tests
    success = tester.run_all_tests(args.image)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
