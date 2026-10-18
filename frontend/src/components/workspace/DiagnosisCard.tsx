import React from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Sparkles, RefreshCw, FileText, Download } from 'lucide-react';
import { MarkdownView } from '../ui/MarkdownView';

interface DiagnosisCardProps {
  diagnosisMarkdown?: string;
  isDiagnosing: boolean;
  onDiagnose: () => void;
  onExportMarkdown: () => void;
  scope?: string;
}

const SCOPE_LABELS: Record<string, string> = {
  all: 'Full Timeline',
  night: '🌙 Night Drain',
  screen_off: '📱 Screen Off',
  custom: '⏱️ Custom Window'
};

export const DiagnosisCard: React.FC<DiagnosisCardProps> = ({
  diagnosisMarkdown,
  isDiagnosing,
  onDiagnose,
  onExportMarkdown,
  scope = 'all'
}) => {
  const scopeLabel = SCOPE_LABELS[scope] || scope;

  return (
    <Card className="p-5 flex flex-col space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-slate-100">AI Diagnostic Summary</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
            {scopeLabel}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onExportMarkdown}
          >
            <Download className="w-4 h-4 mr-1.5" />
            Export Markdown
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onDiagnose}
            disabled={isDiagnosing}
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${isDiagnosing ? 'animate-spin' : ''}`} />
            {diagnosisMarkdown ? 'Re-Run Diagnosis' : 'Generate Diagnosis'}
          </Button>
        </div>
      </div>

      <div className="prose prose-invert prose-sm max-w-none text-slate-300">
        {isDiagnosing ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
            <p className="text-sm text-slate-400">
              Generating deep battery telemetry diagnosis for {scopeLabel} with LLM...
            </p>
          </div>
        ) : diagnosisMarkdown ? (
          <MarkdownView content={diagnosisMarkdown} />
        ) : (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-2">
            <FileText className="w-8 h-8 text-slate-600" />
            <p className="text-sm text-slate-400">
              No diagnosis generated for {scopeLabel} yet. Click "Generate Diagnosis" above.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
