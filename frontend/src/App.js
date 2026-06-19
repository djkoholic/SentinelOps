// frontend/src/App.js
import React, { useState } from 'react';

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setReport(null);

    try {
      const response = await fetch('http://localhost:8000/investigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setReport(data.result);
    } catch (error) {
      setReport(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1> SentinelOps </h1>
        <p> Your AI Reliability Engineer </p>
        <p> Standing Guard Against Operational Risk </p>
      </header>
      <main>
        <form onSubmit={handleSubmit}>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your query..."
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Investigating...' : 'Investigate'}
          </button>
        </form>
        {report && (
          <div className="report">
            <h2>Investigation Report</h2>
            <pre>{typeof report === 'string' ? report : JSON.stringify(report, null, 2)}</pre>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;