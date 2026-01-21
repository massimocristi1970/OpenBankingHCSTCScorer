#!/usr/bin/env python3
"""
A/B Testing Framework for HCSTC Scoring System

This module provides tools for safely testing scoring model changes
using controlled experiments.

Usage:
    from ab_testing import ABTestManager, ScoringExperiment
    
    # Create an experiment
    experiment = ScoringExperiment(
        name="income_stability_weight_increase",
        description="Test increasing income stability weight from 12 to 20",
        control_config=CURRENT_CONFIG,
        treatment_config=NEW_CONFIG,
        traffic_split=0.10,  # 10% to treatment
    )
    
    # Run the experiment
    manager = ABTestManager()
    manager.register_experiment(experiment)
    config = manager.get_config(application_id)
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import random
import statistics


class ExperimentStatus(Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ExperimentResult:
    """Results from an A/B test experiment."""
    experiment_name: str
    status: str
    start_date: str
    end_date: Optional[str]
    
    # Sample sizes
    control_count: int
    treatment_count: int
    
    # Decision rates
    control_approve_rate: float
    treatment_approve_rate: float
    control_refer_rate: float
    treatment_refer_rate: float
    control_decline_rate: float
    treatment_decline_rate: float
    
    # Score statistics
    control_score_mean: float
    treatment_score_mean: float
    control_score_std: float
    treatment_score_std: float
    
    # Statistical significance (simplified)
    score_diff: float
    approval_rate_diff: float
    is_significant: bool
    p_value_estimate: float
    
    # Recommendation
    recommendation: str


@dataclass
class ScoringExperiment:
    """
    A/B test experiment configuration.
    
    Attributes:
        name: Unique experiment identifier
        description: Human-readable description
        control_config: Configuration for control group
        treatment_config: Configuration for treatment group
        traffic_split: Fraction of traffic for treatment (0.0-1.0)
        min_sample_size: Minimum samples before analysis
        max_duration_days: Maximum experiment duration
    """
    name: str
    description: str
    control_config: Dict
    treatment_config: Dict
    traffic_split: float = 0.10
    min_sample_size: int = 100
    max_duration_days: int = 14
    status: ExperimentStatus = ExperimentStatus.DRAFT
    start_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate experiment configuration."""
        if not 0 < self.traffic_split <= 0.5:
            raise ValueError("traffic_split must be between 0 and 0.5")


@dataclass
class AssignmentLog:
    """Log entry for experiment assignment."""
    application_id: str
    experiment_name: str
    variant: str  # "control" or "treatment"
    timestamp: str
    score: Optional[float] = None
    decision: Optional[str] = None


