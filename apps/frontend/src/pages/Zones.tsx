import React, { useState, useEffect, useRef } from 'react';
import { 
  CheckCircle, Layers, Plus, Trash2, Edit3, Move, 
  Eye, Save, RotateCcw, AlertTriangle, Shield, Crosshair, 
  Sparkles, Check, Info, MousePointer, ShieldAlert
} from 'lucide-react';
import { useZones, useSaveZones, useDeleteZone } from '../api/hooks';
import { Zone, ZonePoint } from '../types';
import { playSuccessPing, playWarningChime } from '../utils/audioAlerts';

// Standard Ray-Casting algorithm for point-in-polygon test
const isPointInPolygon = (point: ZonePoint, polygon: ZonePoint[]): boolean => {
  if (polygon.length < 3) return false;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x, yi = polygon[i].y;
    const xj = polygon[j].x, yj = polygon[j].y;
    const intersect = ((yi > point.y) !== (yj > point.y))
        && (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
};

export const Zones: React.FC = () => {
  const { data: zonesData, isLoading } = useZones();
  const { mutate: saveZonesMutation, isPending: isSaving } = useSaveZones();
  const { mutate: deleteZoneMutation } = useDeleteZone();

  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('PHONE-CAM-01');

  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [newPoints, setNewPoints] = useState<ZonePoint[]>([]);
  const [cursorPos, setCursorPos] = useState<ZonePoint | null>(null);

  // Dragging vertex state
  const [draggingVertex, setDraggingVertex] = useState<{ zoneId: string; pointIdx: number } | null>(null);

  // Interactive Simulation state
  const [simulationActive, setSimulationActive] = useState(false);
  const [simTargetPos, setSimTargetPos] = useState<ZonePoint | null>(null);
  const [simulatedBreachedZone, setSimulatedBreachedZone] = useState<Zone | null>(null);

  // Feedback notifications
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (zonesData) {
      setZones(zonesData);
      if (zonesData.length > 0 && !selectedZoneId) {
        setSelectedZoneId(zonesData[0].zone_id);
      }
    }
  }, [zonesData]);

  const selectedZone = zones.find((z) => z.zone_id === selectedZoneId) || null;

  // Converts client mouse event into normalized [0.0, 1.0] coordinates relative to SVG
  const getNormalizedCoordinates = (e: React.MouseEvent<SVGSVGElement>): ZonePoint => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    return { x: Number(x.toFixed(3)), y: Number(y.toFixed(3)) };
  };

  const handleCanvasClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDrawing) return;
    const pt = getNormalizedCoordinates(e);
    
    // If clicking close to the first point with at least 3 points, close the polygon
    if (newPoints.length >= 3) {
      const first = newPoints[0];
      const dist = Math.hypot(pt.x - first.x, pt.y - first.y);
      if (dist < 0.04) {
        finishDrawing();
        return;
      }
    }

    setNewPoints((prev) => [...prev, pt]);
    playSuccessPing();
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const pt = getNormalizedCoordinates(e);
    setCursorPos(pt);

    // Handle vertex drag
    if (draggingVertex) {
      setZones((prev) =>
        prev.map((z) => {
          if (z.zone_id !== draggingVertex.zoneId) return z;
          const updated = [...z.points];
          updated[draggingVertex.pointIdx] = pt;
          return { ...z, points: updated };
        })
      );
    }

    // Handle intruder simulation
    if (simulationActive) {
      setSimTargetPos(pt);
      const breached = zones.find((z) => {
        if (!z.enabled) return false;
        if (z.camera_id && z.camera_id !== selectedCameraId) return false;
        return isPointInPolygon(pt, z.points);
      });

      if (breached && (!simulatedBreachedZone || simulatedBreachedZone.zone_id !== breached.zone_id)) {
        playWarningChime();
      }
      setSimulatedBreachedZone(breached || null);
    }
  };

  const handleMouseUp = () => {
    if (draggingVertex) {
      setDraggingVertex(null);
      setStatusNotice('Vertex moved. Remember to save changes.');
    }
  };

  const startDrawing = () => {
    setIsDrawing(true);
    setSimulationActive(false);
    setNewPoints([]);
  };

  const cancelDrawing = () => {
    setIsDrawing(false);
    setNewPoints([]);
  };

  const finishDrawing = () => {
    if (newPoints.length < 3) {
      alert('A polygon zone requires at least 3 points.');
      return;
    }

    const newZoneId = `ZONE_${Date.now().toString().slice(-5)}`;
    const newZone: Zone = {
      zone_id: newZoneId,
      name: `Sector ${zones.length + 1}`,
      camera_id: selectedCameraId,
      zone_type: 'RESTRICTED_ZONE',
      enabled: true,
      color: '#EF4444',
      points: newPoints,
    };

    const updated = [...zones, newZone];
    setZones(updated);
    setSelectedZoneId(newZoneId);
    setIsDrawing(false);
    setNewPoints([]);
    playSuccessPing();
    setStatusNotice(`Created ${newZone.name}! Click "Save Zones to Backend" to apply.`);
  };

  const handleSaveToBackend = () => {
    saveZonesMutation(zones, {
      onSuccess: () => {
        playSuccessPing();
        setStatusNotice('✅ All spatial virtual zones saved successfully to disk (configs/zones.yaml)!');
        setTimeout(() => setStatusNotice(null), 4000);
      },
      onError: (err: any) => {
        alert(`Failed to save zones: ${err.message}`);
      }
    });
  };

  const handleDeleteZone = (zoneId: string) => {
    if (!confirm('Are you sure you want to delete this virtual fence zone?')) return;
    const remaining = zones.filter((z) => z.zone_id !== zoneId);
    setZones(remaining);
    deleteZoneMutation(zoneId);
    if (selectedZoneId === zoneId) {
      setSelectedZoneId(remaining.length > 0 ? remaining[0].zone_id : null);
    }
    playSuccessPing();
    setStatusNotice('Zone deleted.');
  };

  const handleApplyPreset = (presetType: 'perimeter' | 'checkpoint' | 'quad') => {
    let pts: ZonePoint[] = [];
    let name = 'Perimeter Fence';
    if (presetType === 'perimeter') {
      name = 'Perimeter Border Tripwire';
      pts = [
        { x: 0.1, y: 0.7 },
        { x: 0.9, y: 0.7 },
        { x: 0.9, y: 0.9 },
        { x: 0.1, y: 0.9 },
      ];
    } else if (presetType === 'checkpoint') {
      name = 'Vehicle Gate Checkpoint';
      pts = [
        { x: 0.35, y: 0.3 },
        { x: 0.65, y: 0.3 },
        { x: 0.65, y: 0.8 },
        { x: 0.35, y: 0.8 },
      ];
    } else {
      name = 'Restricted Sector Alpha';
      pts = [
        { x: 0.2, y: 0.2 },
        { x: 0.8, y: 0.2 },
        { x: 0.8, y: 0.8 },
        { x: 0.2, y: 0.8 },
      ];
    }

    const newZoneId = `ZONE_${Date.now().toString().slice(-5)}`;
    const newZone: Zone = {
      zone_id: newZoneId,
      name,
      camera_id: selectedCameraId,
      zone_type: 'RESTRICTED_ZONE',
      enabled: true,
      color: '#EF4444',
      points: pts,
    };

    setZones((prev) => [...prev, newZone]);
    setSelectedZoneId(newZoneId);
    playSuccessPing();
    setStatusNotice(`Added preset template: ${name}!`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none" onMouseUp={handleMouseUp}>
      {/* Header */}
      <div className="glass-panel rounded-2xl p-5 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-xl shadow-lg shadow-blue-950/40">
            <Layers size={22} />
          </div>
          <div>
            <h1 className="text-xl font-extrabold dark:text-white text-slate-900 tracking-tight">Virtual Defense Fences & Geo-Spatial Studio</h1>
            <p className="dark:text-slate-400 text-slate-500 text-xs mt-0.5 font-medium">
              Draw custom multi-point polygonal tripwires, drag vertices, and simulate ray-casting intruder detection.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleSaveToBackend}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-950/40 cursor-pointer"
          >
            <Save size={14} />
            {isSaving ? 'Saving to Core...' : 'Save Fences to System'}
          </button>
        </div>
      </div>

      {statusNotice && (
        <div className="p-3 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-xl flex items-center justify-between text-xs font-medium animate-in fade-in">
          <span>{statusNotice}</span>
          <button onClick={() => setStatusNotice(null)} className="text-slate-400 hover:text-white font-bold ml-2 cursor-pointer">✕</button>
        </div>
      )}

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Interactive Canvas */}
        <div className="lg:col-span-2 glass-panel rounded-2xl border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl p-4 space-y-3">
          {/* Controls Bar */}
          <div className="flex flex-wrap justify-between items-center gap-2 border-b dark:border-slate-800/80 border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold dark:text-slate-300 text-slate-700">Outpost Camera:</span>
              <select
                value={selectedCameraId}
                onChange={(e) => setSelectedCameraId(e.target.value)}
                className="text-xs font-mono font-semibold dark:bg-slate-950 dark:border-slate-700 dark:text-white bg-slate-100 border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="PHONE-CAM-01">PHONE-CAM-01 (Mobile WiFi)</option>
                <option value="WEBCAM-01">WEBCAM-01 (Laptop Webcam)</option>
                <option value="CAM-02">CAM-02 (Perimeter East)</option>
              </select>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {!isDrawing ? (
                <>
                  <button
                    onClick={startDrawing}
                    className="px-3 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition shadow-md shadow-blue-950/30 cursor-pointer"
                  >
                    <Plus size={14} /> Draw Polygon
                  </button>
                  <button
                    onClick={() => {
                      setSimulationActive(!simulationActive);
                      if (!simulationActive) playSuccessPing();
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition shadow-xs cursor-pointer ${
                      simulationActive
                        ? 'bg-amber-600 text-white animate-pulse'
                        : 'dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    <Crosshair size={14} />
                    {simulationActive ? '🎯 Intruder Test: ACTIVE' : '🎯 Simulate Intrusion'}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={finishDrawing}
                    disabled={newPoints.length < 3}
                    className="px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition shadow-xs cursor-pointer"
                  >
                    <Check size={14} /> Complete Polygon ({newPoints.length} pts)
                  </button>
                  <button
                    onClick={cancelDrawing}
                    className="px-3 py-1.5 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-xl text-xs font-semibold transition cursor-pointer"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Interactive SVG Viewport */}
          <div className="relative bg-black rounded-2xl overflow-hidden aspect-video border dark:border-slate-800 border-slate-700 shadow-2xl hud-corner">
            {/* Live Camera Stream Background Preview */}
            <img
              src={`/api/v1/cameras/${selectedCameraId}/stream`}
              alt="Camera Preview"
              className="absolute inset-0 w-full h-full object-cover opacity-60 pointer-events-none"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />

            {/* Interactive SVG Layer */}
            <svg
              ref={svgRef}
              className={`w-full h-full relative z-10 ${
                isDrawing ? 'cursor-crosshair' : simulationActive ? 'cursor-none' : 'cursor-default'
              }`}
              onClick={handleCanvasClick}
              onMouseMove={handleCanvasMouseMove}
              viewBox="0 0 1000 1000"
              preserveAspectRatio="none"
            >
              {/* Existing Defined Zones */}
              {zones
                .filter((z) => !z.camera_id || z.camera_id === selectedCameraId)
                .map((zone) => {
                  const isSelected = selectedZoneId === zone.zone_id;
                  const ptsStr = zone.points.map((p) => `${p.x * 1000},${p.y * 1000}`).join(' ');
                  const firstPt = zone.points[0] || { x: 0.1, y: 0.1 };
                  const isSimHit = simulatedBreachedZone?.zone_id === zone.zone_id;

                  return (
                    <g
                      key={zone.zone_id}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!isDrawing && !simulationActive) {
                          setSelectedZoneId(zone.zone_id);
                          playSuccessPing();
                        }
                      }}
                      className="cursor-pointer group"
                    >
                      <polygon
                        points={ptsStr}
                        fill={isSimHit ? 'rgba(239, 68, 68, 0.4)' : isSelected ? 'rgba(59, 130, 246, 0.25)' : 'rgba(239, 68, 68, 0.15)'}
                        stroke={isSimHit ? '#FF0000' : isSelected ? '#3B82F6' : zone.color || '#EF4444'}
                        strokeWidth={isSelected || isSimHit ? 3.5 : 2}
                        strokeDasharray={zone.zone_type === 'TRIPWIRE_LINE' ? '6,4' : undefined}
                      />
                      <text
                        x={firstPt.x * 1000 + 8}
                        y={firstPt.y * 1000 + 20}
                        fill={isSimHit ? '#FF4444' : isSelected ? '#60A5FA' : '#EF4444'}
                        fontSize="14"
                        fontWeight="bold"
                        className="drop-shadow"
                      >
                        ⚠️ {zone.name}
                      </text>

                      {isSelected &&
                        !isDrawing &&
                        !simulationActive &&
                        zone.points.map((pt, pIdx) => (
                          <circle
                            key={pIdx}
                            cx={pt.x * 1000}
                            cy={pt.y * 1000}
                            r="6"
                            fill="#3B82F6"
                            stroke="#FFFFFF"
                            strokeWidth="2"
                            className="hover:scale-125 transition cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                          />
                        ))}
                    </g>
                  );
                })}

              {/* In-progress polygon drawing */}
              {isDrawing && newPoints.length > 0 && (
                <g className="pointer-events-none">
                  <polyline
                    points={newPoints.map((p) => `${p.x * 1000},${p.y * 1000}`).join(' ')}
                    fill="rgba(59, 130, 246, 0.15)"
                    stroke="#3B82F6"
                    strokeWidth="2.5"
                    strokeDasharray="4,4"
                  />
                  {cursorPos && (
                    <line
                      x1={newPoints[newPoints.length - 1].x * 1000}
                      y1={newPoints[newPoints.length - 1].y * 1000}
                      x2={cursorPos.x * 1000}
                      y2={cursorPos.y * 1000}
                      stroke="#60A5FA"
                      strokeWidth="2"
                      strokeDasharray="2,2"
                    />
                  )}
                  {newPoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={p.x * 1000}
                      cy={p.y * 1000}
                      r={idx === 0 ? '8' : '5'}
                      fill={idx === 0 ? '#10B981' : '#3B82F6'}
                      stroke="#FFFFFF"
                      strokeWidth="2"
                    />
                  ))}
                </g>
              )}

              {/* Interactive Simulation Target Reticle */}
              {simulationActive && simTargetPos && (
                <g className="pointer-events-none animate-pulse">
                  <circle
                    cx={simTargetPos.x * 1000}
                    cy={simTargetPos.y * 1000}
                    r="12"
                    fill={simulatedBreachedZone ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.4)'}
                    stroke={simulatedBreachedZone ? '#EF4444' : '#10B981'}
                    strokeWidth="3"
                  />
                  <line
                    x1={simTargetPos.x * 1000 - 20}
                    y1={simTargetPos.y * 1000}
                    x2={simTargetPos.x * 1000 + 20}
                    y2={simTargetPos.y * 1000}
                    stroke={simulatedBreachedZone ? '#EF4444' : '#10B981'}
                    strokeWidth="2"
                  />
                  <line
                    x1={simTargetPos.x * 1000}
                    y1={simTargetPos.y * 1000 - 20}
                    x2={simTargetPos.x * 1000}
                    y2={simTargetPos.y * 1000 + 20}
                    stroke={simulatedBreachedZone ? '#EF4444' : '#10B981'}
                    strokeWidth="2"
                  />
                  <text
                    x={simTargetPos.x * 1000 + 15}
                    y={simTargetPos.y * 1000 - 15}
                    fill={simulatedBreachedZone ? '#EF4444' : '#10B981'}
                    fontSize="13"
                    fontWeight="bold"
                    className="drop-shadow font-mono"
                  >
                    {simulatedBreachedZone ? `🚨 BREACH: ${simulatedBreachedZone.name}` : 'SAFE'}
                  </text>
                </g>
              )}
            </svg>

            {/* Coordinates / Instructions Footer */}
            <div className="absolute bottom-2 left-3 right-3 flex justify-between items-center text-[11px] font-mono text-slate-400 bg-black/80 px-3 py-1.5 rounded-xl backdrop-blur-md border border-slate-700/80">
              <span>
                {isDrawing
                  ? `Click canvas to add point (${newPoints.length} added). Double-click or click start to close.`
                  : simulationActive
                  ? 'Move cursor to simulate target coordinates.'
                  : 'Click a zone to select. Drag white vertex handles to reshape.'}
              </span>
              <span className="text-cyan-400 font-bold">
                {cursorPos ? `X: ${(cursorPos.x * 100).toFixed(1)}% | Y: ${(cursorPos.y * 100).toFixed(1)}%` : 'Ready'}
              </span>
            </div>
          </div>

          {/* Quick Preset Templates */}
          <div className="pt-2 flex items-center justify-between flex-wrap gap-2 text-xs">
            <span className="text-slate-400 font-semibold flex items-center gap-1">
              <Sparkles size={13} className="text-amber-400" /> Fast Templates:
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleApplyPreset('perimeter')}
                className="px-2.5 py-1 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition cursor-pointer shadow-xs"
              >
                + Perimeter Tripwire
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('checkpoint')}
                className="px-2.5 py-1 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition cursor-pointer shadow-xs"
              >
                + Gate Corridor
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('quad')}
                className="px-2.5 py-1 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition cursor-pointer shadow-xs"
              >
                + Restricted Box
              </button>
            </div>
          </div>
        </div>

        {/* Right Col: Zone Inspector & Metadata Editor */}
        <div className="glass-panel rounded-2xl border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl p-4 space-y-4 flex flex-col h-[650px] overflow-hidden">
          <h2 className="font-bold text-sm dark:text-white text-slate-800 flex items-center justify-between border-b dark:border-slate-800/80 border-slate-100 pb-2">
            <span>Perimeter Zones Ledger</span>
            <span className="text-xs font-normal text-slate-400 font-mono">
              {zones.filter((z) => !z.camera_id || z.camera_id === selectedCameraId).length} Zones
            </span>
          </h2>

          {/* Zone Cards List */}
          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {zones
              .filter((z) => !z.camera_id || z.camera_id === selectedCameraId)
              .map((zone) => {
                const isSelected = selectedZoneId === zone.zone_id;
                return (
                  <div
                    key={zone.zone_id}
                    onClick={() => {
                      setSelectedZoneId(zone.zone_id);
                      playSuccessPing();
                    }}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'border-blue-500 dark:bg-blue-950/30 bg-blue-50/60 shadow-md ring-1 ring-blue-400'
                        : 'dark:border-slate-800/80 dark:bg-slate-900/80 hover:border-slate-700 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-bold dark:text-white text-slate-900">{zone.name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{zone.zone_id}</p>
                      </div>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 font-mono">
                        {zone.zone_type}
                      </span>
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 border-t dark:border-slate-800/80 border-slate-100 pt-2 font-mono">
                      <span>Nodes: <strong className="text-cyan-400">{zone.points.length} vertices</strong></span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteZone(zone.zone_id);
                        }}
                        className="text-slate-400 hover:text-red-400 transition p-1 cursor-pointer"
                        title="Delete Zone"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>

          {/* Selected Zone Editor Form */}
          {selectedZone && (
            <div className="p-3.5 dark:bg-slate-950/80 dark:border-slate-800/80 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
              <span className="font-bold dark:text-white text-slate-700 block font-mono">Edit Selected: {selectedZone.name}</span>

              <div>
                <label className="text-[11px] font-medium text-slate-400 block mb-1">Zone Name</label>
                <input
                  type="text"
                  value={selectedZone.name}
                  onChange={(e) => {
                    const val = e.target.value;
                    setZones((prev) =>
                      prev.map((z) => (z.zone_id === selectedZone.zone_id ? { ...z, name: val } : z))
                    );
                  }}
                  className="w-full px-2.5 py-1.5 dark:bg-slate-900 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">Zone Type</label>
                  <select
                    value={selectedZone.zone_type}
                    onChange={(e) => {
                      const val = e.target.value;
                      setZones((prev) =>
                        prev.map((z) => (z.zone_id === selectedZone.zone_id ? { ...z, zone_type: val } : z))
                      );
                    }}
                    className="w-full px-2 py-1.5 dark:bg-slate-900 dark:border-slate-700 dark:text-white bg-white border border-slate-300 rounded-lg text-slate-800 text-xs focus:outline-none font-mono"
                  >
                    <option value="RESTRICTED_ZONE">RESTRICTED_ZONE</option>
                    <option value="TRIPWIRE_LINE">TRIPWIRE_LINE</option>
                    <option value="LOITERING_ZONE">LOITERING_ZONE</option>
                    <option value="ENTRY_CORRIDOR">ENTRY_CORRIDOR</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">Color Marker</label>
                  <input
                    type="color"
                    value={selectedZone.color || '#EF4444'}
                    onChange={(e) => {
                      const val = e.target.value;
                      setZones((prev) =>
                        prev.map((z) => (z.zone_id === selectedZone.zone_id ? { ...z, color: val } : z))
                      );
                    }}
                    className="w-full h-8 p-0.5 dark:bg-slate-900 dark:border-slate-700 bg-white border border-slate-300 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
