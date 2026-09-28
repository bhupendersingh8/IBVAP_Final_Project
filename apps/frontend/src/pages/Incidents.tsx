import React, { useState, useMemo } from 'react';
import { 
  useIncidents, useUpdateIncidentStatus, useBatchUpdateIncidentStatus 
} from '../api/hooks';
import { format } from 'date-fns';
import { 
  Search, AlertTriangle, CheckCircle, Clock, 
  ShieldCheck, Lock, Eye, CheckSquare, 
  Square, Download, FileText, Check, Filter
} from 'lucide-react';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { LedgerAuditModal } from '../components/LedgerAuditModal';
import { playSuccessPing } from '../utils/audioAlerts';

export const Incidents = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedIncidentIds, setSelectedIncidentIds] = useState<string[]>([]);
  
  // Modals
  const [lightboxData, setLightboxData] = useState<{ url: string; title: string; camera: string; time: string; sha256?: string | null } | null>(null);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  const { data: incidents, isLoading } = useIncidents(100, false);
  const { mutate: updateStatus } = useUpdateIncidentStatus();
  const { mutate: batchUpdateStatus, isPending: isBatchUpdating } = useBatchUpdateIncidentStatus();

  // Filtered incidents calculation
  const filtered = useMemo(() => {
    if (!incidents) return [];
    return incidents.filter((inc) => {
      const currentStatus = inc.status || (inc.acknowledged ? 'ACKNOWLEDGED' : 'NEW');
      if (statusFilter !== 'ALL' && currentStatus !== statusFilter) return false;
      if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchCam = inc.camera_id?.toLowerCase().includes(q);
        const matchType = inc.event_type?.toLowerCase().includes(q);
        const matchExp = inc.explanation?.toLowerCase().includes(q);
        if (!matchCam && !matchType && !matchExp) return false;
      }
      return true;
    });
  }, [incidents, statusFilter, severityFilter, searchQuery]);

  const handleToggleSelect = (id: string) => {
    setSelectedIncidentIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIncidentIds.length === filtered.length) {
      setSelectedIncidentIds([]);
    } else {
      setSelectedIncidentIds(filtered.map((i) => i.id));
    }
  };

  const handleBatchStatus = (status: string) => {
    if (selectedIncidentIds.length === 0) return;
    batchUpdateStatus({ incidentIds: selectedIncidentIds, status }, {
      onSuccess: () => {
        playSuccessPing();
        setSelectedIncidentIds([]);
      }
    });
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* ── Top Header & Forensic Ledger Status ──────────────────────────────── */}
      <div className="tactical-glass p-4 lg:p-5 rounded-2xl border border-cyan-500/20 flex flex-wrap justify-between items-center gap-4 hud-box">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-950/70 border border-cyan-400/40 text-cyan-400 neon-glow-cyan">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-lg lg:text-xl font-black text-white tracking-wide flex items-center gap-2">
              <span>FORENSIC INCIDENT LEDGER</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
                SEC 65B COMPLIANT
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Cryptographically verified incident timeline with immutable SHA-256 Merkle hash chain.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAuditModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 bg-purple-950/60 hover:bg-purple-900/60 text-purple-300 border border-purple-500/40 rounded-xl text-xs font-mono font-bold transition shadow-lg shadow-purple-950/40"
          >
            <Lock size={13} className="text-purple-400" />
            <span>Audit Hash Ledger</span>
          </button>
        </div>
      </div>

      {/* ── Filter & Search Toolbar ─────────────────────────────────────────── */}
      <div className="tactical-glass p-3 rounded-xl border border-cyan-500/20 flex flex-wrap items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by camera, event type, or keywords..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-700/60 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
          />
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-slate-500 text-[11px]">Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2 py-1 rounded-md text-[11px] font-bold transition-all ${
                severityFilter === sev
                  ? sev === 'CRITICAL'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 neon-glow-crimson'
                    : 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 neon-glow-cyan'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        {/* Batch Status Actions */}
        {selectedIncidentIds.length > 0 && (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-700">
            <span className="text-[11px] font-mono text-cyan-300 font-bold">
              {selectedIncidentIds.length} Selected:
            </span>
            <button
              onClick={() => handleBatchStatus('ACKNOWLEDGED')}
              disabled={isBatchUpdating}
              className="px-2.5 py-1 rounded bg-blue-950/60 text-blue-300 border border-blue-500/40 text-[11px] font-mono font-bold hover:bg-blue-900/60"
            >
              Acknowledge
            </button>
            <button
              onClick={() => handleBatchStatus('RESOLVED')}
              disabled={isBatchUpdating}
              className="px-2.5 py-1 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 text-[11px] font-mono font-bold hover:bg-emerald-900/60"
            >
              Resolve
            </button>
          </div>
        )}
      </div>

      {/* ── Incidents Forensic Table ────────────────────────────────────────── */}
      <div className="tactical-glass rounded-2xl border border-cyan-500/20 overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/80 border-b border-cyan-500/20 text-slate-400 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="p-3 w-8">
                  <button onClick={handleSelectAll} className="text-slate-400 hover:text-white">
                    {selectedIncidentIds.length === filtered.length && filtered.length > 0 ? (
                      <CheckSquare size={14} className="text-cyan-400" />
                    ) : (
                      <Square size={14} />
                    )}
                  </button>
                </th>
                <th className="p-3">Incident ID & Severity</th>
                <th className="p-3">Event Type</th>
                <th className="p-3">Camera / Sector</th>
                <th className="p-3">Forensic SHA-256 Hash</th>
                <th className="p-3">Timestamp</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 font-mono">
                    Loading cryptographic ledger records...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 font-mono">
                    No incidents matching selected filters.
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => {
                  const isSelected = selectedIncidentIds.includes(inc.id);
                  const isCritical = inc.severity === 'CRITICAL' || inc.severity === 'HIGH';
                  return (
                    <tr 
                      key={inc.id}
                      className={`hover:bg-cyan-950/20 transition-all ${isSelected ? 'bg-cyan-950/30' : ''}`}
                    >
                      <td className="p-3">
                        <button onClick={() => handleToggleSelect(inc.id)} className="text-slate-400 hover:text-white">
                          {isSelected ? (
                            <CheckSquare size={14} className="text-cyan-400" />
                          ) : (
                            <Square size={14} />
                          )}
                        </button>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isCritical 
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' 
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          }`}>
                            {inc.severity}
                          </span>
                          <span className="font-bold text-slate-200">
                            {inc.id.slice(0, 8)}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-cyan-300 font-bold">
                        {inc.event_type.replace(/_/g, ' ')}
                      </td>
                      <td className="p-3 text-slate-300">
                        {inc.camera_id}
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-black/60 text-purple-300 border border-purple-500/30 font-mono text-[10px]" title={inc.sha256 || 'None'}>
                          {inc.sha256 ? `${inc.sha256.slice(0, 12)}...` : 'PENDING'}
                        </span>
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">
                        {format(new Date(inc.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {inc.evidence_reference && (
                            <button
                              onClick={() => {
                                const filename = inc.evidence_reference ? inc.evidence_reference.split(/[/\\]/).pop() || '' : '';
                                setLightboxData({
                                  url: `/evidence/${filename}`,
                                  title: `${inc.event_type} (${inc.severity})`,
                                  camera: inc.camera_id,
                                  time: new Date(inc.timestamp).toLocaleString(),
                                  sha256: inc.sha256
                                });
                              }}
                              className="px-2 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-500/30 text-[10px] font-bold flex items-center gap-1"
                            >
                              <Eye size={11} />
                              <span>View Evidence</span>
                            </button>
                          )}
                          {!inc.acknowledged && (
                            <button
                              onClick={() => updateStatus({ incidentId: inc.id, status: 'ACKNOWLEDGED' })}
                              className="px-2 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold flex items-center gap-1"
                            >
                              <Check size={11} />
                              <span>Ack</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lightbox Modal */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={true}
          onClose={() => setLightboxData(null)}
          imageUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          camera={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
        />
      )}

      {/* Audit Modal */}
      <LedgerAuditModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </div>
  );
};
