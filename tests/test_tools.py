import asyncio
from datetime import date
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.tools.risk_logger import report_layoff_signal, LayoffSignal

async def test_get_latest_structured_payload():
    """Test payload retrieval tool"""
    print("Testing payload tool...")
    
    # Test with a company that exists
    result = await get_latest_structured_payload("anthropic")
    assert result.company_record is not None
    assert "legal_name" in result.company_record or "company_id" in result.company_record
    print("✅ Payload tool test passed")
    return True

async def test_rag_search_company():
    """Test RAG search tool"""
    print("Testing RAG search tool...")
    
    results = await rag_search_company("anthropic", "funding")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "text" in results[0]
    assert "score" in results[0]
    print("✅ RAG search tool test passed")
    return True

async def test_report_layoff_signal():
    """Test risk logging tool"""
    print("Testing risk logger tool...")
    
    signal = LayoffSignal(
        company_id="test_company",
        occurred_on=date.today(),
        description="Test layoff event",
        source_url="https://example.com/test"
    )
    
    result = await report_layoff_signal(signal)
    assert result == True
    
    # Verify log file was created
    log_file = Path("logs/risk_signals.jsonl")
    assert log_file.exists()
    print("✅ Risk logger tool test passed")
    return True

async def main():
    """Run all tests"""
    print("\n🚀 Running Lab 12 Tool Tests...\n")
    
    try:
        await test_get_latest_structured_payload()
        await test_rag_search_company()
        await test_report_layoff_signal()
        print("\n🎉 All Lab 12 tool tests passed!")
        print("✅ Lab 12 Checkpoint Complete!")
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)
