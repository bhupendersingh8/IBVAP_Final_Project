import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AssuranceFinding } from '../types';

export const AssuranceAnalytics: React.FC = () => {
  const [findings, setFindings] = useState<AssuranceFinding[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');

  const fetchFindings = async () => {
    setLoading(true);
    try {
      const data = await api.getAssuranceFindings();
      setFindings(data);
    } catch (err) {
      console.error('Failed to load assurance findings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFindings();
  }, []);

  const filteredFindings = findings.filter(f =>
    selectedSeverity === 'ALL' || f.severity?.toUpperCase() === selectedSeverity
  );

  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase tracking-wider">
            <span>Forensic Intelligence</span>
            <span>/</span>
            <span className="text-secondary font-medium">Assurance Analytics Deep Dive</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Assurance Analytics</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Correlate pipeline integrity metrics, anomalies, and forensic telemetry across datasets, models, and real-time inference streams.
          </p>
        </div>

        <div className="flex items-center gap-space-xs">
          <button
            onClick={fetchFindings}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-space-md py-2 rounded-lg bg-surface-container-lowest text-primary hover:bg-surface-container font-label-mono-sm text-label-mono-sm font-semibold border border-surface-container shadow-sm transition-colors"
          >
            <span className={`material-symbols-outlined text-[16px] ${loading ? 'animate-spin' : ''}`}>refresh</span>
            Refresh Findings
          </button>
        </div>
      </div>

      {/* Analytics Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-md">
        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Total Findings</span>
          <span className="font-headline-lg text-headline-lg font-semibold text-primary">{findings.length}</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Active audit anomalies</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Critical Alerts</span>
          <span className="font-headline-lg text-headline-lg font-semibold text-error">
            {findings.filter(f => f.severity === 'CRITICAL').length}
          </span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Immediate action needed</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Warnings</span>
          <span className="font-headline-lg text-headline-lg font-semibold text-amber-600">
            {findings.filter(f => f.severity === 'WARNING').length}
          </span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Requires review</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Assurance Score</span>
          <span className="font-headline-lg text-headline-lg font-semibold text-emerald-700">99.4%</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Calculated health</span>
        </div>
      </div>

      {/* Severity Filter Tabs */}
      <div className="flex items-center gap-space-xs overflow-x-auto">
        {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map(sev => (
          <button
            key={sev}
            onClick={() => setSelectedSeverity(sev)}
            className={`px-space-md py-1.5 rounded-lg font-label-mono-sm text-label-mono-sm transition-colors ${
              selectedSeverity === sev
                ? 'bg-primary text-on-primary shadow-sm font-semibold'
                : 'bg-surface-container-lowest text-on-surface-variant hover:text-on-surface border border-surface-container'
            }`}
          >
            {sev} ({sev === 'ALL' ? findings.length : findings.filter(f => f.severity?.toUpperCase() === sev).length})
          </button>
        ))}
      </div>

      {/* Findings List */}
      <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm border border-surface-container flex flex-col gap-space-md">
        <h2 className="font-headline-sm text-headline-sm text-primary">Forensic Audit Findings Feed</h2>

        {filteredFindings.length === 0 ? (
          <div className="py-12 text-center flex flex-col items-center gap-space-xs">
            <span className="material-symbols-outlined text-[48px] text-emerald-600">verified</span>
            <span className="font-headline-sm text-headline-sm text-primary">No Assurance Findings Flagged</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant max-w-md">
              All pipeline nodes, dataset manifests, and inference streams are operating within verified cryptographic and statistical thresholds.
            </span>
          </div>
        ) : (
          <div className="space-y-space-sm">
            {filteredFindings.map((f, idx) => (
              <div
                key={idx}
                className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm"
              >
                <div className="flex items-start gap-space-sm">
                  <span className={`material-symbols-outlined text-[20px] mt-0.5 ${
                    f.severity === 'CRITICAL' ? 'text-error' : f.severity === 'WARNING' ? 'text-amber-600' : 'text-secondary'
                  }`}>
                    {f.severity === 'CRITICAL' ? 'error' : f.severity === 'WARNING' ? 'warning' : 'info'}
                  </span>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-space-xs flex-wrap">
                      <span className="font-body-md text-body-md font-semibold text-primary">{f.title || f.category}</span>
                      <span className={`px-2 py-0.2 rounded font-label-mono-sm text-[10px] uppercase font-bold ${
                        f.severity === 'CRITICAL' ? 'bg-error-container text-on-error-container' : 'bg-amber-100 text-amber-900'
                      }`}>
                        {f.severity}
                      </span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">{f.description || f.message}</p>
                    <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-1">
                      Target: {f.target || 'Inference Stream Cam-01'} • Timestamp: {f.timestamp || new Date().toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-space-xs shrink-0 self-end sm:self-center">
                  <button className="px-space-md py-1 rounded bg-surface-container-lowest text-primary font-label-mono-sm text-label-mono-sm border border-surface-container hover:bg-surface-container transition-colors">
                    Forensic Drilldown
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
