import  { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertCircle } from 'lucide-react';

interface Incident {
  id: number;
  component_id: string;
  status: string;
  start_time: string;
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const fetchIncidents = async () => {
    const res = await axios.get('http://localhost:3000/incidents');
    setIncidents(res.data);
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000); // Poll every 5s for "Live Feed"[cite: 2]
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <AlertCircle className="text-red-500" /> Mission-Critical IMS
        </h1>
      </header>

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
                  <span className={`px-2 py-1 rounded text-xs ${incident.status === 'OPEN' ? 'bg-red-900 text-red-200' : 'bg-green-900 text-green-200'}`}>
                    {incident.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-400">
                  {new Date(incident.start_time).toLocaleString()}
                </td>
                <td className="px-6 py-4">
                  <button className="text-sm bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded">
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;