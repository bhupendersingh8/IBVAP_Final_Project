import React, { useState } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { useCameras } from '../api/hooks';
import apiClient from '../api/client';
import { format } from 'date-fns';
import { Video, Plus, Settings, Trash2, Camera as CameraIcon, Shield, Radio, CheckCircle } from 'lucide-react';

export const Cameras = () => {
  const queryClient = useQueryClient();
  const { data: cameras, isLoading } = useCameras();
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({ id: '', name: '', rtsp_url: '', scenario: 'daytime' });

  // Add Camera API Call
  const addCameraMutation = useMutation({
    mutationFn: async (newCamera: any) => {
      const { data } = await apiClient.post('/cameras/', newCamera);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      setShowAddModal(false);
      setFormData({ id: '', name: '', rtsp_url: '', scenario: 'daytime' });
    }
  });

  // Delete Camera API Call
  const deleteCameraMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/cameras/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addCameraMutation.mutate(formData);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="glass-panel rounded-2xl p-5 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-xl shadow-lg shadow-blue-950/40">
            <Video size={22} />
          </div>
          <div>
            <h1 className="text-xl font-extrabold dark:text-white text-slate-900 tracking-tight">Camera Grid Operations</h1>
            <p className="dark:text-slate-400 text-slate-500 text-xs mt-0.5 font-medium">Configure surveillance nodes, RTSP feeds, and AI profile pipelines.</p>
          </div>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-950/40 cursor-pointer"
        >
          <Plus size={16} />
          Add Surveillance Camera
        </button>
      </div>

      {/* Cameras Table */}
      <div className="glass-panel rounded-2xl border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
            <thead className="dark:bg-slate-950/70 bg-slate-50 dark:text-slate-400 text-slate-700 font-semibold border-b dark:border-slate-800/80 border-slate-200 uppercase text-[11px] font-mono tracking-wider">
              <tr>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Camera ID</th>
                <th className="px-6 py-4">Name & Outpost</th>
                <th className="px-6 py-4">AI Scenario Profile</th>
                <th className="px-6 py-4">Registered On</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y dark:divide-slate-800/60 divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-slate-400 font-mono text-xs">Loading surveillance grid...</td></tr>
              ) : cameras?.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                    <Video size={36} className="mx-auto text-slate-500 mb-2 opacity-50" />
                    <p className="font-semibold text-sm">No cameras configured yet.</p>
                    <p className="text-xs text-slate-500 mt-1">Click "Add Surveillance Camera" to connect an RTSP or IP stream.</p>
                  </td>
                </tr>
              ) : (
                cameras?.map((cam) => (
                  <tr key={cam.id} className="dark:hover:bg-slate-800/40 hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {cam.enabled ? (
                        <span className="flex items-center gap-2 text-emerald-400 font-bold text-xs font-mono">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>ACTIVE
                        </span>
                      ) : (
                        <span className="flex items-center gap-2 text-slate-500 font-medium text-xs font-mono">
                          <span className="w-2 h-2 rounded-full bg-slate-500"></span>DISABLED
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono font-bold dark:text-cyan-400 text-slate-900">{cam.id}</td>
                    <td className="px-6 py-4 font-semibold dark:text-slate-200 text-slate-800">{cam.name}</td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold uppercase tracking-wider dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/50 border bg-blue-50 text-blue-700">
                        {cam.scenario.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-400">{format(new Date(cam.created_at), 'MMM dd, yyyy')}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-3 text-slate-400">
                        <button onClick={() => deleteCameraMutation.mutate(cam.id)} className="hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-red-500/10 cursor-pointer" title="Delete Camera">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="dark:bg-slate-900/95 bg-white rounded-2xl shadow-2xl border dark:border-slate-700/80 border-slate-200 w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-bold dark:text-white text-slate-900 font-mono">Add Surveillance Stream</h2>
              <span className="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono font-bold">RTSP</span>
            </div>
            <p className="text-xs dark:text-slate-400 text-slate-500 mb-5">Enter camera details. RTSP stream credentials are encrypted and hashed.</p>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold dark:text-slate-300 text-slate-700 mb-1">Camera ID (e.g. CAM-05)</label>
                <input required type="text" value={formData.id} onChange={(e) => setFormData({...formData, id: e.target.value})} className="w-full px-3 py-2 text-xs font-mono dark:bg-slate-950 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold dark:text-slate-300 text-slate-700 mb-1">Friendly Outpost Name</label>
                <input required type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} className="w-full px-3 py-2 text-xs dark:bg-slate-950 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-semibold dark:text-slate-300 text-slate-700 mb-1">RTSP Stream URL</label>
                <input required type="text" value={formData.rtsp_url} onChange={(e) => setFormData({...formData, rtsp_url: e.target.value})} className="w-full px-3 py-2 text-xs font-mono dark:bg-slate-950 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="rtsp://admin:pass@192.168.1.100:554/h264Preview" />
              </div>
              <div>
                <label className="block text-xs font-semibold dark:text-slate-300 text-slate-700 mb-1">AI Detection Profile</label>
                <select value={formData.scenario} onChange={(e) => setFormData({...formData, scenario: e.target.value})} className="w-full px-3 py-2 text-xs dark:bg-slate-950 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="daytime">Daytime General (YOLOv8 + ByteTrack)</option>
                  <option value="night">Night Vision (CLAHE Enhancement)</option>
                  <option value="zone_intrusion">Virtual Fence Perimeter Intrusion</option>
                  <option value="vehicle_anpr">Vehicle ANPR License Plate Reading</option>
                </select>
              </div>
              
              <div className="flex justify-end gap-3 mt-6 pt-3 border-t dark:border-slate-800 border-slate-100">
                <button type="button" onClick={() => setShowAddModal(false)} className="px-4 py-2 text-xs font-semibold dark:text-slate-400 dark:hover:text-white text-slate-600 hover:bg-slate-100 rounded-xl transition cursor-pointer">
                  Cancel
                </button>
                <button type="submit" disabled={addCameraMutation.isPending} className="px-4 py-2 text-xs font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl shadow-md transition cursor-pointer">
                  {addCameraMutation.isPending ? 'Connecting...' : 'Save Camera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

