export interface AgentTraceStep {
    agent: string;
    timestamp: string;
    output: string;
    confidence: number;
}

export interface Alert {
    ticker: string;
    company_name?: string;
    action: string;
    verdict: string;
    reasoning: string[];
    estimated_pnl: string;
    sources: string[];
    disclaimer: string;
    confidence: number;
    created_at?: string;
}

export interface AnalysisResult {
    ticker: string;
    company_name?: string;
    event_type: string;
    signal?: any;
    chart_signals: any[];
    context?: any;
    filing_chunks?: string[];
    conflicts?: any[];
    net_signal?: string;
    confidence: number;
    portfolio_impact?: any;
    estimated_pnl?: number;
    action?: string;
    action_reasoning?: string;
    citations?: string[];
    alert?: Alert;
    final_response: string;
    agent_trace: AgentTraceStep[];
    total_latency_ms?: number;
}

export interface MarketMover {
    ticker: string;
    price: number;
    change_pct: number;
    last_signal?: string;
}
