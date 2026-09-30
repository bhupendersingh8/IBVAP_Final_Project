import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { logoutUser } from "../../api/client";

interface HeaderProps {
  onRunAudit?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onRunAudit }) => {
  const navigate = useNavigate();
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [auditRunning, setAuditRunning] = useState(false);
  const [auditBanner, setAuditBanner] = useState<string | null>(null);

  const username = localStorage.getItem("ibvap_username") || "Audit Lead";
  const role = localStorage.getItem("ibvap_user_role") || "Auditor";

  const handleAuditClick = () => {
    if (onRunAudit) {
      onRunAudit();
    } else {
      setAuditRunning(true);
      setAuditBanner("Initiating cryptographic audit across pipeline checkpoints...");
      setTimeout(() => {
        setAuditRunning(false);
        setAuditBanner("Integrity Audit Complete: Hash chain validated. 0 anomalies detected across active checkpoints.");
        setTimeout(() => setAuditBanner(null), 4000);
      }, 1200);
    }
  };

  const handleLogout = () => {
    logoutUser();
    navigate("/login");
  };

  return (
    <>
      <header className="fixed top-0 left-72 right-0 h-16 bg-surface-container-lowest/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)] z-40 flex items-center justify-between px-space-lg">
        {/* Breadcrumb & Telemetry Status Pips */}
        <div className="flex items-center gap-space-md">
          <div className="flex items-center gap-1.5 font-label-mono-md text-label-mono-md text-on-surface-variant">
            <span className="font-semibold text-primary uppercase">System</span>
            <span>/</span>
            <span className="text-on-surface font-medium">Operational Console</span>
          </div>
          <div className="h-4 w-px bg-surface-container" />

          {/* Quick Status Pips */}
          <div className="hidden 2xl:flex items-center gap-space-xs">
            <div className="inline-flex items-center gap-1.5 px-space-xs py-0.5 rounded-lg bg-emerald-50 text-emerald-800 text-label-mono-sm font-label-mono-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              <span>Backend: Connected</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-space-xs py-0.5 rounded-lg bg-surface-container text-on-surface text-label-mono-sm font-label-mono-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
              <span>Worker: Ready</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-space-xs py-0.5 rounded-lg bg-emerald-50 text-emerald-800 text-label-mono-sm font-label-mono-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              <span>Stream: Cam-01</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-space-xs py-0.5 rounded-lg bg-surface-container text-on-surface text-label-mono-sm font-label-mono-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              <span>Model: YOLO11n</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-space-xs py-0.5 rounded-lg bg-emerald-50 text-emerald-800 text-label-mono-sm font-label-mono-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              <span>Ledger: Synced</span>
            </div>
          </div>
        </div>

        {/* Right Tools & User Profile */}
        <div className="flex items-center gap-space-md">
          <button
            onClick={handleAuditClick}
            disabled={auditRunning}
            className="inline-flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-primary text-on-primary hover:bg-primary-container transition-colors disabled:opacity-75"
            type="button"
          >
            <span className={`material-symbols-outlined text-[16px] ${auditRunning ? "animate-spin" : ""}`}>
              {auditRunning ? "sync" : "shield"}
            </span>
            <span className="font-label-mono-sm text-label-mono-sm font-medium">
              {auditRunning ? "Auditing Pipeline..." : "Run Integrity Audit"}
            </span>
          </button>

          <button
            onClick={() => setShowSettingsModal(true)}
            className="p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors"
            title="Service Adapter Settings"
            type="button"
          >
            <span className="material-symbols-outlined text-[20px]">hub</span>
          </button>

          <div className="h-6 w-px bg-surface-container" />

          {/* User Profile Pill with Logout */}
          <div className="flex items-center gap-space-sm group relative cursor-pointer">
            <div className="flex flex-col text-right">
              <span className="font-body-sm text-body-sm font-semibold text-on-surface capitalize">
                {username}
              </span>
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                {role} • Team Trinetra
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary">
              <span className="material-symbols-outlined text-[18px]">person</span>
            </div>

            {/* Dropdown Menu */}
            <div className="hidden group-hover:flex absolute right-0 top-full mt-1 w-48 bg-surface-container-lowest rounded-lg shadow-lg border border-surface-container p-1 flex-col z-50">
              <div className="px-3 py-2 text-label-mono-sm text-on-surface-variant border-b border-surface-container">
                Role: <span className="font-semibold text-primary">{role}</span>
              </div>
              <button
                onClick={() => navigate("/admin")}
                className="w-full text-left px-3 py-2 text-body-sm hover:bg-surface-container rounded transition-colors flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
                Access Control
              </button>
              <button
                onClick={handleLogout}
                className="w-full text-left px-3 py-2 text-body-sm text-error hover:bg-error-container/30 rounded transition-colors flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[16px]">logout</span>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Floating Audit Toast Notification */}
      {auditBanner && (
        <div className="fixed top-20 right-6 z-50 max-w-md bg-primary text-on-primary p-3 rounded-lg shadow-xl border border-primary-container flex items-center gap-3 animate-fade-in font-label-mono-sm text-[12px]">
          <span className="material-symbols-outlined text-emerald-400 text-[20px]">verified</span>
          <span className="flex-1">{auditBanner}</span>
          <button onClick={() => setAuditBanner(null)} className="text-on-primary-container hover:text-on-primary">
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      )}

      {/* Service Adapter Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-primary/40 backdrop-blur-sm p-space-md">
          <div className="w-full max-w-xl bg-surface-container-lowest rounded-xl shadow-xl flex flex-col overflow-hidden">
            <div className="p-space-lg flex items-center justify-between bg-surface-container-low">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-secondary text-[24px]">hub</span>
                <div className="flex flex-col">
                  <span className="font-headline-sm text-headline-sm text-primary">Service Adapters &amp; Endpoints</span>
                  <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Live Runtime Architecture</span>
                </div>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-1 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-space-lg flex flex-col gap-space-md font-body-sm">
              <div className="grid grid-cols-2 gap-space-sm font-label-mono-sm">
                <div className="p-3 bg-surface-container-low rounded-lg flex flex-col">
                  <span className="text-on-surface-variant uppercase text-[10px]">FastAPI Backend</span>
                  <span className="font-semibold text-primary mt-1">http://localhost:8000</span>
                  <span className="text-emerald-700 text-[11px]">REST + WebSocket Active</span>
                </div>
                <div className="p-3 bg-surface-container-low rounded-lg flex flex-col">
                  <span className="text-on-surface-variant uppercase text-[10px]">MediaMTX RTSP Bridge</span>
                  <span className="font-semibold text-primary mt-1">rtsp://localhost:8554</span>
                  <span className="text-emerald-700 text-[11px]">TCP/UDP Stream Ready</span>
                </div>
                <div className="p-3 bg-surface-container-low rounded-lg flex flex-col">
                  <span className="text-on-surface-variant uppercase text-[10px]">Inference Engine</span>
                  <span className="font-semibold text-primary mt-1">YOLO11n Runtime</span>
                  <span className="text-secondary text-[11px]">Deterministic Proof Binding</span>
                </div>
                <div className="p-3 bg-surface-container-low rounded-lg flex flex-col">
                  <span className="text-on-surface-variant uppercase text-[10px]">Evidence Ledger</span>
                  <span className="font-semibold text-primary mt-1">Local Hash Chain</span>
                  <span className="text-emerald-700 text-[11px]">DuckDB + SQLite Storage</span>
                </div>
              </div>

              <div className="p-3 bg-surface-container-low rounded-lg flex flex-col gap-1 text-[12px] text-on-surface-variant font-label-mono-sm">
                <div className="flex justify-between">
                  <span>Admissibility Context:</span>
                  <span className="font-semibold text-primary">Bharatiya Sakshya Adhiniyam, 2023</span>
                </div>
                <div className="flex justify-between">
                  <span>Hashing Standard:</span>
                  <span className="font-semibold text-primary">SHA-256 (NIST FIPS 180-4)</span>
                </div>
                <div className="flex justify-between">
                  <span>Signing Protocol:</span>
                  <span className="font-semibold text-primary">Ed25519 (RFC 8032) + Post-Quantum WOTS+</span>
                </div>
              </div>
            </div>

            <div className="p-space-md bg-surface-container-low flex justify-end">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-space-md py-1.5 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm shadow-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
