"""
Test export functionality with various error scenarios to verify error handling
"""
import json
from dashboard import app


def test_export_with_server_errors():
    """Test that export endpoints handle errors gracefully."""
    
    print("Testing Export Error Scenarios")
    print("=" * 80)
    
    with app.test_client() as client:
        
        # Test 1: Export with non-JSON content type
        print("\n1. Testing CSV export with invalid content type:")
        try:
            response = client.post('/export/csv',
                                  data='not json',
                                  content_type='text/plain')
            print(f"   Status: {response.status_code}")
            if response.status_code >= 400:
                try:
                    error_data = response.get_json()
                    print(f"   Error response: {error_data}")
                except:
                    print(f"   Response: {response.data[:100]}")
        except Exception as e:
            print(f"   Exception caught: {e}")
        
        # Test 2: Export with malformed JSON
        print("\n2. Testing CSV export with invalid JSON:")
        try:
            response = client.post('/export/csv',
                                  data='{invalid json}',
                                  content_type='application/json')
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Exception caught (expected): {type(e).__name__}")
        
        # Test 3: Export with results that have special characters
        print("\n3. Testing CSV export with special characters:")
        results_with_special_chars = [
            {
                'date': '2024-01-01',
                'description': 'Test "quoted" transaction, with commas',
                'amount': -100.0,
                'merchant_name': "O'Reilly's Store",
                'category': 'essential',
                'subcategory': 'groceries',
                'confidence': 0.95,
                'match_method': 'direct_match',
                'description_text': 'Test\nwith\nnewlines',
                'plaid_category_primary': 'FOOD_AND_DRINK',
                'plaid_category_detailed': 'FOOD_AND_DRINK_GROCERIES',
                'risk_level': 'low',
                'weight': 1.0,
                'is_stable': True,
                'is_housing': False
            }
        ]
        response = client.post('/export/csv',
                              json={'results': results_with_special_chars},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        csv_content = response.data.decode('utf-8')
        assert 'O\'Reilly\'s Store' in csv_content or "O'Reilly's Store" in csv_content
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Special characters handled correctly")
        
        # Test 4: Export with very large dataset (performance)
        print("\n4. Testing CSV export with large dataset:")
        large_results = []
        for i in range(1000):
            large_results.append({
                'date': f'2024-01-{(i % 28) + 1:02d}',
                'description': f'Transaction {i}',
                'amount': -float(i),
                'merchant_name': f'Merchant {i}',
                'category': 'essential',
                'subcategory': 'groceries',
                'confidence': 0.95,
                'match_method': 'direct_match',
                'description_text': f'Description {i}',
                'plaid_category_primary': 'FOOD_AND_DRINK',
                'plaid_category_detailed': 'FOOD_AND_DRINK_GROCERIES',
                'risk_level': 'low',
                'weight': 1.0,
                'is_stable': True,
                'is_housing': False
            })
        
        response = client.post('/export/csv',
                              json={'results': large_results},
                              content_type='application/json')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        lines = response.data.decode('utf-8').split('\n')
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Exported {len(lines) - 1} transactions")
        
        # Test 5: JSON export with nested objects (should serialize correctly)
        print("\n5. Testing JSON export with complex data:")
        response = client.post('/export/json',
                              json={'results': results_with_special_chars},
                              content_type='application/json')
        
        assert response.status_code == 200
        json_content = json.loads(response.data.decode('utf-8'))
        assert json_content[0]['merchant_name'] == "O'Reilly's Store"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ JSON serialized correctly")
        
        # Test 6: Verify error responses have proper format
        print("\n6. Testing error response format:")
        response = client.post('/export/csv',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 400
        error_data = response.get_json()
        assert 'error' in error_data, "Error response should have 'error' field"
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error format: {error_data}")
        
    print("\n" + "=" * 80)
    print("All Export Error Scenario Tests Passed!")
    print("=" * 80)


if __name__ == '__main__':
    test_export_with_server_errors()
