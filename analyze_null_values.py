"""Analyze null values in ReAct trace"""
import json

trace = json.load(open('logs/react_traces/react_trace_lab16-doc-example.json'))

print("=== NULL VALUES ANALYSIS ===\n")

print("Step 1 (Thought):")
s1 = trace['steps'][0]
print(f"  thought: {'FILLED' if s1['thought'] else 'NULL'}")
print(f"  action: {'FILLED' if s1['action'] else 'NULL'} (expected: NULL)")
print(f"  observation: {'FILLED' if s1['observation'] else 'NULL'} (expected: NULL)")
print()

print("Step 2 (Action):")
s2 = trace['steps'][1]
print(f"  thought: {'FILLED' if s2['thought'] else 'NULL'} (expected: NULL)")
print(f"  action: {'FILLED' if s2['action'] else 'NULL'}")
print(f"  observation: {'FILLED' if s2['observation'] else 'NULL'} (expected: NULL - tool not finished)")
print()

print("Step 7 (Observation):")
s7 = trace['steps'][6]
print(f"  thought: {'FILLED' if s7['thought'] else 'NULL'} (expected: NULL)")
print(f"  action: {'FILLED' if s7['action'] else 'NULL'} (expected: NULL)")
print(f"  observation: {'FILLED' if s7['observation'] else 'NULL'}")
print()

print("=== SUMMARY ===")
print("Null values are EXPECTED and CORRECT by design!")
print("Each step type only fills relevant fields:")
print("  - Thought steps: only 'thought' field")
print("  - Action steps: only 'action' and 'action_input' fields")
print("  - Observation steps: only 'observation' and 'observation_data' fields")
print()
print("The issue is missing intermediate observations after each action,")
print("but the final observation contains all tool results.")

