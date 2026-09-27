import React, { useState, useEffect } from 'react';
import { 
  Camera, AlertTriangle, Settings, Activity, ShieldAlert, 
  Video, Volume2, VolumeX, Keyboard, Radio, Palette, 
  Clock, Maximize, Minimize, Sparkles
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { KeyboardShortcutsModal } from '../KeyboardShortcutsModal';
import { isAudioMuted, setAudioMuted, playSuccessPing } from '../../utils/audioAlerts';

export type ThemePreset = 'theme-cyber-aurora' | 'theme-ocean-cobalt' | 'theme-emerald-defense' | 'theme-sunset-recon' | 'theme-radiant-light';

const THEME_PRESETS: { id: ThemePreset; name: string; isDark: boolean; colors: string; desc: string }[] = [
  { id: 'theme-cyber-aurora', name: 'Cyber Aurora', isDark: true, colors: 'from-cyan-400 via-indigo-500 to-emerald-400', desc: 'Obsidian navy with vibrant cyan & violet glows' },
  { id: 'theme-ocean-cobalt', name: 'Ocean Cobalt', isDark: true, colors: 'from-blue-500 via-sky-400 to-indigo-600', desc: 'Deep sapphire with electric azure lighting' },
  { id: 'theme-emerald-defense', name: 'Emerald Defense', isDark: true, colors: 'from-emerald-400 via-teal-500 to-green-600', desc: 'Military radar dark slate with neon emerald glow' },
  { id: 'theme-sunset-recon', name: 'Sunset Recon', isDark: true, colors: 'from-rose-500 via-amber-400 to-purple-600', desc: 'Tactical twilight with crimson & amber alert tones' },
  { id: 'theme-radiant-light', name: 'Radiant Light', isDark: false, colors: 'from-indigo-400 via-sky-300 to-pink-300', desc: 'Modern crisp canvas with pastel ambient mesh' },
];

const Sidebar: React.FC<{ activeTheme: ThemePreset }> = ({ activeTheme }) => {
  const location = useLocation();
  const isDark = activeTheme !== 'theme-radiant-light';
  
  const menuItems = [
    { name: 'Dashboard', path: '/', icon: Activity, badge: 'LIVE' },
    { name: 'Incidents', path: '/incidents', icon: ShieldAlert, badge: null },
    { name: 'Cameras', path: '/cameras', icon: Video, badge: null },
    { name: 'Zones', path: '/zones', icon: Camera, badge: null },
    { name: 'Settings', path: '/settings', icon: Settings, badge: null },
  ];

  return (
    <div className={`w-64 h-screen flex flex-col fixed left-0 top-0 z-50 select-none transition-all duration-300 ${
      isDark 
        ? 'bg-slate-950/85 backdrop-blur-2xl text-slate-300 border-r border-slate-800/80 shadow-2xl' 
        : 'bg-white/90 backdrop-blur-2xl text-slate-700 border-r border-slate-200 shadow-xl'
    }`}>
      {/* Brand Header */}
      <div className={`p-5 border-b flex items-center gap-3 transition-colors ${
        isDark ? 'border-slate-800/80' : 'border-slate-200'
      }`}>
        <div className="relative">
          <div className="p-2.5 bg-gradient-to-br from-red-600 to-rose-700 text-white rounded-xl shadow-lg shadow-red-600/30 ring-1 ring-white/20">
            <ShieldAlert size={22} className="animate-pulse" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-950 animate-ping"></div>
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-950"></div>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className={`font-black text-xl tracking-wider ${isDark ? 'text-white' : 'text-slate-900'}`}>
              IBVAP
            </span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
              AI
            </span>
          </div>
          <p className="text-[10px] font-mono tracking-widest text-slate-400 uppercase font-semibold">
            Border Defense Grid
          </p>
        </div>
      </div>
      
      {/* Navigation List */}
      <nav className="flex-1 py-4 px-3 overflow-y-auto">
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-3 mb-2 font-bold">
          Surveillance Ops
        </div>
        <ul className="space-y-1.5">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <li key={item.name}>
                <Link 
                  to={item.path} 
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl transition-all duration-200 group ${
                    isActive 
                      ? isDark
                        ? 'bg-gradient-to-r from-blue-600/20 to-indigo-600/20 text-white font-semibold border border-blue-500/40 shadow-lg shadow-blue-500/10' 
                        : 'bg-blue-50 text-blue-800 font-semibold border border-blue-200 shadow-sm'
                      : isDark
                        ? 'text-slate-400 hover:text-white hover:bg-slate-900/60 border border-transparent'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <item.icon size={18} className={`transition-transform group-hover:scale-110 ${
                      isActive ? (isDark ? 'text-cyan-400' : 'text-blue-600') : 'text-slate-400'
                    }`} />
                    <span className="text-xs font-semibold tracking-wide">{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className={`text-[9px] font-mono font-extrabold px-1.5 py-0.5 rounded-full ${
                      item.badge === 'LIVE' 
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse' 
                        : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Quick Hotkeys Legend */}
        <div className={`mt-6 p-3 rounded-xl border text-[11px] font-mono ${
          isDark ? 'bg-slate-900/40 border-slate-800/80 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1">
              <Keyboard size={12} /> Hotkeys
            </span>
            <span className="text-[9px] bg-slate-800 text-slate-400 px-1 rounded">PRO</span>
          </div>
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between"><span>[1] Phone Cam</span> <span className="text-cyan-400">Select</span></div>
            <div className="flex justify-between"><span>[2] Webcam</span> <span className="text-cyan-400">Select</span></div>
            <div className="flex justify-between"><span>[3] CAM-02</span> <span className="text-cyan-400">Select</span></div>
            <div className="flex justify-between"><span>[M] Mute Audio</span> <span className="text-amber-400">Toggle</span></div>
            <div className="flex justify-between"><span>[?] Shortcuts</span> <span className="text-purple-400">Modal</span></div>
          </div>
        </div>
      </nav>
      
      {/* System Status Footer */}
      <div className={`p-4 border-t text-xs ${isDark ? 'border-slate-800/80' : 'border-slate-200'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </div>
            <span className={`text-[11px] font-bold ${isDark ? 'text-slate-300' : 'text-slate-800'}`}>
              Defense Core v2.4
            </span>
          </div>
          <span className={`text-[9px] px-2 py-0.5 rounded font-mono font-bold ${
            isDark ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40' : 'bg-emerald-100 text-emerald-800'
          }`}>
            ONLINE
          </span>
        </div>
      </div>
    </div>
  );
};

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [muted, setMuted] = useState(isAudioMuted());
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState({ utc: '', ist: '' });
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Active theme atmosphere state initialized from localStorage
  const [activeTheme, setActiveTheme] = useState<ThemePreset>(() => {
    const saved = localStorage.getItem('ibvap_theme') as ThemePreset;
    return saved && THEME_PRESETS.some(t => t.id === saved) ? saved : 'theme-cyber-aurora';
  });

  const currentThemeObj = THEME_PRESETS.find(t => t.id === activeTheme) || THEME_PRESETS[0];
  const isDark = currentThemeObj.isDark;

  // Apply theme class and dark mode class to document element
  useEffect(() => {
    const root = document.documentElement;
    THEME_PRESETS.forEach(t => root.classList.remove(t.id));
    root.classList.add(activeTheme);
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('ibvap_theme', activeTheme);
    window.dispatchEvent(new CustomEvent('ibvap:theme_changed', { detail: activeTheme }));
  }, [activeTheme, isDark]);

  // Real-time Tactical Defense Clock (UTC & IST)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const utc = now.toUTCString().slice(17, 25) + ' UTC';
      const ist = now.toLocaleTimeString('en-IN', { hour12: false, timeZone: 'Asia/Kolkata' }) + ' IST';
      setCurrentTime({ utc, ist });
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleSound = () => {
    const next = !muted;
    setMuted(next);
    setAudioMuted(next);
    if (!next) playSuccessPing();
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Global Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }

      if (e.key === '?') {
        e.preventDefault();
        setShortcutsOpen((prev) => !prev);
      } else if (e.key === 'm' || e.key === 'M') {
        toggleSound();
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen();
      } else if (e.key === '1') {
        localStorage.setItem('ibvap_selected_camera', 'CAM-01');
        window.dispatchEvent(new CustomEvent('ibvap:switch_camera', { detail: 'CAM-01' }));
        playSuccessPing();
      } else if (e.key === '2') {
        localStorage.setItem('ibvap_selected_camera', 'WEBCAM-01');
        window.dispatchEvent(new CustomEvent('ibvap:switch_camera', { detail: 'WEBCAM-01' }));
        playSuccessPing();
      } else if (e.key === '3') {
        localStorage.setItem('ibvap_selected_camera', 'PHONE-CAM-01');
        window.dispatchEvent(new CustomEvent('ibvap:switch_camera', { detail: 'PHONE-CAM-01' }));
        playSuccessPing();
      } else if (e.key === '4') {
        localStorage.setItem('ibvap_selected_camera', 'CAM-02');
        window.dispatchEvent(new CustomEvent('ibvap:switch_camera', { detail: 'CAM-02' }));
        playSuccessPing();
      } else if (e.key === 'Escape') {
        setShortcutsOpen(false);
        setThemeDropdownOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [muted]);

  return (
    <div className={`min-h-screen flex relative overflow-x-hidden ${activeTheme}`}>
      {/* Dynamic Colorful Ambient Lighting Orbs (Non-interactive) */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="cyber-glow-1 absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full blur-3xl opacity-70 animate-pulse-slow"></div>
        <div className="cyber-glow-2 absolute top-1/4 -right-40 w-[650px] h-[650px] rounded-full blur-3xl opacity-60 animate-pulse-slow"></div>
        <div className="cyber-glow-3 absolute -bottom-40 left-1/3 w-[700px] h-[700px] rounded-full blur-3xl opacity-50"></div>
        <div className="absolute inset-0 cyber-grid opacity-60"></div>
      </div>

      <Sidebar activeTheme={activeTheme} />

      <div className="flex-1 ml-64 flex flex-col min-w-0 relative z-10">
        {/* Top Tactical Command Bar */}
        <header className={`px-6 py-2.5 flex items-center justify-between sticky top-0 z-40 transition-colors backdrop-blur-xl border-b ${
          isDark 
            ? 'bg-slate-950/70 border-slate-800/80 text-white shadow-xl' 
            : 'bg-white/80 border-slate-200/90 text-slate-800 shadow-md shadow-slate-200/30'
        }`}>
          {/* Left Grid Status & Defense Clock */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Radio size={13} className="text-emerald-400 animate-pulse" />
                Perimeter Defense Grid Active
              </span>
            </div>

            {/* Defense Clock */}
            <div className={`hidden md:flex items-center gap-2 px-3 py-1 rounded-lg border text-[11px] font-mono ${
              isDark ? 'bg-slate-900/60 border-slate-800 text-slate-300' : 'bg-slate-100 border-slate-300 text-slate-700'
            }`}>
              <Clock size={12} className="text-cyan-400" />
              <span>{currentTime.ist || '21:45:00 IST'}</span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-400">{currentTime.utc || '16:15:00 UTC'}</span>
            </div>
          </div>

          {/* Right Action Controls: Atmosphere Switcher, Sound, Fullscreen, Shortcuts */}
          <div className="flex items-center gap-2.5">
            {/* Background Atmosphere & Color Switcher */}
            <div className="relative">
              <button
                onClick={() => setThemeDropdownOpen(!themeDropdownOpen)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border cursor-pointer ${
                  isDark 
                    ? 'bg-slate-900/80 text-slate-200 border-slate-700 hover:border-cyan-500/60 hover:text-white shadow-md' 
                    : 'bg-white text-slate-700 border-slate-300 hover:border-blue-400 shadow-xs'
                }`}
                title="Change Background Atmosphere & Colors"
              >
                <div className={`w-3.5 h-3.5 rounded-full bg-gradient-to-tr ${currentThemeObj.colors} ring-1 ring-white/50 shadow-sm animate-pulse`}></div>
                <span className="hidden sm:inline font-medium">{currentThemeObj.name}</span>
                <Palette size={13} className="text-cyan-400" />
              </button>

              {/* Theme Dropdown Menu */}
              {themeDropdownOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setThemeDropdownOpen(false)} 
                  />
                  <div className={`absolute right-0 mt-2 w-64 rounded-xl border p-2 shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-150 ${
                    isDark 
                      ? 'bg-slate-900/95 backdrop-blur-2xl border-slate-700 text-white shadow-cyan-950/40' 
                      : 'bg-white/95 backdrop-blur-2xl border-slate-200 text-slate-800 shadow-xl'
                  }`}>
                    <div className="px-2 py-1.5 border-b border-slate-800/50 mb-1 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                      <span className="flex items-center gap-1.5"><Sparkles size={12} className="text-cyan-400" /> Background Atmosphere</span>
                      <span className="text-[9px] bg-cyan-950 text-cyan-400 px-1.5 py-0.5 rounded">Colors</span>
                    </div>
                    <div className="space-y-1">
                      {THEME_PRESETS.map((preset) => (
                        <button
                          key={preset.id}
                          onClick={() => {
                            setActiveTheme(preset.id);
                            setThemeDropdownOpen(false);
                            playSuccessPing();
                          }}
                          className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center gap-2.5 transition-all cursor-pointer ${
                            activeTheme === preset.id 
                              ? isDark 
                                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40' 
                                : 'bg-blue-50 text-blue-800 font-bold border border-blue-200'
                              : isDark 
                                ? 'hover:bg-slate-800/80 text-slate-300' 
                                : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <div className={`w-4 h-4 rounded-full bg-gradient-to-tr ${preset.colors} shadow-sm shrink-0 ring-1 ring-white/30`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-[11px] truncate">{preset.name}</span>
                              {activeTheme === preset.id && (
                                <span className="text-[9px] text-cyan-400 font-mono">ACTIVE</span>
                              )}
                            </div>
                            <p className="text-[9px] text-slate-400 truncate">{preset.desc}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Audio Siren Mute/Unmute Toggle */}
            <button
              onClick={toggleSound}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition border cursor-pointer ${
                muted 
                  ? isDark 
                    ? 'bg-slate-900/70 text-slate-400 border-slate-800 hover:bg-slate-800' 
                    : 'bg-slate-100 text-slate-500 border-slate-300 hover:bg-slate-200'
                  : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 hover:bg-emerald-500/30'
              }`}
              title={muted ? 'Alarm Audio Muted (Click to Unmute Siren)' : 'Alarm Siren Active (Click to Mute)'}
            >
              {muted ? <VolumeX size={14} /> : <Volume2 size={14} className="text-emerald-400 animate-pulse" />}
              <span className="hidden sm:inline">{muted ? 'Muted' : 'Siren Active'}</span>
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={toggleFullscreen}
              className={`p-1.5 rounded-lg transition border cursor-pointer ${
                isDark 
                  ? 'bg-slate-900/70 text-slate-300 border-slate-800 hover:text-white hover:bg-slate-800' 
                  : 'bg-white text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title={isFullscreen ? 'Exit Fullscreen (F)' : 'Enter Fullscreen (F)'}
            >
              {isFullscreen ? <Minimize size={15} /> : <Maximize size={15} />}
            </button>

            {/* Keyboard Shortcuts Button */}
            <button
              onClick={() => setShortcutsOpen(true)}
              className={`p-1.5 rounded-lg transition border cursor-pointer ${
                isDark 
                  ? 'bg-slate-900/70 text-slate-300 border-slate-800 hover:text-white hover:bg-slate-800' 
                  : 'bg-white text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Tactical Keyboard Shortcuts (?)"
            >
              <Keyboard size={15} />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6 md:p-8 overflow-auto w-full flex-1">
          {children}
        </main>
      </div>

      <KeyboardShortcutsModal
        isOpen={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  );
};

