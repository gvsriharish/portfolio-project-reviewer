import React from "react";
import { ShieldCheck, Sparkles } from "lucide-react";

interface NavbarProps {
  onSelfReview: () => void;
  onReset: () => void;
  isAnalyzing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onSelfReview, onReset, isAnalyzing }) => {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-900/80 border-b border-slate-800 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div 
          onClick={onReset}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-100 tracking-tight">Portfolio Project Reviewer</span>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Turn Your GitHub Repository Into a Recruiter-Ready Project</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onSelfReview}
            disabled={isAnalyzing}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition disabled:opacity-50"
            title="Analyze this application's own codebase"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Self-Review Demo</span>
          </button>
        </div>
      </div>
    </header>
  );
};
