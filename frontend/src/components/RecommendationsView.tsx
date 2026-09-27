import React from "react";
import type { Recommendation } from "../types/analysis";
import { AlertOctagon, Zap, Sparkles } from "lucide-react";

interface RecommendationsViewProps {
  recommendations: Recommendation[];
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({ recommendations }) => {
  const fixFirst = recommendations.filter((r) => r.priority_group === "Fix First");
  const improveNext = recommendations.filter((r) => r.priority_group === "Improve Next");
  const portfolioImpr = recommendations.filter((r) => r.priority_group === "Portfolio Improvements");

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-xl font-bold text-slate-100">Prioritized Action Roadmap</h3>
        <p className="text-xs text-slate-400 mt-1">
          A step-by-step engineering roadmap generated from repository evidence to make your project recruiter-ready.
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-rose-400 uppercase tracking-wider">
          <AlertOctagon className="w-4 h-4" />
          <span>1. Fix First (Critical Security & Correctness Gaps)</span>
        </div>
        <div className="space-y-3">
          {fixFirst.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              ✓ No critical or high severity blockers found!
            </div>
          ) : (
            fixFirst.map((rec) => (
              <div key={rec.id} className="p-4 rounded-xl bg-slate-900 border border-rose-900/30 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 text-xs flex items-center justify-center font-mono">
                      {rec.rank}
                    </span>
                    <span>{rec.title}</span>
                  </h4>
                </div>
                <p className="text-xs text-slate-300"><strong>Action:</strong> {rec.action}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                  <div><strong>Why:</strong> {rec.reason}</div>
                  <div><strong>Verification:</strong> {rec.verification}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-amber-400 uppercase tracking-wider">
          <Zap className="w-4 h-4" />
          <span>2. Improve Next (Engineering Hygiene & Test Coverage)</span>
        </div>
        <div className="space-y-3">
          {improveNext.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              ✓ No medium-priority improvements identified.
            </div>
          ) : (
            improveNext.map((rec) => (
              <div key={rec.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 text-xs flex items-center justify-center font-mono">
                    {rec.rank}
                  </span>
                  <span>{rec.title}</span>
                </h4>
                <p className="text-xs text-slate-300"><strong>Action:</strong> {rec.action}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                  <div><strong>Why:</strong> {rec.reason}</div>
                  <div><strong>Verification:</strong> {rec.verification}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-indigo-400 uppercase tracking-wider">
          <Sparkles className="w-4 h-4" />
          <span>3. Portfolio Polish (Recruiter Presentation & Visuals)</span>
        </div>
        <div className="space-y-3">
          {portfolioImpr.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              No portfolio polish items generated. Run analysis with AI enabled to get recruiter-ready suggestions.
            </div>
          ) : (
            portfolioImpr.map((rec) => (
              <div key={rec.id} className="p-4 rounded-xl bg-slate-900 border border-indigo-900/30 space-y-2">
                <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs flex items-center justify-center font-mono">
                    {rec.rank}
                  </span>
                  <span>{rec.title}</span>
                </h4>
                <p className="text-xs text-slate-300"><strong>Action:</strong> {rec.action}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                  <div><strong>Why:</strong> {rec.reason}</div>
                  <div><strong>Verification:</strong> {rec.verification}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
