import React, { useState, useEffect, useRef } from 'react';
import './styles.css';

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Auto-scroll to bottom of logs
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const addLog = (message, typeOverride) => {
    // Parse log level from message format "[LEVEL] message"
    let logLevel = 'info';
    let cleanMessage = message;
    
    const levelMatch = message.match(/^\[([A-Z]+)\]\s*(.*)$/);
    if (levelMatch) {
      const level = levelMatch[1].toLowerCase();
      cleanMessage = levelMatch[2];
      
      // Map Python logging levels to display types
      if (level === 'debug') logLevel = 'info';
      else if (level === 'warning') logLevel = 'warning';
      else if (level === 'error') logLevel = 'error';
      else if (level === 'critical') logLevel = 'error';
      else logLevel = 'info';
    }
    
    // Use typeOverride if provided, otherwise use parsed type
    const type = typeOverride || logLevel;
    
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = {
      id: Date.now() + Math.random(),
      message: cleanMessage,
      type,
      timestamp,
    };
    setLogs(prev => [...prev, logEntry]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setReport(null);
    setLogs([]);
    addLog('Starting investigation...', 'info');

    try {
      addLog('Connecting to API...', 'info');
      
      // Step 1: Start investigation
      const response = await fetch('http://localhost:8000/investigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      const investigationId = data.investigation_id;
      
      addLog(`Investigation started (ID: ${investigationId.slice(0, 8)}...)`, 'info');

      // Step 2: Connect to streaming endpoint
      connectToStream(investigationId);

    } catch (error) {
      addLog(`Error: ${error.message}`, 'error');
      setReport(null);
      setLoading(false);
    }
  };

  const connectToStream = (investigationId) => {
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(
      `http://localhost:8000/stream/${investigationId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
          // Add log message
          addLog(data.message);
        } else if (data.type === 'complete') {
          // Investigation complete
          if (data.status === 'error') {
            addLog(`Investigation failed: ${data.error}`, 'error');
            setReport(null);
          } else {
            addLog('Investigation completed successfully', 'info');
            setReport(data.result);
          }
          
          // Close the connection
          eventSource.close();
          setLoading(false);
        }
      } catch (err) {
        console.error('Error parsing event:', err, 'event.data:', event.data);
      }
    };

    eventSource.onerror = (event) => {
      console.error('EventSource error:', event);
      addLog('Connection lost', 'error');
      eventSource.close();
      setLoading(false);
    };

    eventSourceRef.current = eventSource;
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const renderReport = (report) => {
    if (typeof report === 'string') {
      return (
        <div className="text-slate-300 whitespace-pre-wrap">{report}</div>
      );
    }

    if (typeof report === 'object' && report !== null) {
      return (
        <div className="space-y-6">
          {Object.entries(report).map(([key, value]) => (
            <div key={key} className="report-section">
              <h3 className="report-section-title">
                {key
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, l => l.toUpperCase())}
              </h3>
              <div className="report-content">
                {typeof value === 'string' && value ? (
                  <p>{value}</p>
                ) : value ? (
                  <pre className="bg-slate-900 p-4 rounded text-sm overflow-auto max-h-96 text-slate-300">
                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                  </pre>
                ) : (
                  <p className="text-slate-500 italic">No data available</p>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return <div>No report data</div>;
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-8 py-8">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl font-bold text-white mb-2 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              SentinelOps
            </h1>
            <p className="text-lg text-slate-300 mb-1">Your AI Reliability Engineer</p>
            <p className="text-sm text-slate-400">Standing Guard Against Operational Risk</p>
          </div>
        </header>

        {/* Main Container */}
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto px-8 py-8">
            {/* Investigation Section */}
            <div className="mb-12">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label htmlFor="query" className="block text-sm font-medium text-slate-300 mb-3">
                    Investigation Query
                  </label>
                  <textarea
                    id="query"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Describe the issue you want to investigate. Example: 'High latency in API endpoints between 2:00 PM and 2:15 PM today'"
                    required
                    disabled={loading}
                    className="w-full min-h-32 px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-vertical disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className={`w-full py-3 px-4 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
                    loading || !query.trim()
                      ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-700 hover:to-cyan-700 active:scale-95'
                  }`}
                >
                  {loading ? (
                    <>
                      <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-white rounded-full animate-spin"></span>
                      Investigating...
                    </>
                  ) : (
                    'Investigate'
                  )}
                </button>
              </form>
            </div>

            {/* Report Section */}
            {report && (
              <div className="bg-slate-900/30 border border-slate-800 rounded-lg p-8 backdrop-blur-sm">
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Investigation Report
                </h2>
                <div className="prose prose-invert max-w-none">
                  {renderReport(report)}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!report && !loading && (
              <div className="text-center py-16">
                <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-slate-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <p className="text-slate-400">Enter a query to start investigating</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Debug Logs Sidebar */}
      <aside className="w-80 bg-slate-900/50 border-l border-slate-800 flex flex-col">
        {/* Sidebar Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            Debug Logs
          </h2>
          {logs.length > 0 && (
            <button
              onClick={clearLogs}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {/* Logs Container */}
        <div className="flex-1 overflow-auto p-4 space-y-2">
          {logs.length === 0 ? (
            <div className="text-center text-slate-500 py-8">
              <p className="text-sm">No logs yet</p>
              <p className="text-xs text-slate-600 mt-1">Debug logs will appear here</p>
            </div>
          ) : (
            logs.map(log => (
              <div
                key={log.id}
                className={`debug-log-entry ${log.type}`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-slate-600 text-xs flex-shrink-0 font-mono">{log.timestamp}</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-sm flex-shrink-0 ${
                    log.type === 'warning' ? 'bg-yellow-900 text-yellow-200' :
                    log.type === 'error' ? 'bg-red-900 text-red-200' :
                    'bg-blue-900 text-blue-200'
                  }`}>
                    {log.type.toUpperCase()}
                  </span>
                  <span className="flex-1 text-sm">{log.message}</span>
                </div>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </aside>
    </div>
  );
}

export default App;