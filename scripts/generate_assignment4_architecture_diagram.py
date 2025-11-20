"""
Generate Architecture Diagram for Assignment 4 - Project ORBIT Part 1
Using the diagrams library to create a comprehensive system architecture diagram

Installation:
    pip install diagrams

Dependencies:
    - Graphviz (system dependency)
    On Windows: Download from https://graphviz.org/download/
    On Mac: brew install graphviz
    On Linux: sudo apt-get install graphviz

Usage:
    python scripts/generate_assignment4_architecture_diagram.py
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
from diagrams.generic.blank import Blank

def main():
    """Generate the architecture diagram for Assignment 4"""
    
    with Diagram(
        "Assignment 4 - Project ORBIT Part 1 Architecture\nAutomating Private-Equity Intelligence for the Forbes AI 50",
        filename="docs/assignment4_architecture_diagram",
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
        # External Data Source
        forbes = Internet("Forbes AI 50\n\nData Source:\n- Company websites\n- LinkedIn pages\n- Press/blog pages")
        
        # Airflow Orchestration Layer
        with Cluster("☁️ Airflow Orchestration Layer"):
            dag_initial = Airflow("Initial Load DAG\n(One-time full ingestion)\nSchedule: @once")
            dag_daily = Airflow("Daily Refresh DAG\n(Incremental updates)\nSchedule: 0 3 * * *")
        
        # Data Ingestion Layer
        with Cluster("📥 Data Ingestion Layer"):
            scraper = Python("Web Scraper\n\nFetches:\n- Homepage\n- /about\n- /product\n- /careers\n- /blog")
            raw_storage = S3("Raw Data Storage\n(S3/GCS or Local)\n\nStores:\n- Raw HTML\n- Clean text\n- Metadata")
        
        # Processing Layer - Two Parallel Pipelines
        with Cluster("🔄 Processing Layer - Two Parallel Pipelines"):
            # RAG Pipeline
            with Cluster("📚 RAG Pipeline (Unstructured)"):
                chunker = Server("Text Chunker\n(500-1000 tokens)")
                vector_db = MongoDB("Vector DB\n(ChromaDB/FAISS)\n\nStores:\n- Document embeddings\n- Chunks")
                rag_llm = Python("LLM\n(RAG Dashboard)\n\nContext: Top-K chunks\nPrompt: dashboard_system.md")
                rag_dashboard = Storage("RAG Dashboard\n(Markdown)\n\n8 Sections:\n1. Company Overview\n2. Business Model\n3. Funding\n4. Growth\n5. Visibility\n6. Risks\n7. Outlook\n8. Disclosure Gaps")
            
            # Structured Pipeline
            with Cluster("📊 Structured Pipeline (Pydantic)"):
                instructor = Python("Instructor\n(Pydantic Extraction)\n\nModels:\n- Company\n- Event\n- Snapshot\n- Product\n- Leadership\n- Visibility")
                structured_data = Storage("Structured Data\n(JSON)\n\nNormalized:\n- Company record\n- Events\n- Snapshots\n- Products")
                payload_assembler = Server("Payload Assembler\n\nCombines:\n- Company record\n- Events\n- Snapshots\n- Products\n- Leadership\n- Visibility\n- Notes\n- Provenance")
                structured_payload = Storage("Structured Payload\n(JSON)\n\nValidated:\n- Complete schema\n- Provenance tags")
                structured_llm = Python("LLM\n(Structured Dashboard)\n\nContext: Structured payload\nPrompt: dashboard_system.md")
                structured_dashboard = Storage("Structured Dashboard\n(Markdown)\n\n8 Sections:\nSame schema as RAG")
        
        # API & UI Layer
        with Cluster("🌐 API & UI Layer"):
            fastapi = FastAPI("FastAPI Server\nPort: 8000\n\nEndpoints:\n- /companies\n- /dashboard/rag\n- /dashboard/structured\n- /rag/search")
            streamlit = Python("Streamlit UI\nPort: 8501\n\nFeatures:\n- Company dropdown\n- Dashboard display\n- Comparison view")
        
        # Evaluation Layer
        with Cluster("📊 Evaluation & Comparison"):
            evaluator = Server("Evaluation Engine\n\nRubric:\n- Factual correctness (0-3)\n- Schema adherence (0-2)\n- Provenance use (0-2)\n- Hallucination control (0-2)\n- Readability (0-1)")
            eval_results = Storage("Evaluation Results\n(EVAL.md)\n\nComparison:\n- RAG vs Structured\n- 5+ companies\n- Reflection notes")
        
        # Storage Layer
        with Cluster("💾 Storage Layer"):
            structured_storage = S3("Structured Storage\n\nStores:\n- data/structured/\n- data/payloads/")
            dashboard_storage = Storage("Dashboard Storage\n\nStores:\n- Generated dashboards\n- Comparison results")
        
        # Connections - Data Ingestion
        forbes >> Edge(label="Scrape", color="blue") >> scraper
        scraper >> Edge(label="Store Raw Data", color="blue") >> raw_storage
        
        # Airflow to Scraper
        dag_initial >> Edge(label="Trigger Full Load", color="darkblue", style="bold") >> scraper
        dag_daily >> Edge(label="Trigger Daily Refresh", color="darkblue", style="bold") >> scraper
        
        # RAG Pipeline Flow
        raw_storage >> Edge(label="Extract Text", color="green") >> chunker
        chunker >> Edge(label="Create Embeddings", color="green") >> vector_db
        vector_db >> Edge(label="RAG Query\n(Top-K chunks)", color="green", style="bold") >> rag_llm
        rag_llm >> Edge(label="Generate Dashboard", color="green") >> rag_dashboard
        
        # Structured Pipeline Flow
        raw_storage >> Edge(label="Extract & Normalize", color="orange") >> instructor
        instructor >> Edge(label="Pydantic Models", color="orange") >> structured_data
        structured_data >> Edge(label="Assemble Payload", color="orange") >> payload_assembler
        payload_assembler >> Edge(label="Validated Payload", color="orange") >> structured_payload
        structured_payload >> Edge(label="Structured Context", color="orange", style="bold") >> structured_llm
        structured_llm >> Edge(label="Generate Dashboard", color="orange") >> structured_dashboard
        
        # Storage connections
        structured_data >> Edge(label="Save", color="gray") >> structured_storage
        structured_payload >> Edge(label="Save", color="gray") >> structured_storage
        rag_dashboard >> Edge(label="Save", color="gray") >> dashboard_storage
        structured_dashboard >> Edge(label="Save", color="gray") >> dashboard_storage
        
        # API connections
        fastapi >> Edge(label="Query", color="purple") >> vector_db
        fastapi >> Edge(label="Load Payload", color="purple") >> structured_storage
        fastapi >> Edge(label="Generate RAG", color="purple") >> rag_llm
        fastapi >> Edge(label="Generate Structured", color="purple") >> structured_llm
        
        # Streamlit connections
        streamlit >> Edge(label="API Calls", color="cyan") >> fastapi
        streamlit >> Edge(label="Display Dashboards", color="cyan") >> dashboard_storage
        
        # Evaluation connections
        evaluator >> Edge(label="Compare", color="red", style="bold") >> rag_dashboard
        evaluator >> Edge(label="Compare", color="red", style="bold") >> structured_dashboard
        evaluator >> Edge(label="Save Results", color="red") >> eval_results
        
        # Airflow to Storage
        dag_initial >> Edge(label="Store Results", color="gray") >> structured_storage
        dag_daily >> Edge(label="Update Payloads", color="gray") >> structured_storage

    print("✅ Assignment 4 architecture diagram generated successfully!")
    print("📁 Output saved to: docs/assignment4_architecture_diagram.png")
    print("\n📋 Diagram Components:")
    print("   - Airflow Orchestration Layer (2 DAGs: Initial Load, Daily Refresh)")
    print("   - Data Ingestion Layer (Web Scraper, Raw Storage)")
    print("   - Processing Layer (2 Parallel Pipelines: RAG & Structured)")
    print("   - API & UI Layer (FastAPI, Streamlit)")
    print("   - Evaluation & Comparison Layer")
    print("   - Storage Layer (S3/GCS, Vector DB, Local)")
    print("\n🔄 Pipeline Flows:")
    print("   RAG: Raw → Chunk → Embed → Vector DB → LLM → Dashboard")
    print("   Structured: Raw → Instructor → Pydantic → Payload → LLM → Dashboard")
    print("\nTo regenerate, run: python scripts/generate_assignment4_architecture_diagram.py")


if __name__ == "__main__":
    main()

