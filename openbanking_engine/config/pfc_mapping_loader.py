"""
Plaid Personal Finance Category (PFC) Mapping Loader.

Loads CSV mappings from Plaid taxonomy categories to engine categories.
Future enhancement: Load from external CSV for easy maintenance by non-technical stakeholders.
"""

import csv
from typing import Dict, Optional
from pathlib import Path


def load_pfc_mapping(csv_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    Load Plaid PFC to engine category mapping from CSV.
    
    Args:
        csv_path: Path to CSV file with columns: plaid_category, engine_category, engine_subcategory
        
    Returns:
        Dictionary mapping plaid_category -> {'category': str, 'subcategory': str}
        
    Example CSV format:
        plaid_category,engine_category,engine_subcategory
        INCOME_WAGES,income,salary
        TRANSFER_IN_DEPOSIT,transfer,internal
        LOAN_PAYMENTS_CREDIT_CARD_PAYMENT,debt,credit_cards
    """
    if csv_path is None:
        # Return empty dict - patterns will be used as fallback
        return {}
    
    mapping = {}
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        raise FileNotFoundError(f"PFC mapping CSV not found: {csv_path}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plaid_cat = row.get('plaid_category', '').strip()
            engine_cat = row.get('engine_category', '').strip()
            engine_subcat = row.get('engine_subcategory', '').strip()
            
            if plaid_cat and engine_cat:
                mapping[plaid_cat] = {
                    'category': engine_cat,
                    'subcategory': engine_subcat
                }
    
    return mapping
