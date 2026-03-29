import logging
import time
from typing import Dict, Any, List
from graph.state import AgentState
from data.rag_pipeline import retrieve_context

logger = logging.getLogger("copilot.context_enrich")

async def context_enrich_agent(state: AgentState) -> Dict[str, Any]:
    """Agent 3: Enriches signals with fundamental context from RAG."""
    ticker = state["ticker"]
    
    print(f"\n[📚 CONTEXT ENRICH] Querying ChromaDB for {ticker} filings...")
    time.sleep(1.0) # Simulate semantic search
    
    try:
        # Retrieve context from filings
        chunks = await retrieve_context(
            query=f"Analyze {ticker} recently corporate filings for distress sell or routine block deal",
            ticker=ticker,
            k=3
        )
        
        # Determine sentiment from context (Simplified for now)
        context_summary = "NEUTRAL"
        if chunks:
            # In a real app, an LLM would summarize these chunks
            context_summary = "DATA_RETRIEVED"
            print(f"  ├─ Found {len(chunks)} relevant filing chunks.")
            for i, chunk in enumerate(chunks):
                print(f"  ├─ Ref {i+1}: {chunk[:80]}...")
        else:
            print("  └─ ⚠️ No local filings found. Falling back to generic market context.")
            chunks = ["Market-wide FMCG sentiment is stable.", "IT sector facing headwinds in US/EU."]
            
        trace = state.get("agent_trace", [])
        trace.append({
            "agent": "context_enrich",
            "timestamp": time.strftime("%H:%M:%SZ"),
            "output": f"RAG context retrieved: {len(chunks)} chunks",
            "confidence": 0.85
        })
        
        return {
            "filing_chunks": chunks,
            "context": {"summary": context_summary, "chunks": chunks},
            "agent_trace": trace
        }
        
    except Exception as e:
        logger.error(f"Context Enrich error for {ticker}: {e}")
        print(f"  └─ ⚠️ RAG Engine failure: {e}")
        return {"errors": [f"Context Enrich Failure: {str(e)}"]}
