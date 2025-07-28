#!/usr/bin/env python3
"""
Test script for CABYS API functionality

This script tests the CABYS service and API endpoints to ensure they're working correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.services.cabys_service import cabys_service


async def test_cabys_service():
    """Test CABYS service functionality"""
    print("🧪 Testing CABYS Service...")
    
    # Test 1: Get a specific CABYS code (using a real code)
    print("\n1. Testing get_code()...")
    code_data = await cabys_service.get_code("0111100000100")  # Real CABYS code
    if code_data:
        print(f"✅ Found code: {code_data['codigo']} - {code_data['descripcion']}")
        print(f"   Category: {code_data['categoria_completa']}")
        print(f"   IVA: {code_data['impuesto_iva']}%")
    else:
        print("❌ Code not found")
    
    # Test 2: Search codes
    print("\n2. Testing search_codes()...")
    search_results = await cabys_service.search_codes("arroz", limit=5)
    print(f"✅ Search for 'arroz' returned {len(search_results['results'])} results")
    for result in search_results['results'][:3]:
        print(f"   - {result['codigo']}: {result['descripcion']}")
    
    # Test 3: Search by prefix
    print("\n3. Testing search_by_code_prefix()...")
    prefix_results = await cabys_service.search_by_code_prefix("101", limit=5)
    print(f"✅ Prefix search for '101' returned {len(prefix_results)} results")
    for result in prefix_results[:3]:
        print(f"   - {result['codigo']}: {result['descripcion']}")
    
    # Test 4: Search by category
    print("\n4. Testing search_by_category()...")
    category_results = await cabys_service.search_by_category("Productos alimenticios", nivel=1, limit=5)
    print(f"✅ Category search returned {len(category_results)} results")
    for result in category_results[:3]:
        print(f"   - {result['codigo']}: {result['descripcion']}")
    
    # Test 5: Get most used codes
    print("\n5. Testing get_most_used()...")
    most_used = await cabys_service.get_most_used(limit=5)
    print(f"✅ Most used codes: {len(most_used)} results")
    for result in most_used[:3]:
        print(f"   - {result['codigo']}: {result['descripcion']} (used {result['veces_usado']} times)")
    
    # Test 6: Validate code
    print("\n6. Testing validate_code()...")
    is_valid, error = await cabys_service.validate_code("0111100000100")  # Real CABYS code
    print(f"✅ Code validation: {'Valid' if is_valid else 'Invalid'}")
    if error:
        print(f"   Error: {error}")
    
    # Test 7: Get categories
    print("\n7. Testing get_categories()...")
    categories = await cabys_service.get_categories(nivel=1)
    print(f"✅ Level 1 categories: {len(categories)} found")
    for cat in categories[:3]:
        print(f"   - {cat}")
    
    # Test 8: Get statistics
    print("\n8. Testing get_statistics()...")
    stats = await cabys_service.get_statistics()
    print(f"✅ Statistics:")
    print(f"   - Total codes: {stats['total_codes']}")
    print(f"   - Active codes: {stats['active_codes']}")
    print(f"   - Used codes: {stats['used_codes']}")
    if stats['most_used_code']['codigo']:
        print(f"   - Most used: {stats['most_used_code']['codigo']} ({stats['most_used_code']['veces_usado']} times)")


async def test_api_endpoints():
    """Test API endpoints using httpx"""
    try:
        import httpx
    except ImportError:
        print("❌ httpx not installed. Skipping API tests.")
        print("   Install with: pip install httpx")
        return
    
    print("\n🌐 Testing API Endpoints...")
    
    base_url = "http://localhost:8000/api/v1/cabys"
    headers = {"Authorization": "Bearer test-token"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test search endpoint
            print("\n1. Testing /search endpoint...")
            response = await client.get(
                f"{base_url}/search",
                params={"q": "arroz", "limit": 3},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Search API: {len(data['results'])} results")
                for result in data['results']:
                    print(f"   - {result['codigo']}: {result['descripcion']}")
            else:
                print(f"❌ Search API failed: {response.status_code}")
        
        except Exception as e:
            print(f"❌ API test failed: {str(e)}")
            print("   Make sure the API server is running: uvicorn app.main:app --reload")


async def main():
    """Main test function"""
    print("🚀 CABYS API Test Suite")
    print("=" * 50)
    
    try:
        await test_cabys_service()
        await test_api_endpoints()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("\n📝 Next steps:")
        print("   1. Start the API server: uvicorn app.main:app --reload")
        print("   2. Visit http://localhost:8000/docs to see the API documentation")
        print("   3. Test the endpoints in the interactive docs")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())