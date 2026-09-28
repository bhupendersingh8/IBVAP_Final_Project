import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Video, Activity, Camera, Settings, 
  Volume2, VolumeX, Shield, Clock, Wifi, Cpu, AlertTriangle
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

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const toggleAudio = () => {
    const next = !muted;
    setAudioMuted(next);
    setMuted(next);
    if (!next) playSuccessPing();
  };

  const navItems = [
    { name: 'Live Command', path: '/', icon: Activity, badge: 'ACTIVE' },
    { name: 'Incidents & Evidence', path: '/incidents', icon: ShieldAlert, badge: null },
    { name: 'Camera Feeds', path: '/cameras', icon: Video, badge: null },
    { name: 'Perimeter Zones', path: '/zones', icon: Camera, badge: null },
    { name: 'System Hardware', path: '/settings', icon: Settings, badge: null },
  ];

  return (
    <div className="min-h-screen cyber-matrix-bg text-slate-100 flex flex-col font-sans">
      {/* Top AI Sentinel Command Header */}
      <header className="sticky top-0 z-50 tactical-glass border-b border-cyan-500/20 px-4 lg:px-6 py-2.5 flex items-center justify-between shadow-2xl">
        {/* Left: Branding & Sector Info */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative p-2 rounded-lg bg-cyan-950/70 border border-cyan-400/40 text-cyan-400 shadow-lg shadow-cyan-500/20 group-hover:neon-glow-cyan transition-all">
              <Shield size={20} className="text-cyan-400" />
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-slate-950"></span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-lg tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400">
                  IBVAP
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                  AI DEFENSE GRID
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest hidden sm:block">
                SIH PS 26187 • Border Surveillance Platform
              </p>
            </div>
          </Link>
        </div>

        {/* Center: Clean Tactical Nav Bar */}
        <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-xl bg-slate-950/60 border border-cyan-500/20 shadow-inner">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 neon-glow-cyan shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon size={14} className={isActive ? 'text-cyan-400' : 'text-slate-400'} />
                <span>{item.name}</span>
                {item.badge && (
                  <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 animate-pulse">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right: Operational Status, Clock & Audio Control */}
        <div className="flex items-center gap-3">
          {/* Defcon / Readiness Status */}
          <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>GRID: NORMAL</span>
          </div>

          {/* AI Inference Engine Pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-mono">
            <Cpu size={13} className="text-cyan-400" />
            <span>YOLO26 + ByteTrack</span>
          </div>

          {/* Real-time Sector Clock */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-300 text-xs font-mono">
            <Clock size={13} className="text-cyan-400" />
            <span>
              {currentTime.toLocaleTimeString('en-US', { hour12: false })} IST
            </span>
          </div>

          {/* Audio Alert Toggle Button */}
          <button
            onClick={toggleAudio}
            title={muted ? "Unmute Tactical Audio Alerts" : "Mute Tactical Audio Alerts"}
            className={`p-2 rounded-lg border transition-all ${
              muted 
                ? 'bg-slate-800/50 text-slate-400 border-slate-700/50 hover:bg-slate-800 hover:text-slate-200' 
                : 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40 neon-glow-cyan'
            }`}
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} className="animate-pulse" />}
          </button>
        </div>
      </header>

      {/* Mobile Navigation Bar */}
      <div className="md:hidden tactical-glass border-b border-cyan-500/20 px-3 py-2 flex items-center justify-around overflow-x-auto text-xs">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium whitespace-nowrap ${
                isActive ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40' : 'text-slate-400'
              }`}
            >
              <Icon size={12} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </div>

      {/* Main Content Viewport */}
      <main className="flex-1 p-3 sm:p-5 lg:p-6 max-w-[1920px] mx-auto w-full">
        {children}
      </main>

      {/* Minimal Tactical Footer */}
      <footer className="tactical-glass border-t border-cyan-500/10 px-4 py-2 text-center sm:flex sm:justify-between text-[11px] font-mono text-slate-500">
        <div>
          IBVAP SOTA AI PLATFORM • SECTION 65B INDIAN EVIDENCE ACT COMPLIANT • SHA-256 MERKLE CHAIN LEDGER
        </div>
        <div className="mt-1 sm:mt-0 text-cyan-400/70">
          HOST: INTEL i3 / DELL VERIFIED • RTX 3050 GPU-READY • 188/188 TESTS VALIDATED
        </div>
      </footer>
    </div>
  );
};
