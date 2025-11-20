"""Check correctness of trace files"""
import json
from pathlib import Path

def analyze_trace(file_path):
    """Analyze a trace file for correctness"""
    print(f"\n{'='*70}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*70}")
    
    with open(file_path, 'r') as f:
        trace = json.load(f)
    
    print(f"\nRun ID: {trace['run_id']}")
    print(f"Company: {trace['company_id']}")
    print(f"Total Steps: {len(trace['steps'])}")
    
    # Count step types
    thoughts = [s for s in trace['steps'] if s['step_type'] == 'thought']
    actions = [s for s in trace['steps'] if s['step_type'] == 'action']
    observations = [s for s in trace['steps'] if s['step_type'] == 'observation']
    
    print(f"\nStep Breakdown:")
    print(f"  Thoughts: {len(thoughts)}")
    print(f"  Actions: {len(actions)}")
    print(f"  Observations: {len(observations)}")
    
    # Check for issues
    issues = []
    
    # Check 1: Missing action steps
    if len(actions) == 0 and len(thoughts) > 0:
        issues.append("❌ CRITICAL: No action steps found! (Only thoughts and observations)")
    
    # Check 2: Actions without observations
    if len(actions) > 0 and len(observations) < len(actions):
        missing_obs = len(actions) - len(observations)
        issues.append(f"⚠️  WARNING: {missing_obs} action(s) missing corresponding observation(s)")
    
    # Check 3: Null values in action steps
    action_with_nulls = sum(1 for a in actions if a.get('observation') is None)
    if action_with_nulls > 0:
        issues.append(f"ℹ️  INFO: {action_with_nulls} action step(s) have null observations (expected)")
    
    # Check 4: Sequential step numbers
    step_nums = [s['step_number'] for s in trace['steps']]
    if step_nums != sorted(step_nums):
        issues.append("❌ ERROR: Step numbers are not sequential!")
    
    # Check 5: Required fields
    required_fields = ['timestamp', 'run_id', 'company_id', 'step_number', 'step_type']
    missing_fields = []
    for step in trace['steps']:
        for field in required_fields:
            if field not in step:
                missing_fields.append(f"Step {step.get('step_number', '?')} missing {field}")
    
    if missing_fields:
        issues.append(f"❌ ERROR: Missing required fields: {missing_fields[0]}")
    
    # Print issues
    if issues:
        print(f"\n⚠️  Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ No issues found!")
    
    # Show step sequence
    print(f"\nStep Sequence:")
    for step in trace['steps']:
        step_type = step['step_type']
        if step_type == 'thought':
            content = step.get('thought', '')[:60] + '...' if step.get('thought') else 'null'
        elif step_type == 'action':
            content = f"{step.get('action', 'unknown')}()"
        else:
            content = step.get('observation', '')[:60] + '...' if step.get('observation') else 'null'
        print(f"  Step {step['step_number']}: {step_type.upper():12} - {content}")
    
    return {
        'file': file_path.name,
        'total_steps': len(trace['steps']),
        'thoughts': len(thoughts),
        'actions': len(actions),
        'observations': len(observations),
        'issues': issues
    }

# Analyze both files
print("="*70)
print("TRACE CORRECTNESS ANALYSIS")
print("="*70)

results = []

# File 1
file1 = Path("logs/react_traces/react_trace_test-fix-abridge-20251114-213030.json")
if file1.exists():
    results.append(analyze_trace(file1))
else:
    print(f"\n❌ File not found: {file1}")

# File 2
file2 = Path("logs/react_traces/react_trace_test-all-anthropic-20251114-212536.json")
if file2.exists():
    results.append(analyze_trace(file2))
else:
    print(f"\n❌ File not found: {file2}")

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

for r in results:
    print(f"\n{r['file']}:")
    print(f"  Steps: {r['total_steps']} ({r['thoughts']}T, {r['actions']}A, {r['observations']}O)")
    if r['issues']:
        print(f"  Issues: {len(r['issues'])}")
        for issue in r['issues']:
            print(f"    {issue}")
    else:
        print(f"  Status: ✅ OK")

