import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { ReportDetail } from '../../types/api';
import { api } from '../../api/client';
import { useDialog } from '../ui/DialogContext';
import { Edit3, FileText } from 'lucide-react';

interface EditReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: ReportDetail;
  onSaved: () => void;
}

export const EditReportModal: React.FC<EditReportModalProps> = ({
  isOpen,
  onClose,
  report,
  onSaved
}) => {
  const { showError } = useDialog();
  const [customName, setCustomName] = useState(report.custom_name);
  const [description, setDescription] = useState(report.description || '');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setCustomName(report.custom_name);
      setDescription(report.description || '');
    }
  }, [isOpen, report]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customName.trim()) return;

    setIsSaving(true);
    try {
      await api.updateReport(report.id, {
        custom_name: customName.trim(),
        description: description.trim()
      });
      onSaved();
      onClose();
    } catch (err) {
      console.error('Failed to update report metadata:', err);
      showError(err, 'Updating Report Details');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2 text-slate-100 font-semibold">
          <Edit3 className="w-5 h-5 text-indigo-400" />
          <span>Edit Report Details</span>
        </div>
      }
      maxWidth="md"
    >
      <form onSubmit={handleSave} className="p-6 space-y-5">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
            Report Name
          </label>
          <input
            type="text"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            required
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            placeholder="e.g. Night Standby (Airplane Mode)"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
            Description / Experiment Notes
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none"
            placeholder="Add context on test conditions (e.g., 5G disabled, bedtime standby, Bluetooth off, sync enabled)..."
          />
          <p className="text-[11px] text-slate-500 mt-1.5">
            Notes are displayed on the report banner and automatically injected into AI diagnostic and chat contexts.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSaving || !customName.trim()}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
