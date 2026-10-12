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
      x: Math.max(50, window.innerWidth - 550),
      y: 80,
      width: 480,
      height: 600
    };
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; startGeomX: number; startGeomY: number }>({
    startX: 0,
    startY: 0,
    startGeomX: 0,
    startGeomY: 0
  });

  // Save geometry changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(geometry));
    } catch (e) {
      // ignore
    }
  }, [geometry]);

  // Handle Dragging
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;

      const newX = Math.max(10, Math.min(window.innerWidth - geometry.width - 10, dragRef.current.startGeomX + dx));
      const newY = Math.max(10, Math.min(window.innerHeight - geometry.height - 10, dragRef.current.startGeomY + dy));

      setGeometry((prev) => ({
        ...prev,
        x: newX,
        y: newY
      }));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, geometry.width, geometry.height]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startGeomX: geometry.x,
      startGeomY: geometry.y
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
      className="fixed z-50 flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl"
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleMouseDown}
        className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800 cursor-move select-none"
      >
        <div className="flex items-center gap-2">
          <Move className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-xs font-semibold text-slate-200">{title}</span>
        </div>

        <div className="flex items-center gap-2">
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
    </div>
  );
};
