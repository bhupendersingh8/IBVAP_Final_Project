import React from "react";
import { NavLink } from "react-router-dom";

interface NavItem {
  name: string;
  path: string;
  icon: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Core",
    items: [
      { name: "Overview", path: "/overview", icon: "space_dashboard" },
      { name: "Live Inference", path: "/live-inference", icon: "videocam" },
      { name: "Data Integrity", path: "/data-integrity", icon: "fingerprint" },
      { name: "Model Assurance", path: "/model-assurance", icon: "model_training" },
    ],
  },
  {
    title: "Analysis",
    items: [
      { name: "Assurance Analytics", path: "/assurance-analytics", icon: "insights" },
      { name: "Drift Monitor", path: "/drift-monitor", icon: "troubleshoot" },
      { name: "Integrity Test Lab", path: "/integrity-test-lab", icon: "science" },
      { name: "Performance Benchmark", path: "/performance-benchmark", icon: "speed" },
    ],
  },
  {
    title: "Evidence",
    items: [
      { name: "Evidence & Provenance", path: "/evidence-and-provenance", icon: "fact_check" },
      { name: "Verification Console", path: "/verification-console", icon: "terminal" },
      { name: "Evidence Ledger", path: "/evidence-ledger", icon: "receipt_long" },
      { name: "Reports", path: "/reports", icon: "summarize" },
    ],
  },
  {
    title: "Governance & System",
    items: [
      { name: "Governance System", path: "/governance-system", icon: "policy" },
      { name: "Edge Hardware & Runtime", path: "/edge-hardware-and-runtime", icon: "memory" },
    ],
  },
  {
    title: "Admin",
    items: [
      { name: "Access Control", path: "/admin", icon: "admin_panel_settings" },
    ],
  },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="fixed left-0 top-0 h-screen w-72 bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.04)] z-50 flex flex-col justify-between overflow-y-auto">
      <div className="flex flex-col">
        {/* Header / Brand */}
        <div className="p-space-lg flex flex-col gap-space-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <div className="w-7 h-7 rounded-lg overflow-hidden flex items-center justify-center shrink-0">
                <img src="/logo.svg" alt="IBVAP Logo" className="w-full h-full object-contain" />
              </div>
              <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">
                IBVAP
              </span>
            </div>
            <span className="font-label-mono-sm text-label-mono-sm px-space-xs py-0.5 rounded-lg bg-surface-container text-on-surface-variant font-medium">
              v2.6.0-audit
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-body-sm text-body-sm text-on-surface font-medium">
              Vision Assurance Platform
            </span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
              SIH26228 • Team Trinetra
            </span>
          </div>
        </div>

        <div className="h-px bg-surface-container mx-space-lg mb-space-sm" />

        {/* Navigation Sections */}
        <nav className="flex flex-col gap-space-md px-space-md py-space-xs">
          {navSections.map((section) => (
            <div key={section.title} className="flex flex-col gap-1">
              <span className="px-space-sm py-1 font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant tracking-wider font-semibold">
                {section.title}
              </span>
              {section.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-space-sm px-space-sm py-1.5 rounded-lg transition-all ${
                      isActive
                        ? "bg-primary text-on-primary font-medium shadow-sm"
                        : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                    }`
                  }
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {item.icon}
                  </span>
                  <span className="font-body-md text-body-md">
                    {item.name}
                  </span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer Node Info */}
      <div className="p-space-md m-space-md bg-surface-container-low rounded-lg flex flex-col gap-space-xs">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-label-mono-sm font-semibold text-on-surface">
            Backend: Operational
          </span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
          FastAPI Engine • DBUU-Host-01
        </span>
        <div className="h-px bg-surface-container my-1" />
        <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant font-medium">
          SIH 2026 • Team Trinetra
        </span>
      </div>
    </aside>
  );
};
