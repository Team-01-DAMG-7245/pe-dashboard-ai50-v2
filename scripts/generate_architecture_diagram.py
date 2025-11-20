"""
Generate Architecture Diagram for Assignment 5 - Project ORBIT Part 2
Using the diagrams library to create a comprehensive system architecture diagram

Installation:
    pip install diagrams

Dependencies:
    - Graphviz (system dependency)
    On Windows: Download from https://graphviz.org/download/
    On Mac: brew install graphviz
    On Linux: sudo apt-get install graphviz

Usage:
    python scripts/generate_architecture_diagram.py
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users, Client
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.database import PostgreSQL, MongoDB
from diagrams.onprem.network import Internet
from diagrams.onprem.compute import Server
from diagrams.aws.storage import S3
from diagrams.programming.language import Python
from diagrams.programming.framework import FastAPI
from diagrams.generic.storage import Storage

def main():
    """Generate the architecture diagram for Assignment 5"""
    
    with Diagram(
        "Assignment 5 - Project ORBIT Part 2 Architecture\nAgentification and Secure Scaling of PE Intelligence using MCP",
        filename="docs/architecture_diagram",
        show=False,
        direction="TB",
        outformat="png",
        graph_attr={
            "fontsize": "16",
            "bgcolor": "white",
            "pad": "0.5",
            "splines": "ortho",
            "nodesep": "1.0",
            "ranksep": "1.2"
        }
    ):
        # External Users/Triggers
        users = Users("Data Engineers\n(Priya Rao)")
        
        # Airflow Orchestration Layer
        with Cluster("☁️ Airflow Orchestration Layer"):
            dag_initial = Airflow("Initial Load DAG\n(One-time setup)")
            dag_daily = Airflow("Daily Update DAG\n(Scheduled refresh)")
            dag_agentic = Airflow("Agentic Dashboard DAG\n(Daily agent workflow)")
        
        # Services Layer
        with Cluster("🔧 Services Layer"):
            mcp_server = FastAPI("MCP Server\nPort: 8000\n\nTools:\n- generate_structured_dashboard\n- generate_rag_dashboard\n\nResources:\n- /resource/ai50/companies\n\nPrompts:\n- /prompt/pe-dashboard")
            supervisor_agent = Python("Supervisor Agent\n(LangChain/LangGraph)\n\nReAct Pattern:\nThought → Action → Observation")
            
            with Cluster("Vector Database"):
                vector_db = MongoDB("ChromaDB\n(Embeddings & RAG)\n\nStores:\n- Document embeddings\n- Company context\n- Semantic search")
        
        # Workflow Graph Nodes
        with Cluster("🔄 Agent Workflow (LangGraph StateGraph)"):
            planner = Server("1. Planner Node\n\n- Creates execution plan\n- Generates run_id\n- Sets parameters")
            data_gen = Server("2. Data Generator Node\n\n- Invokes MCP tools\n- Retrieves payloads\n- Performs RAG queries")
            evaluator = Server("3. Evaluator Node\n\n- Generates dashboard\n- Scores quality (1-10)\n- Validates schema")
            risk_det = Server("4. Risk Detector Node\n\n- Scans for keywords\n- Classifies severity\n- Sets requires_hitl flag")
            hitl = Client("5. HITL Approval\n\n- Human review\n- Risk verification\n- Approval/rejection")
        
        # Storage Layer
        with Cluster("💾 Storage Layer"):
            s3_storage = S3("S3 Bucket\n\nStores:\n- Raw scraped data\n- Structured payloads\n- Company snapshots")
            dashboard_db = PostgreSQL("Dashboards DB\n\nStores:\n- Generated dashboards\n- Metadata\n- Timestamps")
            logs_storage = Storage("Structured Logs\n(JSON Format)\n\nContains:\n- ReAct traces\n- Tool invocations\n- Risk signals")
        
        # External APIs
        with Cluster("🌐 External Services"):
            llm_api = Internet("LLM API\n\nProviders:\n- OpenAI GPT-4\n- Anthropic Claude")
            forbes_api = Internet("Forbes AI 50\n\nData Source:\n- Company profiles\n- News articles\n- Updates")
        
        # Connections - User to Airflow
        users >> Edge(label="Triggers Workflow", style="dashed", color="gray") >> dag_agentic
        
        # Airflow DAGs connections
        dag_initial >> Edge(label="Initial Load\n(One-time)", color="blue") >> s3_storage
        dag_daily >> Edge(label="Incremental Update\n(Daily)", color="blue") >> s3_storage
        dag_daily >> Edge(label="Update Embeddings\n(Refresh vector DB)", color="blue") >> vector_db
        
        # Agentic DAG connections
        dag_agentic >> Edge(label="HTTP Request\n(Invoke MCP)", color="darkblue", style="bold") >> mcp_server
        dag_agentic >> Edge(label="Start Workflow\n(Trigger agent)", color="darkblue", style="bold") >> supervisor_agent
        
        # MCP Server connections
        mcp_server >> Edge(label="Tool Invocation\n(Standardized API)", color="green", style="bold") >> supervisor_agent
        mcp_server >> Edge(label="Dashboard Tools\n(generate_structured_dashboard\ngenerate_rag_dashboard)", color="green") >> data_gen
        
        # Supervisor Agent to Workflow
        supervisor_agent >> Edge(label="Orchestrates\n(LangGraph execution)", color="purple", style="bold") >> planner
        
        # Workflow node connections (sequential flow)
        planner >> Edge(label="Execution Plan", color="orange") >> data_gen
        data_gen >> Edge(label="Aggregated Data\n(structured + RAG)", color="orange") >> evaluator
        evaluator >> Edge(label="Dashboard + Score", color="orange") >> risk_det
        
        # Risk Detector branching (conditional)
        risk_det >> Edge(label="High Risk Detected\n(layoffs, breaches, etc.)", color="red", style="bold") >> hitl
        risk_det >> Edge(label="No Risk\n(Safe to proceed)", color="green", style="bold") >> dashboard_db
        
        # HITL connections
        hitl >> Edge(label="Approved\n(Save dashboard)", color="green", style="bold") >> dashboard_db
        hitl >> Edge(label="Rejected\n(Log and skip)", color="red") >> logs_storage
        
        # Data Generator connections (data retrieval)
        data_gen >> Edge(label="RAG Query\n(Semantic search)", color="cyan") >> vector_db
        data_gen >> Edge(label="Retrieve Payload\n(Structured data)", color="cyan") >> s3_storage
        
        # Supervisor Agent connections
        supervisor_agent >> Edge(label="LLM API Calls\n(Reasoning & generation)", color="purple") >> llm_api
        supervisor_agent >> Edge(label="ReAct Traces\n(Thought/Action/Observation)", color="purple") >> logs_storage
        
        # Data ingestion (from external sources)
        dag_initial >> Edge(label="Scrape Data\n(Initial collection)", color="gray") >> forbes_api
        dag_daily >> Edge(label="Refresh Data\n(Daily updates)", color="gray") >> forbes_api
        
        # Vector DB population
        dag_initial >> Edge(label="Create Embeddings\n(Index documents)", color="gray") >> vector_db

    print("✅ Architecture diagram generated successfully!")
    print("📁 Output saved to: docs/architecture_diagram.png")
    print("\n📋 Diagram Components:")
    print("   - Airflow Orchestration Layer (3 DAGs)")
    print("   - Services Layer (MCP Server, Supervisor Agent, Vector DB)")
    print("   - Agent Workflow (5 nodes with conditional branching)")
    print("   - Storage Layer (S3, PostgreSQL, Logs)")
    print("   - External Services (LLM API, Forbes AI 50)")
    print("\n🔄 Workflow Flow:")
    print("   Planner → Data Generator → Evaluator → Risk Detector → [HITL or Save]")
    print("\nTo regenerate, run: python scripts/generate_architecture_diagram.py")


if __name__ == "__main__":
    main()

