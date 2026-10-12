import React, { useState, useRef } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { api } from '../../api/client';
import { ReportDetail } from '../../types/api';
import { UploadCloud, FileArchive, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (report: ReportDetail) => void;
  defaultTimezone?: string;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
  defaultTimezone = 'UTC'
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [autoDiagnose, setAutoDiagnose] = useState(false);
  const [timezone, setTimezone] = useState(defaultTimezone);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a bugreport file to upload.');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const report = await api.uploadReport(file, autoDiagnose, timezone);
      setFile(null);
      onUploadSuccess(report);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to upload bugreport.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Import Android Bugreport" maxWidth="lg">
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
                  <p className="text-xs text-slate-500 mt-1">or click to browse files from your computer</p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Options */}
        <div className="space-y-3 bg-slate-950/40 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-slate-300">Device Timezone</label>
            <Input
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="e.g. Europe/Warsaw or UTC"
              className="w-48 text-xs h-8"
            />
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

        {error && (
          <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-xl text-xs text-rose-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={uploading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" size="sm" disabled={!file || uploading}>
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Telemetry...</span>
              </>
            ) : (
              <span>Import Bugreport</span>
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
