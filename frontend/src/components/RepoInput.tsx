import React, { useState } from "react";
import { Search, Sparkles, ArrowRight, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { SampleProjectInfo } from "../types/analysis";

interface RepoInputProps {
  onAnalyze: (url: string) => void;
  samples: SampleProjectInfo[];
  isLoading: boolean;
}

export const RepoInput: React.FC<RepoInputProps> = ({ onAnalyze, samples, isLoading }) => {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Please enter a public GitHub repository URL or select a sample project below.");
      return;
    }
    if (!trimmed.startsWith("sample:") && !trimmed.startsWith("local:") && !trimmed.includes("github.com/")) {
      setError("Please enter a valid GitHub URL (e.g. https://github.com/username/project)");
      return;
    }
    onAnalyze(trimmed);
  };

  return (
    <div className="max-w-4xl mx-auto text-center pt-8 pb-12 px-4">
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-medium mb-6">
        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
        <span>AI-Powered GitHub Project Health & Portfolio Improvement</span>
      </div>

      <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-100 tracking-tight mb-4">
        Turn Your GitHub Repository Into a <br className="hidden sm:inline" />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400">
          Recruiter-Ready Project.
        </span>
      </h1>
      
      <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto mb-8">
        Deterministic static analysis for code quality, security, documentation, testing, architecture and portfolio presentation — paired with grounded AI reasoning.
      </p>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-8">
        <div className="relative flex items-center bg-slate-900 border border-slate-700 rounded-2xl p-2 shadow-2xl focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all">
          <Search className="w-5 h-5 text-slate-400 ml-3 shrink-0" />
          <input
            type="text"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setError(""); }}
            placeholder="https://github.com/username/project"
            disabled={isLoading}
            className="w-full bg-transparent px-3.5 py-2.5 text-sm sm:text-base text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm shadow-md shadow-indigo-600/30 flex items-center gap-2 shrink-0 transition disabled:opacity-50"
          >
            <span>{isLoading ? "Analyzing..." : "Analyze Project"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
        {error && <p className="text-xs text-rose-400 mt-2 text-left px-3">{error}</p>}
      </form>

      <div className="max-w-3xl mx-auto mt-6">
        <div className="text-xs uppercase tracking-wider font-bold text-slate-500 mb-3 text-left">
          Or try instant built-in benchmark projects:
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {samples.map((sample) => (
            <div
              key={sample.id}
              onClick={() => onAnalyze(`sample:${sample.id}`)}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 cursor-pointer text-left transition group shadow-sm"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {sample.id === "bad_project" ? (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  )}
                  <span className="font-semibold text-sm text-slate-200 group-hover:text-indigo-400 transition-colors">
                    {sample.name}
                  </span>
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {sample.expected_score_range}
                </span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                {sample.description}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {sample.key_traits.slice(0, 3).map((trait, i) => (
                  <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/50">
                    {trait}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
