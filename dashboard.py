"""
Transaction Categorization Review Dashboard

A non-intrusive Flask-based tool for reviewing and analyzing transaction categorization.
This dashboard helps identify miscategorizations by processing transaction data through
the existing categorization engine and displaying detailed results with confidence scores.

This tool is read-only and does NOT modify any core categorization logic.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import csv
import io

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from transaction_categorizer import TransactionCategorizer, CategoryMatch


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/dashboard_uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize categorizer (read-only usage)
categorizer = TransactionCategorizer()


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'json'


def process_transaction_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Process a JSON transaction file through the categorization engine.
    
    Args:
        filepath: Path to JSON file containing transaction data
        
    Returns:
        List of transaction results with categorization details
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    # Support both {"transactions": [...]} and direct array [...]
    if isinstance(data, dict) and 'transactions' in data:
        transactions = data['transactions']
    elif isinstance(data, list):
        transactions = data
    else:
        raise ValueError("Invalid JSON format. Expected array or object with 'transactions' key")
    
    # Use batch categorization for better performance
    results = categorizer.categorize_transactions_batch(transactions)
    
    # Format results with detailed information
    detailed_results = []
    for txn, category_match in results:
        result = {
            'description': txn.get('name', 'Unknown'),
            'amount': txn.get('amount', 0),
            'date': txn.get('date', ''),
            'merchant_name': txn.get('merchant_name', ''),
            'plaid_category_primary': txn.get('personal_finance_category.primary', ''),
            'plaid_category_detailed': txn.get('personal_finance_category.detailed', ''),
            'category': category_match.category,
            'subcategory': category_match.subcategory,
            'confidence': round(category_match.confidence, 3),
            'match_method': category_match.match_method,
            'description_text': category_match.description,
            'risk_level': category_match.risk_level or '',
            'weight': category_match.weight,
            'is_stable': category_match.is_stable,
            'is_housing': category_match.is_housing,
        }
        
        # Handle nested personal_finance_category
        if 'personal_finance_category' in txn and isinstance(txn['personal_finance_category'], dict):
            pfc = txn['personal_finance_category']
            if not result['plaid_category_primary']:
                result['plaid_category_primary'] = pfc.get('primary', '')
            if not result['plaid_category_detailed']:
                result['plaid_category_detailed'] = pfc.get('detailed', '')
        
        detailed_results.append(result)
    
    return detailed_results


def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate aggregate summary statistics from categorization results.
    
    Args:
        results: List of categorization results
        
    Returns:
        Dictionary with summary statistics
    """
    summary = {
        'total_transactions': len(results),
        'by_category': defaultdict(int),
        'by_subcategory': defaultdict(int),
        'by_confidence_level': {
            'high': 0,      # >= 0.80
            'medium': 0,    # 0.60 - 0.79
            'low': 0,       # < 0.60
        },
        'by_risk_level': defaultdict(int),
        'income_count': 0,
        'expense_count': 0,
        'low_confidence_transactions': [],
    }
    
    for result in results:
        # Category counts
        summary['by_category'][result['category']] += 1
        subcategory_key = f"{result['category']}/{result['subcategory']}"
        summary['by_subcategory'][subcategory_key] += 1
        
        # Income/expense counts
        if result['category'] == 'income':
            summary['income_count'] += 1
        else:
            summary['expense_count'] += 1
        
        # Confidence level buckets
        confidence = result['confidence']
        if confidence >= 0.80:
            summary['by_confidence_level']['high'] += 1
        elif confidence >= 0.60:
            summary['by_confidence_level']['medium'] += 1
        else:
            summary['by_confidence_level']['low'] += 1
            # Track low confidence transactions for review
            summary['low_confidence_transactions'].append({
                'description': result['description'],
                'amount': result['amount'],
                'category': result['category'],
                'subcategory': result['subcategory'],
                'confidence': result['confidence'],
                'match_method': result['match_method'],
            })
        
        # Risk level counts
        if result['risk_level']:
            summary['by_risk_level'][result['risk_level']] += 1
    
    # Convert defaultdicts to regular dicts for JSON serialization
    summary['by_category'] = dict(summary['by_category'])
    summary['by_subcategory'] = dict(summary['by_subcategory'])
    summary['by_risk_level'] = dict(summary['by_risk_level'])
    
    return summary


