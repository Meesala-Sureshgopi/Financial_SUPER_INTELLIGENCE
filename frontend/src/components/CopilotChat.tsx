import React, { useState, useRef, useEffect } from 'react';

const CopilotChat: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'agent', text: "👋 Welcome to Avalon. I'm your Neural Intelligence Orchestrator. Every analysis I provide is synthesized from real-time market signals, technical patterns, and SEBI filings. How can I assist your investment strategy today?" },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const resp = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg })
      });
      const result = await resp.json();
      
      const response = result.response || 'Neural synthesis complete. No actionable intelligence found.';
      
      setMessages(prev => [...prev, {
        role: 'agent',
        text: response,
      }]);
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: 'agent',
        text: `⚠️ Engine Error: ${e.message}\n\nPlease ensure the backend is active.`,
      }]);
    }
    setLoading(false);
  }

  return (
    <div className="chat-container">
      {open && (
        <div className="glass-card chat-panel animate-slide-up">
          <div className="chat-header">
            <h3>✨ AI Orchestrator</h3>
            <button className="chat-close" onClick={() => setOpen(false)}>✕</button>
          </div>
          <div className="chat-messages" ref={messagesRef}>
            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg ${msg.role}`}>
                {msg.text}
              </div>
            ))}
            {loading && (
              <div className="chat-msg agent">
                <div className="loader">
                  <div className="loader-dot"></div>
                  <div className="loader-dot"></div>
                  <div className="loader-dot"></div>
                  <span>Neural Core Processing...</span>
                </div>
              </div>
            )}
          </div>
          <div className="chat-input-row">
            <input
              placeholder="Ask about a ticker (e.g. UPL)..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={loading}
            />
            <button className="btn btn-primary btn-sm" onClick={handleSend} disabled={loading}>
              Send
            </button>
          </div>
        </div>
      )}
      <button className="chat-toggle" onClick={() => setOpen(!open)}>
        {open ? '✕' : '✨'}
      </button>
    </div>
  );
}

export default CopilotChat;
