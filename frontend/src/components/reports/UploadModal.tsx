import React, { useState, useRef } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { api } from '../../api/client';
import { ReportDetail, UploadProgressEvent } from '../../types/api';
import {
  UploadCloud,
  FileArchive,
  AlertTriangle,
  Loader2,
  Globe,
  Terminal,
  CheckCircle2,
  Circle,
  Sparkles,
  RefreshCw
} from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (report: ReportDetail) => void;
  defaultTimezone?: string;
}

type ModalState = 'idle' | 'uploading' | 'completed' | 'error';

interface PhaseDef {
  id: string;
  label: string;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  defaultTimezone = 'Europe/Warsaw'
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [autoDiagnose, setAutoDiagnose] = useState(false);
  const [modalState, setModalState] = useState<ModalState>('idle');
  const [currentPhase, setCurrentPhase] = useState<string>('unpacking');
  const [progress, setProgress] = useState<number>(0);
  const [phaseMessage, setPhaseMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const resetUploadState = () => {
    setModalState('idle');
    setProgress(0);
    setCurrentPhase('unpacking');
    setPhaseMessage('');
    setError(null);
  };

  const handleModalClose = () => {
    if (modalState === 'uploading') return;
    resetUploadState();
    setFile(null);
    onClose();
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0];
      if (dropped.name.endsWith('.zip') || dropped.name.endsWith('.txt')) {
        setFile(dropped);
        setError(null);
      } else {
        setError('Please drop a valid Android bugreport archive (.zip) or text file (.txt).');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    resetUploadState();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a bugreport file to upload.');
      return;
    }

    setModalState('uploading');
    setProgress(5);
    setCurrentPhase('unpacking');
    setPhaseMessage('Preparing upload...');
    setError(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const report = await api.uploadReportStream(
        file,
        autoDiagnose,
        undefined,
        (event: UploadProgressEvent) => {
          if (event.phase) {
            setCurrentPhase(event.phase);
          }
          if (typeof event.progress === 'number') {
            setProgress(event.progress);
          }
          if (event.message) {
            setPhaseMessage(event.message);
          }
        },
        controller.signal
      );

      setModalState('completed');
      setProgress(100);
      setPhaseMessage('Import complete!');

      setTimeout(() => {
        setFile(null);
        resetUploadState();
        onUploadSuccess(report);
        onClose();
      }, 600);
    } catch (err: any) {
      if (err.name === 'AbortError' || err.message?.includes('aborted')) {
        resetUploadState();
        return;
      }
      setModalState('error');
      setError(err.message || 'Failed to upload bugreport.');
    } finally {
      abortControllerRef.current = null;
    }
  };

  // Phase steps definition based on autoDiagnose choice
  const phases: PhaseDef[] = [
    { id: 'unpacking', label: 'Unpacking bugreport archive' },
    { id: 'telemetry', label: 'Extracting system UIDs & batterystats' },
    { id: 'history', label: 'Parsing battery discharge timeline' },
    ...(autoDiagnose ? [{ id: 'ai_diagnose', label: 'Generating AI diagnostic plan' }] : []),
    { id: 'saving', label: 'Saving report to database' }
  ];

  const phaseOrder = [
    'unpacking',
    'telemetry',
    'history',
    ...(autoDiagnose ? ['ai_diagnose'] : []),
    'saving',
    'completed'
  ];

  const getStepStatus = (stepId: string) => {
    if (modalState === 'completed') return 'completed';
    const currentIdx = phaseOrder.indexOf(currentPhase);
    const stepIdx = phaseOrder.indexOf(stepId);

    if (modalState === 'error') {
      if (currentIdx === stepIdx) return 'error';
      return stepIdx < currentIdx ? 'completed' : 'pending';
    }

    if (stepIdx < currentIdx) return 'completed';
    if (stepIdx === currentIdx) return 'active';
    return 'pending';
  };

