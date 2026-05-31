"use client";

import type { ReactNode } from "react";

interface AeroWindowProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function AeroWindow({ title, children, className = "" }: AeroWindowProps) {
  return (
    <div className={`aero-window w-full ${className}`}>
      <div className="aero-title-bar">
        <div className="flex items-center gap-2 min-w-0">
          <span className="aero-title-icon" aria-hidden="true" />
          <span className="aero-title-bar-text">{title}</span>
        </div>
        <div className="aero-title-bar-controls">
          <button type="button" aria-label="Minimize">
            _
          </button>
          <button type="button" aria-label="Maximize">
            ◻
          </button>
          <button type="button" aria-label="Close" className="close">
            ×
          </button>
        </div>
      </div>
      <div className="aero-window-body">{children}</div>
    </div>
  );
}
