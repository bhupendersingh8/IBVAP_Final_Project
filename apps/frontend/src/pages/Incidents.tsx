import React, { useState, useMemo } from 'react';
import { 
  useIncidents, useUpdateIncidentStatus, useBatchUpdateIncidentStatus, useAcknowledgeIncident 
} from '../api/hooks';
import { format, formatDistanceToNow } from 'date-fns';
import { 
  Search, Eye, Check, X, ShieldCheck
} from 'lucide-react';
import { Badge, BadgeVariant } from '../components/ui/Badge';
import { StatusIndicator } from '../components/ui/StatusIndicator';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { LedgerAuditModal } from '../components/LedgerAuditModal';
import { Incident } from '../types';
import { playSuccessPing } from '../utils/audioAlerts';

export const Incidents: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedIncidentIds, setSelectedIncidentIds] = useState<string[]>([]);
  
  // Modals & Detail Drawer
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [lightboxData, setLightboxData] = useState<{ url: string; title: string; camera: string; time: string; sha256?: string | null } | null>(null);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  const { data: incidents, isLoading } = useIncidents(100, false);
  const { mutate: updateStatus } = useUpdateIncidentStatus();
  const { mutate: acknowledge } = useAcknowledgeIncident();
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

  const getSeverityBadgeVariant = (severity: string): BadgeVariant => {
    switch (severity) {
      case 'CRITICAL': return 'danger';
      case 'HIGH': return 'danger';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'info';
      default: return 'neutral';
    }
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      
      {/* ======================================================== */}
      {/* 1. TOP HEADER & FILTER BAR                               */}
      {/* ======================================================== */}
      <div className="vms-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Incident Management</h2>
          <p className="text-xs text-slate-400">
            Review, acknowledge, and audit security alerts logged across border sectors.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAuditModalOpen(true)}
            className="vms-btn text-xs font-medium"
            title="Verify evidence integrity hash chain"
          >
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Verify Evidence Chain</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="vms-card p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          {/* Search Input */}
          <div className="relative flex-1 max-w-sm">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by camera or incident type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-md pl-9 pr-3 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-[#0f172a] border border-[#334155] text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#0f172a] border border-[#334155] text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="NEW">New (Unacknowledged)</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>

        {/* Batch Actions */}
        {selectedIncidentIds.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-slate-400">{selectedIncidentIds.length} selected</span>
            <button
              onClick={() => handleBatchStatus('ACKNOWLEDGED')}
              disabled={isBatchUpdating}
              className="vms-btn vms-btn-primary"
            >
              <Check size={12} /> Acknowledge Selected
            </button>
            <button
              onClick={() => handleBatchStatus('RESOLVED')}
              disabled={isBatchUpdating}
              className="vms-btn"
            >
              Resolve Selected
            </button>
          </div>
        )}
      </div>

      {/* ======================================================== */}
      {/* 2. ENTERPRISE INCIDENT TABLE                             */}
      {/* ======================================================== */}
      <div className="vms-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="vms-table-header">
                <th className="py-2.5 px-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIncidentIds.length === filtered.length}
                    onChange={handleSelectAll}
                    className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                  />
                </th>
                <th className="py-2.5 px-3">Time</th>
                <th className="py-2.5 px-3">Camera</th>
                <th className="py-2.5 px-3">Incident Type</th>
                <th className="py-2.5 px-3">Location / Detail</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b] text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    Loading incident ledger...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    No incidents match the active filters.
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => {
                  const isSelected = selectedIncidentIds.includes(inc.id);
                  const isAck = inc.acknowledged || inc.status === 'ACKNOWLEDGED' || inc.status === 'RESOLVED';
                  return (
                    <tr
                      key={inc.id}
                      className={`vms-table-row ${isSelected ? 'bg-blue-950/20' : ''}`}
                    >
                      <td className="py-3 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelect(inc.id)}
                          className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                        />
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300 whitespace-nowrap">
                        <div>{format(new Date(inc.timestamp), 'HH:mm:ss')}</div>
                        <div className="text-[10px] text-slate-500">
                          {formatDistanceToNow(new Date(inc.timestamp), { addSuffix: true })}
                        </div>
                      </td>
                      <td className="py-3 px-3 font-semibold text-white whitespace-nowrap">
                        {inc.camera_id}
                      </td>
                      <td className="py-3 px-3 text-slate-200 font-medium">
                        {inc.event_type}
                      </td>
                      <td className="py-3 px-3 text-slate-400 max-w-xs truncate">
                        {inc.explanation || 'Perimeter alert recorded'}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <Badge variant={getSeverityBadgeVariant(inc.severity)}>
                          {inc.severity}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {inc.status === 'RESOLVED' ? (
                          <StatusIndicator status="verified" label="Resolved" />
                        ) : isAck ? (
                          <StatusIndicator status="online" label="Acknowledged" />
                        ) : (
                          <StatusIndicator status="critical" label="Open" />
                        )}
                      </td>
                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setSelectedIncident(inc)}
                            className="vms-btn text-xs"
                            title="View incident details"
                          >
                            <Eye size={12} /> View
                          </button>
                          {!isAck && (
                            <button
                              onClick={() => {
                                acknowledge(inc.id);
                                playSuccessPing();
                              }}
                              className="vms-btn vms-btn-primary text-xs"
                            >
                              Acknowledge
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

      {/* ======================================================== */}
      {/* 3. INCIDENT DETAIL MODAL                                 */}
      {/* ======================================================== */}
      {selectedIncident && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="bg-[#1e293b] border border-[#334155] rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="px-5 py-4 border-b border-[#334155] flex items-center justify-between bg-[#0f172a]">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <span>Incident Report #{selectedIncident.id.substring(0, 8)}</span>
                  <Badge variant={getSeverityBadgeVariant(selectedIncident.severity)}>
                    {selectedIncident.severity}
                  </Badge>
                </h3>
                <span className="text-xs text-slate-400 font-mono">
                  {format(new Date(selectedIncident.timestamp), 'yyyy-MM-dd HH:mm:ss')} IST
                </span>
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content */}
            <div className="p-5 space-y-4 text-xs">
              {/* Information Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#0f172a] p-3 rounded border border-[#334155]">
                <div>
                  <span className="text-slate-500 block uppercase text-[10px]">Camera ID</span>
                  <span className="font-semibold text-white">{selectedIncident.camera_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block uppercase text-[10px]">Event Type</span>
                  <span className="font-semibold text-slate-200">{selectedIncident.event_type}</span>
                </div>
                <div>
                  <span className="text-slate-500 block uppercase text-[10px]">Confidence</span>
                  <span className="font-mono text-slate-200">
                    {Math.round((selectedIncident.confidence || 0.85) * 100)}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block uppercase text-[10px]">Status</span>
                  <span className="font-semibold text-white">
                    {selectedIncident.status || (selectedIncident.acknowledged ? 'ACKNOWLEDGED' : 'NEW')}
                  </span>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Incident Summary</label>
                <div className="bg-[#0f172a] p-3 rounded border border-[#334155] text-slate-300">
                  {selectedIncident.explanation || 'Target motion detected across monitored perimeter boundaries.'}
                </div>
              </div>

              {/* Evidence Frame Preview */}
              <div>
                <label className="text-slate-400 block mb-1 font-medium">Captured Visual Evidence</label>
                <div className="aspect-video bg-black rounded border border-[#334155] overflow-hidden relative flex items-center justify-center">
                  <img
                    src={`/api/v1/evidence/${selectedIncident.id}/snapshot`}
                    alt="Evidence Frame"
                    className="w-full h-full object-contain cursor-pointer"
                    onClick={() => setLightboxData({
                      url: `/api/v1/evidence/${selectedIncident.id}/snapshot`,
                      title: selectedIncident.event_type,
                      camera: selectedIncident.camera_id,
                      time: selectedIncident.timestamp,
                      sha256: selectedIncident.sha256
                    })}
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `/api/v1/cameras/${selectedIncident.camera_id}/snapshot`;
                    }}
                  />
                </div>
              </div>

              {/* Audit & Integrity Information */}
              {selectedIncident.sha256 && (
                <div className="bg-[#0f172a] p-3 rounded border border-[#334155] space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                    <ShieldCheck size={14} className="text-emerald-400" />
                    <span>Evidence Integrity Verification</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-400 break-all">
                    SHA-256: {selectedIncident.sha256}
                  </div>
                </div>
              )}

              {/* Modal Actions */}
              <div className="flex items-center justify-between pt-3 border-t border-[#334155]">
                <div className="flex items-center gap-2">
                  <select
                    value={selectedIncident.status || (selectedIncident.acknowledged ? 'ACKNOWLEDGED' : 'NEW')}
                    onChange={(e) => {
                      updateStatus({ incidentId: selectedIncident.id, status: e.target.value });
                      setSelectedIncident({ ...selectedIncident, status: e.target.value as any });
                      playSuccessPing();
                    }}
                    className="bg-[#0f172a] border border-[#334155] text-slate-200 rounded px-2.5 py-1 text-xs"
                  >
                    <option value="NEW">New</option>
                    <option value="ACKNOWLEDGED">Acknowledged</option>
                    <option value="INVESTIGATING">Investigating</option>
                    <option value="RESOLVED">Resolved</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedIncident(null)}
                    className="vms-btn"
                  >
                    Close
                  </button>
                  {!selectedIncident.acknowledged && (
                    <button
                      onClick={() => {
                        acknowledge(selectedIncident.id);
                        setSelectedIncident({ ...selectedIncident, acknowledged: true, status: 'ACKNOWLEDGED' });
                        playSuccessPing();
                      }}
                      className="vms-btn vms-btn-primary"
                    >
                      Acknowledge Incident
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Lightbox */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={true}
          onClose={() => setLightboxData(null)}
          snapshotUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          cameraId={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
        />
      )}

      {/* Ledger Audit Modal */}
      {isAuditModalOpen && (
        <LedgerAuditModal
          isOpen={true}
          onClose={() => setIsAuditModalOpen(false)}
        />
      )}
    </div>
  );
};
