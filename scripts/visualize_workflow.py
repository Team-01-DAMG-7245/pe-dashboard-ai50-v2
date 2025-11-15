"""
Workflow Visualization Script

Generates Mermaid diagrams from workflow execution traces showing:
- Node execution order
- HITL decision points
- Branch taken (safe vs high-risk)
- Human approval/rejection
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def load_trace(trace_file: Path) -> Dict[str, Any]:
    """Load workflow trace JSON file"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_mermaid_diagram(trace: Dict[str, Any]) -> str:
    """Generate Mermaid diagram from trace data"""
    
    run_id = trace.get('run_id', 'unknown')
    company_id = trace.get('company_id', 'unknown')
    events = trace.get('events', [])
    node_order = trace.get('node_execution_order', [])
    final_state = trace.get('final_state', {})
    
    # Determine branch taken
    requires_hitl = final_state.get('requires_hitl', False)
    hitl_approved = final_state.get('hitl_approved', False)
    
    # Find HITL events
    hitl_events = [e for e in events if e.get('event_type', '').startswith('HITL_')]
    
    # Build diagram
    diagram_lines = [
        "```mermaid",
        "graph TD",
        "    Start([Workflow Start])",
        "    Start --> Planner[Planner Node]",
    ]
    
    # Add nodes in execution order
    if 'data_generator' in node_order:
        diagram_lines.append("    Planner --> DataGen[Data Generator Node]")
    if 'evaluator' in node_order:
        diagram_lines.append("    DataGen --> Evaluator[Evaluator Node]")
    if 'risk_detector' in node_order:
        diagram_lines.append("    Evaluator --> RiskDet[Risk Detector Node]")
    
    # Add conditional branching
    if requires_hitl:
        diagram_lines.append("    RiskDet -->|High Risk Detected| HITL[HITL Approval Node]")
        
        # Add HITL decision
        if hitl_approved:
            diagram_lines.append("    HITL -->|Approved| End([Workflow End])")
            diagram_lines.append("    style HITL fill:#90EE90")
            diagram_lines.append("    style End fill:#90EE90")
        else:
            diagram_lines.append("    HITL -->|Rejected| End([Workflow End])")
            diagram_lines.append("    style HITL fill:#FFB6C1")
            diagram_lines.append("    style End fill:#FFB6C1")
    else:
        diagram_lines.append("    RiskDet -->|No High Risk| End([Workflow End])")
        diagram_lines.append("    style End fill:#90EE90")
    
    # Add styling
    diagram_lines.append("    style Start fill:#E6F3FF")
    diagram_lines.append("    style Planner fill:#FFE6CC")
    diagram_lines.append("    style DataGen fill:#FFE6CC")
    diagram_lines.append("    style Evaluator fill:#FFE6CC")
    diagram_lines.append("    style RiskDet fill:#FFE6CC")
    
    if requires_hitl:
        diagram_lines.append("    style HITL fill:#FFF4E6")
    
    diagram_lines.append("```")
    
    # Add metadata section
    metadata = [
        "",
        "## Execution Metadata",
        "",
        f"- **Run ID:** {run_id}",
        f"- **Company:** {company_id}",
        f"- **Start Time:** {trace.get('start_time', 'N/A')}",
        f"- **End Time:** {trace.get('end_time', 'N/A')}",
        f"- **Branch Taken:** {'HIGH-RISK PATH -> HITL Approval -> END' if requires_hitl else 'SAFE PATH -> END (Direct)'}",
    ]
    
    if requires_hitl:
        metadata.extend([
            f"- **HITL Approved:** {hitl_approved}",
            f"- **HITL Reviewer:** {final_state.get('hitl_reviewer', 'N/A')}",
        ])
    
    metadata.extend([
        f"- **Dashboard Score:** {final_state.get('dashboard_score', 'N/A')}/10",
        f"- **Risk Signals:** {final_state.get('risk_signals_count', 0)}",
        "",
        "## HITL Events",
        "",
    ])
    
    if hitl_events:
        for event in hitl_events:
            event_type = event.get('event_type', '')
            timestamp = event.get('timestamp', '')
            metadata.append(f"- **{event_type}** at {timestamp}")
            if 'reviewer' in event:
                metadata.append(f"  - Reviewer: {event['reviewer']}")
            if 'notes' in event and event['notes']:
                metadata.append(f"  - Notes: {event['notes']}")
    else:
        metadata.append("- No HITL events (safe path)")
    
    return "\n".join(diagram_lines) + "\n" + "\n".join(metadata)


