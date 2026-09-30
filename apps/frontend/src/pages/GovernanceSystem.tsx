import React from 'react';

export const GovernanceSystem: React.FC = () => {
  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase tracking-wider">
            <span>Statutory Compliance</span>
            <span>/</span>
            <span className="text-secondary font-medium">Governance & Legal Framework</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Governance System</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Policy definitions, statutory evidentiary alignment, and cryptographic governance architecture ensuring compliance with legal standards.
          </p>
        </div>
      </div>

      {/* Primary Statutory Reference Banner */}
      <div className="p-space-lg bg-surface-container-low rounded-xl border border-surface-container flex items-start gap-space-md">
        <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-secondary text-[28px]">policy</span>
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="font-headline-sm text-headline-sm text-primary">Cryptographically Verifiable Technical Evidence</h2>
          <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
            IBVAP generates technically verifiable electronic evidence designed to support evidence and audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023. Legal admissibility remains subject to applicable law and judicial process.
          </p>
          <div className="flex items-center gap-space-sm text-label-mono-sm text-on-surface-variant mt-1">
            <span>Jurisdiction: Republic of India</span>
            <span>•</span>
            <span>Reference: Section 63 / 65 Electronic Records Provisions</span>
          </div>
        </div>
      </div>

      {/* Governance Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-sm">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-secondary text-[22px]">lock</span>
            <h3 className="font-headline-sm text-headline-sm text-primary">Zero-Trust Architecture</h3>
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
            No machine learning model weight or inference result is assumed trustworthy. Every artifact is verified deterministically against public key signatures and behavioral invariant gates.
          </p>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-primary">
            Policy: Strict Dual-Vector Enforced
          </div>
        </div>

        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-sm">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-secondary text-[22px]">link</span>
            <h3 className="font-headline-sm text-headline-sm text-primary">Append-Only Hash Chain</h3>
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
            Sequential evidence records are linked using cryptographic Merkle roots and SHA-256 state transitions, ensuring any tampering invalidates all subsequent chain hashes.
          </p>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-primary">
            Protocol: Cryptographically Linked Evidence Chain
          </div>
        </div>

        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-space-sm">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-secondary text-[22px]">badge</span>
            <h3 className="font-headline-sm text-headline-sm text-primary">Role-Based Accountability</h3>
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
            Clear role boundaries separate standard operators, technical auditors, and system administrators, recording authenticated actions into the tamper-evident audit ledger.
          </p>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-primary">
            Enforcement: USER, AUDITOR, ADMIN
          </div>
        </div>
      </div>
    </div>
  );
};
