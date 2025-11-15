#!/usr/bin/env python3
"""
Phase 3 Validation Script
Validates that all Phase 3 components (Labs 16, 17, 18) are complete and working.

This script checks:
- ReAct Logging (Lab 16)
- Graph Workflow (Lab 17)
- HITL Integration (Lab 18)
- Testing completeness
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any
import subprocess

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_check(name: str, status: bool, details: str = ""):
    """Print a check result"""
    # Use ASCII-safe symbols for Windows compatibility
    symbol = f"{Colors.GREEN}[OK]{Colors.RESET}" if status else f"{Colors.RED}[X]{Colors.RESET}"
    status_text = f"{Colors.GREEN}PASS{Colors.RESET}" if status else f"{Colors.RED}FAIL{Colors.RESET}"
    print(f"  {symbol} {name:<50} [{status_text}]")
    if details and not status:
        print(f"    {Colors.YELLOW}-> {details}{Colors.RESET}")

def check_file_exists(filepath: Path, description: str) -> Tuple[bool, str]:
    """Check if a file exists"""
    if filepath.exists():
        return True, f"Found: {filepath}"
    return False, f"Missing: {filepath}"

def check_file_content(filepath: Path, required_strings: List[str], description: str) -> Tuple[bool, str]:
    """Check if file contains required strings"""
    if not filepath.exists():
        return False, f"File not found: {filepath}"
    
    try:
        content = filepath.read_text(encoding='utf-8')
        missing = [s for s in required_strings if s not in content]
        if missing:
            return False, f"Missing content: {', '.join(missing)}"
        return True, "All required content found"
    except Exception as e:
        return False, f"Error reading file: {e}"

def check_module_import(module_path: Path, module_name: str) -> Tuple[bool, str]:
    """Check if a Python module can be imported"""
    if not module_path.exists():
        return False, f"Module file not found: {module_path}"
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            return False, "Could not create module spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "Module imported successfully"
    except Exception as e:
        return False, f"Import error: {str(e)}"

def check_class_exists(module_path: Path, class_name: str) -> Tuple[bool, str]:
    """Check if a class exists in a module"""
    try:
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        if spec is None or spec.loader is None:
            return False, "Could not create module spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, class_name):
            return True, f"Class {class_name} found"
        return False, f"Class {class_name} not found in module"
    except Exception as e:
        return False, f"Error checking class: {str(e)}"

def check_function_exists(module_path: Path, function_name: str) -> Tuple[bool, str]:
    """Check if a function exists in a module"""
    try:
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        if spec is None or spec.loader is None:
            return False, "Could not create module spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, function_name) and callable(getattr(module, function_name)):
            return True, f"Function {function_name} found"
        return False, f"Function {function_name} not found or not callable"
    except Exception as e:
        return False, f"Error checking function: {str(e)}"

def check_json_file(filepath: Path) -> Tuple[bool, str]:
    """Check if a file is valid JSON"""
    if not filepath.exists():
        return False, f"File not found: {filepath}"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, "Valid JSON format"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def run_pytest_tests(test_path: Path) -> Tuple[bool, str, int, int]:
    """Run pytest tests and return results"""
    if not test_path.exists():
        return False, f"Test file not found: {test_path}", 0, 0
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse output for test counts
        output = result.stdout + result.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        total = passed + failed
        
        if result.returncode == 0:
            return True, f"All tests passed ({passed}/{total})", passed, total
        else:
            return False, f"Some tests failed ({passed} passed, {failed} failed)", passed, total
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 60 seconds", 0, 0
    except Exception as e:
        return False, f"Error running tests: {str(e)}", 0, 0

def validate_react_logging(project_root: Path) -> Dict[str, Any]:
    """Validate Lab 16: ReAct Logging"""
    results = {
        "name": "Lab 16: ReAct Logging",
        "checks": [],
        "passed": 0,
        "total": 0
    }
    
    print_header("LAB 16: ReAct Logging Validation")
    
    # Check 1: react_logger.py exists
    react_logger_path = project_root / "src" / "react_logging" / "react_logger.py"
    status, details = check_file_exists(react_logger_path, "ReAct Logger file")
    results["checks"].append(("ReAct Logger file exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("ReAct Logger file exists", status, details)
    
    # Check 2: Can import ReActLogger (check for class definition in file)
    if react_logger_path.exists():
        status, details = check_file_content(react_logger_path, ["class ReActLogger"], "ReActLogger class")
        results["checks"].append(("ReActLogger class exists", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("ReActLogger class exists", status, details)
    
    # Check 3: REACT_TRACE_EXAMPLE.md exists
    react_doc_path = project_root / "docs" / "REACT_TRACE_EXAMPLE.md"
    status, details = check_file_exists(react_doc_path, "ReAct documentation")
    results["checks"].append(("REACT_TRACE_EXAMPLE.md exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("REACT_TRACE_EXAMPLE.md exists", status, details)
    
    # Check 4: Documentation has required content
    if react_doc_path.exists():
        required_content = ["trace", "example", "json"]
        status, details = check_file_content(react_doc_path, required_content, "Documentation content")
        results["checks"].append(("Documentation has required content", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Documentation has required content", status, details)
    
    # Check 5: Trace logs directory exists
    trace_dir = project_root / "logs" / "react_traces"
    status, details = check_file_exists(trace_dir, "Trace logs directory")
    results["checks"].append(("Trace logs directory exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("Trace logs directory exists", status, details)
    
    # Check 6: Sample trace file is valid JSON (if exists)
    if trace_dir.exists():
        trace_files = list(trace_dir.glob("*.json"))
        if trace_files:
            status, details = check_json_file(trace_files[0])
            results["checks"].append(("Sample trace file is valid JSON", status, details))
            results["total"] += 1
            if status:
                results["passed"] += 1
            print_check("Sample trace file is valid JSON", status, details)
        else:
            results["checks"].append(("Sample trace file exists", False, "No trace files found"))
            results["total"] += 1
            print_check("Sample trace file exists", False, "No trace files found (optional)")
    
    return results

def validate_graph_workflow(project_root: Path) -> Dict[str, Any]:
    """Validate Lab 17: Graph Workflow"""
    results = {
        "name": "Lab 17: Graph Workflow",
        "checks": [],
        "passed": 0,
        "total": 0
    }
    
    print_header("LAB 17: Graph Workflow Validation")
    
    # Check 1: due_diligence_graph.py exists
    graph_path = project_root / "src" / "workflows" / "due_diligence_graph.py"
    status, details = check_file_exists(graph_path, "Workflow graph file")
    results["checks"].append(("due_diligence_graph.py exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("due_diligence_graph.py exists", status, details)
    
    # Check 2: Graph can be imported
    if graph_path.exists():
        status, details = check_module_import(graph_path, "due_diligence_graph")
        results["checks"].append(("Graph module can be imported", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Graph module can be imported", status, details)
    
    # Check 3: Required node functions exist
    if graph_path.exists():
        required_nodes = ["planner_node", "data_generator_node", "evaluator_node", "risk_detector_node"]
        for node in required_nodes:
            status, details = check_function_exists(graph_path, node)
            results["checks"].append((f"{node} exists", status, details))
            results["total"] += 1
            if status:
                results["passed"] += 1
            print_check(f"{node} exists", status, details)
    
    # Check 4: WorkflowState TypedDict exists
    if graph_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("temp_module", graph_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "WorkflowState"):
                    status, details = True, "WorkflowState TypedDict found"
                else:
                    status, details = False, "WorkflowState TypedDict not found"
            else:
                status, details = False, "Could not load module"
        except Exception as e:
            status, details = False, f"Error: {str(e)}"
        
        results["checks"].append(("WorkflowState TypedDict exists", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("WorkflowState TypedDict exists", status, details)
    
    # Check 5: run_due_diligence_workflow function exists
    if graph_path.exists():
        status, details = check_function_exists(graph_path, "run_due_diligence_workflow")
        results["checks"].append(("run_due_diligence_workflow exists", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("run_due_diligence_workflow exists", status, details)
    
    # Check 6: Graph has conditional edges (check for should_require_hitl or similar)
    if graph_path.exists():
        status, details = check_file_content(
            graph_path,
            ["add_conditional_edges", "should_require_hitl"],
            "Conditional edges configuration"
        )
        results["checks"].append(("Conditional edges configured", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Conditional edges configured", status, details)
    
    # Check 7: WORKFLOW_GRAPH.md exists
    workflow_doc_path = project_root / "docs" / "WORKFLOW_GRAPH.md"
    status, details = check_file_exists(workflow_doc_path, "Workflow documentation")
    results["checks"].append(("WORKFLOW_GRAPH.md exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("WORKFLOW_GRAPH.md exists", status, details)
    
    # Check 8: Documentation has diagram
    if workflow_doc_path.exists():
        status, details = check_file_content(
            workflow_doc_path,
            ["mermaid", "graph", "planner", "risk_detector"],
            "Mermaid diagram"
        )
        results["checks"].append(("Documentation has Mermaid diagram", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Documentation has Mermaid diagram", status, details)
    
    return results

def validate_hitl_integration(project_root: Path) -> Dict[str, Any]:
    """Validate Lab 18: HITL Integration"""
    results = {
        "name": "Lab 18: HITL Integration",
        "checks": [],
        "passed": 0,
        "total": 0
    }
    
    print_header("LAB 18: HITL Integration Validation")
    
    # Check 1: hitl_handler.py exists
    hitl_path = project_root / "src" / "workflows" / "hitl_handler.py"
    status, details = check_file_exists(hitl_path, "HITL handler file")
    results["checks"].append(("hitl_handler.py exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("hitl_handler.py exists", status, details)
    
    # Check 2: HITLRequest model exists
    if hitl_path.exists():
        status, details = check_file_content(hitl_path, ["class HITLRequest", "HITLRequest"], "HITLRequest model")
        results["checks"].append(("HITLRequest model exists", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("HITLRequest model exists", status, details)
    
    # Check 3: CLI approval function exists
    if hitl_path.exists():
        status, details = check_function_exists(hitl_path, "pause_for_approval_cli")
        results["checks"].append(("CLI approval function exists", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("CLI approval function exists", status, details)
    
    # Check 4: HTTP endpoints exist
    if hitl_path.exists():
        required_endpoints = ["/hitl/request", "/hitl/approve", "/hitl/reject"]
        status, details = check_file_content(
            hitl_path,
            ["/hitl/request", "/hitl/approve", "/hitl/reject"],
            "HTTP endpoints"
        )
        results["checks"].append(("HTTP endpoints exist", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("HTTP endpoints exist", status, details)
    
    # Check 5: HITL events logging
    if hitl_path.exists():
        status, details = check_file_content(
            hitl_path,
            ["log_hitl_event", "HITL_TRIGGERED", "HITL_APPROVED"],
            "HITL event logging"
        )
        results["checks"].append(("HITL events logging implemented", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("HITL events logging implemented", status, details)
    
    # Check 6: Workflow integration (hitl_approval_node in graph)
    graph_path = project_root / "src" / "workflows" / "due_diligence_graph.py"
    if graph_path.exists():
        status, details = check_file_content(
            graph_path,
            ["hitl_approval_node", "pause_for_approval"],
            "HITL workflow integration"
        )
        results["checks"].append(("HITL integrated in workflow", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("HITL integrated in workflow", status, details)
    
    # Check 7: HITL server script exists
    hitl_server_script = project_root / "start_hitl_server.ps1"
    status, details = check_file_exists(hitl_server_script, "HITL server script")
    results["checks"].append(("HITL server script exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("HITL server script exists", status, details)
    
    return results

def validate_testing(project_root: Path) -> Dict[str, Any]:
    """Validate Testing Completeness"""
    results = {
        "name": "Testing",
        "checks": [],
        "passed": 0,
        "total": 0
    }
    
    print_header("TESTING VALIDATION")
    
    # Check 1: Integration test file exists
    integration_test = project_root / "tests" / "test_phase3_integration.py"
    status, details = check_file_exists(integration_test, "Integration test file")
    results["checks"].append(("Integration test file exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("Integration test file exists", status, details)
    
    # Check 2: Workflow branch test exists
    branch_test = project_root / "tests" / "test_workflow_branches.py"
    status, details = check_file_exists(branch_test, "Workflow branch test file")
    results["checks"].append(("Workflow branch test exists", status, details))
    results["total"] += 1
    if status:
        results["passed"] += 1
    print_check("Workflow branch test exists", status, details)
    
    # Check 3: Integration test covers both branches
    if integration_test.exists():
        status, details = check_file_content(
            integration_test,
            ["test_normal_flow", "test_high_risk", "test_complete_integration"],
            "Test coverage"
        )
        results["checks"].append(("Integration test covers both branches", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Integration test covers both branches", status, details)
    
    # Check 4: Mock HITL approval in tests
    if integration_test.exists():
        status, details = check_file_content(
            integration_test,
            ["mock_input", "approve", "reject"],
            "Mock HITL approval"
        )
        results["checks"].append(("Mock HITL approval in tests", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Mock HITL approval in tests", status, details)
    
    # Check 5: Run integration tests
    if integration_test.exists():
        print(f"\n  {Colors.BLUE}Running integration tests...{Colors.RESET}")
        status, details, passed, total = run_pytest_tests(integration_test)
        results["checks"].append(("Integration tests pass", status, details))
        results["total"] += 1
        if status:
            results["passed"] += 1
        print_check("Integration tests pass", status, details)
        results["test_stats"] = {"passed": passed, "total": total}
    
    return results

def print_summary(all_results: List[Dict[str, Any]]):
    """Print final summary report"""
    print_header("PHASE 3 VALIDATION SUMMARY")
    
    total_checks = 0
    total_passed = 0
    
    for result in all_results:
        name = result["name"]
        passed = result["passed"]
        total = result["total"]
        percentage = (passed / total * 100) if total > 0 else 0
        
        total_checks += total
        total_passed += passed
        
        status_color = Colors.GREEN if passed == total else Colors.YELLOW if percentage >= 80 else Colors.RED
        status_symbol = "[OK]" if passed == total else "[!]" if percentage >= 80 else "[X]"
        
        print(f"{status_symbol} {name:<40} {status_color}{passed}/{total} ({percentage:.0f}%){Colors.RESET}")
    
    overall_percentage = (total_passed / total_checks * 100) if total_checks > 0 else 0
    overall_color = Colors.GREEN if overall_percentage == 100 else Colors.YELLOW if overall_percentage >= 80 else Colors.RED
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Overall: {overall_color}{total_passed}/{total_checks} checks passed ({overall_percentage:.0f}%){Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    if overall_percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}[OK] Phase 3 is complete and ready for Phase 4!{Colors.RESET}\n")
    elif overall_percentage >= 80:
        print(f"{Colors.YELLOW}{Colors.BOLD}[!] Phase 3 is mostly complete. Review failed checks above.{Colors.RESET}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}[X] Phase 3 needs more work. Review failed checks above.{Colors.RESET}\n")

def main():
    """Main validation function"""
    # Get project root (assume script is in scripts/ directory)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("PHASE 3 VALIDATION SCRIPT".center(70))
    print("Labs 16, 17, 18 - Pre-Submission Checklist".center(70))
    print("="*70)
    print(f"{Colors.RESET}\n")
    print(f"Project root: {project_root}\n")
    
    # Run all validations
    all_results = []
    
    all_results.append(validate_react_logging(project_root))
    all_results.append(validate_graph_workflow(project_root))
    all_results.append(validate_hitl_integration(project_root))
    all_results.append(validate_testing(project_root))
    
    # Print summary
    print_summary(all_results)
    
    # Exit with appropriate code
    total_checks = sum(r["total"] for r in all_results)
    total_passed = sum(r["passed"] for r in all_results)
    
    if total_passed == total_checks:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Some checks failed

if __name__ == "__main__":
    main()

