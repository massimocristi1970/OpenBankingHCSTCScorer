"""
Test export error handling improvements
"""
import json
from dashboard import app


def test_export_error_handling():
    """Test comprehensive error handling for CSV and JSON exports."""
    
    print("Testing Export Error Handling")
    print("=" * 80)
    
    with app.test_client() as client:
        
        # Test 1: CSV export with missing results key
        print("\n1. Testing CSV export with missing 'results' key:")
        response = client.post('/export/csv',
                              json={'data': []},
                              content_type='application/json')
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert 'error' in data, "Error message not in response"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error: {data['error']}")
        
        # Test 2: CSV export with empty results (allowed for backward compatibility)
        print("\n2. Testing CSV export with empty results array:")
        response = client.post('/export/csv',
                              json={'results': []},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        csv_content = response.data.decode('utf-8')
        lines = csv_content.split('\n')
        assert len(lines) >= 1, "CSV should have at least header row"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Empty CSV exported successfully (header only)")
        
        # Test 3: CSV export with invalid results type
        print("\n3. Testing CSV export with non-array results:")
        response = client.post('/export/csv',
                              json={'results': 'not an array'},
                              content_type='application/json')
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert 'error' in data, "Error message not in response"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error: {data['error']}")
        
        # Test 4: CSV export with missing fields (restval should handle this)
        print("\n4. Testing CSV export with missing fields:")
        results_with_missing_fields = [
            {
                'date': '2024-01-01',
                'description': 'Test transaction',
                'amount': -100.0,
                # Missing many fields
            }
        ]
        response = client.post('/export/csv',
                              json={'results': results_with_missing_fields},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        csv_content = response.data.decode('utf-8')
        lines = csv_content.split('\n')
        assert len(lines) >= 2, "CSV should have header and at least one data row"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ CSV exported successfully with missing fields")
        print(f"   ✓ Header: {lines[0][:80]}...")
        print(f"   ✓ Data row: {lines[1][:80]}...")
        
        # Test 5: JSON export with missing results key
        print("\n5. Testing JSON export with missing 'results' key:")
        response = client.post('/export/json',
                              json={'data': []},
                              content_type='application/json')
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert 'error' in data, "Error message not in response"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error: {data['error']}")
        
        # Test 6: JSON export with empty results (allowed for backward compatibility)
        print("\n6. Testing JSON export with empty results array:")
        response = client.post('/export/json',
                              json={'results': []},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        json_content = json.loads(response.data.decode('utf-8'))
        assert json_content == [], "Empty JSON should be empty array"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Empty JSON exported successfully (empty array)")
        
        # Test 7: JSON export with invalid results type
        print("\n7. Testing JSON export with non-array results:")
        response = client.post('/export/json',
                              json={'results': {'not': 'an array'}},
                              content_type='application/json')
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert 'error' in data, "Error message not in response"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error: {data['error']}")
        
        # Test 8: Valid CSV export (regression test)
        print("\n8. Testing valid CSV export (regression test):")
        valid_results = [
            {
                'date': '2024-01-25',
                'description': 'BANK GIRO CREDIT ACME CORP LTD',
                'amount': -2800.0,
                'merchant_name': 'ACME CORP LTD',
                'category': 'income',
                'subcategory': 'account_transfer',  # Changed from 'salary'
                'confidence': 0.98,  # Changed from 0.95 (strict PLAID match)
                'match_method': 'plaid_strict',  # Changed from 'behavioral_income'
                'description_text': 'BANK GIRO CREDIT ACME CORP LTD',
                'plaid_category_primary': 'TRANSFER_IN',
                'plaid_category_detailed': 'TRANSFER_IN_ACCOUNT_TRANSFER',  
                'risk_level': 'low',
                'weight': 1.0,
                'is_stable':  False,  # Changed from True (account_transfer is not stable)
                'is_housing': False
            }
        ]
        response = client.post('/export/csv',
                              json={'results': valid_results},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content_type == 'text/csv; charset=utf-8'
        csv_content = response.data.decode('utf-8')
        assert 'BANK GIRO CREDIT' in csv_content
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Content-Type: {response.content_type}")
        print(f"   ✓ CSV contains expected data")
        
        # Test 9: Valid JSON export (regression test)
        print("\n9. Testing valid JSON export (regression test):")
        response = client.post('/export/json',
                              json={'results': valid_results},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content_type == 'application/json'
        json_content = json.loads(response.data.decode('utf-8'))
        assert len(json_content) == 1
        assert json_content[0]['description'] == 'BANK GIRO CREDIT ACME CORP LTD'
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Content-Type: {response.content_type}")
        print(f"   ✓ JSON contains expected data")
        
    print("\n" + "=" * 80)
    print("All Export Error Handling Tests Passed!")
    print("=" * 80)


if __name__ == '__main__':
    test_export_error_handling()
