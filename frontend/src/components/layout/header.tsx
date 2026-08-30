"use client";

import { Video } from "lucide-react";

export function Header() {
  return (
    <header className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-4 shrink-0 z-20 relative">
      <div className="flex items-center gap-2">
        <Video className="w-5 h-5 text-slate-700" />
        <h1 className="text-sm font-bold text-slate-800 tracking-tight">Video Intel Dashboard</h1>
      </div>
    </header>
  );
}