  const modalTitle =
    modalState === 'uploading'
      ? 'Importing Android Bugreport'
      : modalState === 'completed'
      ? 'Import Complete'
      : modalState === 'error'
      ? 'Import Failed'
      : 'Import Android Bugreport';

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleModalClose}
      title={modalTitle}
      maxWidth="lg"
      preventClose={modalState === 'uploading' || modalState === 'completed'}
    >
      {modalState === 'idle' ? (
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragActive
                ? 'border-emerald-500 bg-emerald-950/20'
                : file
                ? 'border-emerald-600/60 bg-slate-950/40'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/20'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.txt"
              onChange={handleFileChange}
              className="hidden"
            />

            <div className="flex flex-col items-center justify-center gap-3">
              {file ? (
                <>
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <FileArchive className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{file.name}</p>
                    <p className="text-xs text-slate-400">{(file.size / (1024 * 1024)).toFixed(1)} MB</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      Drag and drop your <code className="text-emerald-400 bg-emerald-950/50 px-1 py-0.5 rounded">bugreport-*.zip</code> here
                    </p>
                    <p className="text-xs text-slate-500 mt-1">or click to browse files from your computer (200MB max • ZIP, TXT)</p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Options & Read-Only Timezone Info */}
          <div className="space-y-3 bg-slate-950/40 border border-slate-800/80 rounded-xl p-4">
            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2.5">
              <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-indigo-400" />
                Configured Device Timezone (from Settings DB)
              </span>
              <Badge variant="scope" className="font-mono text-xs">
                {defaultTimezone}
              </Badge>
            </div>

            <label className="flex items-center gap-2.5 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={autoDiagnose}
                onChange={(e) => setAutoDiagnose(e.target.checked)}
                className="rounded border-slate-700 text-emerald-600 focus:ring-emerald-500 bg-slate-900"
              />
              <span className="text-xs text-slate-300 select-none">
                Generate AI diagnostic plan immediately upon import
              </span>
            </label>
          </div>

          {/* ADB Tip */}
          <div className="p-3 bg-slate-900/70 border border-slate-800 rounded-xl text-xs text-slate-400 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              Tip: Run <code className="bg-slate-950 px-1.5 py-0.5 rounded text-emerald-300 font-mono">adb bugreport bugreport.zip</code> in your terminal to create bug reports.
            </span>
          </div>

          {error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-xl text-xs text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" size="sm" onClick={handleModalClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={!file}>
              <span>Import Bugreport</span>
            </Button>
          </div>
        </form>
      ) : (
        /* In-Progress / Completed / Error Dedicated View */
        <div className="space-y-6 py-1">
          {/* File Header Card */}
          <div className="flex items-center justify-between bg-slate-950/50 border border-slate-800/80 rounded-xl p-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                <FileArchive className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-100 truncate">{file?.name}</p>
                <p className="text-xs text-slate-400">
                  {file ? (file.size / (1024 * 1024)).toFixed(1) : 0} MB
                </p>
              </div>
            </div>

            {autoDiagnose && (
              <Badge variant="scope" className="flex items-center gap-1 font-sans text-xs shrink-0">
                <Sparkles className="w-3 h-3 text-indigo-400" />
                AI Diagnostic
              </Badge>
            )}
          </div>

          {/* Progress Bar & Status Text */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-slate-300">
                {modalState === 'error'
                  ? 'Import encountered an error'
                  : modalState === 'completed'
                  ? 'Import complete!'
                  : phaseMessage || 'Processing telemetry...'}
              </span>
              <span className="font-mono text-emerald-400 font-semibold">{progress}%</span>
            </div>

            <div className="h-2.5 w-full bg-slate-800/80 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
              <div
                className={`h-full rounded-full transition-all duration-300 ease-out ${
                  modalState === 'error'
                    ? 'bg-rose-500'
                    : modalState === 'completed'
                    ? 'bg-emerald-500'
                    : 'bg-gradient-to-r from-emerald-500 to-indigo-500'
                }`}
                style={{ width: `${Math.max(5, Math.min(100, progress))}%` }}
              />
            </div>
          </div>

          {/* Phase Steps Checklist */}
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-4 space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Import Pipeline
            </div>
            {phases.map((phase) => {
              const status = getStepStatus(phase.id);
              return (
                <div key={phase.id} className="flex items-center gap-3 text-xs">
                  {status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : status === 'active' ? (
                    <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                  ) : status === 'error' ? (
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-600 shrink-0" />
                  )}

                  <span
                    className={`transition-colors ${
                      status === 'completed'
                        ? 'text-slate-300 font-medium'
                        : status === 'active'
                        ? 'text-slate-100 font-semibold'
                        : status === 'error'
                        ? 'text-rose-300 font-medium'
                        : 'text-slate-500'
                    }`}
                  >
                    {phase.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Error Message */}
          {modalState === 'error' && error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-xl text-xs text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            {modalState === 'uploading' && (
              <Button type="button" variant="ghost" size="sm" onClick={handleCancel}>
                Cancel
              </Button>
            )}

            {modalState === 'error' && (
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={resetUploadState}
                className="flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Try Again</span>
              </Button>
            )}

            {modalState === 'completed' && (
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 py-1">
                <CheckCircle2 className="w-4 h-4" />
                <span>Ready! Opening report...</span>
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
};
