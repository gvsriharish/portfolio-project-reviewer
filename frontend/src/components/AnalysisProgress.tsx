import React from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface AnalysisProgressProps {
  stage: string;
  progressPercent: number;
  status: string;
  error?: string | null;
}

const STAGES = [
  { id: 10, label: "Fetching repository & validating safety limits" },
  { id: 25, label: "Scanning files and directory structure" },
  { id: 40, label: "Detecting languages & framework manifests" },
  { id: 55, label: "Executing AST code quality checks" },
  { id: 70, label: "Scanning for secrets and security vulnerabilities" },
  { id: 80, label: "Evaluating README onboarding clarity & docs" },
  { id: 90, label: "Inspecting test coverage & git hygiene" },
  { id: 95, label: "Generating grounded AI recommendations & interview prep" },
];

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  stage,
  progressPercent,
  status,
  error
}) => {
  return (
    <div className="max-w-2xl mx-auto my-12 p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            {status === "FAILED" ? (
              <AlertCircle className="w-5 h-5 text-rose-400" />
            ) : (
              <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            )}
            <span>{status === "FAILED" ? "Analysis Failed" : "Auditing Repository..."}</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">{stage}</p>
        </div>
        <div className="text-xl font-bold font-mono text-indigo-400">
          {progressPercent}%
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden mb-6">
        <div 
          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-300 rounded-full"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          <strong>Error:</strong> {error}
        </div>
      ) : (
        <div className="space-y-2.5">
          {STAGES.map((s) => {
            const isDone = progressPercent >= s.id;
            const isCurrent = progressPercent < s.id && progressPercent >= (s.id - 15);
            return (
              <div 
                key={s.id}
                className={`flex items-center gap-3 text-xs ${
                  isDone ? "text-slate-300" : isCurrent ? "text-indigo-400 font-semibold" : "text-slate-600"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                )}
                <span>{s.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
