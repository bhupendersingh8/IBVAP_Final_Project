import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, Video, AlertCircle, ShieldCheck, 
  Car, MapPin, FileBarChart, Server, Sliders,
  Volume2, VolumeX, Menu, X, LogOut, User, Clock
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { isAudioMuted, setAudioMuted, playSuccessPing } from '../../utils/audioAlerts';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const [muted, setMuted] = useState(isAudioMuted());
  const [currentTime, setCurrentTime] = useState(new Date());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const toggleAudio = () => {
    const next = !muted;
    setAudioMuted(next);
    setMuted(next);
    if (!next) playSuccessPing();
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Live Cameras', path: '/cameras', icon: Video },
    { name: 'Incidents', path: '/incidents', icon: AlertCircle },
    { name: 'Evidence', path: '/evidence', icon: ShieldCheck },
    { name: 'ANPR', path: '/anpr', icon: Car },
    { name: 'Zones', path: '/zones', icon: MapPin },
    { name: 'Reports', path: '/reports', icon: FileBarChart },
    { name: 'System', path: '/system', icon: Server },
    { name: 'Settings', path: '/settings', icon: Sliders },
  ];

  // Route title mapper
  const getPageTitle = (path: string) => {
    switch (path) {
      case '/': return 'Operational Dashboard';
      case '/cameras': return 'Live CCTV Surveillance';
      case '/incidents': return 'Incident Management';
      case '/evidence': return 'Evidence Ledger';
      case '/anpr': return 'Automated Number Plate Recognition';
      case '/zones': return 'Perimeter Zone Configuration';
      case '/reports': return 'Operational Reports & Audits';
      case '/system': return 'System Health & Hardware';
      case '/settings': return 'Platform Settings';
      default: return 'Border Video Analytics Platform';
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] text-slate-100 flex flex-col font-sans">
      <div className="flex flex-1 min-h-screen">
        
        {/* ======================================================== */}
        {/* LEFT SIDEBAR (Desktop & Collapsible Mobile Drawer)      */}
        {/* ======================================================== */}
        <aside 
          className={`
            fixed inset-y-0 left-0 z-50 w-64 bg-[#0f172a] border-r border-[#1e293b] flex flex-col justify-between transition-transform duration-200 ease-in-out
            lg:translate-x-0 lg:static lg:z-auto
            ${mobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'}
          `}
        >
          {/* Top: Logo & System Identity */}
          <div className="flex flex-col">
            <div className="h-16 px-5 border-b border-[#1e293b] flex items-center justify-between">
              <Link to="/" className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center font-bold text-white tracking-wider text-sm shadow">
                  IB
                </div>
                <div>
                  <div className="font-bold text-sm tracking-wide text-white flex items-center gap-1.5">
                    IBVAP <span className="text-[10px] font-normal px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">VMS</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Border Surveillance System</div>
                </div>
              </Link>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="lg:hidden text-slate-400 hover:text-white p-1"
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </div>

            {/* Navigation Links */}
            <nav className="p-3 space-y-1 overflow-y-auto">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white font-semibold shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon size={16} className={isActive ? 'text-white' : 'text-slate-400'} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Bottom: User Profile & Session Controls */}
          <div className="p-3 border-t border-[#1e293b] bg-[#0b1120]/50 space-y-2">
            <div className="flex items-center gap-2.5 px-2 py-1.5">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-200">
                <User size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-slate-200 truncate">Operator 1</div>
                <div className="text-[11px] text-slate-400 truncate">Security Supervisor</div>
              </div>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem('ibvap_token');
                localStorage.removeItem('access_token');
                window.location.reload();
              }}
              className="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded text-xs text-slate-400 hover:text-red-300 hover:bg-red-950/30 border border-transparent hover:border-red-900/40 transition"
              title="End session"
            >
              <LogOut size={13} />
              <span>Logout</span>
            </button>
          </div>
        </aside>

        {/* Mobile backdrop */}
        {mobileMenuOpen && (
          <div 
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 z-40 bg-black/60 lg:hidden backdrop-blur-sm"
          />
        )}

        {/* ======================================================== */}
        {/* MAIN APPLICATION VIEWPORT                               */}
        {/* ======================================================== */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          
          {/* TOP BAR */}
          <header className="h-14 bg-[#0f172a] border-b border-[#1e293b] px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
            {/* Left: Mobile Toggle & Page Title */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="lg:hidden text-slate-400 hover:text-white p-1"
                aria-label="Open navigation menu"
              >
                <Menu size={20} />
              </button>
              <div>
                <h1 className="text-sm lg:text-base font-semibold text-white">
                  {getPageTitle(location.pathname)}
                </h1>
              </div>
            </div>

            {/* Right: Site Selector, Status, Clock & Audio */}
            <div className="flex items-center gap-3 sm:gap-4 text-xs">
              {/* Site / Zone Indicator */}
              <div className="hidden md:flex items-center gap-1.5 text-slate-300 bg-slate-800/80 px-2.5 py-1 rounded border border-slate-700/80">
                <span className="text-slate-400">Site:</span>
                <span className="font-medium text-slate-200">North Sector — Outpost 4</span>
              </div>

              {/* Status Indicator */}
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/40 border border-emerald-800/60 text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium hidden sm:inline">System Operational</span>
                <span className="font-medium sm:hidden">Online</span>
              </div>

              {/* Real-time Clock */}
              <div className="hidden sm:flex items-center gap-1 text-slate-300 font-mono">
                <Clock size={13} className="text-slate-400" />
                <span>{currentTime.toLocaleTimeString('en-US', { hour12: false })} IST</span>
              </div>

              {/* Audio Alarm Toggle */}
              <button
                onClick={toggleAudio}
                title={muted ? "Unmute alert tones" : "Mute alert tones"}
                className={`p-1.5 rounded border transition-colors ${
                  muted
                    ? 'bg-slate-800 border-slate-700 text-slate-500 hover:text-slate-300'
                    : 'bg-blue-950/60 border-blue-800/60 text-blue-400 hover:bg-blue-900/60'
                }`}
                aria-label={muted ? "Unmute alert tones" : "Mute alert tones"}
              >
                {muted ? <VolumeX size={15} /> : <Volume2 size={15} />}
              </button>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto p-4 lg:p-6 bg-[#0b1120]">
            {children}
          </main>
        </div>

      </div>
    </div>
  );
};
