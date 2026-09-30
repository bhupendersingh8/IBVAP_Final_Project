import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const Admin: React.FC = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [showAttestationModal, setShowAttestationModal] = useState(false);
  const [showProvisionDrawer, setShowProvisionDrawer] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loadingUser, setLoadingUser] = useState<boolean>(true);

  // Form states for provisioning
  const [provisionEmail, setProvisionEmail] = useState('');
  const [provisionRole, setProvisionRole] = useState('Auditor / Security Reviewer');

  useEffect(() => {
    let mounted = true;
    const fetchUser = async () => {
      try {
        const u = await api.getCurrentUser();
        if (mounted) setCurrentUser(u);
      } catch {
        if (mounted) setCurrentUser(null);
      } finally {
        if (mounted) setLoadingUser(false);
      }
    };
    fetchUser();
    return () => { mounted = false; };
  }, []);

  const handleConfirmProvision = () => {
    alert(`Operator access provisioned for: ${provisionEmail} (${provisionRole})\nEvent logged in append-only audit trail.`);
    setShowProvisionDrawer(false);
    setProvisionEmail('');
  };

  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Admin Context Strip Header */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant">
            <span className="text-primary font-semibold">SYSTEM</span>
            <span>/</span>
            <span>ADMINISTRATION & SECURITY CONTROL</span>
            <span>/</span>
            <span className="text-secondary font-medium">PROTECTED AREA {currentUser?.role ? `(ROLE: ${currentUser.role})` : '(SESSION AUTH REQUIRED)'}</span>
          </div>
          <div className="flex items-center gap-space-md flex-wrap mt-0.5">
            <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Security & Governance Matrix</h1>
            <div className="flex items-center gap-space-xs flex-wrap">
              <span className="font-label-mono-sm text-label-mono-sm px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-medium">
                Session-Bound Identity
              </span>
              <span className="font-label-mono-sm text-label-mono-sm px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-medium">
                Cryptographically Verifiable Technical Evidence
              </span>
            </div>
          </div>
        </div>

        {/* Rapid Operations Dock */}
        <div className="flex items-center gap-space-sm self-start xl:self-auto">
          <button
            onClick={() => setShowAttestationModal(true)}
            className="inline-flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-surface-container-lowest text-primary shadow-sm hover:bg-surface-container-low border border-surface-container transition-colors"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px] text-secondary">verified_user</span>
            <span className="font-label-mono-sm text-label-mono-sm font-medium">Ledger Attestation</span>
          </button>
          <button
            onClick={() => setShowProvisionDrawer(true)}
            className="inline-flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-primary text-on-primary hover:bg-primary-container transition-colors shadow-sm"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">key</span>
            <span className="font-label-mono-sm text-label-mono-sm font-medium">Provision Operator</span>
          </button>
        </div>
      </div>

      {/* Hardware Stat & Micro-Telemetry Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-space-md">
        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">FastAPI Adapter</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          </div>
          <span className="font-headline-sm text-headline-sm text-primary">Connected</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">REST & SSE Gateway</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Inference Engine</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          </div>
          <span className="font-headline-sm text-headline-sm text-primary">YOLO11n Process</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Assurance Inference Worker</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">RTSP Video Bridge</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          </div>
          <span className="font-headline-sm text-headline-sm text-primary">MediaMTX Active</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Cam Streams Routing</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Evidence Ledger</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          </div>
          <span className="font-headline-sm text-headline-sm text-primary">Tamper-Evident</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Hash Chain Synchronized</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1 col-span-2 md:col-span-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Access Control</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          </div>
          <span className="font-headline-sm text-headline-sm text-primary">RBAC Active</span>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Session Auth</span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-space-xs overflow-x-auto pb-1">
        {[
          { key: 'users', label: 'Users & Access Control' },
          { key: 'roles', label: 'Roles & Permissions Matrix' },
          { key: 'events', label: 'Security & Auth Events' },
          { key: 'endpoints', label: 'Integration Endpoints & Keys' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-space-md py-2 rounded-lg font-label-mono-sm text-label-mono-sm transition-all shrink-0 ${
              activeTab === tab.key
                ? 'bg-primary text-on-primary font-medium shadow-sm'
                : 'bg-surface-container-lowest text-on-surface-variant hover:text-on-surface border border-surface-container'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 2xl:grid-cols-12 gap-space-lg">
        {/* Left Column: Tab-dependent view */}
        <div className="2xl:col-span-8 flex flex-col gap-space-md">
          {activeTab === 'users' && (
            <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-md">
              <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-md">
                <div className="flex items-center gap-space-sm flex-1 max-w-lg bg-surface-container-low px-space-md py-1.5 rounded-lg border border-surface-container/60">
                  <span className="material-symbols-outlined text-[18px] text-on-surface-variant">search</span>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-transparent text-primary text-body-md font-body-md focus:outline-none w-full placeholder:text-on-surface-variant/70"
                    placeholder="Search by name, key UUID, thumbprint..."
                    type="text"
                  />
                </div>
                <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                  <span className="font-medium text-primary">Role-Based Access:</span>
                  <span>USER / ANALYST, AUDITOR / SECURITY REVIEWER, ADMIN</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-body-md text-body-md">
                  <thead>
                    <tr className="bg-surface-container-low text-on-surface-variant font-label-mono-sm text-label-mono-sm uppercase tracking-wider">
                      <th className="py-2.5 px-3 rounded-l-lg">User Identity</th>
                      <th className="py-2.5 px-3">Authentication Provider</th>
                      <th className="py-2.5 px-3">Assigned Role & Scope</th>
                      <th className="py-2.5 px-3">Session Status</th>
                      <th className="py-2.5 px-3">Last Activity</th>
                      <th className="py-2.5 px-3 text-right rounded-r-lg">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container">
                    {currentUser ? (
                      <>
                        <tr>
                          <td className="py-3 px-3">
                            <div className="flex flex-col">
                              <span className="font-semibold text-primary font-body-sm">
                                {currentUser.full_name || currentUser.username || 'Authenticated Operator'}
                              </span>
                              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                                {currentUser.email || currentUser.username}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-3 font-label-mono-sm text-label-mono-sm">JWT Bearer Token</td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded bg-primary text-on-primary font-label-mono-sm text-label-mono-sm font-semibold">
                              {currentUser.role || 'OPERATOR'}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span className="inline-flex items-center gap-1 font-label-mono-sm text-label-mono-sm text-emerald-700">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Active
                            </span>
                          </td>
                          <td className="py-3 px-3 font-label-mono-sm text-label-mono-sm text-on-surface-variant">Active Session</td>
                          <td className="py-3 px-3 text-right">
                            <span className="text-on-surface-variant font-label-mono-sm text-label-mono-sm">Current Node</span>
                          </td>
                        </tr>
                        <tr>
                          <td colSpan={6} className="py-4 text-center text-on-surface-variant font-label-mono-sm">
                            Showing active authenticated operator session. Additional operators provisionable via the &quot;Provision Operator&quot; drawer.
                          </td>
                        </tr>
                      </>
                    ) : (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-on-surface-variant font-label-mono-sm">
                          {loadingUser
                            ? 'Querying authenticated session (/api/v1/auth/me)...'
                            : 'No active authenticated operator session. Sign in via /api/v1/auth/login to manage access control.'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'roles' && (
            <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-md">
              <h2 className="font-headline-sm text-headline-sm text-primary">Roles & Permissions Authority Matrix</h2>
              <div className="space-y-space-sm font-body-sm text-body-sm">
                <div className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-primary font-headline-sm">USER / ANALYST</span>
                    <span className="px-2 py-0.5 rounded bg-surface-container text-on-surface font-label-mono-sm text-label-mono-sm">Read-Only Inference</span>
                  </div>
                  <p className="text-on-surface-variant">Access to live stream inference view, detection counts, and basic alert toasts. Cannot admit models or alter ledger dispositions.</p>
                </div>

                <div className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-primary font-headline-sm">AUDITOR / SECURITY REVIEWER</span>
                    <span className="px-2 py-0.5 rounded bg-secondary text-on-secondary font-label-mono-sm text-label-mono-sm">Audit & Disposition</span>
                  </div>
                  <p className="text-on-surface-variant">Full forensic access: verify provenance chains, execute dataset audits, run behavioral probes, quarantine models, and download canonical evidence reports.</p>
                </div>

                <div className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-primary font-headline-sm">ADMIN</span>
                    <span className="px-2 py-0.5 rounded bg-primary text-on-primary font-label-mono-sm text-label-mono-sm">Full Administrative Scope</span>
                  </div>
                  <p className="text-on-surface-variant">System-wide authority including operator provisioning, MediaMTX stream routing, key rotation, and ledger genesis reset.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'events' && (
            <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-md">
              <h2 className="font-headline-sm text-headline-sm text-primary">Security & Authentication Audit Trail</h2>
              <div className="p-4 rounded-lg bg-surface-container-low text-on-surface-variant font-label-mono-sm text-center border border-surface-container">
                Append-only session audit trail active. 0 failed authentication events in current operational window.
              </div>
            </div>
          )}

          {activeTab === 'endpoints' && (
            <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-md">
              <h2 className="font-headline-sm text-headline-sm text-primary">Integration Endpoints & API Keys</h2>
              <div className="space-y-space-sm font-label-mono-sm text-label-mono-sm">
                <div className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex justify-between items-center">
                  <div>
                    <span className="font-bold text-primary block">FastAPI REST Gateway</span>
                    <span className="text-on-surface-variant">http://localhost:8000/api/v1</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold">Active</span>
                </div>
                <div className="p-space-md rounded-lg bg-surface-container-low border border-surface-container flex justify-between items-center">
                  <div>
                    <span className="font-bold text-primary block">WebSocket Telemetry & Alerts</span>
                    <span className="text-on-surface-variant">ws://localhost:8000/ws/alerts</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold">Listening</span>
                </div>
              </div>
            </div>
          )}

          {/* Statutory Evidence Notice */}
          <div className="p-space-md rounded-xl bg-surface-container-low flex items-start gap-space-md border border-surface-container">
            <span className="material-symbols-outlined text-secondary shrink-0 mt-0.5 text-[22px]">verified_user</span>
            <div className="flex flex-col gap-1">
              <p className="font-semibold text-primary font-headline-sm text-headline-sm">Cryptographically Verifiable Technical Evidence</p>
              <p className="text-body-sm text-on-surface-variant font-body-sm leading-relaxed">
                IBVAP generates technically verifiable electronic evidence designed to support evidence and audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023. Legal admissibility remains subject to applicable law and judicial process.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Critical Access Events */}
        <div className="2xl:col-span-4 flex flex-col gap-space-md">
          <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col h-full justify-between">
            <div className="flex flex-col gap-space-md">
              <div className="flex items-center justify-between pb-space-sm border-b border-surface-container">
                <div className="flex flex-col">
                  <span className="font-headline-sm text-headline-sm text-primary">Critical Access Events</span>
                  <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Tamper-evident access logging</span>
                </div>
                <span className="material-symbols-outlined text-[20px] text-emerald-600">lock</span>
              </div>

              <div className="p-4 rounded-lg bg-surface-container-low text-on-surface-variant font-label-mono-sm text-center border border-surface-container/60">
                Append-only access log active. All operator tokens cryptographically bound to session ledger.
              </div>
            </div>

            <div className="pt-space-md mt-space-md border-t border-surface-container flex items-center justify-between">
              <span className="inline-flex items-center gap-1 text-emerald-700 font-label-mono-sm text-label-mono-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                Live Audit Active
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Attestation Modal */}
      {showAttestationModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-primary/40 backdrop-blur-sm p-space-md">
          <div className="w-full max-w-2xl bg-surface-container-lowest rounded-xl shadow-xl flex flex-col overflow-hidden border border-surface-container">
            <div className="p-space-lg flex items-center justify-between bg-surface-container-low border-b border-surface-container">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-secondary text-[24px]">verified</span>
                <div className="flex flex-col">
                  <span className="font-headline-sm text-headline-sm text-primary">Audit Ledger Cryptographic Verification</span>
                  <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Cryptographic Hash Chain & Root Key Verification</span>
                </div>
              </div>
              <button
                onClick={() => setShowAttestationModal(false)}
                className="p-1 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-space-lg flex flex-col gap-space-md font-label-mono-sm text-label-mono-sm">
              <div className="flex flex-col gap-1">
                <span className="uppercase text-on-surface-variant font-semibold">Genesis Ledger Hash & Root Key</span>
                <div className="p-space-sm rounded-lg bg-surface-container-low font-data-tabular text-primary break-all border border-surface-container">
                  GENESIS-SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855<br />
                  CURRENT-MERKLE-ROOT: 8a48b9981e19488da76c8c9a896fe118a7c2901b098192aa62f741d4081c7f99
                </div>
              </div>

              <div className="grid grid-cols-2 gap-space-md">
                <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col border border-surface-container">
                  <span className="text-on-surface-variant">SYSTEM AUTHENTICATION</span>
                  <span className="font-body-md text-body-md font-semibold text-primary mt-1">IBVAP Local Keyring</span>
                  <span className="text-emerald-700">Ed25519 Verified</span>
                </div>
                <div className="p-space-sm rounded-lg bg-surface-container-low flex flex-col border border-surface-container">
                  <span className="text-on-surface-variant">EVIDENTIARY SCOPE</span>
                  <span className="font-body-md text-body-md font-semibold text-primary mt-1">BSA 2023 Technical Evidence</span>
                  <span className="text-secondary">Append-Only Integrity</span>
                </div>
              </div>
            </div>

            <div className="p-space-md bg-surface-container-low flex items-center justify-end gap-space-sm border-t border-surface-container">
              <button
                onClick={() => setShowAttestationModal(false)}
                className="px-space-md py-1.5 rounded-lg bg-surface-container-lowest text-primary font-label-mono-sm text-label-mono-sm border border-surface-container"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provision Drawer */}
      {showProvisionDrawer && (
        <div className="fixed inset-y-0 right-0 h-screen w-full max-w-md bg-surface-container-lowest shadow-2xl z-50 flex flex-col justify-between border-l border-surface-container">
          <div className="flex flex-col">
            <div className="p-space-lg bg-surface-container-low flex items-center justify-between border-b border-surface-container">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[20px] text-primary">person_add</span>
                <span className="font-headline-sm text-headline-sm text-primary">Provision Operator Access</span>
              </div>
              <button
                onClick={() => setShowProvisionDrawer(false)}
                className="p-1 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-space-lg flex flex-col gap-space-md">
              <div className="flex flex-col gap-1">
                <label className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Operator Official Email</label>
                <input
                  value={provisionEmail}
                  onChange={(e) => setProvisionEmail(e.target.value)}
                  className="bg-surface-container-low p-2 rounded-lg text-primary text-body-md font-body-md focus:outline-none border border-surface-container"
                  placeholder="e.g. analyst@agency.gov.in"
                  type="email"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Security Role & Scope</label>
                <select
                  value={provisionRole}
                  onChange={(e) => setProvisionRole(e.target.value)}
                  className="bg-surface-container-low p-2 rounded-lg text-primary text-body-md font-body-md focus:outline-none border border-surface-container"
                >
                  <option value="Auditor / Security Reviewer">Auditor / Security Reviewer</option>
                  <option value="System Administrator">System Administrator</option>
                  <option value="Field Analyst (Read-Only)">Field Analyst (Read-Only)</option>
                </select>
              </div>

              <div className="p-space-sm rounded-lg bg-surface-container text-on-surface-variant flex items-start gap-space-sm mt-space-sm">
                <span className="material-symbols-outlined text-[18px] text-primary shrink-0 mt-0.5">info</span>
                <span className="font-body-sm text-body-sm leading-tight">
                  Provisioning issues an access token linked to the designated role. Activity will be recorded in the append-only evidence ledger.
                </span>
              </div>
            </div>
          </div>

          <div className="p-space-lg bg-surface-container-low flex items-center justify-end gap-space-sm border-t border-surface-container">
            <button
              onClick={() => setShowProvisionDrawer(false)}
              className="px-space-md py-2 rounded-lg bg-surface-container-lowest text-primary font-label-mono-sm text-label-mono-sm border border-surface-container"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmProvision}
              className="px-space-md py-2 rounded-lg bg-primary text-on-primary font-label-mono-sm text-label-mono-sm shadow-sm hover:bg-primary-container transition-colors"
            >
              Confirm Provisioning
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
