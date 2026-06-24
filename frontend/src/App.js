import React, { useState } from 'react';
import './styles.css';

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [events, setEvents] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!query.trim()) return;

    setLoading(true);
    setReport(null);
    setEvents([]);

    try {
      const response = await fetch(
        'http://localhost:8000/investigate',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        }
      );

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();

      const investigationId = data.investigation_id;

      const eventSource = new EventSource(
        `http://localhost:8000/stream/${investigationId}`
      );

      eventSource.onmessage = (event) => {
        const payload = JSON.parse(event.data);

        if (payload.type === 'complete') {
          setReport(payload.result);
          setLoading(false);
          eventSource.close();
          return;
        }

        if (payload.type === 'error') {
          setReport({
            error: payload.error,
          });

          setLoading(false);
          eventSource.close();
          return;
        }

        setEvents((prev) => [...prev, payload]);
      };

      eventSource.onerror = () => {
        eventSource.close();

        setLoading(false);

        setReport({
          error: 'Connection to event stream lost.',
        });
      };

    } catch (error) {
      setLoading(false);

      setReport({
        error: error.message,
      });
    }
  };

  const renderReport = (report) => {
    if (!report) {
    return <div>No report data</div>;
    }

    if (typeof report === 'string') {
    return ( <div className="text-slate-300 whitespace-pre-wrap">
    {report} </div>
    );
    }

    return ( <div className="space-y-8">
    {Object.entries(report).map(([key, value]) => ( <div key={key} className="report-section"> <h3 className="report-section-title">
    {key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())} </h3>

    
          <div className="report-content whitespace-pre-wrap
           text-slate-300">
            {Array.isArray(value)
              ? value.join('\n')
              : typeof value === 'object' && value !== null
              ? JSON.stringify(value, null, 2)
              : String(value)}
          </div>
        </div>
      ))}
    </div>
    
    );
    };


  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">

      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-8 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-white mb-2 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            SentinelOps
          </h1>

          <p className="text-lg text-slate-300 mb-1">
            Your AI Reliability Engineer
          </p>

          <p className="text-sm text-slate-400">
            Standing Guard Against Operational Risk
          </p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-8">

        <form onSubmit={handleSubmit} className="space-y-6 mb-8">

          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe the issue you want to investigate..."
            disabled={loading}
            required
            className="w-full min-h-32 px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-100"
          />

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Investigating...' : 'Investigate'}
          </button>

        </form>

        {events.length > 0 && (
          <div className="bg-slate-900/30 border border-slate-800 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-bold mb-4">
              Agent Activity
            </h2>

            <div className="space-y-2">
              {events.map((event, index) => (
                <div
                  key={index}
                  className="bg-slate-900 border border-slate-800 rounded px-4 py-3 text-sm text-slate-300"
                >
                  {event.message}
                </div>
              ))}
            </div>
          </div>
        )}

        {report && (
          <div className="bg-slate-900/30 border border-slate-800 rounded-lg p-8">
            <h2 className="text-2xl font-bold text-white mb-6">
              Investigation Report
            </h2>

            {renderReport(report)}
          </div>
        )}

      </main>

    </div>
  );
}

export default App;