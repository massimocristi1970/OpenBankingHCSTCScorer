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

from transaction_categorizer import TransactionCategorizer
from metrics_calculator import MetricsCalculator
from scoring_engine import ScoringEngine, ScoringResult, Decision


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    conditional: int = 0
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


class HCSTCBatchProcessor:
    """Batch processor for HCSTC loan applications."""
    
    def __init__(
        self,
        default_loan_amount: float = 500,
        default_loan_term: int = 4,
        months_of_data: int = 3
    ):
        """
        Initialize the batch processor.
        
        Args:
            default_loan_amount: Default loan amount if not specified
            default_loan_term: Default loan term in months
            months_of_data: Number of months of transaction data
        """
        self.default_loan_amount = default_loan_amount
        self.default_loan_term = default_loan_term
        self.months_of_data = months_of_data
        
        # Initialize components
        self.categorizer = TransactionCategorizer()
        self.metrics_calculator = MetricsCalculator(months_of_data=months_of_data)
        self.scoring_engine = ScoringEngine()
        
        logger.info(
            f"Initialized batch processor: amount=£{default_loan_amount}, "
            f"term={default_loan_term}m, data_months={months_of_data}"
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
                elif result.decision == Decision.CONDITIONAL:
                    stats.conditional += 1
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
        # Parse JSON
        data = json.loads(content.decode("utf-8"))
        
        # Extract data
        accounts = data.get("accounts", [])
        transactions = data.get("transactions", [])
        
        if not transactions:
            raise ValueError("No transactions found in file")
        
        # Validate transactions
        self._validate_transactions(transactions)
        
        # Categorize transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=accounts,
            loan_amount=loan_amount,
            loan_term=loan_term
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
                "Risk Flags": "; ".join(result.risk_flags) if result.risk_flags else "",
                "Decline Reasons": "; ".join(result.decline_reasons) if result.decline_reasons else "",
                "Conditions": "; ".join(result.conditions) if result.conditions else "",
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
