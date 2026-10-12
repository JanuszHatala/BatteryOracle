import React from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles, RefreshCw, FileText, Download } from 'lucide-react';

interface DiagnosisCardProps {
  diagnosisMarkdown?: string;
  isDiagnosing: boolean;
  onDiagnose: () => void;
  onExportMarkdown: () => void;
}

export const DiagnosisCard: React.FC<DiagnosisCardProps> = ({
  diagnosisMarkdown,
  isDiagnosing,
  onDiagnose,
  onExportMarkdown
}) => {
  return (
    <Card className="p-5 flex flex-col space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-slate-100">AI Diagnostic Summary</h3>
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
              Generating deep battery telemetry diagnosis with LLM...
            </p>
          </div>
        ) : diagnosisMarkdown ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ ...props }) => <h1 className="text-xl font-bold text-slate-100 mt-4 mb-2" {...props} />,
              h2: ({ ...props }) => <h2 className="text-lg font-semibold text-slate-200 mt-3 mb-2" {...props} />,
              h3: ({ ...props }) => <h3 className="text-base font-medium text-slate-300 mt-2 mb-1" {...props} />,
              ul: ({ ...props }) => <ul className="list-disc pl-5 space-y-1 text-slate-300" {...props} />,
              ol: ({ ...props }) => <ol className="list-decimal pl-5 space-y-1 text-slate-300" {...props} />,
              li: ({ ...props }) => <li className="text-slate-300 leading-relaxed" {...props} />,
              p: ({ ...props }) => <p className="mb-2.5 leading-relaxed text-slate-300" {...props} />,
              code: ({ ...props }) => (
                <code className="bg-slate-800 px-1 py-0.5 rounded text-indigo-300 text-xs font-mono" {...props} />
              ),
              pre: ({ ...props }) => (
                <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 overflow-x-auto text-xs my-2" {...props} />
              )
            }}
          >
            {diagnosisMarkdown}
          </ReactMarkdown>
        ) : (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-2">
            <FileText className="w-8 h-8 text-slate-600" />
            <p className="text-sm text-slate-400">
              No diagnosis generated for this report yet. Click "Generate Diagnosis" above.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
