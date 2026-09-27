import React, { useState } from 'react';
import { Incident } from '../types';
import { useSubmitFeedback } from '../api/hooks';
import { EventTypeBadge } from './EventTypeBadge';
import { X, CheckCircle, AlertTriangle, HelpCircle, ShieldAlert, Loader2, Send } from 'lucide-react';

interface OperatorFeedbackModalProps {
  incident: Incident | null;
  isOpen: boolean;
  onClose: () => void;
}

export const OperatorFeedbackModal: React.FC<OperatorFeedbackModalProps> = ({
  incident,
  isOpen,
  onClose,
}) => {
  const [selectedLabel, setSelectedLabel] = useState<'TRUE_INTRUSION' | 'FALSE_ALARM' | 'UNSURE'>('TRUE_INTRUSION');
  const [notes, setNotes] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const { mutate: submitFeedback, isPending } = useSubmitFeedback();

  if (!isOpen || !incident) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitFeedback(
      {
        incidentId: incident.id,
        label: selectedLabel,
        notes: notes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setSubmitSuccess(true);
          setTimeout(() => {
            setSubmitSuccess(false);
            setNotes('');
            onClose();
          }, 1200);
        },
      }
    );
  };

  const evidenceFilename = incident.evidence_reference?.split(/[/\\]/).pop();

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-600 rounded-lg text-white">
              <ShieldAlert size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold flex items-center gap-2">
                Operator Feedback Loop
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-800 text-blue-200">
                  Active Learning
                </span>
              </h3>
              <p className="text-[11px] text-slate-300">
                Provide ground truth labeling to update the neural pipeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Incident Summary Card */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/80 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <EventTypeBadge eventType={incident.event_type} />
              <span className="font-mono text-[11px] text-slate-500 font-bold">
                {incident.camera_id}
              </span>
            </div>
            <p className="text-slate-700 font-medium leading-relaxed">
              {incident.explanation || `${incident.event_type} observed on ${incident.camera_id}`}
            </p>
            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1.5 border-t border-slate-200/60 font-mono">
              <span>Confidence: {(incident.confidence * 100).toFixed(1)}%</span>
              <span>Severity: {incident.severity}</span>
            </div>
          </div>

          {/* Evidence Preview if available */}
          {evidenceFilename && (
            <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-100">
              <img
                src={`/evidence/${evidenceFilename}`}
                alt="Incident Evidence"
                className="w-full h-36 object-cover"
              />
              {incident.sha256 && (
                <div className="p-1.5 bg-slate-900 text-slate-400 text-[10px] font-mono truncate">
                  SHA-256: {incident.sha256}
                </div>
              )}
            </div>
          )}

          {/* Feedback Form */}
          <form onSubmit={handleSubmit} className="space-y-4 pt-1">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Operator Label Classification *
              </label>
              <div className="grid grid-cols-3 gap-2.5">
                {/* True Intrusion */}
                <button
                  type="button"
                  onClick={() => setSelectedLabel('TRUE_INTRUSION')}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all cursor-pointer flex flex-col items-center gap-1 ${
                    selectedLabel === 'TRUE_INTRUSION'
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-900 shadow-sm ring-2 ring-emerald-200 font-bold'
                      : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                  }`}
                >
                  <CheckCircle size={18} className={selectedLabel === 'TRUE_INTRUSION' ? 'text-emerald-600' : 'text-slate-400'} />
                  <span className="text-[11px]">True Intrusion</span>
                </button>

                {/* False Alarm */}
                <button
                  type="button"
                  onClick={() => setSelectedLabel('FALSE_ALARM')}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all cursor-pointer flex flex-col items-center gap-1 ${
                    selectedLabel === 'FALSE_ALARM'
                      ? 'border-rose-500 bg-rose-50 text-rose-900 shadow-sm ring-2 ring-rose-200 font-bold'
                      : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                  }`}
                >
                  <AlertTriangle size={18} className={selectedLabel === 'FALSE_ALARM' ? 'text-rose-600' : 'text-slate-400'} />
                  <span className="text-[11px]">False Alarm</span>
                </button>

                {/* Unsure */}
                <button
                  type="button"
                  onClick={() => setSelectedLabel('UNSURE')}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all cursor-pointer flex flex-col items-center gap-1 ${
                    selectedLabel === 'UNSURE'
                      ? 'border-amber-500 bg-amber-50 text-amber-900 shadow-sm ring-2 ring-amber-200 font-bold'
                      : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
                  }`}
                >
                  <HelpCircle size={18} className={selectedLabel === 'UNSURE' ? 'text-amber-600' : 'text-slate-400'} />
                  <span className="text-[11px]">Unsure</span>
                </button>
              </div>
            </div>

            {/* Operator Notes */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Operator Notes (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Authorized patrol team on night routine, benign livestock movement, or verified border breach..."
                rows={3}
                className="w-full p-2.5 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              />
            </div>

            {/* Status Messages */}
            {submitSuccess && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-bold flex items-center gap-2 animate-in fade-in">
                <CheckCircle size={16} className="text-emerald-600" />
                Feedback recorded as {selectedLabel}! Retraining dataset updated.
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending || submitSuccess}
                className="px-4 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                {isPending ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send size={13} />
                    Submit Ground Truth
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
};