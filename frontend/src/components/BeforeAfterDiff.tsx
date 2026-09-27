import React, { useState } from "react";
import type { ComparisonResponse } from "../types/analysis";
import { compareAnalyses, analyzeRepository } from "../services/api";
import { ArrowRight, TrendingUp, RefreshCw } from "lucide-react";

interface BeforeAfterDiffProps {
  currentAnalysisId: string;
}

export const BeforeAfterDiff: React.FC<BeforeAfterDiffProps> = ({ currentAnalysisId }) => {
  const [beforeId, setBeforeId] = useState("");
  const [afterId, setAfterId] = useState(currentAnalysisId);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = async (bId?: string, aId?: string) => {
    const b = bId || beforeId;
    const a = aId || afterId;
    if (!b || !a) {
      setError("Please specify both Before and After Analysis IDs.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await compareAnalyses(b, a);
      setComparison(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to compare analyses");
    } finally {
      setLoading(false);
    }
  };

  const loadBenchmarkSampleComparison = async () => {
    setLoading(true);
    setError("");
    try {
      const badRes = await analyzeRepository("sample:bad_project", false);
      const goodRes = await analyzeRepository("sample:improved_project", false);
      setBeforeId(badRes.id);
      setAfterId(goodRes.id);
      await handleCompare(badRes.id, goodRes.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load sample comparison";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100">Before vs. After Comparison</h3>
          <p className="text-xs text-slate-400 mt-1">
            Validate actual measurable score improvements and resolved findings across two analysis runs.
          </p>
        </div>
        <button
          onClick={loadBenchmarkSampleComparison}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Load Benchmark Comparison Demo</span>
        </button>
      </div>

      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1">Before Analysis ID</label>
          <input
            type="text"
            value={beforeId}
            onChange={(e) => setBeforeId(e.target.value)}
            placeholder="e.g. 5a1b..."
            className="w-full px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-700 text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1">After Analysis ID</label>
          <input
            type="text"
            value={afterId}
            onChange={(e) => setAfterId(e.target.value)}
            placeholder="e.g. 9c2f..."
            className="w-full px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-700 text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={() => handleCompare()}
            disabled={loading}
            className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 transition"
          >
            {loading ? "Comparing..." : "Compare Runs"}
          </button>
        </div>
      </div>

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {comparison && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 to-indigo-950 border border-indigo-900/40 shadow-xl flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-xs uppercase font-bold text-slate-400">Before</div>
                <div className="text-3xl font-extrabold font-mono text-slate-300">{comparison.overall_score_before}</div>
              </div>

              <ArrowRight className="w-6 h-6 text-indigo-400" />

              <div className="text-center">
                <div className="text-xs uppercase font-bold text-slate-400">After</div>
                <div className="text-3xl font-extrabold font-mono text-emerald-400">{comparison.overall_score_after}</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold font-mono text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                <span>+{comparison.overall_score_delta} pts</span>
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-300 font-medium">{comparison.summary}</p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(comparison.category_deltas).map(([cat, deltaData]) => (
              <div key={cat} className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <div className="text-xs font-semibold text-slate-300 truncate">{cat}</div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs font-mono text-slate-400">{deltaData.before_score} &rarr; {deltaData.after_score}</span>
                  <span className={`text-xs font-bold font-mono ${deltaData.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {deltaData.delta >= 0 ? `+${deltaData.delta}` : deltaData.delta}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {[
            ["Resolved", comparison.resolved_findings, "text-emerald-400", "RESOLVED"],
            ["Still Present", comparison.persistent_findings, "text-amber-400", "STILL_PRESENT"],
            ["New", comparison.new_findings, "text-rose-400", "NEW"],
            ["Changed", comparison.changed_findings || [], "text-sky-400", "CHANGED"],
          ].map(([label, items, tone, status]) => (
            <div className="space-y-3" key={String(status)}>
              <h4 className={`text-sm font-bold ${tone}`}>{String(label)} ({(items as any[]).length})</h4>
              <div className="space-y-2">
                {(items as any[]).map((f) => (
                  <div key={f.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-200 font-medium">{f.title}</span>
                      <span className="text-slate-500 font-mono">{f.file_path}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-slate-500 font-mono">
                      <span>key: {f.finding_key || "legacy"}</span>
                      <span>severity: {f.before_severity || "—"} → {f.after_severity || "—"}</span>
                      <span>match: {f.match_method || "—"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-200">Verification Results ({(comparison.verification_results || []).length})</h4>
            <div className="space-y-2">
              {(comparison.verification_results || []).map((v) => (
                <div key={v.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-bold">{v.result}</span>
                    <span className="font-mono text-slate-500">{v.finding_key}</span>
                  </div>
                  <p className="mt-1 text-slate-400">{v.details}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
