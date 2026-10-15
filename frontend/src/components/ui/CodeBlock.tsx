import React, { useState } from 'react';
import { Copy, Check, Terminal, Code2, FileCode } from 'lucide-react';

export const CodeBlockContext = React.createContext<boolean>(false);

export const MarkdownPre: React.FC<React.HTMLAttributes<HTMLPreElement>> = ({ children }) => {
  return (
    <CodeBlockContext.Provider value={true}>
      {children}
    </CodeBlockContext.Provider>
  );
};

export const MarkdownCode: React.FC<React.HTMLAttributes<HTMLElement>> = ({ className, children }) => {
  const isInsidePre = React.useContext(CodeBlockContext);
  return (
    <CodeBlock className={className} inline={!isInsidePre}>
      {children}
    </CodeBlock>
  );
};

interface CodeBlockProps {
  children?: React.ReactNode;
  className?: string;
  inline?: boolean;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  children,
  className,
  inline
}) => {
  const [copied, setCopied] = useState(false);
  const rawCode = String(children || '').replace(/\n$/, '');

  // Extract language from className (e.g. "language-bash" -> "bash")
  const match = /language-(\w+)/.exec(className || '');
  const detectedLang = match ? match[1].toLowerCase() : '';

  // Check if an inline code snippet is an ADB or shell command
  const isAdbOrShell =
    rawCode.startsWith('adb ') ||
    rawCode.startsWith('cmd ') ||
    rawCode.startsWith('dumpsys ') ||
    rawCode.startsWith('pm ') ||
    rawCode.includes('adb shell');

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(rawCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code to clipboard:', err);
    }
  };

  // 1. Special Handling for Inline ADB / Shell Commands
  if (inline && isAdbOrShell) {
    return (
      <span className="inline-flex items-center gap-1.5 my-0.5 mx-0.5 px-2 py-0.5 rounded-md bg-slate-950 border border-indigo-900/60 font-mono text-xs text-indigo-200 group hover:border-indigo-500/60 transition-colors shadow-sm align-middle">
        <Terminal className="w-3 h-3 text-indigo-400 shrink-0" />
        <span className="select-all font-medium">{rawCode}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="ml-1 p-0.5 rounded text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors shrink-0"
          title={copied ? 'Copied to clipboard!' : 'Copy command'}
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
        </button>
      </span>
    );
  }

  // 2. Regular Inline Code
  if (inline) {
    return (
      <code className="bg-slate-800/80 border border-slate-700/60 px-1.5 py-0.5 rounded text-indigo-300 font-mono text-xs">
        {children}
      </code>
    );
  }

  // 3. Fenced Code Block (Multi-line or Language tagged)
  const langDisplay = detectedLang
    ? detectedLang.toUpperCase()
    : isAdbOrShell
    ? 'BASH'
    : 'CODE';

  const getLangIcon = () => {
    switch (detectedLang) {
      case 'bash':
      case 'sh':
      case 'zsh':
      case 'shell':
        return <Terminal className="w-3.5 h-3.5 text-indigo-400" />;
      case 'json':
      case 'yaml':
      case 'yml':
      case 'xml':
        return <FileCode className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Code2 className="w-3.5 h-3.5 text-emerald-400" />;
    }
  };

  const lines = rawCode.split('\n');

  return (
    <div className="my-3 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-md group">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/90 border-b border-slate-800/80 text-[11px]">
        <div className="flex items-center gap-2">
          {getLangIcon()}
          <span className="font-semibold tracking-wider font-mono text-slate-300">
            {langDisplay}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            {lines.length} {lines.length === 1 ? 'line' : 'lines'}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60 text-[11px] font-medium cursor-pointer"
          title="Copy code snippet"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-slate-400" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Body */}
      <div className="p-3.5 overflow-x-auto text-xs font-mono leading-relaxed text-indigo-100/90 selection:bg-indigo-600/40">
        <pre className="m-0 p-0 bg-transparent border-0 font-mono">
          <code>{rawCode}</code>
        </pre>
      </div>
    </div>
  );
};
