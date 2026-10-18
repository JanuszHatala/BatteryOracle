import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MarkdownCode, MarkdownPre } from './CodeBlock';

interface MarkdownViewProps {
  content: string;
  className?: string;
  compact?: boolean;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({
  content,
  className = '',
  compact = false
}) => {
  if (!content) return null;

  return (
    <div className={`text-slate-200 leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ ...props }) => (
            <h1
              className={`${
                compact ? 'text-base my-2' : 'text-lg md:text-xl mt-5 mb-2.5'
              } font-bold text-slate-100 pb-1.5 border-b border-slate-800 flex items-center gap-2`}
              {...props}
            />
          ),
          h2: ({ ...props }) => (
            <h2
              className={`${
                compact ? 'text-sm my-1.5' : 'text-base md:text-lg mt-4 mb-2'
              } font-bold text-slate-100 flex items-center gap-2`}
              {...props}
            />
          ),
          h3: ({ ...props }) => (
            <h3
              className={`${
                compact ? 'text-xs my-1' : 'text-sm md:text-base mt-3.5 mb-1.5'
              } font-semibold text-slate-200 flex items-center gap-1.5`}
              {...props}
            />
          ),
          h4: ({ ...props }) => (
            <h4
              className={`${
                compact ? 'text-xs my-1' : 'text-xs md:text-sm mt-3 mb-1'
              } font-semibold text-slate-300`}
              {...props}
            />
          ),
          p: ({ ...props }) => (
            <p
              className={`${
                compact ? 'mb-2 text-xs' : 'mb-3 text-xs md:text-sm'
              } text-slate-300 leading-relaxed last:mb-0`}
              {...props}
            />
          ),
          ul: ({ ...props }) => (
            <ul
              className={`list-disc pl-5 space-y-1 my-2.5 text-slate-300 ${
                compact ? 'text-xs' : 'text-xs md:text-sm'
              }`}
              {...props}
            />
          ),
          ol: ({ ...props }) => (
            <ol
              className={`list-decimal pl-5 space-y-1 my-2.5 text-slate-300 ${
                compact ? 'text-xs' : 'text-xs md:text-sm'
              }`}
              {...props}
            />
          ),
          li: ({ ...props }) => (
            <li className="text-slate-300 leading-relaxed" {...props} />
          ),
          table: ({ ...props }) => (
            <div className="overflow-x-auto my-3 rounded-lg border border-slate-800 bg-slate-950/70 shadow-sm">
              <table className="w-full text-left text-xs border-collapse" {...props} />
            </div>
          ),
          thead: ({ ...props }) => (
            <thead className="bg-slate-900/90 text-slate-200 font-semibold border-b border-slate-800" {...props} />
          ),
          tbody: ({ ...props }) => (
            <tbody className="divide-y divide-slate-800/60 bg-slate-950/40" {...props} />
          ),
          tr: ({ ...props }) => (
            <tr className="hover:bg-slate-900/40 transition-colors" {...props} />
          ),
          th: ({ ...props }) => (
            <th
              className="px-3.5 py-2.5 text-slate-200 font-semibold text-xs tracking-wider border-r border-slate-800 last:border-r-0 whitespace-nowrap"
              {...props}
            />
          ),
          td: ({ ...props }) => (
            <td
              className="px-3.5 py-2 text-slate-300 text-xs border-r border-slate-800/40 last:border-r-0 leading-relaxed align-top"
              {...props}
            />
          ),
          blockquote: ({ ...props }) => (
            <blockquote
              className="border-l-2 border-indigo-500 bg-indigo-950/20 px-3.5 py-2 my-2.5 rounded-r-lg text-slate-300 italic text-xs md:text-sm"
              {...props}
            />
          ),
          hr: ({ ...props }) => (
            <hr className="my-4 border-slate-800" {...props} />
          ),
          strong: ({ ...props }) => (
            <strong className="font-semibold text-slate-100" {...props} />
          ),
          em: ({ ...props }) => (
            <em className="italic text-slate-200" {...props} />
          ),
          a: ({ ...props }) => (
            <a
              className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
          code: MarkdownCode,
          pre: MarkdownPre
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
