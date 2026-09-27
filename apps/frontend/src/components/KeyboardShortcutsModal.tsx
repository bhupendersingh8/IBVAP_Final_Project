import React from 'react';
import { X, Keyboard, Command } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: '1', desc: 'Switch active camera to CAM-01 (CCTV Canonical)' },
    { key: '2', desc: 'Switch active camera to WEBCAM-01 (Laptop Webcam)' },
    { key: '3', desc: 'Switch active camera to PHONE-CAM-01 (Mobile WiFi)' },
    { key: '4', desc: 'Switch active camera to CAM-02 (Perimeter East)' },
    { key: 'Space', desc: 'Acknowledge real-time breach banner alert' },
    { key: 'Z', desc: 'Toggle Digital PTZ Zoom (1x → 2x → 3x → Reset)' },
    { key: 'G', desc: 'Toggle Multi-Camera Grid View (2x2 Multi-Stream)' },
    { key: 'M', desc: 'Toggle Audio Siren / Alert Chime (Mute/Unmute)' },
    { key: 'Esc', desc: 'Close open dialogs, modals, and drawers' },
    { key: '?', desc: 'Open this Tactical Keyboard Shortcuts cheat sheet' },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 text-white rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg">
              <Keyboard size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold">Tactical Command Shortcuts</h3>
              <p className="text-[11px] text-slate-400">High-speed operator keyboard controls</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Shortcuts List */}
        <div className="p-4 space-y-2 text-xs">
          {shortcuts.map((sc) => (
            <div
              key={sc.key}
              className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/50 border border-slate-800 hover:border-slate-700 transition"
            >
              <span className="text-slate-300 font-medium">{sc.desc}</span>
              <kbd className="px-2.5 py-1 bg-slate-950 text-emerald-400 border border-slate-700 rounded font-mono font-bold shadow-xs text-xs">
                {sc.key}
              </kbd>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 text-right">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
};
