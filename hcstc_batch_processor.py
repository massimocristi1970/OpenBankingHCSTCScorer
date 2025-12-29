"""
HCSTC Batch Processor for processing multiple loan applications.  
Handles JSON files and ZIP archives with comprehensive error handling.
"""

import json
import logging
import zipfile
import io
import os
from typing import Dict, List, Optional, Tuple, Generator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import traceback

from openbanking_engine.scoring.scoring_engine import ScoringEngine, Decision, ScoringResult
from openbanking_engine.config.scoring_config import PRODUCT_CONFIG
from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine. income.income_detector import IncomeDetector
from openbanking_engine.scoring.feature_builder import MetricsCalculator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class InvalidJsonStructureError(Exception):
    """Raised when JSON structure cannot be normalized to expected format."""
    pass


@dataclass
class ProcessingError:
    """Details of a processing error."""
    file_name: str
    error_type: str
    error_message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BatchStats:
    """Statistics for batch processing."""
    total_files: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    
    # Decision counts
    approved: int = 0
    referred: int = 0
    declined: int = 0
    
    # Score statistics
    total_score: float = 0.0
    min_score: float = 100.0
    max_score: float = 0.0
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def average_score(self) -> float:
        """Calculate average score."""
        if self.successful == 0:
            return 0.0
        return self.total_score / self.successful
    
    @property
    def processing_time(self) -> float:
        """Calculate total processing time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful / self.total_files) * 100


@dataclass
class BatchResult:
    """Complete result of batch processing."""
    stats: BatchStats
    results: List[ScoringResult]
    errors: List[ProcessingError]
    error_summary: Dict[str, int] = field(default_factory=dict)
    
    @staticmethod
    def merge_results(result1: 'BatchResult', result2: 'BatchResult') -> 'BatchResult':
        """
        Merge two BatchResult objects into a single combined result.
        
        This is used for cumulative batch processing where results from
        multiple uploads need to be combined.
        
        Args:
            result1: First batch result (typically the existing cumulative result)
            result2: Second batch result (typically the new batch to add)
        
        Returns:
            New BatchResult with merged data
        """
        # Create merged stats
        merged_stats = BatchStats()
        
        # Sum all count fields
        merged_stats.total_files = result1.stats.total_files + result2.stats.total_files
        merged_stats.processed = result1.stats.processed + result2.stats.processed
        merged_stats.successful = result1.stats.successful + result2.stats.successful
        merged_stats.failed = result1.stats.failed + result2.stats.failed
        merged_stats.approved = result1.stats.approved + result2.stats.approved
        merged_stats.referred = result1.stats.referred + result2.stats.referred
        merged_stats.declined = result1.stats.declined + result2.stats.declined
        merged_stats.total_score = result1.stats.total_score + result2.stats.total_score
        
        # Recalculate min and max scores
        # Handle case where one result might have no successful files
        if result1.stats.successful > 0 and result2.stats.successful > 0:
            merged_stats.min_score = min(result1.stats.min_score, result2.stats.min_score)
            merged_stats.max_score = max(result1.stats.max_score, result2.stats.max_score)
        elif result1.stats.successful > 0:
            merged_stats.min_score = result1.stats.min_score
            merged_stats.max_score = result1.stats.max_score
        elif result2.stats.successful > 0:
            merged_stats.min_score = result2.stats.min_score
            merged_stats.max_score = result2.stats.max_score
        else:
            # No successful files in either batch
            merged_stats.min_score = 0.0
            merged_stats.max_score = 0.0
        
        # Use earliest start time and latest end time
        if result1.stats.start_time and result2.stats.start_time:
            merged_stats.start_time = min(result1.stats.start_time, result2.stats.start_time)
        else:
            merged_stats.start_time = result1.stats.start_time or result2.stats.start_time
        
        if result1.stats.end_time and result2.stats.end_time:
            merged_stats.end_time = max(result1.stats.end_time, result2.stats.end_time)
        else:
            merged_stats.end_time = result1.stats.end_time or result2.stats.end_time
        
        # Concatenate results and errors
        merged_results = result1.results + result2.results
        merged_errors = result1.errors + result2.errors
        
        # Merge error summaries
        merged_error_summary = {}
        for error_type, count in result1.error_summary.items():
            merged_error_summary[error_type] = count
        for error_type, count in result2.error_summary.items():
            merged_error_summary[error_type] = merged_error_summary.get(error_type, 0) + count
        
        return BatchResult(
            stats=merged_stats,
            results=merged_results,
            errors=merged_errors,
            error_summary=merged_error_summary
        )


class HCSTCBatchProcessor:
    """Batch processor for HCSTC loan applications."""
    
    def __init__(
        self,
        default_loan_amount: float = 500,
        default_loan_term: int = 4,
        months_of_data: Optional[int] = None
    ):
        """
        Initialize the batch processor.
        
        Args:
            default_loan_amount: Default loan amount if not specified
            default_loan_term: Default loan term in months
            months_of_data: Number of months of transaction data (optional).
                           If not provided, will be calculated from transactions automatically.
        """
        self.default_loan_amount = default_loan_amount
        self.default_loan_term = default_loan_term
        self.months_of_data = months_of_data
        
        # Initialize components
        self.categorizer = TransactionCategorizer()
        # Note: metrics_calculator will be created per-application with transactions
        self.scoring_engine = ScoringEngine()
        
        if months_of_data is not None:
            logger.info(
                f"Initialized batch processor: amount=£{default_loan_amount}, "
                f"term={default_loan_term}m, data_months={months_of_data} (manual override)"
            )
        else:
            logger.info(
                f"Initialized batch processor: amount=£{default_loan_amount}, "
                f"term={default_loan_term}m, data_months=auto-calculated from transactions"
            )
    
    def process_batch(
        self,
        files: List[Tuple[str, bytes]],
        loan_amount: Optional[float] = None,
        loan_term: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> BatchResult:
        """
        Process a batch of application files.
        
        Args:
            files: List of (filename, content) tuples
            loan_amount: Loan amount to use (or default)
            loan_term: Loan term to use (or default)
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            BatchResult with all processing results
        """
        amount = loan_amount or self.default_loan_amount
        term = loan_term or self.default_loan_term
        
        stats = BatchStats(
            total_files=len(files),
            start_time=datetime.now()
        )
        
        results = []
        errors = []
        error_types = {}
        
        logger.info(f"Starting batch processing of {len(files)} files")
        
        for idx, (filename, content) in enumerate(files):
            try:
                if progress_callback:
                    progress_callback(idx + 1, len(files), f"Processing: {filename}")
                
                logger.debug(f"Processing file {idx + 1}/{len(files)}: {filename}")
                
                # Process individual application
                result = self._process_single_application(
                    filename=filename,
                    content=content,
                    loan_amount=amount,
                    loan_term=term
                )
                
                results.append(result)
                stats.processed += 1
                stats.successful += 1
                
                # Update score statistics
                stats.total_score += result.score
                stats.min_score = min(stats.min_score, result.score)
                stats.max_score = max(stats.max_score, result.score)
                
                # Update decision counts
                if result.decision == Decision.APPROVE:
                    stats.approved += 1
                elif result.decision == Decision.REFER:
                    stats.referred += 1
                elif result.decision == Decision.DECLINE:
                    stats.declined += 1
                
            except json.JSONDecodeError as e:
                error = ProcessingError(
                    file_name=filename,
                    error_type="JSON_PARSE_ERROR",
                    error_message=f"Invalid JSON: {str(e)}"
                )
                errors.append(error)
                stats.failed += 1
                stats.processed += 1
                error_types["JSON_PARSE_ERROR"] = error_types.get("JSON_PARSE_ERROR", 0) + 1
                logger.error(f"JSON parse error in {filename}: {e}")
                
            except KeyError as e:
                error = ProcessingError(
                    file_name=filename,
                    error_type="MISSING_DATA",
                    error_message=f"Missing required field: {str(e)}"
                )
                errors.append(error)
                stats.failed += 1
                stats.processed += 1
                error_types["MISSING_DATA"] = error_types.get("MISSING_DATA", 0) + 1
                logger.error(f"Missing data in {filename}: {e}")
                
            except ValueError as e:
                error = ProcessingError(
                    file_name=filename,
                    error_type="DATA_VALIDATION_ERROR",
                    error_message=str(e)
                )
                errors.append(error)
                stats.failed += 1
                stats.processed += 1
                error_types["DATA_VALIDATION_ERROR"] = error_types.get("DATA_VALIDATION_ERROR", 0) + 1
                logger.error(f"Data validation error in {filename}: {e}")
                
            except InvalidJsonStructureError as e:
                error = ProcessingError(
                    file_name=filename,
                    error_type="INVALID_JSON_STRUCTURE",
                    error_message=str(e)
                )
                errors.append(error)
                stats.failed += 1
                stats.processed += 1
                error_types["INVALID_JSON_STRUCTURE"] = error_types.get("INVALID_JSON_STRUCTURE", 0) + 1
                logger.error(f"Invalid JSON structure in {filename}: {e}")
                
            except Exception as e:
                error = ProcessingError(
                    file_name=filename,
                    error_type="PROCESSING_ERROR",
                    error_message=f"{type(e).__name__}: {str(e)}"
                )
                errors.append(error)
                stats.failed += 1
                stats.processed += 1
                error_types["PROCESSING_ERROR"] = error_types.get("PROCESSING_ERROR", 0) + 1
                logger.error(f"Processing error in {filename}: {traceback.format_exc()}")
        
        stats.end_time = datetime.now()
        
        # Fix min_score if no files processed
        if stats.successful == 0:
            stats.min_score = 0.0
        
        logger.info(
            f"Batch processing complete: {stats.successful}/{stats.total_files} successful, "
            f"avg score: {stats.average_score:.1f}, time: {stats.processing_time:.1f}s"
        )
        
        return BatchResult(
            stats=stats,
            results=results,
            errors=errors,
            error_summary=error_types
        )
    
    def _process_single_application(
        self,
        filename: str,
        content: bytes,
        loan_amount: float,
        loan_term: int
    ) -> ScoringResult:
        """Process a single application file."""
        # Parse JSON with fallback encoding handling
        try:
            data = json.loads(content.decode("utf-8"))
        except UnicodeDecodeError:
            # Fallback to cp1252 for Windows-encoded characters (e.g., byte 0x9c)
            try:
                data = json.loads(content.decode("cp1252"))
            except UnicodeDecodeError:
                # Final fallback to latin-1 which accepts all byte values
                data = json.loads(content.decode("latin-1"))
        
        # Normalize JSON structure to handle different Plaid formats
        accounts, transactions = self._normalize_json_structure(data, filename)
        
        if not transactions:
            raise ValueError("No transactions found in file")
        
        # Validate transactions
        self._validate_transactions(transactions)
        
        # Categorize transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create metrics calculator with automatic month calculation
        # If months_of_data was manually set in constructor, use it; otherwise auto-calculate
        metrics_calculator = MetricsCalculator(
            months_of_data=self.months_of_data,
            transactions=transactions
        )
        
        # Calculate metrics
        metrics = metrics_calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=accounts,
            loan_amount=loan_amount,
            loan_term=loan_term,
            categorized_transactions=categorized
        )
        
        # Generate application reference from filename
        app_ref = Path(filename).stem
        
        # Score application
        result = self.scoring_engine.score_application(
            metrics=metrics,
            requested_amount=loan_amount,
            requested_term=loan_term,
            application_ref=app_ref
        )
        
        return result
    
    def _validate_transactions(self, transactions: List[Dict]) -> None:
        """Validate transaction data."""
        if not transactions:
            raise ValueError("Empty transaction list")
        
        for idx, txn in enumerate(transactions):
            if "amount" not in txn:
                raise ValueError(f"Transaction {idx} missing 'amount' field")
            if "date" not in txn:
                raise ValueError(f"Transaction {idx} missing 'date' field")
            
            # Validate amount is numeric
            try:
                float(txn["amount"])
            except (ValueError, TypeError):
                raise ValueError(f"Transaction {idx} has invalid amount: {txn['amount']}")
    
    def _normalize_json_structure(
        self,
        data,
        filename: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Normalize different Plaid JSON structures to expected format.
        
        Handles:
        - Dictionary with 'accounts' and 'transactions' keys (standard format)
        - Root-level list of transactions
        - Root-level list of account objects with nested 'transactions'
        - Dictionary with only 'transactions' key
        
        Args:
            data: Parsed JSON data (dict or list)
            filename: Filename for logging purposes
        
        Returns:
            Tuple of (accounts, transactions) lists
        
        Raises:
            InvalidJsonStructureError: If structure cannot be normalized
        """
        accounts = []
        transactions = []
        
        if isinstance(data, dict):
            # Standard format: dictionary with accounts and/or transactions
            accounts = data.get("accounts", [])
            transactions = data.get("transactions", [])
            
            # Check for alternative key names that Plaid might use
            if not transactions:
                # Try 'transaction' (singular) as alternative
                transactions = data.get("transaction", [])
            
            if not transactions and not accounts:
                # Check if the dict itself looks like it contains transaction data at root
                # Some Plaid responses have data nested under other keys
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        if self._looks_like_transactions(value):
                            transactions = value
                            logger.info(
                                f"{filename}: Found transactions under key '{key}'"
                            )
                            break
                        elif self._looks_like_accounts(value):
                            accounts = value
                            # Check if accounts have nested transactions
                            nested_txns = self._extract_transactions_from_accounts(value)
                            if nested_txns:
                                transactions = nested_txns
                                logger.info(
                                    f"{filename}: Found {len(nested_txns)} transactions "
                                    f"nested within {len(value)} accounts"
                                )
            
            logger.debug(
                f"{filename}: Dictionary format - "
                f"found {len(accounts)} accounts, {len(transactions)} transactions"
            )
            
        elif isinstance(data, list):
            # Root-level list - could be transactions or accounts
            if len(data) == 0:
                raise InvalidJsonStructureError(
                    f"Empty array in JSON file: {filename}"
                )
            
            if self._looks_like_transactions(data):
                # List of transactions
                transactions = data
                logger.info(
                    f"{filename}: Root-level array detected as transactions list "
                    f"({len(data)} items)"
                )
                
            elif self._looks_like_accounts(data):
                # List of account objects - extract nested transactions
                accounts = data
                transactions = self._extract_transactions_from_accounts(data)
                logger.info(
                    f"{filename}: Root-level array detected as accounts list "
                    f"({len(data)} accounts, {len(transactions)} transactions)"
                )
                
            else:
                # Try to detect if this is a mixed or unknown structure
                logger.warning(
                    f"{filename}: Root-level array with unrecognized structure. "
                    f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}"
                )
                raise InvalidJsonStructureError(
                    f"Unrecognized JSON array structure in {filename}. "
                    f"Expected transaction objects (with 'amount', 'date') or "
                    f"account objects (with 'account_id' or 'transactions')."
                )
        else:
            raise InvalidJsonStructureError(
                f"Unexpected JSON root type in {filename}: {type(data).__name__}. "
                f"Expected dict or list."
            )
        
        return accounts, transactions
    
    def _looks_like_transactions(self, items: List) -> bool:
        """
        Check if a list appears to contain transaction objects.
        
        A transaction typically has 'amount' and 'date' fields.
        """
        if not items or not isinstance(items[0], dict):
            return False
        
        # Check first few items for transaction-like fields
        sample_size = min(3, len(items))
        transaction_indicators = 0
        
        for item in items[:sample_size]:
            if not isinstance(item, dict):
                continue
            # Check for common transaction fields
            has_amount = "amount" in item
            has_date = "date" in item or "datetime" in item or "transaction_date" in item
            has_name = "name" in item or "description" in item or "merchant_name" in item
            
            if has_amount and (has_date or has_name):
                transaction_indicators += 1
        
        # Consider it transactions if majority of samples look like transactions
        return transaction_indicators >= sample_size // 2 + 1
    
    def _looks_like_accounts(self, items: List) -> bool:
        """
        Check if a list appears to contain account objects.
        
        An account typically has 'account_id' or contains nested 'transactions'.
        """
        if not items or not isinstance(items[0], dict):
            return False
        
        # Check first few items for account-like fields
        sample_size = min(3, len(items))
        account_indicators = 0
        
        for item in items[:sample_size]:
            if not isinstance(item, dict):
                continue
            # Check for common account fields
            # Require 'account_id' specifically, or 'id' with other account-like fields
            has_account_id = "account_id" in item
            has_id_with_context = "id" in item and ("balances" in item or "transactions" in item)
            has_balances = "balances" in item or "balance" in item
            has_transactions = "transactions" in item
            has_type = "type" in item or "subtype" in item
            
            if has_account_id or has_id_with_context or has_transactions or (has_balances and has_type):
                account_indicators += 1
        
        return account_indicators >= sample_size // 2 + 1
    
    def _extract_transactions_from_accounts(self, accounts: List[Dict]) -> List[Dict]:
        """
        Extract transactions from account objects that have nested transactions.
        
        Args:
            accounts: List of account objects
        
        Returns:
            Flattened list of all transactions from all accounts
        """
        all_transactions = []
        
        for account in accounts:
            if not isinstance(account, dict):
                continue
            
            # Get transactions from this account
            account_transactions = account.get("transactions", [])
            
            if isinstance(account_transactions, list):
                # Optionally add account_id to each transaction for traceability
                account_id = account.get("account_id") or account.get("id")
                for txn in account_transactions:
                    if isinstance(txn, dict):
                        # Create a copy to avoid modifying the original data
                        txn_copy = txn.copy()
                        # Add account_id if transaction doesn't have one
                        if account_id and "account_id" not in txn_copy:
                            txn_copy["account_id"] = account_id
                        all_transactions.append(txn_copy)
        
        return all_transactions
    
    def load_files_from_uploads(
        self,
        uploaded_files: List
    ) -> List[Tuple[str, bytes]]:
        """
        Load files from Streamlit uploaded files.
        Handles both JSON files and ZIP archives.
        
        Args:
            uploaded_files: List of Streamlit UploadedFile objects
        
        Returns:
            List of (filename, content) tuples
        """
        all_files = []
        
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            content = uploaded_file.read()
            
            # Reset file pointer for potential re-read
            uploaded_file.seek(0)
            
            if filename.lower().endswith(".zip"):
                # Extract files from ZIP
                logger.info(f"Extracting ZIP archive: {filename}")
                zip_files = self._extract_zip(content)
                all_files.extend(zip_files)
                logger.info(f"Extracted {len(zip_files)} files from {filename}")
            
            elif filename.lower().endswith(".json"):
                all_files.append((filename, content))
            
            else:
                logger.warning(f"Skipping unsupported file: {filename}")
        
        logger.info(f"Total files loaded: {len(all_files)}")
        return all_files
    
    def _extract_zip(self, content: bytes) -> List[Tuple[str, bytes]]:
        """Extract JSON files from a ZIP archive."""
        files = []
        
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            for name in zf.namelist():
                # Skip directories and non-JSON files
                if name.endswith("/"):
                    continue
                if not name.lower().endswith(".json"):
                    continue
                
                # Extract file content
                file_content = zf.read(name)
                
                # Use just the filename without path
                filename = os.path.basename(name)
                files.append((filename, file_content))
        
        return files
    
    def results_to_dataframe(self, results: List[ScoringResult]):
        """
        Convert scoring results to a pandas DataFrame.
        
        Args:
            results: List of ScoringResult objects
        
        Returns:
            pandas DataFrame
        """
        import pandas as pd
        
        rows = []
        # Default values for when no loan offer is available
        default_offer = {
            "approved_amount": 0,
            "approved_term": 0,
            "monthly_repayment": 0,
            "total_repayable": 0
        }
        
        for result in results:
            # Use loan offer if available, otherwise use defaults
            if result.loan_offer:
                offer_data = {
                    "approved_amount": result.loan_offer.approved_amount,
                    "approved_term": result.loan_offer.approved_term,
                    "monthly_repayment": result.loan_offer.monthly_repayment,
                    "total_repayable": result.loan_offer.total_repayable
                }
            else:
                offer_data = default_offer

            row = {
                "Application Ref": result.application_ref,
                "Decision": result.decision.value,
                "Score": result.score,
                "Risk Level": result.risk_level.value,
                "Approved Amount": offer_data["approved_amount"],
                "Approved Term": offer_data["approved_term"],
                "Monthly Repayment": offer_data["monthly_repayment"],
                "Total Repayable": offer_data["total_repayable"],
                "Monthly Income": round(result.monthly_income, 2),
                "Monthly Expenses": round(result.monthly_expenses, 2),
                "Monthly Disposable": round(result.monthly_disposable, 2),
                "Post-Loan Disposable": round(result.post_loan_disposable, 2),

                # --- Behavioural diagnostics (NEW) ---
                "Months Observed": getattr(metrics.get("balance"), "months_observed", None),
                "Overdraft Days per Month": getattr(metrics.get("balance"), "overdraft_days_per_month", None),
                "Income Stability Score": getattr(metrics.get("income"), "income_stability_score", None),

                "Risk Flags": "; ".join(result.risk_flags) if result.risk_flags else "",
                "Decline Reasons": "; ".join(result.decline_reasons) if result.decline_reasons else "",
            }

            # Add score breakdown if available
            if result.score_breakdown:
                row["Affordability Score"] = result.score_breakdown.affordability_score
                row["Income Quality Score"] = result.score_breakdown.income_quality_score
                row["Account Conduct Score"] = result.score_breakdown.account_conduct_score
                row["Risk Indicators Score"] = result.score_breakdown.risk_indicators_score
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def errors_to_dataframe(self, errors: List[ProcessingError]):
        """
        Convert processing errors to a pandas DataFrame.
        
        Args:
            errors: List of ProcessingError objects
        
        Returns:
            pandas DataFrame
        """
        import pandas as pd
        
        rows = []
        for error in errors:
            row = {
                "File Name": error.file_name,
                "Error Type": error.error_type,
                "Error Message": error.error_message,
                "Timestamp": error.timestamp,
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