@app.route('/')
def index():
    """Main dashboard page with file upload form."""
    return render_template('dashboard.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Handle multiple file uploads and process transactions.
    
    Returns JSON with categorization results and summary statistics.
    """
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    all_results = []
    file_summaries = []
    errors = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                results = process_transaction_file(filepath)
                all_results.extend(results)
                
                file_summaries.append({
                    'filename': filename,
                    'transaction_count': len(results),
                    'status': 'success'
                })
                
                # Clean up file after processing
                os.remove(filepath)
                
            except Exception as e:
                errors.append({
                    'filename': filename,
                    'error': str(e)
                })
        else:
            if file and file.filename:
                errors.append({
                    'filename': file.filename,
                    'error': 'Invalid file type. Only JSON files are allowed.'
                })
    
    if not all_results and errors:
        return jsonify({'error': 'All files failed to process', 'details': errors}), 400
    
    # Generate summary statistics
    summary = generate_summary(all_results)
    
    response = {
        'success': True,
        'files_processed': len(file_summaries),
        'file_summaries': file_summaries,
        'total_transactions': len(all_results),
        'results': all_results,
        'summary': summary,
        'errors': errors if errors else None,
    }
    
    return jsonify(response)


@app.route('/export/csv', methods=['POST'])
def export_csv():
    """
    Export categorization results to CSV format.
    
    Expects JSON body with 'results' field containing categorization results.
    """
    try:
        data = request.get_json()
        
        if not data or 'results' not in data:
            app.logger.warning("CSV export: No results provided in request")
            return jsonify({'error': 'No results provided'}), 400
        
        results = data['results']
        
        if not isinstance(results, list):
            app.logger.error(f"CSV export: Results is not a list, got {type(results)}")
            return jsonify({'error': 'Results must be an array'}), 400
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'date', 'description', 'amount', 'merchant_name',
            'category', 'subcategory', 'confidence', 'match_method',
            'description_text', 'plaid_category_primary', 'plaid_category_detailed',
            'risk_level', 'weight', 'is_stable', 'is_housing'
        ], restval='')  # Use empty string for missing fields
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
        
        # Convert to bytes for sending
        output.seek(0)
        csv_data = output.getvalue().encode('utf-8')
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'categorization_results_{timestamp}.csv'
        
        app.logger.info(f"CSV export: Successfully exported {len(results)} results")
        
        return send_file(
            io.BytesIO(csv_data),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        app.logger.error(f"CSV export error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to export CSV: {str(e)}'}), 500


@app.route('/export/json', methods=['POST'])
def export_json():
    """
    Export categorization results to JSON format.
    
    Expects JSON body with 'results' field containing categorization results.
    """
    try:
        data = request.get_json()
        
        if not data or 'results' not in data:
            app.logger.warning("JSON export: No results provided in request")
            return jsonify({'error': 'No results provided'}), 400
        
        results = data['results']
        
        if not isinstance(results, list):
            app.logger.error(f"JSON export: Results is not a list, got {type(results)}")
            return jsonify({'error': 'Results must be an array'}), 400
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'categorization_results_{timestamp}.json'
        
        # Create JSON in memory
        json_data = json.dumps(results, indent=2).encode('utf-8')
        
        app.logger.info(f"JSON export: Successfully exported {len(results)} results")
        
        return send_file(
            io.BytesIO(json_data),
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        app.logger.error(f"JSON export error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to export JSON: {str(e)}'}), 500


if __name__ == '__main__':
    import os
    
    print("=" * 80)
    print("Transaction Categorization Review Dashboard")
    print("=" * 80)
    print("\nStarting dashboard on http://localhost:5001")
    print("This is a READ-ONLY tool that does not modify core categorization logic.")
    print("\nPress Ctrl+C to stop the server.")
    print("=" * 80)
    
    # Run on port 5001 to avoid conflicts with main app (if running)
    # Debug mode is controlled by environment variable for security
    # Set FLASK_DEBUG=1 only in development environments
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    if debug_mode:
        print("\n⚠️  WARNING: Running in DEBUG mode. Not suitable for production!")
        print("=" * 80)
    
    app.run(debug=debug_mode, port=5001, host='0.0.0.0')
