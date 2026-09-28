import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, Trash2, Save, AlertTriangle, Layers, X
} from 'lucide-react';
import { useZones, useSaveZones, useDeleteZone, useCameras } from '../api/hooks';
import { Zone, ZonePoint } from '../types';
import { playSuccessPing, playWarningChime } from '../utils/audioAlerts';
import { Badge } from '../components/ui/Badge';

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
  const { data: zonesData } = useZones();
  const { data: cameras } = useCameras();
  const { mutate: saveZonesMutation, isPending: isSaving } = useSaveZones();
  const { mutate: deleteZoneMutation } = useDeleteZone();

  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('CAM-01');

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
      name: `Perimeter Zone ${zones.length + 1}`,
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
    setStatusNotice(`Created ${newZone.name}. Click "Save Zones" to apply.`);
    playSuccessPing();
  };

  const handleDeleteZone = (zoneId: string) => {
    deleteZoneMutation(zoneId, {
      onSuccess: () => {
        setZones((prev) => prev.filter((z) => z.zone_id !== zoneId));
        if (selectedZoneId === zoneId) {
          setSelectedZoneId(null);
        }
        setStatusNotice('Zone deleted.');
        playSuccessPing();
      }
    });
  };

  const handleSaveAll = () => {
    saveZonesMutation(zones, {
      onSuccess: () => {
        setStatusNotice('All configured zones successfully saved to video pipeline.');
        playSuccessPing();
        setTimeout(() => setStatusNotice(null), 3500);
      }
    });
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      
      {/* Top Header */}
      <div className="vms-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Perimeter Zone Configuration</h2>
          <p className="text-xs text-slate-400">
            Define restricted zones, boundary tripwires, and monitored areas.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {statusNotice && (
            <span className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800 px-2.5 py-1 rounded">
              {statusNotice}
            </span>
          )}
          <button
            onClick={handleSaveAll}
            disabled={isSaving}
            className="vms-btn vms-btn-primary text-xs"
          >
            <Save size={13} />
            <span>{isSaving ? 'Saving...' : 'Save Zones'}</span>
          </button>
        </div>
      </div>

      {/* Main 2-Column Workstation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* Left: Zone List and Settings (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          
          {/* Camera Selector Card */}
          <div className="vms-card p-3 space-y-2 text-xs">
            <label className="text-slate-400 block font-medium">Select Camera Feed</label>
            <select
              value={selectedCameraId}
              onChange={(e) => setSelectedCameraId(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] text-slate-200 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500"
            >
              {cameras?.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  {cam.id} — {cam.name || 'Camera Feed'}
                </option>
              )) || <option value="CAM-01">CAM-01 — Perimeter North</option>}
            </select>
          </div>

          {/* Zones List */}
          <div className="vms-card flex flex-col flex-1 overflow-hidden">
            <div className="vms-card-header flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-semibold text-slate-200">
                <Layers size={14} className="text-blue-400" />
                Configured Zones ({zones.length})
              </span>
              {!isDrawing ? (
                <button
                  onClick={startDrawing}
                  className="vms-btn vms-btn-primary text-[11px] py-1 px-2"
                >
                  <Plus size={12} /> Draw Zone
                </button>
              ) : (
                <button
                  onClick={cancelDrawing}
                  className="vms-btn text-[11px] py-1 px-2 text-red-400 border-red-800"
                >
                  <X size={12} /> Cancel
                </button>
              )}
            </div>

            <div className="p-2 space-y-2 overflow-y-auto max-h-96 text-xs">
              {zones.length === 0 ? (
                <div className="py-8 text-center text-slate-500">
                  No zones defined. Click "Draw Zone" to define a perimeter boundary.
                </div>
              ) : (
                zones.map((zone) => {
                  const isSelected = zone.zone_id === selectedZoneId;
                  return (
                    <div
                      key={zone.zone_id}
                      onClick={() => setSelectedZoneId(zone.zone_id)}
                      className={`p-2.5 rounded border cursor-pointer transition ${
                        isSelected
                          ? 'bg-blue-950/40 border-blue-500 text-white'
                          : 'bg-[#0f172a] border-[#334155] text-slate-300 hover:bg-[#1e293b]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs">{zone.name}</span>
                        <Badge variant={zone.enabled ? 'danger' : 'neutral'}>
                          {zone.zone_type || 'RESTRICTED'}
                        </Badge>
                      </div>

                      <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                        <span>{zone.points.length} vertices</span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteZone(zone.zone_id);
                            }}
                            className="text-slate-500 hover:text-red-400 p-1"
                            title="Delete zone"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Selected Zone Properties */}
          {selectedZone && (
            <div className="vms-card p-3 space-y-3 text-xs">
              <div className="font-semibold text-slate-200 border-b border-[#334155] pb-1.5">
                Zone Properties: {selectedZone.name}
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Zone Name</label>
                <input
                  type="text"
                  value={selectedZone.name}
                  onChange={(e) => {
                    const newName = e.target.value;
                    setZones((prev) =>
                      prev.map((z) => z.zone_id === selectedZone.zone_id ? { ...z, name: newName } : z)
                    );
                  }}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-2.5 py-1 text-white"
                />
              </div>
              <div className="flex items-center justify-between pt-1">
                <span className="text-slate-400">Monitoring Active</span>
                <input
                  type="checkbox"
                  checked={selectedZone.enabled}
                  onChange={(e) => {
                    const enabled = e.target.checked;
                    setZones((prev) =>
                      prev.map((z) => z.zone_id === selectedZone.zone_id ? { ...z, enabled } : z)
                    );
                  }}
                  className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                />
              </div>
            </div>
          )}
        </div>

        {/* Right: Interactive Calibration Viewport (8 cols) */}
        <div className="lg:col-span-8 flex flex-col vms-card overflow-hidden">
          
          {/* Viewport Top Bar */}
          <div className="vms-card-header flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Canvas Calibration: {selectedCameraId}</span>
            </span>

            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={() => setSimulationActive(!simulationActive)}
                className={`px-2.5 py-1 rounded border text-[11px] font-medium transition ${
                  simulationActive
                    ? 'bg-amber-600/30 text-amber-300 border-amber-500/50'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {simulationActive ? 'Testing: Move Mouse on Feed' : 'Test Intrusion Boundary'}
              </button>
            </div>
          </div>

          {/* Interactive Canvas */}
          <div className="relative aspect-video bg-black overflow-hidden flex items-center justify-center select-none">
            {/* Background Camera Snapshot */}
            <img
              src={`/api/v1/cameras/${selectedCameraId}/snapshot`}
              alt="Calibration Background"
              className="w-full h-full object-cover pointer-events-none"
              onError={(e) => {
                (e.target as HTMLImageElement).src = '/api/v1/cameras/CAM-01/snapshot';
              }}
            />

            {/* SVG Interactive Overlay */}
            <svg
              ref={svgRef}
              className={`absolute inset-0 w-full h-full ${isDrawing ? 'cursor-crosshair' : 'cursor-default'}`}
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              onClick={handleCanvasClick}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleMouseUp}
            >
              {/* Existing Defined Zones */}
              {zones.map((zone) => {
                if (!zone.points || zone.points.length < 3) return null;
                const pointsStr = zone.points.map((p) => `${p.x * 100},${p.y * 100}`).join(' ');
                const isSelected = zone.zone_id === selectedZoneId;
                const isBreached = simulatedBreachedZone?.zone_id === zone.zone_id;

                return (
                  <g key={zone.zone_id}>
                    <polygon
                      points={pointsStr}
                      fill={isBreached ? 'rgba(239, 68, 68, 0.35)' : isSelected ? 'rgba(59, 130, 246, 0.20)' : 'rgba(239, 68, 68, 0.12)'}
                      stroke={isBreached ? '#ef4444' : isSelected ? '#3b82f6' : '#ef4444'}
                      strokeWidth={isSelected ? '1' : '0.7'}
                      strokeDasharray={isSelected ? 'none' : '2 1'}
                    />
                    <text
                      x={zone.points[0].x * 100}
                      y={zone.points[0].y * 100 - 1.5}
                      fill={isBreached ? '#fca5a5' : isSelected ? '#93c5fd' : '#f87171'}
                      fontSize="2.4"
                      fontWeight="bold"
                    >
                      {zone.name}
                    </text>

                    {/* Vertices for selected zone */}
                    {isSelected && !isDrawing && (
                      zone.points.map((p, idx) => (
                        <circle
                          key={idx}
                          cx={p.x * 100}
                          cy={p.y * 100}
                          r="1.2"
                          fill="#ffffff"
                          stroke="#2563eb"
                          strokeWidth="0.5"
                          className="cursor-move pointer-events-auto"
                          onMouseDown={(e) => {
                            e.stopPropagation();
                            setDraggingVertex({ zoneId: zone.zone_id, pointIdx: idx });
                          }}
                        />
                      ))
                    )}
                  </g>
                );
              })}

              {/* In-Progress Drawing Polygon */}
              {isDrawing && newPoints.length > 0 && (
                <g>
                  {newPoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={p.x * 100}
                      cy={p.y * 100}
                      r="1.2"
                      fill={idx === 0 ? '#10b981' : '#3b82f6'}
                      stroke="#ffffff"
                      strokeWidth="0.4"
                    />
                  ))}
                  {newPoints.length > 1 && (
                    <polyline
                      points={newPoints.map((p) => `${p.x * 100},${p.y * 100}`).join(' ')}
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="0.8"
                    />
                  )}
                  {cursorPos && (
                    <line
                      x1={newPoints[newPoints.length - 1].x * 100}
                      y1={newPoints[newPoints.length - 1].y * 100}
                      x2={cursorPos.x * 100}
                      y2={cursorPos.y * 100}
                      stroke="#94a3b8"
                      strokeWidth="0.6"
                      strokeDasharray="1.5 1.5"
                    />
                  )}
                </g>
              )}

              {/* Simulation Target Cursor */}
              {simulationActive && simTargetPos && (
                <circle
                  cx={simTargetPos.x * 100}
                  cy={simTargetPos.y * 100}
                  r="1.5"
                  fill={simulatedBreachedZone ? '#ef4444' : '#10b981'}
                  stroke="#ffffff"
                  strokeWidth="0.4"
                />
              )}
            </svg>

            {/* Instruction Overlay */}
            {isDrawing && (
              <div className="absolute top-3 left-3 bg-slate-900/90 border border-blue-500/60 p-2.5 rounded text-xs text-slate-200">
                Click to place polygon vertices. Click the initial green point to close the zone.
              </div>
            )}

            {/* Breach Alert in Simulation Mode */}
            {simulationActive && simulatedBreachedZone && (
              <div className="absolute top-3 right-3 bg-red-950/80 border border-red-600 text-red-200 text-xs px-3 py-1.5 rounded font-semibold flex items-center gap-2">
                <AlertTriangle size={14} className="text-red-400" />
                <span>Boundary Breach: {simulatedBreachedZone.name}</span>
              </div>
            )}
          </div>

          {/* Viewport Footer */}
          <div className="bg-[#0f172a] px-4 py-2 border-t border-[#1e293b] flex items-center justify-between text-xs text-slate-400">
            <span>Coordinates: Normalized [0.00 – 1.00]</span>
            <span>Click and drag white vertex dots to calibrate</span>
          </div>
        </div>

      </div>
    </div>
  );
};
