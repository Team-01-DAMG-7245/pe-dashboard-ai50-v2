"""
Lab 6 Checkpoint Test - Verify all payloads validate
"""
from structured_pipeline import load_payload

test_companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']

print("=" * 60)
print("LAB 6 CHECKPOINT: Payload Validation")
print("=" * 60)

success_count = 0

for company_id in test_companies:
    try:
        payload = load_payload(company_id)
        if payload:
            print(f"✅ {company_id}: Payload validates successfully")
            print(f"   - Legal name: {payload.company_record.legal_name}")
            print(f"   - Products: {len(payload.products)}")
            print(f"   - Leadership: {len(payload.leadership)}")
            success_count += 1
    except Exception as e:
        print(f"❌ {company_id}: Failed - {e}")

print("\n" + "=" * 60)
print(f"RESULT: {success_count}/{len(test_companies)} payloads validated")
if success_count == len(test_companies):
    print("✅ LAB 6 CHECKPOINT PASSED!")
    print("All payloads can be loaded by src/structured_pipeline.py")
print("=" * 60)
