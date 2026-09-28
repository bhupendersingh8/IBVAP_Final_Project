import React, { useState, useMemo } from 'react';
import { useANPRObservations } from '../api/hooks';
import { format, formatDistanceToNow } from 'date-fns';
import { Search, Download } from 'lucide-react';
import { Badge } from '../components/ui/Badge';

export const ANPR: React.FC = () => {
  const { data: anprRecords, isLoading } = useANPRObservations(50);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filtered = useMemo(() => {
    if (!anprRecords) return [];
    return anprRecords.filter((rec) => {
      if (statusFilter !== 'ALL' && rec.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchPlate = rec.plate_text?.toLowerCase().includes(q);
        const matchCam = rec.camera_id?.toLowerCase().includes(q);
        const matchClass = rec.vehicle_class?.toLowerCase().includes(q);
        if (!matchPlate && !matchCam && !matchClass) return false;
      }
      return true;
    });
  }, [anprRecords, searchQuery, statusFilter]);

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="vms-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Automated Number Plate Recognition (ANPR)</h2>
          <p className="text-xs text-slate-400">
            Log and query vehicle movement across perimeter entry points and access gates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const csvContent = "data:text/csv;charset=utf-8," 
                + ["Time,Camera,Plate,Vehicle,Confidence,Status"].join(",") + "\n"
                + filtered.map(r => `"${r.timestamp}","${r.camera_id}","${r.plate_text || ''}","${r.vehicle_class}","${Math.round(r.plate_confidence * 100)}%","${r.status}"`).join("\n");
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", `anpr_log_${Date.now()}.csv`);
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
            className="vms-btn text-xs font-medium"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="vms-card p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3 flex-1 max-w-xl">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by license plate number, vehicle class, or camera..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-md pl-9 pr-3 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#0f172a] border border-[#334155] text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="PENDING">Pending Consensus</option>
            <option value="FLAGGED">Flagged / Watchlist</option>
          </select>
        </div>

        <div className="text-slate-400 text-xs">
          Showing {filtered.length} observations
        </div>
      </div>

      {/* ANPR Records Table */}
      <div className="vms-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="vms-table-header">
                <th className="py-2.5 px-4">Time</th>
                <th className="py-2.5 px-4">Camera</th>
                <th className="py-2.5 px-4">Vehicle Type</th>
                <th className="py-2.5 px-4">License Plate</th>
                <th className="py-2.5 px-4">Confidence</th>
                <th className="py-2.5 px-4">Consensus</th>
                <th className="py-2.5 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b] text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    Loading ANPR logs...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No vehicle plate logs recorded.
                  </td>
                </tr>
              ) : (
                filtered.map((rec) => (
                  <tr key={rec.id} className="vms-table-row">
                    <td className="py-3 px-4 text-slate-300 font-mono whitespace-nowrap">
                      <div>{format(new Date(rec.timestamp), 'HH:mm:ss')}</div>
                      <div className="text-[10px] text-slate-500">
                        {formatDistanceToNow(new Date(rec.timestamp), { addSuffix: true })}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-semibold text-white whitespace-nowrap">
                      {rec.camera_id}
                    </td>
                    <td className="py-3 px-4 text-slate-200 capitalize">
                      {rec.vehicle_class || 'Vehicle'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-sm tracking-wider text-amber-300 bg-amber-950/40 border border-amber-800/80 px-2 py-0.5 rounded">
                        {rec.plate_text || 'UNREADABLE'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {Math.round((rec.plate_confidence || 0.85) * 100)}%
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {rec.consistent_readings || 1} frames
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Badge variant={rec.status === 'CONFIRMED' ? 'success' : 'neutral'}>
                        {rec.status || 'LOGGED'}
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
