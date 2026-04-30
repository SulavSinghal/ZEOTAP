import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertCircle, X } from 'lucide-react';

interface Incident {
  id: number;
  component_id: string;
  status: string;
  start_time: string;
}

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [rawSignals, setRawSignals] = useState<any[]>([]);
  const [rcaForm, setRcaForm] = useState({ root_cause: '', fix_applied: '', prevention_steps: '' });

  const fetchIncidents = async () => {
    const res = await axios.get('http://localhost:3000/incidents');
    setIncidents(res.data);
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleManageClick = async (incident: Incident) => {
    setSelectedIncident(incident);
    // Fetch raw signals for the Data Lake view
    const res = await axios.get(`http://localhost:3000/incidents/${incident.component_id}/signals`);
    setRawSignals(res.data);
  };

  const handleCloseIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncident) return;

    try {
      await axios.patch(`http://localhost:3000/incidents/${selectedIncident.id}/close`, rcaForm);
      setSelectedIncident(null);
      setRcaForm({ root_cause: '', fix_applied: '', prevention_steps: '' });
      fetchIncidents(); // Refresh the list
    } catch (error) {
      alert("Failed to close incident. Ensure all RCA fields are filled.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <AlertCircle className="text-red-500" /> Mission-Critical IMS
        </h1>
      </header>

      {/* Live Feed Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
        <table className="w-full text-left">
          <thead className="bg-gray-700 text-gray-300 uppercase text-xs">
            <tr>
              <th className="px-6 py-3">ID</th>
              <th className="px-6 py-3">Component</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Triggered At</th>
              <th className="px-6 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {incidents.map((incident) => (
              <tr key={incident.id} className="hover:bg-gray-750">
                <td className="px-6 py-4">#{incident.id}</td>
                <td className="px-6 py-4 font-mono text-blue-400">{incident.component_id}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${incident.status === 'OPEN' ? 'bg-red-900 text-red-200' : 'bg-green-900 text-green-200'}`}>
                    {incident.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-400">
                  {new Date(incident.start_time).toLocaleString()}
                </td>
                <td className="px-6 py-4">
                  <button 
                    onClick={() => handleManageClick(incident)}
                    className="text-sm bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded transition"
                  >
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* RCA Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center p-4">
          <div className="bg-gray-800 rounded-lg max-w-2xl w-full flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-xl font-bold">Manage Incident #{selectedIncident.id}</h2>
              <button onClick={() => setSelectedIncident(null)}><X /></button>
            </div>
            
            <div className="p-4 overflow-y-auto">
              <h3 className="font-bold text-gray-400 mb-2">Raw Signals (MongoDB)</h3>
              <div className="bg-gray-900 p-3 rounded font-mono text-xs text-green-400 h-32 overflow-y-auto mb-6">
                {rawSignals.length > 0 ? JSON.stringify(rawSignals, null, 2) : "No raw signals found."}
              </div>

              {selectedIncident.status === 'OPEN' && (
                <form onSubmit={handleCloseIncident} className="space-y-4">
                  <h3 className="font-bold text-gray-400 mb-2">Root Cause Analysis (RCA)</h3>
                  <div>
                    <label className="block text-sm mb-1">Root Cause *</label>
                    <textarea required className="w-full bg-gray-700 rounded p-2 text-sm" 
                      value={rcaForm.root_cause} onChange={e => setRcaForm({...rcaForm, root_cause: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Fix Applied *</label>
                    <textarea required className="w-full bg-gray-700 rounded p-2 text-sm" 
                      value={rcaForm.fix_applied} onChange={e => setRcaForm({...rcaForm, fix_applied: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Prevention Steps</label>
                    <textarea className="w-full bg-gray-700 rounded p-2 text-sm" 
                      value={rcaForm.prevention_steps} onChange={e => setRcaForm({...rcaForm, prevention_steps: e.target.value})} />
                  </div>
                  <button type="submit" className="w-full bg-green-600 hover:bg-green-700 py-2 rounded font-bold transition">
                    Resolve & Close Incident
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}