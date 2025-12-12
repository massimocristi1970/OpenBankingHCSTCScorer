"""
Comprehensive test of export functionality
"""
import json
import csv
import io
from dashboard import app, process_transaction_file

def test_comprehensive_export():
    """Comprehensive test of CSV and JSON export endpoints."""
    
    print("Comprehensive Export Testing")
    print("=" * 80)
    
    with app.test_client() as client:
        # Load sample data
        sample_file = '/home/runner/work/OpenBankingHCSTCScorer/OpenBankingHCSTCScorer/sample_transactions.json'
        results = process_transaction_file(sample_file)
        
        print(f"\n1. Loaded {len(results)} sample transactions")
        print(f"   Fields in each result: {list(results[0].keys())}")
        
        # Test CSV export with all results
        print("\n2. Testing CSV Export with all results:")
        csv_response = client.post('/export/csv',
                                   json={'results': results},
                                   content_type='application/json')
        
        assert csv_response.status_code == 200, f"CSV export failed with status {csv_response.status_code}"
        assert csv_response.content_type == 'text/csv; charset=utf-8', "Wrong content type"
        
        # Verify CSV can be parsed
        csv_content = csv_response.data.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        csv_rows = list(csv_reader)
        
        print(f"   ✓ CSV exported successfully")
        print(f"   ✓ CSV contains {len(csv_rows)} rows")
        print(f"   ✓ CSV headers: {csv_reader.fieldnames}")
        
        # Verify all fields are present in CSV
        first_result_keys = set(results[0].keys())
        csv_header_keys = set(csv_reader.fieldnames)
        
        if first_result_keys == csv_header_keys:
            print(f"   ✓ All fields present in CSV headers")
        else:
            missing_in_csv = first_result_keys - csv_header_keys
            extra_in_csv = csv_header_keys - first_result_keys
            if missing_in_csv:
                print(f"   ⚠ Fields missing from CSV: {missing_in_csv}")
            if extra_in_csv:
                print(f"   ⚠ Extra fields in CSV: {extra_in_csv}")
        
        # Verify data integrity
        print(f"\n   First CSV row sample:")
        if csv_rows:
            for key, value in list(csv_rows[0].items())[:5]:
                print(f"     {key}: {value}")
        
        # Test JSON export with all results
        print("\n3. Testing JSON Export with all results:")
        json_response = client.post('/export/json',
                                    json={'results': results},
                                    content_type='application/json')
        
        assert json_response.status_code == 200, f"JSON export failed with status {json_response.status_code}"
        assert json_response.content_type == 'application/json', "Wrong content type"
        
        # Verify JSON can be parsed
        json_content = json_response.data.decode('utf-8')
        json_data = json.loads(json_content)
        
        print(f"   ✓ JSON exported successfully")
        print(f"   ✓ JSON contains {len(json_data)} records")
        print(f"   ✓ JSON fields: {list(json_data[0].keys())}")
        
        # Verify JSON data matches original
        assert len(json_data) == len(results), "JSON record count mismatch"
        print(f"   ✓ JSON record count matches original")
        
        # Test edge cases
        print("\n4. Testing edge cases:")
        
        # Empty results
        empty_csv = client.post('/export/csv', json={'results': []}, content_type='application/json')
        assert empty_csv.status_code == 200, "Empty CSV export failed"
        print("   ✓ Empty results CSV export works")
        
        empty_json = client.post('/export/json', json={'results': []}, content_type='application/json')
        assert empty_json.status_code == 200, "Empty JSON export failed"
        print("   ✓ Empty results JSON export works")
        
        # Missing results key
        no_results_csv = client.post('/export/csv', json={}, content_type='application/json')
        assert no_results_csv.status_code == 400, "Should fail without results key"
        print("   ✓ Missing results key properly rejected (CSV)")
        
        no_results_json = client.post('/export/json', json={}, content_type='application/json')
        assert no_results_json.status_code == 400, "Should fail without results key"
        print("   ✓ Missing results key properly rejected (JSON)")
        
        # Single result
        single_csv = client.post('/export/csv', json={'results': [results[0]]}, content_type='application/json')
        assert single_csv.status_code == 200, "Single result CSV export failed"
        print("   ✓ Single result CSV export works")
        
        single_json = client.post('/export/json', json={'results': [results[0]]}, content_type='application/json')
        assert single_json.status_code == 200, "Single result JSON export failed"
        print("   ✓ Single result JSON export works")
        
        # Verify Content-Disposition headers for downloads
        print("\n5. Verifying download headers:")
        assert 'attachment' in csv_response.headers.get('Content-Disposition', '').lower(), "CSV not set as attachment"
        print("   ✓ CSV has attachment disposition")
        
        assert 'attachment' in json_response.headers.get('Content-Disposition', '').lower(), "JSON not set as attachment"
        print("   ✓ JSON has attachment disposition")
        
        # Check filenames
        csv_filename = csv_response.headers.get('Content-Disposition', '')
        json_filename = json_response.headers.get('Content-Disposition', '')
        print(f"   ✓ CSV filename pattern: {csv_filename}")
        print(f"   ✓ JSON filename pattern: {json_filename}")
    
    print("\n" + "=" * 80)
    print("✓ All Comprehensive Export Tests Passed!")
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        test_comprehensive_export()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
