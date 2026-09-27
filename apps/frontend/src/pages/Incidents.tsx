import React, { useState, useMemo } from 'react';
import { 
  useIncidents, useAcknowledgeIncident, useUpdateIncidentStatus, 
  useBatchUpdateIncidentStatus 
} from '../api/hooks';
import { format } from 'date-fns';
import { 
  Search, Filter, AlertTriangle, CheckCircle, Clock, 
  ShieldCheck, HelpCircle, MessageSquare, Lock, Eye, CheckSquare, 
  Square, RefreshCw, Download
} from 'lucide-react';
import { EventTypeBadge } from '../components/EventTypeBadge';
import { OperatorFeedbackModal } from '../components/OperatorFeedbackModal';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { LedgerAuditModal } from '../components/LedgerAuditModal';
import { playSuccessPing } from '../utils/audioAlerts';

const SeverityBadge = ({ severity }: { severity: string }) => {
  const colors = {
    INFO: 'bg-slate-100 text-slate-700',
    LOW: 'bg-yellow-100 text-yellow-800',
    MEDIUM: 'bg-orange-100 text-orange-800',
    HIGH: 'bg-red-100 text-red-800',
    CRITICAL: 'bg-red-600 text-white shadow-sm animate-pulse',
  };
  return (
    <span className={`px-2 py-0.5 text-[11px] font-bold rounded-full ${colors[severity as keyof typeof colors] || colors.INFO}`}>
      {severity}
    </span>
  );
};

