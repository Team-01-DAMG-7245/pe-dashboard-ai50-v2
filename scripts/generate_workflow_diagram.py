"""
Generate Mermaid diagram for workflow graph programmatically
"""

def generate_mermaid_diagram():
    """Generate Mermaid diagram code for the workflow graph"""
    
    diagram = """graph TD
    START([START]) --> planner[Planner Node]
    planner --> data_gen[Data Generator Node]
    data_gen --> evaluator[Evaluator Node]
    evaluator --> risk_det[Risk Detector Node]
    
    risk_det -->|requires_hitl = False| END_SAFE([END - Safe Path])
    risk_det -->|requires_hitl = True| hitl[HITL Approval Node]
    hitl --> END_HITL([END - HITL Path])
    
    style START fill:#90EE90
    style END_SAFE fill:#90EE90
    style END_HITL fill:#FFB6C1
    style risk_det fill:#FFD700
    style hitl fill:#FF6B6B
"""
    
    return diagram


if __name__ == "__main__":
    diagram = generate_mermaid_diagram()
    print("Mermaid Diagram Code:")
    print("=" * 60)
    print(diagram)
    print("=" * 60)
    print("\nTo use this diagram:")
    print("1. Copy the code above")
    print("2. Paste it into a markdown file with ```mermaid code blocks")
    print("3. Or use it in Mermaid Live Editor: https://mermaid.live/")

