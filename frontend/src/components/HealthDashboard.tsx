import React, { useState } from "react";
import type { AnalysisResponse } from "../types/analysis";
import { 
  ShieldAlert, Code, BookOpen, FlaskConical, Layers, 
  Package, GitBranch, Briefcase, ChevronDown, ChevronUp
} from "lucide-react";

interface HealthDashboardProps {
  analysis: AnalysisResponse;
  onSelectCategory: (cat: string) => void;
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  "Code Quality": <Code className="w-5 h-5 text-sky-400" />,
  "Security": <ShieldAlert className="w-5 h-5 text-rose-400" />,
  "Documentation": <BookOpen className="w-5 h-5 text-amber-400" />,
  "Testing": <FlaskConical className="w-5 h-5 text-emerald-400" />,
  "Architecture": <Layers className="w-5 h-5 text-violet-400" />,
  "Dependencies": <Package className="w-5 h-5 text-pink-400" />,
  "Git Hygiene": <GitBranch className="w-5 h-5 text-indigo-400" />,
  "Portfolio Readiness": <Briefcase className="w-5 h-5 text-teal-400" />
};

export const HealthDashboard: React.FC<HealthDashboardProps> = ({ analysis, onSelectCategory }) => {
  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  const getScoreColor = (score: number) => {
    if (score >= 85) return "text-emerald-400 stroke-emerald-400";
    if (score >= 65) return "text-amber-400 stroke-amber-400";
    return "text-rose-400 stroke-rose-400";
  };

  const getScoreBg = (score: number) => {
    if (score >= 85) return "bg-emerald-500/10 border-emerald-500/20 text-emerald-300";
    if (score >= 65) return "bg-amber-500/10 border-amber-500/20 text-amber-300";
    return "bg-rose-500/10 border-rose-500/20 text-rose-300";
  };

  const criticals = analysis.findings.filter(f => f.severity === "CRITICAL").length;
  const highs = analysis.findings.filter(f => f.severity === "HIGH").length;
  const mediums = analysis.findings.filter(f => f.severity === "MEDIUM").length;
  const lows = analysis.findings.filter(f => f.severity === "LOW" || f.severity === "INFO").length;

  return (
    <div className="space-y-8">
      {/* Top Banner: Overall Score & Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
        {/* Score Gauge */}
        <div className="flex flex-col items-center justify-center p-4 border-b lg:border-b-0 lg:border-r border-slate-800">
          <div className="relative w-36 h-36 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50" cy="50" r="40"
                className="stroke-slate-800"
                strokeWidth="8"
                fill="transparent"
              />
              <circle
                cx="50" cy="50" r="40"
                className={getScoreColor(analysis.overall_score)}
                strokeWidth="8"
                strokeDasharray="251.2"
                strokeDashoffset={251.2 - (251.2 * analysis.overall_score) / 100}
                strokeLinecap="round"
                fill="transparent"
                style={{ transition: "stroke-dashoffset 1s ease" }}
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className={`text-3xl font-extrabold font-mono ${getScoreColor(analysis.overall_score).split(' ')[0]}`}>
                {analysis.overall_score}
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500">out of 100</span>
            </div>
          </div>
          <div className="mt-3 text-center">
            <div className="text-sm font-bold text-slate-200">Overall Project Health</div>
            <p className="text-[11px] text-slate-400 mt-0.5">Calculated from transparent documented rules</p>
          </div>
        </div>

        {/* Repository Specs */}
        <div className="lg:col-span-2 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                {analysis.owner} / {analysis.repo_name}
              </span>
              {analysis.is_sample && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  DEMO BENCHMARK
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-100">{analysis.repo_name}</h2>
            <p className="text-xs text-slate-400 mt-1">
              Analysis completed in <span className="text-slate-200 font-mono">{analysis.duration_seconds}s</span>.
            </p>
          </div>

          {/* Languages & Frameworks */}
          <div className="flex flex-wrap gap-2">
            {analysis.languages.map((lang) => (
              <span key={lang} className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 font-medium border border-slate-700">
                {lang}
              </span>
            ))}
            {analysis.frameworks.map((fw) => (
              <span key={fw} className="text-xs px-2.5 py-1 rounded-lg bg-indigo-950/60 text-indigo-300 font-medium border border-indigo-800/40">
                {fw}
              </span>
            ))}
          </div>

          {/* Finding Counters */}
          <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-800/80">
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-center">
              <div className="text-base font-bold text-rose-400 font-mono">{criticals}</div>
              <div className="text-[10px] font-bold text-rose-300 uppercase">Critical</div>
            </div>
            <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/20 text-center">
              <div className="text-base font-bold text-orange-400 font-mono">{highs}</div>
              <div className="text-[10px] font-bold text-orange-300 uppercase">High</div>
            </div>
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-center">
              <div className="text-base font-bold text-amber-400 font-mono">{mediums}</div>
              <div className="text-[10px] font-bold text-amber-300 uppercase">Medium</div>
            </div>
            <div className="p-2 rounded-lg bg-slate-800 text-center border border-slate-700">
              <div className="text-base font-bold text-slate-300 font-mono">{lows}</div>
              <div className="text-[10px] font-bold text-slate-400 uppercase">Low / Info</div>
            </div>
          </div>
        </div>
      </div>

      {/* 8 Category Cards Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-slate-200">Category Breakdown & Score Deductions</h3>
          <span className="text-xs text-slate-400">Click any card to inspect penalties or view findings</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(analysis.category_scores).map(([category, scoreData]) => {
            const isExpanded = expandedCat === category;
            return (
              <div
                key={category}
                className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
                      {CATEGORY_ICONS[category] || <Layers className="w-5 h-5 text-slate-400" />}
                    </div>
                    <span className={`text-base font-bold font-mono px-2.5 py-0.5 rounded-md border ${getScoreBg(scoreData.score)}`}>
                      {scoreData.score}/100
                    </span>
                  </div>

                  <h4 className="font-semibold text-sm text-slate-200 group-hover:text-indigo-400 transition-colors">
                    {category}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {scoreData.summary}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800">
                  <div className="flex items-center justify-between text-xs">
                    <button
                      onClick={() => onSelectCategory(category)}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      {scoreData.findings_count} finding{scoreData.findings_count === 1 ? '' : 's'} &rarr;
                    </button>

                    {scoreData.penalty_breakdown.length > 0 && (
                      <button
                        onClick={() => setExpandedCat(isExpanded ? null : category)}
                        className="text-slate-500 hover:text-slate-400 flex items-center gap-1"
                      >
                        <span>Penalties</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>

                  {isExpanded && scoreData.penalty_breakdown.length > 0 && (
                    <div className="mt-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-rose-300/90 space-y-1">
                      {scoreData.penalty_breakdown.map((p, i) => (
                        <div key={i} className="font-mono">{p}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