const StatusBadge = ({ status }: { status?: string }) => {
  const current = status || 'NEW';
  const badges: Record<string, { bg: string; text: string; label: string }> = {
    NEW: { bg: 'bg-orange-100 text-orange-800 border-orange-200', label: 'NEW', text: 'text-orange-600' },
    ACKNOWLEDGED: { bg: 'bg-blue-100 text-blue-800 border-blue-200', label: 'ACKNOWLEDGED', text: 'text-blue-600' },
    INVESTIGATING: { bg: 'bg-purple-100 text-purple-800 border-purple-200', label: 'INVESTIGATING', text: 'text-purple-600' },
    RESOLVED: { bg: 'bg-emerald-100 text-emerald-800 border-emerald-200', label: 'RESOLVED', text: 'text-emerald-600' },
  };
  const cfg = badges[current] || badges.NEW;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.bg}`}>
      {cfg.label}
    </span>
  );
};

export const Incidents = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedIncidentIds, setSelectedIncidentIds] = useState<string[]>([]);
  
  // Modals
  const [feedbackIncident, setFeedbackIncident] = useState<any>(null);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [lightboxData, setLightboxData] = useState<{ url: string; title: string; camera: string; time: string; sha256?: string | null } | null>(null);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  const { data: incidents, isLoading } = useIncidents(100, false);
  const { mutate: updateStatus } = useUpdateIncidentStatus();
  const { mutate: batchUpdateStatus, isPending: isBatchUpdating } = useBatchUpdateIncidentStatus();

  // Filtered incidents calculation
  const filtered = useMemo(() => {
    if (!incidents) return [];
    return incidents.filter((inc) => {
      // Status filter
      const currentStatus = inc.status || (inc.acknowledged ? 'ACKNOWLEDGED' : 'NEW');
      if (statusFilter !== 'ALL' && currentStatus !== statusFilter) return false;

      // Severity filter
      if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;

      // Search query
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

  // Checkbox toggle helpers
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
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner & Audit Trigger */}
      <div className="glass-panel rounded-2xl p-5 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-gradient-to-br from-rose-600 to-red-700 text-white rounded-xl shadow-lg shadow-red-950/40">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-xl font-extrabold dark:text-white text-slate-900 tracking-tight">Perimeter Incidents & Chain-of-Custody Ledger</h1>
            <p className="dark:text-slate-400 text-slate-500 text-xs mt-0.5 font-medium">
              Real-time threat lifecycle states, cryptographic SHA-256 evidence provenance, and operator verification.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAuditModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white rounded-xl text-xs font-bold transition shadow-md border border-slate-700 cursor-pointer"
          >
            <Lock size={14} className="text-emerald-400" />
            Audit Cryptographic Ledger
          </button>
        </div>
      </div>

      {/* Interactive Search & Multi-Filter Bar */}
      <div className="glass-panel rounded-2xl p-4 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Search Bar */}
          <div className="relative flex-1 min-w-[240px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by camera, event type, or description..."
              className="w-full pl-9 pr-3 py-2 text-xs font-mono dark:bg-slate-950/80 dark:border-slate-700/80 dark:text-white bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 shadow-inner"
            />
          </div>

          {/* Severity Pills */}
          <div className="flex items-center gap-1 p-1 rounded-xl dark:bg-slate-950/60 bg-slate-100 border dark:border-slate-800 border-slate-200 text-xs font-bold">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => {
              const count = incidents?.filter((i) => sev === 'ALL' || i.severity === sev).length || 0;
              return (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2.5 py-1 rounded-lg transition-all text-xs font-mono cursor-pointer ${
                    severityFilter === sev 
                      ? 'bg-blue-600 text-white shadow-xs font-bold' 
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {sev} <span className="text-[10px] text-slate-400 font-mono">({count})</span>
                </button>
              );
            })}
          </div>

          {/* Status Pills */}
          <div className="flex items-center gap-1 p-1 rounded-xl dark:bg-slate-950/60 bg-slate-100 border dark:border-slate-800 border-slate-200 text-xs font-bold">
            {['ALL', 'NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-lg transition-all text-xs font-mono cursor-pointer ${
                  statusFilter === st 
                    ? 'bg-purple-600 text-white shadow-xs font-bold' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Batch Operations Bar (Visible when rows are selected) */}
        {selectedIncidentIds.length > 0 && (
          <div className="p-3 bg-blue-500/15 border border-blue-500/30 rounded-xl flex flex-wrap items-center justify-between gap-2 animate-in fade-in text-xs">
            <span className="font-bold text-blue-400 font-mono">
              {selectedIncidentIds.length} incident{selectedIncidentIds.length > 1 ? 's' : ''} selected
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleBatchStatus('ACKNOWLEDGED')}
                disabled={isBatchUpdating}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold transition cursor-pointer shadow-xs"
              >
                Batch Acknowledge
              </button>
              <button
                onClick={() => handleBatchStatus('INVESTIGATING')}
                disabled={isBatchUpdating}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-semibold transition cursor-pointer shadow-xs"
              >
                Batch Investigate
              </button>
              <button
                onClick={() => handleBatchStatus('RESOLVED')}
                disabled={isBatchUpdating}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold transition cursor-pointer shadow-xs"
              >
                Batch Resolve
              </button>
              <button
                onClick={() => setSelectedIncidentIds([])}
                className="px-2.5 py-1.5 text-slate-400 hover:text-white font-medium cursor-pointer"
              >
                Deselect
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="glass-panel rounded-2xl border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300 border-collapse">
            <thead className="dark:bg-slate-950/70 bg-slate-50 dark:text-slate-400 text-slate-700 font-semibold border-b dark:border-slate-800/80 border-slate-200 uppercase text-[10px] font-mono tracking-wider">
              <tr>
                <th className="p-3.5 w-8 text-center">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIncidentIds.length === filtered.length}
                    onChange={handleSelectAll}
                    className="rounded text-blue-600 cursor-pointer"
                  />
                </th>
                <th className="p-3.5">Timestamp</th>
                <th className="p-3.5">Camera</th>
                <th className="p-3.5">Severity</th>
                <th className="p-3.5">Event Type & Explanation</th>
                <th className="p-3.5">Confidence</th>
                <th className="p-3.5">Evidence (SHA-256)</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y dark:divide-slate-800/60 divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="p-12 text-center text-slate-400 font-mono">Loading perimeter logs...</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-16 text-center text-slate-400 flex flex-col items-center justify-center">
                    <CheckCircle size={36} className="text-emerald-400 mb-2 opacity-60" />
                    <p className="font-semibold text-sm">No incidents match active filters.</p>
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => {
                  const currentStatus = inc.status || (inc.acknowledged ? 'ACKNOWLEDGED' : 'NEW');
                  const isSelected = selectedIncidentIds.includes(inc.id);
                  const evFile = inc.evidence_reference?.split(/[/\\]/).pop();

                  return (
                    <tr
                      key={inc.id}
                      className={`dark:hover:bg-slate-800/40 hover:bg-slate-50 transition-colors ${
                        isSelected 
                          ? 'dark:bg-blue-950/30 bg-blue-50/50' 
                          : currentStatus === 'NEW' 
                            ? 'dark:bg-red-950/20 bg-red-50/30' 
                            : ''
                      }`}
                    >
                      <td className="p-3.5 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelect(inc.id)}
                          className="rounded text-blue-600 cursor-pointer"
                        />
                      </td>
                      <td className="p-3.5 font-mono text-[11px] whitespace-nowrap text-slate-400">
                        {format(new Date(inc.timestamp.endsWith('Z') ? inc.timestamp : inc.timestamp + 'Z'), 'MMM dd, HH:mm:ss')}
                      </td>
                      <td className="p-3.5 font-mono font-bold dark:text-cyan-400 text-slate-900">{inc.camera_id}</td>
                      <td className="p-3.5"><SeverityBadge severity={inc.severity} /></td>
                      <td className="p-3.5">
                        <EventTypeBadge eventType={inc.event_type} />
                        <p className="text-[11px] dark:text-slate-300 text-slate-600 mt-1 max-w-xs truncate" title={inc.explanation}>
                          {inc.explanation}
                        </p>
                      </td>
                      <td className="p-3.5 font-mono font-bold dark:text-slate-200 text-slate-700">
                        {Math.round(inc.confidence * 100)}%
                      </td>
                      <td className="p-3.5">
                        {evFile ? (
                          <div
                            onClick={() => {
                              setLightboxData({
                                url: `/evidence/${evFile}`,
                                title: inc.event_type,
                                camera: inc.camera_id,
                                time: format(new Date(inc.timestamp.endsWith('Z') ? inc.timestamp : inc.timestamp + 'Z'), 'MMM dd, HH:mm:ss'),
                                sha256: inc.sha256,
                              });
                              playSuccessPing();
                            }}
                            className="flex items-center gap-2 group cursor-pointer"
                            title="Click to view full-resolution evidence & audit hash"
                          >
                            <img
                              src={`/evidence/${evFile}`}
                              alt="Evidence thumbnail"
                              className="h-8 w-14 object-cover rounded-lg border dark:border-slate-700 border-slate-200 group-hover:border-cyan-400 transition shadow-xs"
                            />
                            <div className="flex flex-col">
                              <span className="text-[10px] text-cyan-400 font-bold group-hover:underline flex items-center gap-1">
                                <Eye size={11} /> View
                              </span>
                              {inc.sha256 && (
                                <span className="font-mono text-[9px] text-slate-400 truncate max-w-[80px]">
                                  {inc.sha256.slice(0, 8)}...
                                </span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-500 italic text-[10px]">No crop</span>
                        )}
                      </td>
                      <td className="p-3.5"><StatusBadge status={currentStatus} /></td>
                      <td className="p-3.5 text-right">
                        <div className="flex justify-end items-center gap-1.5 flex-wrap">
                          <button
                            onClick={() => {
                              setFeedbackIncident(inc);
                              setIsFeedbackOpen(true);
                            }}
                            className="px-2.5 py-1 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-[11px] font-semibold inline-flex items-center gap-1 transition cursor-pointer"
                            title="Submit Operator Ground Truth Feedback"
                          >
                            <MessageSquare size={11} /> Feedback
                          </button>

                          {currentStatus === 'NEW' && (
                            <button
                              onClick={() => updateStatus({ incidentId: inc.id, status: 'ACKNOWLEDGED' })}
                              className="px-2.5 py-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-[11px] font-semibold transition cursor-pointer shadow-xs"
                            >
                              Acknowledge
                            </button>
                          )}
                          {currentStatus === 'ACKNOWLEDGED' && (
                            <button
                              onClick={() => updateStatus({ incidentId: inc.id, status: 'INVESTIGATING' })}
                              className="px-2.5 py-1 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg text-[11px] font-semibold transition cursor-pointer shadow-xs"
                            >
                              Investigate
                            </button>
                          )}
                          {(currentStatus === 'ACKNOWLEDGED' || currentStatus === 'INVESTIGATING') && (
                            <button
                              onClick={() => updateStatus({ incidentId: inc.id, status: 'RESOLVED' })}
                              className="px-2.5 py-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-[11px] font-semibold transition cursor-pointer shadow-xs"
                            >
                              Resolve
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

      {/* Operator Feedback Active Learning Modal */}
      <OperatorFeedbackModal
        incident={feedbackIncident}
        isOpen={isFeedbackOpen}
        onClose={() => {
          setIsFeedbackOpen(false);
          setFeedbackIncident(null);
        }}
      />

      {/* Evidence Lightbox Modal */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={!!lightboxData}
          imageUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          camera={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
          onClose={() => setLightboxData(null)}
        />
      )}

      {/* Cryptographic SHA-256 Ledger Audit Modal */}
      <LedgerAuditModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </div>
  );
};