class ABTestManager:
    """
    Manages A/B test experiments for the scoring system.
    
    Features:
    - Deterministic assignment based on application ID
    - Consistent assignment for the same application
    - Traffic splitting with configurable ratios
    - Experiment lifecycle management
    - Results analysis
    """
    
    def __init__(self, storage_dir: str = "./ab_experiments"):
        """
        Initialize the A/B test manager.
        
        Args:
            storage_dir: Directory to store experiment data
        """
        self.storage_dir = storage_dir
        self.experiments: Dict[str, ScoringExperiment] = {}
        self._ensure_storage_dir()
        self._load_experiments()
    
    def _ensure_storage_dir(self):
        """Create storage directory if it doesn't exist."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_experiment_file(self, name: str) -> str:
        """Get file path for experiment data."""
        return os.path.join(self.storage_dir, f"experiment_{name}.json")
    
    def _get_assignments_file(self, name: str) -> str:
        """Get file path for assignment logs."""
        return os.path.join(self.storage_dir, f"assignments_{name}.jsonl")
    
    def _load_experiments(self):
        """Load all experiments from storage."""
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("experiment_") and filename.endswith(".json"):
                filepath = os.path.join(self.storage_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    # Convert status string back to enum
                    if 'status' in data:
                        data['status'] = ExperimentStatus(data['status'])
                    experiment = ScoringExperiment(**data)
                    self.experiments[experiment.name] = experiment
    
    def _save_experiment(self, experiment: ScoringExperiment):
        """Save experiment to storage."""
        filepath = self._get_experiment_file(experiment.name)
        data = asdict(experiment)
        data['status'] = experiment.status.value  # Convert enum to string
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_experiment(self, experiment: ScoringExperiment) -> bool:
        """
        Register a new experiment.
        
        Args:
            experiment: Experiment configuration
        
        Returns:
            True if registered successfully
        """
        if experiment.name in self.experiments:
            raise ValueError(f"Experiment '{experiment.name}' already exists")
        
        self.experiments[experiment.name] = experiment
        self._save_experiment(experiment)
        return True
    
    def start_experiment(self, name: str) -> bool:
        """
        Start an experiment.
        
        Args:
            name: Experiment name
        
        Returns:
            True if started successfully
        """
        if name not in self.experiments:
            raise ValueError(f"Experiment '{name}' not found")
        
        experiment = self.experiments[name]
        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Can only start experiments in DRAFT status")
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.now().isoformat()
        self._save_experiment(experiment)
        return True
    
    def stop_experiment(self, name: str, complete: bool = True) -> bool:
        """
        Stop an experiment.
        
        Args:
            name: Experiment name
            complete: If True, mark as completed; if False, mark as cancelled
        
        Returns:
            True if stopped successfully
        """
        if name not in self.experiments:
            raise ValueError(f"Experiment '{name}' not found")
        
        experiment = self.experiments[name]
        experiment.status = ExperimentStatus.COMPLETED if complete else ExperimentStatus.CANCELLED
        self._save_experiment(experiment)
        return True
    
    def _hash_to_bucket(self, application_id: str, experiment_name: str) -> float:
        """
        Deterministically hash application ID to a bucket [0, 1).
        
        This ensures the same application always gets the same variant.
        """
        # Combine application ID and experiment name for isolation
        key = f"{experiment_name}:{application_id}"
        hash_bytes = hashlib.sha256(key.encode()).digest()
        # Use first 8 bytes as integer and normalize to [0, 1)
        hash_int = int.from_bytes(hash_bytes[:8], byteorder='big')
        return hash_int / (2**64)
    
    def get_variant(self, application_id: str, experiment_name: str) -> str:
        """
        Get the variant assignment for an application.
        
        Args:
            application_id: Unique application identifier
            experiment_name: Name of the experiment
        
        Returns:
            "control" or "treatment"
        """
        if experiment_name not in self.experiments:
            return "control"  # Default to control if experiment not found
        
        experiment = self.experiments[experiment_name]
        
        # Only running experiments assign to treatment
        if experiment.status != ExperimentStatus.RUNNING:
            return "control"
        
        bucket = self._hash_to_bucket(application_id, experiment_name)
        return "treatment" if bucket < experiment.traffic_split else "control"
    
    def get_config(
        self,
        application_id: str,
        experiment_name: Optional[str] = None,
    ) -> Tuple[Dict, str, str]:
        """
        Get the scoring configuration for an application.
        
        Args:
            application_id: Unique application identifier
            experiment_name: Specific experiment to use (optional)
        
        Returns:
            Tuple of (config, experiment_name, variant)
        """
        # If no specific experiment, find running experiments
        if experiment_name is None:
            running = [
                e for e in self.experiments.values()
                if e.status == ExperimentStatus.RUNNING
            ]
            if not running:
                return {}, "", "control"
            experiment = running[0]  # Use first running experiment
        else:
            if experiment_name not in self.experiments:
                return {}, experiment_name, "control"
            experiment = self.experiments[experiment_name]
        
        variant = self.get_variant(application_id, experiment.name)
        
        if variant == "treatment":
            config = experiment.treatment_config
        else:
            config = experiment.control_config
        
        return config, experiment.name, variant
    
    def log_assignment(
        self,
        application_id: str,
        experiment_name: str,
        variant: str,
        score: Optional[float] = None,
        decision: Optional[str] = None,
    ):
        """
        Log an experiment assignment with outcome.
        
        Args:
            application_id: Application identifier
            experiment_name: Experiment name
            variant: Assigned variant
            score: Calculated score (optional)
            decision: Final decision (optional)
        """
        log_entry = AssignmentLog(
            application_id=application_id,
            experiment_name=experiment_name,
            variant=variant,
            timestamp=datetime.now().isoformat(),
            score=score,
            decision=decision,
        )
        
        filepath = self._get_assignments_file(experiment_name)
        with open(filepath, 'a') as f:
            f.write(json.dumps(asdict(log_entry)) + '\n')
    
    def load_assignments(self, experiment_name: str) -> List[AssignmentLog]:
        """Load all assignments for an experiment."""
        filepath = self._get_assignments_file(experiment_name)
        assignments = []
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        assignments.append(AssignmentLog(**data))
        
        return assignments
    
    def analyze_experiment(self, experiment_name: str) -> ExperimentResult:
        """
        Analyze experiment results.
        
        Args:
            experiment_name: Name of the experiment to analyze
        
        Returns:
            ExperimentResult with statistics and recommendation
        """
        if experiment_name not in self.experiments:
            raise ValueError(f"Experiment '{experiment_name}' not found")
        
        experiment = self.experiments[experiment_name]
        assignments = self.load_assignments(experiment_name)
        
        # Separate control and treatment
        control = [a for a in assignments if a.variant == "control" and a.score is not None]
        treatment = [a for a in assignments if a.variant == "treatment" and a.score is not None]
        
        if not control or not treatment:
            return ExperimentResult(
                experiment_name=experiment_name,
                status=experiment.status.value,
                start_date=experiment.start_date or "",
                end_date=None,
                control_count=len(control),
                treatment_count=len(treatment),
                control_approve_rate=0, treatment_approve_rate=0,
                control_refer_rate=0, treatment_refer_rate=0,
                control_decline_rate=0, treatment_decline_rate=0,
                control_score_mean=0, treatment_score_mean=0,
                control_score_std=0, treatment_score_std=0,
                score_diff=0, approval_rate_diff=0,
                is_significant=False, p_value_estimate=1.0,
                recommendation="Insufficient data to analyze",
            )
        
        # Calculate metrics
        control_scores = [a.score for a in control]
        treatment_scores = [a.score for a in treatment]
        
        control_score_mean = statistics.mean(control_scores)
        treatment_score_mean = statistics.mean(treatment_scores)
        control_score_std = statistics.stdev(control_scores) if len(control_scores) > 1 else 0
        treatment_score_std = statistics.stdev(treatment_scores) if len(treatment_scores) > 1 else 0
        
        # Decision rates
        def calc_rates(assignments):
            total = len(assignments)
            if total == 0:
                return 0, 0, 0
            approve = sum(1 for a in assignments if a.decision == "APPROVE") / total
            refer = sum(1 for a in assignments if a.decision == "REFER") / total
            decline = sum(1 for a in assignments if a.decision == "DECLINE") / total
            return approve, refer, decline
        
        c_approve, c_refer, c_decline = calc_rates(control)
        t_approve, t_refer, t_decline = calc_rates(treatment)
        
        # Statistical significance (simplified z-test approximation)
        score_diff = treatment_score_mean - control_score_mean
        approval_rate_diff = t_approve - c_approve
        
        # Simplified significance test
        pooled_std = ((control_score_std**2 + treatment_score_std**2) / 2) ** 0.5
        if pooled_std > 0 and len(control) > 30 and len(treatment) > 30:
            z_score = abs(score_diff) / (pooled_std / (min(len(control), len(treatment))**0.5))
            # Rough p-value estimate
            p_value = max(0.001, min(1.0, 2 * (1 - min(0.9999, 0.5 + 0.4 * min(z_score/3, 1)))))
            is_significant = p_value < 0.05
        else:
            p_value = 1.0
            is_significant = False
        
        # Generate recommendation
        if len(control) < experiment.min_sample_size or len(treatment) < experiment.min_sample_size:
            recommendation = "Continue collecting data - insufficient sample size"
        elif not is_significant:
            recommendation = "No significant difference detected - consider extending experiment"
        elif score_diff > 0 and approval_rate_diff > 0:
            recommendation = "Treatment shows improvement - consider rolling out"
        elif score_diff < 0 or approval_rate_diff < -0.05:
            recommendation = "Treatment shows degradation - do not roll out"
        else:
            recommendation = "Mixed results - review manually before deciding"
        
        return ExperimentResult(
            experiment_name=experiment_name,
            status=experiment.status.value,
            start_date=experiment.start_date or "",
            end_date=datetime.now().isoformat() if experiment.status != ExperimentStatus.RUNNING else None,
            control_count=len(control),
            treatment_count=len(treatment),
            control_approve_rate=round(c_approve, 4),
            treatment_approve_rate=round(t_approve, 4),
            control_refer_rate=round(c_refer, 4),
            treatment_refer_rate=round(t_refer, 4),
            control_decline_rate=round(c_decline, 4),
            treatment_decline_rate=round(t_decline, 4),
            control_score_mean=round(control_score_mean, 2),
            treatment_score_mean=round(treatment_score_mean, 2),
            control_score_std=round(control_score_std, 2),
            treatment_score_std=round(treatment_score_std, 2),
            score_diff=round(score_diff, 2),
            approval_rate_diff=round(approval_rate_diff, 4),
            is_significant=is_significant,
            p_value_estimate=round(p_value, 4),
            recommendation=recommendation,
        )
    
    def print_analysis(self, result: ExperimentResult):
        """Print formatted experiment analysis."""
        print("\n" + "="*60)
        print(f"A/B TEST ANALYSIS: {result.experiment_name}")
        print("="*60)
        print(f"Status: {result.status}")
        print(f"Start Date: {result.start_date}")
        print()
        
        print("SAMPLE SIZES")
        print("-"*40)
        print(f"  Control:   {result.control_count}")
        print(f"  Treatment: {result.treatment_count}")
        print()
        
        print("APPROVAL RATES")
        print("-"*40)
        print(f"  Control:   {result.control_approve_rate*100:.1f}%")
        print(f"  Treatment: {result.treatment_approve_rate*100:.1f}%")
        print(f"  Difference: {result.approval_rate_diff*100:+.2f}%")
        print()
        
        print("SCORE STATISTICS")
        print("-"*40)
        print(f"  Control Mean:   {result.control_score_mean:.1f} (std: {result.control_score_std:.1f})")
        print(f"  Treatment Mean: {result.treatment_score_mean:.1f} (std: {result.treatment_score_std:.1f})")
        print(f"  Score Diff:     {result.score_diff:+.2f}")
        print()
        
        print("STATISTICAL SIGNIFICANCE")
        print("-"*40)
        print(f"  p-value (est.): {result.p_value_estimate:.4f}")
        print(f"  Significant:    {'Yes' if result.is_significant else 'No'}")
        print()
        
        print("RECOMMENDATION")
        print("-"*40)
        print(f"  {result.recommendation}")
        print("="*60)
    
    def list_experiments(self) -> List[Dict]:
        """List all experiments with their status."""
        return [
            {
                "name": exp.name,
                "status": exp.status.value,
                "description": exp.description,
                "traffic_split": exp.traffic_split,
                "start_date": exp.start_date,
            }
            for exp in self.experiments.values()
        ]


def main():
    """Example usage of the A/B testing framework."""
    manager = ABTestManager()
    
    # Example: Create a new experiment
    experiment = ScoringExperiment(
        name="test_experiment",
        description="Test experiment for demonstration",
        control_config={"version": "1.0", "income_stability_weight": 12},
        treatment_config={"version": "2.0", "income_stability_weight": 20},
        traffic_split=0.20,
    )
    
    try:
        manager.register_experiment(experiment)
        print(f"Registered experiment: {experiment.name}")
    except ValueError as e:
        print(f"Experiment already exists: {e}")
    
    # List all experiments
    print("\nAll Experiments:")
    for exp in manager.list_experiments():
        print(f"  - {exp['name']}: {exp['status']}")
    
    # Example assignment
    app_id = "APP_12345"
    config, exp_name, variant = manager.get_config(app_id)
    print(f"\nApplication {app_id} assigned to: {variant}")


if __name__ == "__main__":
    main()
