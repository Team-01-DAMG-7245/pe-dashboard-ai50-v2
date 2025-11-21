# test HITL
docker-compose exec airflow-scheduler python -c "
import asyncio, sys
sys.path.insert(0, '/opt/airflow')
from src.lab13.agents.supervisor_agent_mcp import MCPEnabledSupervisor
async def test():
    supervisor = MCPEnabledSupervisor()
    results = await supervisor.analyze_company('test_risky')
    await supervisor.close()
asyncio.run(test())
"

# approve
curl http://localhost:9001/api/v1/hitl/pending | jq

APPROVAL_ID=$(curl -s http://localhost:9001/api/v1/hitl/pending | jq -r '.pending_approvals[0].approval_id')

curl -X POST http://localhost:9001/api/v1/hitl/approve/$APPROVAL_ID \
  -H 'Content-Type: application/json' \
  -d '{"approved": true, "reviewer": "PE_Analyst"}'