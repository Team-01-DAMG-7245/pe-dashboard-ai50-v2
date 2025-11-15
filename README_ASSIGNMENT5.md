# Assignment 5: Advanced Agent Implementation

## Lab 12: Core Agent Tools

**Run unit tests:**
```powershell
python -m pytest tests/test_tools.py -v
```

**Expected:** All tool tests pass (get_latest_structured_payload, rag_search_company, report_layoff_signal)

---

## Lab 13: Supervisor Agent Bootstrap

**Run Supervisor Agent:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
python src\lab13\supervisor_agent.py
```

**Expected:** Console logs show Thought → Action → Observation sequence

---

## Lab 14: MCP Server Implementation

**Build MCP Server Docker image:**
```powershell
docker build -f Dockerfile.mcp -t mcp-server .
```

**Run MCP Server:**
```powershell
docker run -p 9000:9000 --env-file .env mcp-server
```

**Or run directly:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
python src\server\mcp_server.py
```

**Verify MCP Inspector:**
- Open MCP Inspector tool
- Connect to `http://localhost:9000`
- Verify registered tools/resources/prompts

---

## Lab 15: Agent MCP Consumption

**Configure mcp_config.json:**
```json
{
  "base_url": "http://localhost:9000",
  "tools": ["generate_structured_dashboard", "generate_rag_dashboard"]
}
```

**Run integration test:**
```powershell
python -m pytest tests/test_mcp_server.py -v
```

**Run Agent with MCP:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
python src\lab15\agent_mcp_client.py
```

**Expected:** Agent → MCP → Dashboard → Agent round trip works

---

## Lab 16: ReAct Pattern Implementation

**Run ReAct Agent:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
python src\lab16\react_agent.py --company anthropic
```

**Check logs:**
```powershell
# View JSON logs
Get-Content logs\react_traces\*.json | ConvertFrom-Json | Format-List

# Or view trace example
cat docs\REACT_TRACE_EXAMPLE.md
```

**Expected:** JSON logs show sequential ReAct steps with Thought/Action/Observation triplets

---

## Lab 17: Supervisory Workflow Pattern (Graph-based)

**Terminal 1 - Start MCP Server:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python -c "import sys; sys.path.insert(0, 'src'); from server.mcp_server import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=9000)"
```

**Terminal 2 - Start API Server:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH="src"
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python src\lab7\rag_dashboard.py
```

**Terminal 3 - Run Workflow:**
```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH=""
python -m src.workflows.due_diligence_graph anthropic
```

**Run unit tests:**
```powershell
python -m pytest tests/test_workflow_branches.py -v
```

**View workflow diagram:**
```powershell
cat docs\WORKFLOW_GRAPH.md
```

**Output:** Dashboard saved to `data/workflow_dashboards/{company_id}_{run_id}_{timestamp}.md`

---

## Lab 18: HITL Approval

### CLI Mode (Default)

```powershell
cd "C:\Users\Swara\Desktop\Big Data Assignments\damg7245-assignmnet4\forbes-ai50-dashboard-assignment4"
$env:PYTHONPATH=""
python -m src.workflows.due_diligence_graph anthropic
# When prompted, type 'yes' or 'no'
```

### HTTP Mode

**Terminal 1 - Start HITL Server:**
```powershell
.\start_hitl_server.ps1
```

**Terminal 2 - Start API Server:**
```powershell
$env:PYTHONPATH="src"
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python src\lab7\rag_dashboard.py
```

**Terminal 3 - Run Workflow:**
```powershell
$env:HITL_METHOD="http"
$env:HITL_BASE_URL="http://localhost:8003"
$env:PYTHONPATH=""
python -m src.workflows.due_diligence_graph anthropic
```

**Terminal 4 - Approve/Reject:**

**PowerShell Scripts:**
```powershell
.\check_hitl_status.ps1
.\approve_hitl.ps1 -RunId "{run_id}" -Approved -Reviewer "admin" -Notes "Approved"
.\approve_hitl.ps1 -RunId "{run_id}" -Rejected -Reviewer "admin" -Notes "Rejected"
```

**Direct PowerShell:**
```powershell
$body = @{approved=$true; reviewer="admin"; notes="Approved"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/hitl/approve/{run_id}" -Method Post -Body $body -ContentType "application/json"
```

**curl.exe:**
```powershell
curl.exe -X POST http://localhost:8003/hitl/approve/{run_id} -H "Content-Type: application/json" -d "{\"approved\": true, \"reviewer\": \"admin\", \"notes\": \"Approved\"}"
```

---

## Quick Reference

**Checkpoints:**
- Lab 12: `pytest tests/test_tools.py -v`
- Lab 13: Check console logs for ReAct sequence
- Lab 14: MCP Inspector shows registered tools/resources/prompts
- Lab 15: `pytest tests/test_mcp_server.py -v`
- Lab 16: Check JSON logs in `logs/react_traces/`
- Lab 17: `pytest tests/test_workflow_branches.py -v` + workflow diagram
- Lab 18: HITL approval works via CLI or HTTP

**Common Commands:**
```powershell
# Set PYTHONPATH
$env:PYTHONPATH="src"

# Run tests
python -m pytest tests/ -v

# Check logs
Get-Content logs\react_traces\*.json

# View workflow diagram
cat docs\WORKFLOW_GRAPH.md
```

