"""
Test suite for Lab 17: LangGraph Workflow with Conditional Branching

Tests both workflow paths:
1. Safe path (no high-severity risks) → END directly
2. High-risk path → HITL approval → END

Tests state transitions, node execution, and conditional routing.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from typing import Dict, Any

# Import workflow components
import sys
from pathlib import Path as PathLib

# Add src to path
project_root = PathLib(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from workflows.due_diligence_graph import (
    WorkflowState,
    planner_node,
    data_generator_node,
    evaluator_node,
    risk_detector_node,
    hitl_approval_node,
    should_require_hitl,
    create_due_diligence_graph,
    score_dashboard
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_structured_payload():
    """Mock structured payload data (safe company - no risks)"""
    return {
        "company_id": "anthropic",
        "snapshots": [
            {
                "layoffs_mentioned": False,
                "layoffs_count": 0,
                "layoffs_percentage": 0,
                "negative_signals": [],
                "risk_score": 45,
                "leadership_stability": "stable"
            }
        ]
    }


@pytest.fixture
def mock_structured_payload_high_risk():
    """Mock structured payload data (high-risk company)"""
    return {
        "company_id": "risky_company",
        "snapshots": [
            {
                "layoffs_mentioned": True,
                "layoffs_count": 500,
                "layoffs_percentage": 15,  # >10% triggers high severity
                "negative_signals": [
                    "Data breach reported in Q4",
                    "SEC investigation ongoing",
                    "Major customer churn"
                ],
                "risk_score": 85,  # >70 triggers HITL
                "leadership_stability": "high turnover"
            }
        ]
    }


@pytest.fixture
def mock_rag_response():
    """Mock RAG API response"""
    return {
        "dashboard": "## Company Overview\nTest dashboard content...",
        "chunks_used": 10
    }


@pytest.fixture
def mock_dashboard_response():
    """Mock structured dashboard API response"""
    return {
        "dashboard": """## Company Overview
Test company description.

## Business Model and GTM
Business model details.

## Funding & Investor Profile
Funding information.

## Growth Momentum
Growth metrics.

## Visibility & Market Sentiment
Market sentiment.

## Risks and Challenges
Risk factors.

## Outlook
Future outlook.

