import React, { useState } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { useCameras } from '../api/hooks';
import apiClient from '../api/client';
import { Video, Plus, Trash2, Shield, Radio, CheckCircle, Wifi, Play, X, Loader2 } from 'lucide-react';
import { playSuccessPing } from '../utils/audioAlerts';

export const Cameras = () => {
  const queryClient = useQueryClient();
  const { data: cameras, isLoading } = useCameras();
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({ id: '', name: '', rtsp_url: '', scenario: 'border_perimeter' });

  const addCameraMutation = useMutation({
    mutationFn: async (newCamera: any) => {
      const { data } = await apiClient.post('/cameras/', newCamera);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      setShowAddModal(false);
      setFormData({ id: '', name: '', rtsp_url: '', scenario: 'border_perimeter' });
      playSuccessPing();
    }
  });

  const deleteCameraMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/cameras/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      playSuccessPing();
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.id.trim()) return;
    addCameraMutation.mutate(formData);
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="tactical-glass p-4 lg:p-5 rounded-2xl border border-cyan-500/20 flex flex-wrap justify-between items-center gap-4 hud-box">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-950/70 border border-cyan-400/40 text-cyan-400 neon-glow-cyan">
            <Video size={22} />
          </div>
          <div>
            <h1 className="text-lg lg:text-xl font-black text-white tracking-wide flex items-center gap-2">
              <span>SURVEILLANCE NODE TOPOLOGY</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                MEDIAMTX BUS
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Active RTSP and WebRTC camera nodes connected to the IBVAP inference engine.
            </p>
          </div>
        </div>

        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-mono font-bold transition-all shadow-lg shadow-cyan-600/30"
        >
          <Plus size={14} />
          <span>Add Camera Node</span>
        </button>
      </div>

      {/* Camera Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-full text-center py-12 text-slate-500 font-mono text-xs">
            Scanning camera topology...
          </div>
        ) : !cameras || cameras.length === 0 ? (
          <div className="col-span-full tactical-glass p-8 text-center rounded-2xl border border-slate-800 text-slate-500 font-mono text-xs">
            No camera nodes registered. Click "Add Camera Node" to register an RTSP feed.
          </div>
        ) : (
          cameras.map((cam) => (
            <div key={cam.id} className="tactical-glass p-4 rounded-xl border border-cyan-500/20 space-y-3 hud-box hover:border-cyan-400/40 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span className="font-mono font-bold text-sm text-white">{cam.name || cam.id}</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                  ONLINE
                </span>
              </div>

              {/* Stream Preview Snapshot or Icon */}
              <div className="relative aspect-video rounded-lg overflow-hidden bg-black/80 border border-slate-800 flex items-center justify-center">
                <iframe
                  src={`http://127.0.0.1:8889/${cam.id}`}
                  title={cam.id}
                  className="w-full h-full border-0 pointer-events-none"
                />
                <div className="absolute bottom-2 left-2 text-[10px] font-mono bg-black/70 px-2 py-0.5 rounded text-cyan-300 border border-cyan-500/30">
                  {cam.id}
                </div>
              </div>

              <div className="text-[11px] font-mono text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Scenario:</span>
                  <span className="text-slate-200">{cam.scenario}</span>
                </div>
                <div className="flex justify-between">
                  <span>Inference:</span>
                  <span className="text-cyan-300">YOLO26 + ByteTrack</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                <a
                  href={`http://127.0.0.1:8889/${cam.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                >
                  <Play size={11} />
                  <span>Open Feed</span>
                </a>
                <button
                  onClick={() => deleteCameraMutation.mutate(cam.id)}
                  className="p-1.5 rounded text-slate-500 hover:text-rose-400 transition-colors"
                  title="Remove Camera"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="tactical-glass max-w-md w-full p-5 rounded-2xl border border-cyan-500/40 shadow-2xl space-y-4 hud-box">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
              <div className="flex items-center gap-2">
                <Video className="text-cyan-400" size={18} />
                <h3 className="font-bold text-sm text-white">Add Surveillance Node</h3>
              </div>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-slate-400">Camera ID (e.g. CAM-03):</label>
                <input
                  type="text"
                  required
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toUpperCase() })}
                  placeholder="CAM-03"
                  className="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400">Node Name:</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="North Watchtower PTZ"
                  className="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono text-slate-400">RTSP Stream URL:</label>
                <input
                  type="text"
                  value={formData.rtsp_url}
                  onChange={(e) => setFormData({ ...formData, rtsp_url: e.target.value })}
                  placeholder="rtsp://127.0.0.1:8554/CAM-03"
                  className="w-full mt-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addCameraMutation.isPending}
                  className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 shadow-lg shadow-cyan-600/30"
                >
                  {addCameraMutation.isPending && <Loader2 size={13} className="animate-spin" />}
                  <span>Register Node</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
