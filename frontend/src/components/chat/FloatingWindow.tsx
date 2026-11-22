import React, { useState, useEffect, useRef } from 'react';
import { X, Dock, Move } from 'lucide-react';

interface FloatingWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onDock: () => void;
  title: string;
  children: React.ReactNode;
}

interface WindowGeometry {
  x: number;
  y: number;
  width: number;
  height: number;
}

const STORAGE_KEY = 'battery_oracle_floating_chat_geom';

export const FloatingWindow: React.FC<FloatingWindowProps> = ({
  isOpen,
  onClose,
  onDock,
  title,
  children
}) => {
  const [geometry, setGeometry] = useState<WindowGeometry>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      // ignore
    }
    return {
      x: Math.max(50, window.innerWidth - 560),
      y: 80,
      width: 520,
      height: 640
    };
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; startGeomX: number; startGeomY: number }>({
    startX: 0,
    startY: 0,
    startGeomX: 0,
    startGeomY: 0
  });

  const [isResizing, setIsResizing] = useState<'se' | 'e' | 's' | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; startW: number; startH: number }>({
    startX: 0,
    startY: 0,
    startW: 0,
    startH: 0
  });

  // Save geometry changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(geometry));
    } catch (e) {
      // ignore
    }
  }, [geometry]);

  // Handle Dragging and Resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const dx = e.clientX - dragRef.current.startX;
        const dy = e.clientY - dragRef.current.startY;

        const newX = Math.max(10, Math.min(window.innerWidth - geometry.width - 10, dragRef.current.startGeomX + dx));
        const newY = Math.max(10, Math.min(window.innerHeight - geometry.height - 10, dragRef.current.startGeomY + dy));

        setGeometry((prev) => ({
          ...prev,
          x: newX,
          y: newY
        }));
      } else if (isResizing) {
        const dx = e.clientX - resizeRef.current.startX;
        const dy = e.clientY - resizeRef.current.startY;

        let newW = resizeRef.current.startW;
        let newH = resizeRef.current.startH;

        if (isResizing === 'se' || isResizing === 'e') {
          newW = Math.max(380, Math.min(window.innerWidth - geometry.x - 20, resizeRef.current.startW + dx));
        }
        if (isResizing === 'se' || isResizing === 's') {
          newH = Math.max(400, Math.min(window.innerHeight - geometry.y - 20, resizeRef.current.startH + dy));
        }

        setGeometry((prev) => ({
          ...prev,
          width: newW,
          height: newH
        }));
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(null);
    };

    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, geometry.x, geometry.y, geometry.width, geometry.height]);

  const handleDragMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startGeomX: geometry.x,
      startGeomY: geometry.y
    };
  };

  const handleResizeMouseDown = (e: React.MouseEvent, dir: 'se' | 'e' | 's') => {
    e.stopPropagation();
    setIsResizing(dir);
    resizeRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startW: geometry.width,
      startH: geometry.height
    };
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        left: `${geometry.x}px`,
        top: `${geometry.y}px`,
        width: `${geometry.width}px`,
        height: `${geometry.height}px`
      }}
      className="fixed z-50 flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100"
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleDragMouseDown}
        className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800 cursor-move select-none"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Move className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <span className="text-xs font-semibold text-slate-200 truncate">{title}</span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onDock}
            className="text-slate-400 hover:text-indigo-300 p-1 rounded hover:bg-slate-800 transition-colors flex items-center gap-1 text-[11px]"
            title="Dock to workspace layout"
          >
            <Dock className="w-3.5 h-3.5" />
            <span className="text-xs">Dock</span>
          </button>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition-colors"
            title="Close window"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Window Body */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0 bg-slate-950/40">
        {children}
      </div>

      {/* Right Edge Resize Handle */}
      <div
        onMouseDown={(e) => handleResizeMouseDown(e, 'e')}
        className="absolute top-0 right-0 w-2 h-full cursor-ew-resize hover:bg-indigo-500/20 transition-colors"
        title="Resize width"
      />

      {/* Bottom Edge Resize Handle */}
      <div
        onMouseDown={(e) => handleResizeMouseDown(e, 's')}
        className="absolute bottom-0 left-0 w-full h-2 cursor-ns-resize hover:bg-indigo-500/20 transition-colors"
        title="Resize height"
      />

      {/* Bottom-Right Corner Resize Grip Handle */}
      <div
        onMouseDown={(e) => handleResizeMouseDown(e, 'se')}
        className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize flex items-end justify-end p-0.5 hover:bg-indigo-500/30 rounded-br-2xl transition-colors group z-10"
        title="Resize window"
      >
        <svg
          viewBox="0 0 6 6"
          className="w-2.5 h-2.5 text-slate-600 group-hover:text-indigo-400 fill-current"
        >
          <path d="M6 6H0L6 0V6Z" />
        </svg>
      </div>
    </div>
  );
};