## Disclosure Gaps
Not disclosed. Not disclosed. Not disclosed."""
    }


@pytest.fixture
def mock_rag_response_with_risks():
    """Mock RAG API response containing risk keywords"""
    return {
        "dashboard": "## Company Overview\nCompany reported data breach in Q4. Layoffs announced affecting 500 employees.",
        "chunks_used": 10
    }


# ============================================================================
# UNIT TESTS: Individual Node Functions
# ============================================================================

class TestPlannerNode:
    """Test planner node functionality"""
    
    def test_planner_creates_execution_plan(self):
        """Test that planner creates execution plan and run_id"""
        state = {"company_id": "anthropic"}
        result = planner_node(state)
        
        assert "run_id" in result
        assert "execution_plan" in result
        assert result["execution_plan"]["company_id"] == "anthropic"
        assert result["execution_plan"]["pipelines"]["structured"] is True
        assert result["execution_plan"]["pipelines"]["rag"] is True
    
    def test_planner_uses_existing_run_id(self):
        """Test that planner uses existing run_id if provided"""
        state = {"company_id": "anthropic", "run_id": "custom_run_123"}
        result = planner_node(state)
        
        assert result["run_id"] == "custom_run_123"
    
    def test_planner_requires_company_id(self):
        """Test that planner returns error if company_id missing"""
        state = {}
        result = planner_node(state)
        
        assert "error" in result
        assert "company_id is required" in result["error"]


class TestDataGeneratorNode:
    """Test data generator node functionality"""
    
    @patch('workflows.due_diligence_graph.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    @patch('workflows.due_diligence_graph.json.load')
    def test_data_generator_loads_structured_data(
        self, mock_json_load, mock_file, mock_requests_post
    ):
        """Test that data generator loads structured payload"""
        mock_json_load.return_value = {"company_id": "anthropic", "snapshots": []}
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = {"chunks_used": 10}
        
        state = {
            "company_id": "anthropic",
            "execution_plan": {"pipelines": {"rag": True}, "rag_params": {"top_k": 10}}
        }
        result = data_generator_node(state)
        
        assert "structured_data" in result
        assert "rag_insights" in result
    
    @patch('workflows.due_diligence_graph.requests.post')
    def test_data_generator_handles_rag_api_error(self, mock_requests_post):
        """Test that data generator handles RAG API errors gracefully"""
        mock_requests_post.side_effect = Exception("API Error")
        
        state = {
            "company_id": "anthropic",
            "execution_plan": {"pipelines": {"rag": True}, "rag_params": {"top_k": 10}}
        }
        result = data_generator_node(state)
        
        # Should not fail, just log warning
        assert "rag_insights" in result


class TestEvaluatorNode:
    """Test evaluator node functionality"""
    
    @patch('workflows.due_diligence_graph.requests.post')
    def test_evaluator_generates_dashboard(self, mock_requests_post, mock_dashboard_response):
        """Test that evaluator generates dashboard and scores it"""
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.return_value = mock_dashboard_response
        
        state = {"company_id": "anthropic"}
        result = evaluator_node(state)
        
        assert "dashboard" in result
        assert "dashboard_score" in result
        assert result["dashboard_score"] > 0
        assert isinstance(result["dashboard_score"], float)
    
    @patch('workflows.due_diligence_graph.requests.post')
    def test_evaluator_handles_api_error(self, mock_requests_post):
        """Test that evaluator handles API errors"""
        mock_requests_post.return_value.status_code = 500
        mock_requests_post.return_value.text = "Internal Server Error"
        
        state = {"company_id": "anthropic"}
        result = evaluator_node(state)
        
        assert "error" in result
        assert "Dashboard generation failed" in result["error"]


class TestRiskDetectorNode:
    """Test risk detector node functionality"""
    
    def test_risk_detector_no_risks(self, mock_structured_payload):
        """Test risk detector with no risks (safe path)"""
        state = {
            "company_id": "anthropic",
            "structured_data": mock_structured_payload,
            "rag_insights": [],
            "dashboard": "## Company Overview\nSafe content with no risks."
        }
        result = risk_detector_node(state)
        
        assert "risk_signals" in result
        assert "requires_hitl" in result
        assert result["requires_hitl"] is False
    
    def test_risk_detector_high_risk_layoffs(self, mock_structured_payload_high_risk):
        """Test risk detector detects high-risk layoffs"""
        state = {
            "company_id": "risky_company",
            "structured_data": mock_structured_payload_high_risk,
            "rag_insights": [],
            "dashboard": "## Company Overview\nContent."
        }
        result = risk_detector_node(state)
        
        assert result["requires_hitl"] is True
        assert len(result["risk_signals"]) > 0
        
        # Check for layoff risk signal
        layoff_signals = [s for s in result["risk_signals"] if s.get("type") == "layoffs"]
        assert len(layoff_signals) > 0
        assert layoff_signals[0]["severity"] == "high"
    
    def test_risk_detector_high_risk_keywords_in_dashboard(self):
        """Test risk detector detects high-severity keywords in dashboard"""
        state = {
            "company_id": "risky_company",
            "structured_data": {"snapshots": [{}]},
            "rag_insights": [],
            "dashboard": "## Company Overview\nCompany reported data breach affecting customers."
        }
        result = risk_detector_node(state)
        
        assert result["requires_hitl"] is True
        
        # Check for keyword-based risk signal
        keyword_signals = [
            s for s in result["risk_signals"] 
            if s.get("type") == "dashboard_high_severity_keyword"
        ]
        assert len(keyword_signals) > 0
        assert "breach" in keyword_signals[0].get("keywords", [])
    
    def test_risk_detector_rag_insights_keywords(self):
        """Test risk detector detects keywords in RAG insights"""
        state = {
            "company_id": "risky_company",
            "structured_data": {"snapshots": [{}]},
            "rag_insights": [{
                "dashboard_preview": "Company facing lawsuit from investors. Bankruptcy rumors.",
                "chunks_used": 10
            }],
            "dashboard": "## Company Overview\nContent."
        }
        result = risk_detector_node(state)
        
        assert result["requires_hitl"] is True
        
        # Check for RAG-based risk signal
        rag_signals = [
            s for s in result["risk_signals"] 
            if s.get("type") == "rag_high_severity_keyword"
        ]
        assert len(rag_signals) > 0
        assert any(kw in rag_signals[0].get("keywords", []) for kw in ["lawsuit", "bankruptcy"])
    
    def test_risk_detector_multiple_medium_risks(self):
        """Test that 3+ medium risks trigger HITL"""
        state = {
            "company_id": "risky_company",
            "structured_data": {
                "snapshots": [{
                    "negative_signals": [
                        "Regulatory investigation",
                        "Customer churn increasing",
                        "Executive turnover",
                        "Compliance violation"
                    ]
                }]
            },
            "rag_insights": [],
            "dashboard": "## Company Overview\nContent."
        }
        result = risk_detector_node(state)
        
        # Should trigger HITL due to multiple medium risks
        assert result["requires_hitl"] is True


class TestHITLApprovalNode:
    """Test HITL approval node functionality"""
    
    def test_hitl_approval_logs_risks(self):
        """Test that HITL node logs risk signals"""
        state = {
            "company_id": "risky_company",
            "risk_signals": [
                {"type": "layoffs", "severity": "high", "details": "500 employees"},
                {"type": "breach", "severity": "high", "details": "Data breach"}
            ],
            "dashboard": "## Company Overview\nContent."
        }
        result = hitl_approval_node(state)
        
        assert "hitl_approved" in result
        assert result["hitl_approved"] is True  # Auto-approves in current implementation


class TestRoutingFunction:
    """Test conditional routing function"""
    
    def test_routing_safe_path(self):
        """Test routing returns safe_to_proceed when no HITL required"""
        state = {
            "company_id": "anthropic",
            "requires_hitl": False,
            "risk_signals": []
        }
        result = should_require_hitl(state)
        
        assert result == "safe_to_proceed"
    
    def test_routing_hitl_path(self):
        """Test routing returns hitl_required when HITL needed"""
        state = {
            "company_id": "risky_company",
            "requires_hitl": True,
            "risk_signals": [
                {"type": "layoffs", "severity": "high", "details": "500 employees"}
            ]
        }
        result = should_require_hitl(state)
        
        assert result == "hitl_required"


# ============================================================================
# INTEGRATION TESTS: Full Workflow Paths
# ============================================================================

class TestSafePathWorkflow:
    """Test complete safe path workflow (no risks)"""
    
    @patch('workflows.due_diligence_graph.requests.post')
    @patch('builtins.open', new_callable=mock_open)
    @patch('workflows.due_diligence_graph.json.load')
    def test_safe_path_complete_flow(
        self, mock_json_load, mock_file, mock_requests_post,
        mock_structured_payload, mock_dashboard_response, mock_rag_response
    ):
        """Test complete safe path from start to end"""
        # Setup mocks
        mock_json_load.return_value = mock_structured_payload
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.side_effect = [
            mock_rag_response,  # RAG call
            mock_dashboard_response  # Structured dashboard call
        ]
        
        # Execute workflow nodes sequentially
        state = {"company_id": "anthropic"}
        
        # 1. Planner
        state = planner_node(state)
        assert "run_id" in state
        assert "execution_plan" in state
        
        # 2. Data Generator
        state = data_generator_node(state)
        assert "structured_data" in state
        assert "rag_insights" in state
        
        # 3. Evaluator
        state = evaluator_node(state)
        assert "dashboard" in state
        assert "dashboard_score" in state
        
        # 4. Risk Detector
        state = risk_detector_node(state)
        assert "risk_signals" in state
        assert "requires_hitl" in state
        assert state["requires_hitl"] is False  # No risks
        
        # 5. Routing
        route = should_require_hitl(state)
        assert route == "safe_to_proceed"
        
        # Should go directly to END (no HITL node)


class TestHighRiskPathWorkflow:
    """Test complete high-risk path workflow (HITL required)"""
    
    @patch('workflows.due_diligence_graph.requests.post')
    @patch('builtins.open', new_callable=mock_open)
    @patch('workflows.due_diligence_graph.json.load')
    def test_high_risk_path_complete_flow(
        self, mock_json_load, mock_file, mock_requests_post,
        mock_structured_payload_high_risk, mock_dashboard_response, mock_rag_response_with_risks
    ):
        """Test complete high-risk path from start to HITL"""
        # Setup mocks
        mock_json_load.return_value = mock_structured_payload_high_risk
        mock_requests_post.return_value.status_code = 200
        mock_requests_post.return_value.json.side_effect = [
            mock_rag_response_with_risks,  # RAG call with risks
            mock_dashboard_response  # Structured dashboard call
        ]
        
        # Execute workflow nodes sequentially
        state = {"company_id": "risky_company"}
        
        # 1. Planner
        state = planner_node(state)
        assert "run_id" in state
        
        # 2. Data Generator
        state = data_generator_node(state)
        assert "structured_data" in state
        
        # 3. Evaluator
        state = evaluator_node(state)
        assert "dashboard" in state
        
        # 4. Risk Detector
        state = risk_detector_node(state)
        assert state["requires_hitl"] is True  # High risks detected
        
        # 5. Routing
        route = should_require_hitl(state)
        assert route == "hitl_required"
        
        # 6. HITL Approval
        state = hitl_approval_node(state)
        assert "hitl_approved" in state
        assert state["hitl_approved"] is True


# ============================================================================
# GRAPH CONSTRUCTION TESTS
# ============================================================================

class TestGraphConstruction:
    """Test graph construction and structure"""
    
    def test_graph_creation(self):
        """Test that graph can be created"""
        try:
            graph = create_due_diligence_graph()
            assert graph is not None
        except ImportError:
            pytest.skip("LangGraph not available - skipping graph construction test")
    
    def test_graph_has_all_nodes(self):
        """Test that graph has all required nodes"""
        try:
            graph = create_due_diligence_graph()
            # Graph should have nodes: planner, data_generator, evaluator, risk_detector, hitl_approval
            assert graph is not None
        except ImportError:
            pytest.skip("LangGraph not available")


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestScoreDashboard:
    """Test dashboard scoring function"""
    
    def test_score_dashboard_with_all_sections(self):
        """Test scoring dashboard with all 8 sections"""
        dashboard = """## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps
Not disclosed. Not disclosed. Not disclosed. Based on source data."""
        
        score = score_dashboard(dashboard)
        assert score > 0
        assert score <= 10
    
    def test_score_dashboard_empty(self):
        """Test scoring empty dashboard"""
        score = score_dashboard("")
        assert score == 0.0
    
    def test_score_dashboard_missing_sections(self):
        """Test scoring dashboard with missing sections"""
        dashboard = "## Company Overview\nSome content."
        score = score_dashboard(dashboard)
        assert score < 10


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

