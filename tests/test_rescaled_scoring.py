"""
Test rescaled scoring configuration to validate 1.75x scaling (40→70 threshold).
This test validates the changes made to rescale all point values by 1.75x.
"""

import unittest
from openbanking_engine.config.scoring_config import SCORING_CONFIG
from openbanking_engine.scoring. scoring_engine import ScoringEngine, Decision
from openbanking_engine.scoring.feature_builder import (
    IncomeMetrics,
    ExpenseMetrics,
    DebtMetrics,
    AffordabilityMetrics,
    BalanceMetrics,
    RiskMetrics,
)


class TestRescaledScoring(unittest.TestCase):
    """Test rescaled scoring configuration thresholds."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scoring_engine = ScoringEngine()
        self.config = SCORING_CONFIG
    
    def test_rescaled_score_thresholds(self):
        """Test that score thresholds have been rescaled correctly."""
        score_ranges = self.config["score_ranges"]
        
        # Test APPROVE threshold (was ≥40, now ≥70)
        self.assertEqual(score_ranges["approve"]["min"], 70)
        self.assertEqual(score_ranges["approve"]["max"], 175)
        
        # Test REFER threshold (was 25-39, now 45-69)
        self.assertEqual(score_ranges["refer"]["min"], 45)
        self.assertEqual(score_ranges["refer"]["max"], 69)
        
        # Test DECLINE threshold (was <25, now <45)
        self.assertEqual(score_ranges["decline"]["min"], 0)
        self.assertEqual(score_ranges["decline"]["max"], 44)
    
    def test_rescaled_weights(self):
        """Test that scoring weights have been rescaled by 1.75x."""
        weights = self.config["weights"]
        
        # Affordability (45 * 1.75 = 78.75)
        self.assertEqual(weights["affordability"]["total"], 78.75)
        self.assertEqual(weights["affordability"]["dti_ratio"], 31.5)
        self.assertEqual(weights["affordability"]["disposable_income"], 26.25)
        self.assertEqual(weights["affordability"]["post_loan_affordability"], 21)
        
        # Income Quality (25 * 1.75 = 43.75)
        self.assertEqual(weights["income_quality"]["total"], 43.75)
        self.assertEqual(weights["income_quality"]["income_stability"], 21)
        self.assertEqual(weights["income_quality"]["income_regularity"], 14)
        self.assertEqual(weights["income_quality"]["income_verification"], 8.75)
        
        # Account Conduct (20 * 1.75 = 35)
        self.assertEqual(weights["account_conduct"]["total"], 35)
        self.assertEqual(weights["account_conduct"]["failed_payments"], 14)
        self.assertEqual(weights["account_conduct"]["overdraft_usage"], 12.25)
        self.assertEqual(weights["account_conduct"]["balance_management"], 8.75)
        
        # Risk Indicators (10 * 1.75 = 17.5)
        self.assertEqual(weights["risk_indicators"]["total"], 17.5)
        self.assertEqual(weights["risk_indicators"]["gambling_activity"], 8.75)
        self.assertEqual(weights["risk_indicators"]["hcstc_history"], 8.75)
    
    def test_rescaled_dti_thresholds(self):
        """Test that DTI ratio thresholds have been rescaled."""
        dti_thresholds = self.config["thresholds"]["dti_ratio"]
        
        self.assertEqual(dti_thresholds[0]["points"], 31.5)  # Was 18
        self.assertEqual(dti_thresholds[1]["points"], 26.25)  # Was 15
        self.assertEqual(dti_thresholds[2]["points"], 21)  # Was 12
        self.assertEqual(dti_thresholds[3]["points"], 14)  # Was 8
        self.assertEqual(dti_thresholds[4]["points"], 7)  # Was 4
    
    def test_rescaled_disposable_income_thresholds(self):
        """Test that disposable income thresholds have been rescaled."""
        disp_thresholds = self.config["thresholds"]["disposable_income"]
        
        self.assertEqual(disp_thresholds[0]["points"], 26.25)  # Was 15
        self.assertEqual(disp_thresholds[1]["points"], 22.75)  # Was 13
        self.assertEqual(disp_thresholds[2]["points"], 17.5)  # Was 10
        self.assertEqual(disp_thresholds[3]["points"], 10.5)  # Was 6
        self.assertEqual(disp_thresholds[4]["points"], 5.25)  # Was 3
    
    def test_rescaled_income_stability_thresholds(self):
        """Test that income stability thresholds have been rescaled."""
        stability_thresholds = self.config["thresholds"]["income_stability"]
        
        self.assertEqual(stability_thresholds[0]["points"], 21)  # Was 12
        self.assertEqual(stability_thresholds[1]["points"], 17.5)  # Was 10
        self.assertEqual(stability_thresholds[2]["points"], 12.25)  # Was 7
        self.assertEqual(stability_thresholds[3]["points"], 7)  # Was 4
    
    def test_rescaled_gambling_thresholds(self):
        """Test that gambling percentage thresholds have been rescaled."""
        gambling_thresholds = self.config["thresholds"]["gambling_percentage"]
        
        self.assertEqual(gambling_thresholds[0]["points"], 8.75)  # Was 5
        self.assertEqual(gambling_thresholds[1]["points"], 5.25)  # Was 3
        self.assertEqual(gambling_thresholds[2]["points"], 0)  # Was 0
        self.assertEqual(gambling_thresholds[3]["points"], -5.25)  # Was -3
        self.assertEqual(gambling_thresholds[4]["points"], -8.75)  # Was -5
    
    def test_rescaled_score_based_limits(self):
        """Test that score-based limits have been rescaled."""
        limits = self.config["score_based_limits"]
        
        # Test rescaled thresholds
        self.assertEqual(limits[0]["min_score"], 149)  # Was 85 (85 * 1.75 = 148.75, rounded to 149)
        self.assertEqual(limits[1]["min_score"], 123)  # Was 70 (70 * 1.75 = 122.5, rounded to 123)
        self.assertEqual(limits[2]["min_score"], 105)  # Was 60 (60 * 1.75 = 105)
        self.assertEqual(limits[3]["min_score"], 88)  # Was 50 (50 * 1.75 = 87.5, rounded to 88)
        self.assertEqual(limits[4]["min_score"], 70)  # Was 40 (40 * 1.75 = 70)
        
        # Verify loan amounts remain unchanged
        self.assertEqual(limits[0]["max_amount"], 1500)
        self.assertEqual(limits[1]["max_amount"], 1200)
        self.assertEqual(limits[2]["max_amount"], 800)
        self.assertEqual(limits[3]["max_amount"], 500)
        self.assertEqual(limits[4]["max_amount"], 300)
    
    def test_score_70_results_in_approval(self):
        """Test that a score of exactly 70 results in APPROVE decision."""
        decision, risk_level = self.scoring_engine._determine_decision(70)
        
        self.assertEqual(decision, Decision.APPROVE,
                        "Score 70 should result in APPROVE (new threshold)")
    
    def test_score_69_results_in_refer(self):
        """Test that a score of 69 (top of REFER range) results in REFER."""
        decision, risk_level = self.scoring_engine._determine_decision(69)
        
        self.assertEqual(decision, Decision.REFER,
                        "Score 69 should result in REFER")
    
    def test_score_45_results_in_refer(self):
        """Test that a score of 45 (bottom of REFER range) results in REFER."""
        decision, risk_level = self.scoring_engine._determine_decision(45)
        
        self.assertEqual(decision, Decision.REFER,
                        "Score 45 should result in REFER (new threshold)")
    
    def test_score_44_results_in_decline(self):
        """Test that a score of 44 (top of DECLINE range) results in DECLINE."""
        decision, risk_level = self.scoring_engine._determine_decision(44)
        
        self.assertEqual(decision, Decision.DECLINE,
                        "Score 44 should result in DECLINE")
    
    def test_max_possible_score_is_175(self):
        """Test that the maximum possible score is now 175."""
        # Create perfect metrics
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=5000,
                has_verifiable_income=True,
                income_stability_score=100,
                income_regularity_score=100
            ),
            "expenses": ExpenseMetrics(
                monthly_essential_total=100,
            ),
            "debt": DebtMetrics(
                monthly_debt_payments=0,
                active_hcstc_count=0,
                active_hcstc_count_90d=0
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=4900,
                debt_to_income_ratio=0,
                post_loan_disposable=4800,
                max_affordable_amount=1500
            ),
            "balance": BalanceMetrics(
                average_balance=5000,
                days_in_overdraft=0
            ),
            "risk": RiskMetrics(
                gambling_percentage=0,
                failed_payments_count=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=0
            ),
        }
        
        result = self.scoring_engine.score_application(
            metrics=metrics,
            requested_amount=300,
            requested_term=3,
            application_ref="TEST_MAX_SCORE"
        )
        
        # Score should be high but capped at 175
        self.assertGreater(result.score, 150, "Perfect metrics should result in high score")
        self.assertLessEqual(result.score, 175, "Score should be capped at 175")
    
    def test_scoring_proportions_maintained(self):
        """Test that scoring proportions are maintained after rescaling."""
        # Create a typical approval case
        metrics = {
            "income": IncomeMetrics(
                effective_monthly_income=1800,
                has_verifiable_income=True,
                income_stability_score=80,
                income_regularity_score=75
            ),
            "expenses": ExpenseMetrics(
                monthly_essential_total=800,
            ),
            "debt": DebtMetrics(
                monthly_debt_payments=250,
                active_hcstc_count=1,
                active_hcstc_count_90d=1
            ),
            "affordability": AffordabilityMetrics(
                monthly_disposable=750,
                debt_to_income_ratio=22,
                post_loan_disposable=600,
                max_affordable_amount=600
            ),
            "balance": BalanceMetrics(
                average_balance=300,
                days_in_overdraft=3
            ),
            "risk": RiskMetrics(
                gambling_percentage=1,
                failed_payments_count=0,
                failed_payments_count_45d=0,
                debt_collection_distinct=0
            ),
        }
        
        result = self.scoring_engine.score_application(
            metrics=metrics,
            requested_amount=400,
            requested_term=4,
            application_ref="TEST_PROPORTIONS"
        )
        
        # The score should be roughly 1.75x what it would have been before
        # With these good metrics, the score should be well above 70
        self.assertGreater(result.score, 70, "Score should be above APPROVE threshold")
        self.assertLessEqual(result.score, 175, "Score should not exceed maximum")
        
        # Decision should be APPROVE if score >= 70
        if result.score >= 70:
            self.assertEqual(result.decision, Decision.APPROVE,
                           f"Score {result.score} (≥70) should result in APPROVE")


if __name__ == "__main__":
    unittest.main()
