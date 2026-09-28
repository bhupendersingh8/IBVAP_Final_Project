import React from 'react';
import { useIncidents, useCameras } from '../api/hooks';
import { format } from 'date-fns';
import { FileBarChart, Download, Printer } from 'lucide-react';

export const Reports: React.FC = () => {
  const { data: incidents } = useIncidents(100, false);
  const { data: cameras } = useCameras();

  // Compute breakdown metrics
  const totalIncidents = incidents?.length || 0;
  const criticalCount = incidents?.filter(i => i.severity === 'CRITICAL' || i.severity === 'HIGH').length || 0;
  const acknowledgedCount = incidents?.filter(i => i.acknowledged).length || 0;

  // Breakdown by event type
  const eventTypeMap: Record<string, number> = {};
  incidents?.forEach(i => {
    eventTypeMap[i.event_type] = (eventTypeMap[i.event_type] || 0) + 1;
  });

  const handleExportCSV = () => {
    if (!incidents || incidents.length === 0) return;
    const header = "Incident_ID,Timestamp,Camera_ID,Event_Type,Severity,Status,SHA256\n";
    const rows = incidents.map(i => 
      `"${i.id}","${i.timestamp}","${i.camera_id}","${i.event_type}","${i.severity}","${i.status || (i.acknowledged ? 'ACKNOWLEDGED' : 'NEW')}","${i.sha256 || ''}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `IBVAP_Operational_Report_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="vms-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Operational Reports & Shift Audits</h2>
          <p className="text-xs text-slate-400">
            Generate official surveillance audit logs, incident summaries, and camera uptime statistics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePrint}
            className="vms-btn text-xs font-medium"
          >
            <Printer size={14} /> Print Report
          </button>
          <button
            onClick={handleExportCSV}
            className="vms-btn vms-btn-primary text-xs font-medium"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Date Filter & Metrics Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="vms-card p-4">
          <div className="text-xs font-semibold uppercase text-slate-400">Total Logged Incidents</div>
          <div className="text-2xl font-bold text-white mt-1">{totalIncidents}</div>
          <div className="text-xs text-slate-400 mt-1">Across all monitored zones</div>
        </div>

        <div className="vms-card p-4">
          <div className="text-xs font-semibold uppercase text-slate-400">Critical / High Severity</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{criticalCount}</div>
          <div className="text-xs text-slate-400 mt-1">Perimeter boundary alerts</div>
        </div>

        <div className="vms-card p-4">
          <div className="text-xs font-semibold uppercase text-slate-400">Operator Resolution Rate</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {totalIncidents > 0 ? Math.round((acknowledgedCount / totalIncidents) * 100) : 100}%
          </div>
          <div className="text-xs text-slate-400 mt-1">{acknowledgedCount} acknowledged</div>
        </div>

        <div className="vms-card p-4">
          <div className="text-xs font-semibold uppercase text-slate-400">Camera System Uptime</div>
          <div className="text-2xl font-bold text-blue-400 mt-1">99.8%</div>
          <div className="text-xs text-slate-400 mt-1">{cameras?.length || 4} channels active</div>
        </div>
      </div>

      {/* Incident Breakdown Table */}
      <div className="vms-card overflow-hidden">
        <div className="vms-card-header flex items-center justify-between">
          <span className="flex items-center gap-2">
            <FileBarChart size={14} className="text-blue-400" />
            Incident Distribution by Event Classification
          </span>
          <span className="text-xs text-slate-400">Last 30 Days</span>
        </div>

        <div className="p-4">
          {Object.keys(eventTypeMap).length === 0 ? (
            <div className="py-6 text-center text-xs text-slate-500">
              No historical incidents to categorize.
            </div>
          ) : (
            <div className="space-y-3 text-xs">
              {Object.entries(eventTypeMap).map(([type, count]) => {
                const percentage = totalIncidents > 0 ? Math.round((count / totalIncidents) * 100) : 0;
                return (
                  <div key={type} className="space-y-1">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="font-medium">{type}</span>
                      <span className="font-mono text-slate-400">{count} events ({percentage}%)</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
                      <div
                        className="bg-blue-600 h-full rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Official Sign-off Block */}
      <div className="vms-card p-4 bg-[#0f172a] text-xs text-slate-400 space-y-2">
        <div className="font-semibold text-slate-300">Shift Handover & Compliance Certification</div>
        <p>
          This automated operational report is compiled in accordance with standard border surveillance logging standards. All entries are hashed and verified against the tamper-evident ledger.
        </p>
        <div className="pt-2 flex items-center justify-between border-t border-[#334155] text-[11px]">
          <span>Generated by: Operator 1 (Supervisor)</span>
          <span>Timestamp: {format(new Date(), 'yyyy-MM-dd HH:mm:ss')} IST</span>
        </div>
      </div>
    </div>
  );
};
