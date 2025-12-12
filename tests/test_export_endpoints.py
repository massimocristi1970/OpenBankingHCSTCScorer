"""
Test the export endpoints to identify issues
"""
import json
from dashboard import app, process_transaction_file

def test_export_endpoints():
    """Test CSV and JSON export endpoints."""
    
    print("Testing Export Endpoints")
    print("=" * 60)
    
    # Create a test client
    with app.test_client() as client:
        # First, load some sample data
        sample_file = '/home/runner/work/OpenBankingHCSTCScorer/OpenBankingHCSTCScorer/sample_transactions.json'
        results = process_transaction_file(sample_file)
        
        print(f"\n1. Loaded {len(results)} sample transactions")
        
        # Test CSV export
        print("\n2. Testing CSV Export:")
        csv_response = client.post('/export/csv',
                                   json={'results': results[:5]},  # Test with first 5
                                   content_type='application/json')
        
        print(f"   Status Code: {csv_response.status_code}")
        print(f"   Content Type: {csv_response.content_type}")
        print(f"   Content Length: {len(csv_response.data)}")
        
        if csv_response.status_code == 200:
            print("   ✓ CSV export successful")
            # Show first few lines
            csv_content = csv_response.data.decode('utf-8')
            lines = csv_content.split('\n')[:3]
            print("   First few lines:")
            for line in lines:
                print(f"     {line[:80]}...")
        else:
            print(f"   ✗ CSV export failed")
            print(f"   Response: {csv_response.data.decode('utf-8')[:200]}")
        
        # Test JSON export
        print("\n3. Testing JSON Export:")
        json_response = client.post('/export/json',
                                    json={'results': results[:5]},
                                    content_type='application/json')
        
        print(f"   Status Code: {json_response.status_code}")
        print(f"   Content Type: {json_response.content_type}")
        print(f"   Content Length: {len(json_response.data)}")
        
        if json_response.status_code == 200:
            print("   ✓ JSON export successful")
            # Try to parse the JSON
            try:
                json_content = json_response.data.decode('utf-8')
                parsed = json.loads(json_content)
                print(f"   Parsed {len(parsed)} records")
            except Exception as e:
                print(f"   ✗ Failed to parse JSON: {e}")
        else:
            print(f"   ✗ JSON export failed")
            print(f"   Response: {json_response.data.decode('utf-8')[:200]}")
        
        # Test with empty results
        print("\n4. Testing with empty results:")
        empty_response = client.post('/export/csv',
                                     json={'results': []},
                                     content_type='application/json')
        print(f"   Status Code: {empty_response.status_code}")
        if empty_response.status_code == 200:
            print("   ✓ Empty results handled")
        
        # Test with missing results
        print("\n5. Testing with missing results key:")
        missing_response = client.post('/export/csv',
                                       json={},
                                       content_type='application/json')
        print(f"   Status Code: {missing_response.status_code}")
        if missing_response.status_code == 400:
            print("   ✓ Missing results detected correctly")
        
    print("\n" + "=" * 60)
    print("Export Endpoint Tests Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_export_endpoints()
