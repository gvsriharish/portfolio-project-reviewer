import React from "react";
import type { ProjectExplanation } from "../types/analysis";
import { BookOpen, Layers, GitFork, CheckCircle, AlertTriangle } from "lucide-react";

interface ExplainProjectViewProps {
  explanation?: ProjectExplanation | null;
}

export const ExplainProjectView: React.FC<ExplainProjectViewProps> = ({ explanation }) => {
  if (!explanation) {
    return (
      <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 text-slate-500">
        No project explanation generated. Re-run analysis with AI reasoning enabled.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-400" />
          <h3 className="text-lg font-bold text-slate-100">Project Overview</h3>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{explanation.summary}</p>
        <div className="pt-3 border-t border-slate-800 text-xs text-slate-400 leading-relaxed">
          <strong className="text-slate-300">Architecture Narrative:</strong> {explanation.architecture_narrative}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
          <Layers className="w-4 h-4 text-indigo-400" />
          <span>Observed & Inferred System Components</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {explanation.main_components.map((comp, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-slate-100">{comp.name}</span>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                  comp.status === 'OBSERVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                }`}>
                  {comp.status}
                </span>
              </div>
              <div className="text-xs text-indigo-400 font-mono">{comp.path}</div>
              <p className="text-xs text-slate-400">{comp.details}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2">
          <GitFork className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">End-to-End Data Flow</h3>
        </div>
        <div className="space-y-2.5">
          {explanation.data_flow.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3 text-xs text-slate-300">
              <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-[11px] shrink-0 font-mono">
                {idx + 1}
              </span>
              <span className="leading-relaxed">{step}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-400">
            <CheckCircle className="w-4 h-4" />
            <span>Key Technical Decisions</span>
          </div>
          <ul className="space-y-2 text-xs text-slate-300 list-disc list-inside">
            {explanation.technical_decisions.map((dec, i) => (
              <li key={i}>{dec}</li>
            ))}
          </ul>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-400">
            <AlertTriangle className="w-4 h-4" />
            <span>Limitations & Scalability Trade-offs</span>
          </div>
          <ul className="space-y-2 text-xs text-slate-400 list-disc list-inside">
            {explanation.limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
