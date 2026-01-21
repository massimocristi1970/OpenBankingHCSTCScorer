#!/usr/bin/env python3
"""
Model Monitoring Infrastructure for HCSTC Scoring System

This module provides tools to monitor model performance over time,
detect score distribution drift, and track outcome metrics.

Usage:
    from model_monitoring import ScoringMonitor
    
    monitor = ScoringMonitor()
    monitor.log_decision(application_id, score, decision, metrics)
    monitor.generate_report()
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics


@dataclass
class DecisionLog:
    """Single decision log entry."""
    application_id: str
    timestamp: str
    score: float
    decision: str  # APPROVE, REFER, DECLINE
    income_stability: float
    monthly_income: float
    disposable_income: float
    dti_ratio: float
    gambling_percentage: float
    failed_payments_count: int
    days_in_overdraft: int
    active_hcstc_count: int
    decline_reasons: List[str] = field(default_factory=list)
    refer_reasons: List[str] = field(default_factory=list)


@dataclass
class MonitoringReport:
    """Monitoring report summary."""
    report_date: str
    period_start: str
    period_end: str
    total_applications: int
    
    # Decision distribution
    approve_count: int
    approve_rate: float
    refer_count: int
    refer_rate: float
    decline_count: int
    decline_rate: float
    
    # Score statistics
    score_mean: float
    score_median: float
    score_std: float
    score_min: float
    score_max: float
    
    # Key metric averages
    avg_income_stability: float
    avg_monthly_income: float
    avg_disposable: float
    avg_dti: float
    
    # Drift indicators
    score_drift_from_baseline: float
    approval_rate_drift: float
    
    # Alerts
    alerts: List[str] = field(default_factory=list)


class ScoringMonitor:
    """
    Monitors scoring model performance over time.
    
    Features:
    - Logs all scoring decisions with key metrics
    - Detects score distribution drift
    - Tracks approval/decline rates
    - Generates periodic reports
    - Alerts on anomalies
    """
    
    def __init__(self, log_dir: str = "./scoring_logs"):
        """
        Initialize the scoring monitor.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        self.baseline_stats: Optional[Dict] = None
        self._ensure_log_dir()
        self._load_baseline()
    
    def _ensure_log_dir(self):
        """Create log directory if it doesn't exist."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _get_log_file(self, date: Optional[datetime] = None) -> str:
        """Get log file path for a given date."""
        if date is None:
            date = datetime.now()
        return os.path.join(self.log_dir, f"decisions_{date.strftime('%Y-%m-%d')}.jsonl")
    
    def _load_baseline(self):
        """Load baseline statistics from file if available."""
        baseline_file = os.path.join(self.log_dir, "baseline_stats.json")
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                self.baseline_stats = json.load(f)
    
    def set_baseline(self, stats: Dict):
        """
        Set baseline statistics for drift detection.
        
        Args:
            stats: Dictionary with baseline statistics
                   Expected keys: score_mean, score_std, approval_rate
        """
        self.baseline_stats = stats
        baseline_file = os.path.join(self.log_dir, "baseline_stats.json")
        with open(baseline_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def log_decision(
        self,
        application_id: str,
        score: float,
        decision: str,
        metrics: Dict,
        decline_reasons: Optional[List[str]] = None,
        refer_reasons: Optional[List[str]] = None,
    ):
        """
        Log a scoring decision.
        
        Args:
            application_id: Unique application identifier
            score: Calculated score (0-100)
            decision: Decision outcome (APPROVE, REFER, DECLINE)
            metrics: Dictionary containing all calculated metrics
            decline_reasons: List of decline reasons if any
            refer_reasons: List of refer reasons if any
        """
        # Extract key metrics safely
        income = metrics.get("income", {})
        affordability = metrics.get("affordability", {})
        risk = metrics.get("risk", {})
        balance = metrics.get("balance", {})
        debt = metrics.get("debt", {})
        
        log_entry = DecisionLog(
            application_id=application_id,
            timestamp=datetime.now().isoformat(),
            score=score,
            decision=decision,
            income_stability=getattr(income, 'income_stability_score', 0) or 0,
            monthly_income=getattr(income, 'effective_monthly_income', 0) or 0,
            disposable_income=getattr(affordability, 'monthly_disposable', 0) or 0,
            dti_ratio=getattr(affordability, 'debt_to_income_ratio', 0) or 0,
            gambling_percentage=getattr(risk, 'gambling_percentage', 0) or 0,
            failed_payments_count=getattr(risk, 'failed_payments_count', 0) or 0,
            days_in_overdraft=getattr(balance, 'days_in_overdraft', 0) or 0,
            active_hcstc_count=getattr(debt, 'active_hcstc_count_90d', 0) or 0,
            decline_reasons=decline_reasons or [],
            refer_reasons=refer_reasons or [],
        )
        
        # Append to daily log file
        log_file = self._get_log_file()
        with open(log_file, 'a') as f:
            f.write(json.dumps(asdict(log_entry)) + '\n')
    
    def load_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DecisionLog]:
        """
        Load decision logs for a date range.
        
        Args:
            start_date: Start of date range (default: 7 days ago)
            end_date: End of date range (default: today)
        
        Returns:
            List of DecisionLog objects
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        logs = []
        current_date = start_date
        
        while current_date <= end_date:
            log_file = self._get_log_file(current_date)
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            logs.append(DecisionLog(**data))
            current_date += timedelta(days=1)
        
        return logs
    
    def generate_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> MonitoringReport:
        """
        Generate a monitoring report for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
        
        Returns:
            MonitoringReport with statistics and alerts
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        logs = self.load_logs(start_date, end_date)
        
        if not logs:
            return MonitoringReport(
                report_date=datetime.now().isoformat(),
                period_start=start_date.isoformat(),
                period_end=end_date.isoformat(),
                total_applications=0,
                approve_count=0, approve_rate=0,
                refer_count=0, refer_rate=0,
                decline_count=0, decline_rate=0,
                score_mean=0, score_median=0, score_std=0,
                score_min=0, score_max=0,
                avg_income_stability=0, avg_monthly_income=0,
                avg_disposable=0, avg_dti=0,
                score_drift_from_baseline=0, approval_rate_drift=0,
                alerts=["No data available for the selected period"],
            )
        
        # Calculate statistics
        scores = [log.score for log in logs]
        decisions = [log.decision for log in logs]
        
        total = len(logs)
        approve_count = sum(1 for d in decisions if d == "APPROVE")
        refer_count = sum(1 for d in decisions if d == "REFER")
        decline_count = sum(1 for d in decisions if d == "DECLINE")
        
        score_mean = statistics.mean(scores)
        score_median = statistics.median(scores)
        score_std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        avg_stability = statistics.mean([log.income_stability for log in logs])
        avg_income = statistics.mean([log.monthly_income for log in logs])
        avg_disposable = statistics.mean([log.disposable_income for log in logs])
        avg_dti = statistics.mean([log.dti_ratio for log in logs])
        
        # Calculate drift from baseline
        score_drift = 0.0
        approval_drift = 0.0
        alerts = []
        
        if self.baseline_stats:
            baseline_score = self.baseline_stats.get("score_mean", score_mean)
            baseline_approval = self.baseline_stats.get("approval_rate", approve_count / total)
            baseline_std = self.baseline_stats.get("score_std", score_std)
            
            # Score drift in standard deviations
            if baseline_std > 0:
                score_drift = (score_mean - baseline_score) / baseline_std
            
            # Approval rate drift
            approval_drift = (approve_count / total) - baseline_approval
            
            # Generate alerts
            if abs(score_drift) > 1.0:
                alerts.append(f"ALERT: Score distribution drift detected ({score_drift:.2f} std)")
            
            if abs(approval_drift) > 0.05:
                direction = "increased" if approval_drift > 0 else "decreased"
                alerts.append(f"ALERT: Approval rate {direction} by {abs(approval_drift)*100:.1f}%")
        
        # Check for other anomalies
        if decline_count / total > 0.3:
            alerts.append(f"WARNING: High decline rate ({decline_count/total*100:.1f}%)")
        
        if avg_stability < 50:
            alerts.append(f"WARNING: Low average income stability ({avg_stability:.1f})")
        
        return MonitoringReport(
            report_date=datetime.now().isoformat(),
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            total_applications=total,
            approve_count=approve_count,
            approve_rate=approve_count / total if total > 0 else 0,
            refer_count=refer_count,
            refer_rate=refer_count / total if total > 0 else 0,
            decline_count=decline_count,
            decline_rate=decline_count / total if total > 0 else 0,
            score_mean=round(score_mean, 2),
            score_median=round(score_median, 2),
            score_std=round(score_std, 2),
            score_min=min(scores),
            score_max=max(scores),
            avg_income_stability=round(avg_stability, 2),
            avg_monthly_income=round(avg_income, 2),
            avg_disposable=round(avg_disposable, 2),
            avg_dti=round(avg_dti, 2),
            score_drift_from_baseline=round(score_drift, 3),
            approval_rate_drift=round(approval_drift, 4),
            alerts=alerts,
        )
    
    def print_report(self, report: MonitoringReport):
        """Print a formatted monitoring report."""
        print("\n" + "="*60)
        print("SCORING MODEL MONITORING REPORT")
        print("="*60)
        print(f"Report Date: {report.report_date}")
        print(f"Period: {report.period_start} to {report.period_end}")
        print(f"Total Applications: {report.total_applications}")
        print()
        
        print("DECISION DISTRIBUTION")
        print("-"*40)
        print(f"  Approve: {report.approve_count} ({report.approve_rate*100:.1f}%)")
        print(f"  Refer:   {report.refer_count} ({report.refer_rate*100:.1f}%)")
        print(f"  Decline: {report.decline_count} ({report.decline_rate*100:.1f}%)")
        print()
        
        print("SCORE STATISTICS")
        print("-"*40)
        print(f"  Mean:   {report.score_mean:.1f}")
        print(f"  Median: {report.score_median:.1f}")
        print(f"  Std:    {report.score_std:.1f}")
        print(f"  Range:  {report.score_min:.1f} - {report.score_max:.1f}")
        print()
        
        print("KEY METRIC AVERAGES")
        print("-"*40)
        print(f"  Income Stability: {report.avg_income_stability:.1f}")
        print(f"  Monthly Income:   £{report.avg_monthly_income:.0f}")
        print(f"  Disposable:       £{report.avg_disposable:.0f}")
        print(f"  DTI Ratio:        {report.avg_dti:.1f}%")
        print()
        
        if self.baseline_stats:
            print("DRIFT INDICATORS")
            print("-"*40)
            print(f"  Score drift:    {report.score_drift_from_baseline:+.3f} std")
            print(f"  Approval drift: {report.approval_rate_drift*100:+.2f}%")
            print()
        
        if report.alerts:
            print("ALERTS")
            print("-"*40)
            for alert in report.alerts:
                print(f"  {alert}")
        else:
            print("No alerts - all metrics within normal ranges")
        
        print("="*60)


def main():
    """Example usage of the monitoring system."""
    monitor = ScoringMonitor()
    
    # Set baseline (would normally come from historical data)
    monitor.set_baseline({
        "score_mean": 64.0,
        "score_std": 14.0,
        "approval_rate": 0.40,
    })
    
    # Generate and print report
    report = monitor.generate_report()
    monitor.print_report(report)


if __name__ == "__main__":
    main()
