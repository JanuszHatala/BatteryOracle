import React, { useState, useRef, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check, Search } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface SelectOption {
  value: string;
  label: string;
  badge?: string;
  disabled?: boolean;
}

export interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  menuClassName?: string;
  size?: 'sm' | 'md';
  searchable?: boolean;
  'aria-label'?: string;
}

export const Select: React.FC<SelectProps> = ({
  value,
  onChange,
  options,
  placeholder = 'Select...',
  disabled = false,
  className,
  menuClassName,
  size = 'md',
  searchable,
  'aria-label': ariaLabel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
    width: number;
    openUpward: boolean;
  }>({ top: 0, left: 0, width: 0, openUpward: false });

  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const isSearchable = searchable ?? options.length > 10;

  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  );

  const filteredOptions = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(q) ||
        opt.value.toLowerCase().includes(q) ||
        (opt.badge && opt.badge.toLowerCase().includes(q))
    );
  }, [options, query]);

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const estimatedMenuHeight = Math.min(options.length * 36 + (isSearchable ? 44 : 12), 296);
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const openUpward = spaceBelow < estimatedMenuHeight && spaceAbove > spaceBelow;

    setCoords({
      top: openUpward ? rect.top - 6 : rect.bottom + 6,
      left: rect.left,
      width: Math.max(rect.width, 200),
      openUpward,
    });
  };

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setHighlightedIndex(-1);
      return;
    }

    updatePosition();

    const idx = filteredOptions.findIndex((o) => o.value === value);
    setHighlightedIndex(idx >= 0 ? idx : 0);

    if (isSearchable) {
      requestAnimationFrame(() => searchInputRef.current?.focus());
    }

    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        menuRef.current?.contains(target)
      ) {
        return;
      }
      setIsOpen(false);
    };

    const handleScrollOrResize = (e: Event) => {
      if (menuRef.current && menuRef.current.contains(e.target as Node)) {
        return;
      }
      updatePosition();
    };

    document.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('resize', handleScrollOrResize);
    window.addEventListener('scroll', handleScrollOrResize, true);

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('scroll', handleScrollOrResize, true);
    };
  }, [isOpen]);

  const handleSelect = (opt: SelectOption) => {
    if (opt.disabled) return;
    onChange(opt.value);
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      e.nativeEvent.stopImmediatePropagation();
      setIsOpen(false);
      triggerRef.current?.focus();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        filteredOptions.length === 0 ? -1 : (prev + 1) % filteredOptions.length
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        filteredOptions.length === 0
          ? -1
          : (prev - 1 + filteredOptions.length) % filteredOptions.length
      );
    } else if (e.key === 'Enter' && highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
      e.preventDefault();
      handleSelect(filteredOptions[highlightedIndex]);
    }
  };

  const sizeClasses =
    size === 'sm' ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-xs';

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className={twMerge(
          clsx(
            'w-full flex items-center justify-between gap-2.5 bg-slate-950/90 border border-slate-800 hover:border-slate-700 rounded-lg text-slate-200 transition-colors focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 disabled:opacity-50 disabled:cursor-not-allowed',
            isOpen && 'border-indigo-500 ring-1 ring-indigo-500/40',
            sizeClasses,
            className
          )
        )}
      >
        <span className={clsx('truncate text-left flex-1 min-w-0', !selectedOption && 'text-slate-500')}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown
          className={clsx(
            'w-4 h-4 text-slate-400 shrink-0 transition-transform duration-150',
            isOpen && 'rotate-180 text-indigo-400'
          )}
        />
      </button>

      {isOpen &&
        createPortal(
          <div
            ref={menuRef}
            onKeyDown={handleKeyDown}
            style={{
              position: 'fixed',
              left: coords.left,
              width: coords.width,
              ...(coords.openUpward
                ? { bottom: window.innerHeight - coords.top }
                : { top: coords.top }),
            }}
            className={twMerge(
              clsx(
                'z-[100] bg-slate-900 border border-slate-700/90 rounded-xl shadow-2xl shadow-black/70 overflow-hidden flex flex-col max-h-72',
                menuClassName
              )
            )}
          >
            {isSearchable && (
              <div className="p-2 border-b border-slate-800 bg-slate-950/50">
                <div className="relative flex items-center">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 pointer-events-none" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setHighlightedIndex(0);
                    }}
                    placeholder="Filter options..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            )}

            <div className="overflow-y-auto py-1">
              {filteredOptions.length === 0 ? (
                <div className="px-3 py-4 text-center text-xs text-slate-500">
                  No matching options
                </div>
              ) : (
                filteredOptions.map((opt, index) => {
                  const isSelected = opt.value === value;
                  const isHighlighted = index === highlightedIndex;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      disabled={opt.disabled}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      onClick={() => handleSelect(opt)}
                      className={clsx(
                        'w-full flex items-center justify-between gap-2.5 px-3 py-2 text-xs text-left transition-colors',
                        isSelected
                          ? 'bg-indigo-600/20 text-indigo-200 font-medium'
                          : isHighlighted
                          ? 'bg-slate-800/80 text-slate-100'
                          : 'text-slate-300 hover:bg-slate-800/70',
                        opt.disabled && 'opacity-40 cursor-not-allowed'
                      )}
                    >
                      <span className="truncate flex-1 min-w-0">{opt.label}</span>
                      <span className="flex items-center gap-2 shrink-0">
                        {opt.badge && (
                          <span className="text-[11px] font-mono text-slate-400">
                            {opt.badge}
                          </span>
                        )}
                        {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  );
};