def generate_detailed_trace_markdown(trace: Dict[str, Any], output_file: Path):
    """Generate detailed markdown trace document"""
    
    run_id = trace.get('run_id', 'unknown')
    company_id = trace.get('company_id', 'unknown')
    events = trace.get('events', [])
    node_order = trace.get('node_execution_order', [])
    final_state = trace.get('final_state', {})
    
    markdown = [
        f"# Workflow Execution Trace: {company_id.upper()}",
        "",
        f"**Run ID:** `{run_id}`",
        f"**Start Time:** {trace.get('start_time', 'N/A')}",
        f"**End Time:** {trace.get('end_time', 'N/A')}",
        "",
        "## Execution Flow Diagram",
        "",
        generate_mermaid_diagram(trace),
        "",
        "## Node Execution Order",
        "",
    ]
    
    for i, node in enumerate(node_order, 1):
        markdown.append(f"{i}. **{node}**")
    
    markdown.extend([
        "",
        "## Event Timeline",
        "",
    ])
    
    for event in events:
        event_type = event.get('event_type', '')
        timestamp = event.get('timestamp', '')
        markdown.append(f"### {event_type}")
        markdown.append(f"**Time:** {timestamp}")
        
        # Add event-specific details
        if event_type == "HITL_TRIGGERED":
            markdown.append(f"- Risk Signals: {event.get('risk_signals_count', 0)}")
            markdown.append(f"- High Severity: {event.get('high_severity_count', 0)}")
        elif event_type in ["HITL_APPROVED", "HITL_REJECTED"]:
            markdown.append(f"- Reviewer: {event.get('reviewer', 'N/A')}")
            if event.get('notes'):
                markdown.append(f"- Notes: {event.get('notes')}")
        elif event_type == "NODE_EXECUTED":
            markdown.append(f"- Node: {event.get('node', 'N/A')}")
        
        markdown.append("")
    
    markdown.extend([
        "## Final State",
        "",
        f"- **Requires HITL:** {final_state.get('requires_hitl', False)}",
        f"- **HITL Approved:** {final_state.get('hitl_approved', False)}",
        f"- **HITL Reviewer:** {final_state.get('hitl_reviewer', 'N/A')}",
        f"- **Dashboard Score:** {final_state.get('dashboard_score', 'N/A')}/10",
        f"- **Risk Signals:** {final_state.get('risk_signals_count', 0)}",
        "",
        "## Branch Analysis",
        "",
    ])
    
    if final_state.get('requires_hitl', False):
        markdown.extend([
            "**Path Taken:** HIGH-RISK PATH -> HITL Approval -> END",
            "",
            "The workflow detected high-severity risks and routed to the HITL approval node.",
            f"The dashboard was {'**APPROVED**' if final_state.get('hitl_approved') else '**REJECTED**'} by {final_state.get('hitl_reviewer', 'N/A')}.",
        ])
    else:
        markdown.extend([
            "**Path Taken:** SAFE PATH -> END (Direct)",
            "",
            "No high-severity risks were detected. The workflow completed directly without HITL intervention.",
        ])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(markdown))


def main():
    """Main function to visualize workflow traces"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualize workflow execution traces")
    parser.add_argument("trace_file", type=str, help="Path to trace JSON file")
    parser.add_argument("--output", "-o", type=str, help="Output markdown file (default: trace_file with .md extension)")
    parser.add_argument("--diagram-only", action="store_true", help="Print only the Mermaid diagram")
    
    args = parser.parse_args()
    
    trace_file = Path(args.trace_file)
    if not trace_file.exists():
        print(f"Error: Trace file not found: {trace_file}")
        sys.exit(1)
    
    # Load trace
    trace = load_trace(trace_file)
    
    if args.diagram_only:
        # Print only diagram
        print(generate_mermaid_diagram(trace))
    else:
        # Generate full markdown document
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = trace_file.with_suffix('.md')
        
        generate_detailed_trace_markdown(trace, output_file)
        print(f"Generated visualization: {output_file}")
        print(f"\nMermaid diagram:")
        print(generate_mermaid_diagram(trace))


if __name__ == "__main__":
    main()

