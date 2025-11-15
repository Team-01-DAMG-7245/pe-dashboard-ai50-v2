# Workflow Tests

This directory contains test suites for the LangGraph workflow implementation.

## Test Files

### `test_workflow_branches.py`

Comprehensive test suite for Lab 17 workflow with conditional branching.

**Test Coverage:**
- Unit tests for each node function
- Integration tests for complete workflow paths
- State transition verification
- Conditional routing tests
- Error handling tests

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
# Run all workflow tests
pytest tests/test_workflow_branches.py -v

# Run with coverage
pytest tests/test_workflow_branches.py --cov=src.workflows --cov-report=html

# Run specific test class
pytest tests/test_workflow_branches.py::TestSafePathWorkflow -v

# Run specific test
pytest tests/test_workflow_branches.py::TestPlannerNode::test_planner_creates_execution_plan -v
```

### Test Structure

```
tests/test_workflow_branches.py
├── TestPlannerNode
│   ├── test_planner_creates_execution_plan
│   ├── test_planner_uses_existing_run_id
│   └── test_planner_requires_company_id
├── TestDataGeneratorNode
│   ├── test_data_generator_loads_structured_data
│   └── test_data_generator_handles_rag_api_error
├── TestEvaluatorNode
│   ├── test_evaluator_generates_dashboard
│   └── test_evaluator_handles_api_error
├── TestRiskDetectorNode
│   ├── test_risk_detector_no_risks
│   ├── test_risk_detector_high_risk_layoffs
│   ├── test_risk_detector_high_risk_keywords_in_dashboard
│   ├── test_risk_detector_rag_insights_keywords
│   └── test_risk_detector_multiple_medium_risks
├── TestHITLApprovalNode
│   └── test_hitl_approval_logs_risks
├── TestRoutingFunction
│   ├── test_routing_safe_path
│   └── test_routing_hitl_path
├── TestSafePathWorkflow
│   └── test_safe_path_complete_flow
├── TestHighRiskPathWorkflow
│   └── test_high_risk_path_complete_flow
├── TestGraphConstruction
│   ├── test_graph_creation
│   └── test_graph_has_all_nodes
└── TestScoreDashboard
    ├── test_score_dashboard_with_all_sections
    ├── test_score_dashboard_empty
    └── test_score_dashboard_missing_sections
```

## Mocking Strategy

Tests use `unittest.mock` to mock:
- **API calls** (`requests.post`) - Mocked to return test data
- **File I/O** (`open`, `json.load`) - Mocked to return test payloads
- **External dependencies** - All external calls are mocked

## Test Fixtures

- `mock_structured_payload` - Safe company data (no risks)
- `mock_structured_payload_high_risk` - High-risk company data
- `mock_rag_response` - RAG API response
- `mock_dashboard_response` - Dashboard API response
- `mock_rag_response_with_risks` - RAG response with risk keywords

## Expected Test Results

All tests should pass when:
- LangGraph is installed (or tests skip graph construction)
- Mocking is properly configured
- Test data fixtures are available

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Workflow Tests
  run: |
    pip install pytest pytest-cov
    pytest tests/test_workflow_branches.py --cov=src.workflows --cov-report=xml
```

## Troubleshooting

### Import Errors

If you see import errors, ensure:
1. `src` directory is in Python path
2. All dependencies are installed
3. Working directory is project root

### LangGraph Not Available

Some tests will skip if LangGraph is not installed:
```python
pytest.skip("LangGraph not available - skipping graph construction test")
```

### Mock Failures

If mocks fail:
1. Check that `@patch` decorators match import paths
2. Verify mock return values match expected structure
3. Ensure fixtures are properly scoped

