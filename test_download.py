#!/usr/bin/env python3
"""
Simple test script for ASF API download
"""

import requests
import json

# Test ASF API connection
def test_asf_api():
    """Test basic ASF API functionality"""
    print("🧪 Testing ASF API connection...")

    # ASF search endpoint
    url = "https://api.daac.asf.alaska.edu/services/search/param"

    # Simple search parameters
    params = {
        'platform': 'Sentinel-1',
        'processingLevel': 'GRD_HD',
        'beamMode': 'IW',
        'polarization': 'VV+VH',
        'start': '2023-07-01',
        'end': '2023-07-31',
        'bbox': '74.5,42.56,74.52,42.58',  # Small test area
        'output': 'json',
        'maxResults': 5
    }

    headers = {
        'User-Agent': 'SAR-Glacier-Monitoring-Test/1.0',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        results = data.get('results', [])

        print(f"✅ ASF API connection successful!")
        print(f"📊 Found {len(results)} granules")

        if results:
            print("📋 First result:")
            result = results[0]
            print(f"   Date: {result.get('sceneDate', 'N/A')}")
            print(f"   Platform: {result.get('platform', 'N/A')}")
            print(f"   Polarization: {result.get('polarization', 'N/A')}")
            print(f"   Size: {result.get('sizeMB', 'N/A')} MB")

            # Try to get download URL
            download_url = result.get('downloadUrl', '')
            if download_url:
                print(f"   Download URL: {download_url[:50]}...")
            else:
                print("   ⚠️ No download URL available")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ ASF API connection failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse API response: {e}")
        return False

def test_small_download():
    """Test downloading a small file"""
    print("\n📥 Testing small file download...")

    # Get search results first
    url = "https://api.daac.asf.alaska.edu/services/search/param"
    params = {
        'platform': 'Sentinel-1',
        'processingLevel': 'GRD_HD',
        'beamMode': 'IW',
        'polarization': 'VV',
        'start': '2023-07-01',
        'end': '2023-07-31',
        'bbox': '74.5,42.56,74.52,42.58',
        'output': 'json',
        'maxResults': 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get('results', [])

        if not results:
            print("❌ No test files found")
            return False

        # Get the first result
        granule = results[0]
        download_url = granule.get('downloadUrl', '')

        if not download_url:
            print("❌ No download URL available for test file")
            return False

        print(f"📁 Test file: {granule.get('sceneDate', 'unknown')} - {granule.get('sizeMB', 'unknown')} MB")

        # Try to download (but don't save, just test connection)
        head_response = requests.head(download_url)
        if head_response.status_code == 200:
            print("✅ Download URL is accessible")
            print(f"   Content length: {head_response.headers.get('content-length', 'unknown')} bytes")
            return True
        else:
            print(f"❌ Download URL not accessible: {head_response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Download test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔬 ASF API CONNECTION TEST")
    print("=" * 60)

    # Test API connection
    api_ok = test_asf_api()

    # Test download capability
    download_ok = test_small_download()

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)

    if api_ok and download_ok:
        print("✅ All tests passed! Ready for full download.")
        print("🚀 You can now run: python3 asf_api_downloader.py --years 2015 2025 --month 7")
    else:
        print("❌ Some tests failed. Check your connection and ASF API availability.")
        if not api_ok:
            print("💡 Try checking ASF website: https://search.asf.alaska.edu/")
        if not download_ok:
            print("💡 Try using a VPN if downloads are blocked")

    print("=" * 60)

