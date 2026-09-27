import { useState, useEffect } from "react";
import type { ClaimSummary, Claim } from "../types/analysis";
import { getClaims, API_BASE } from "../services/api";
import {
  CheckCircle2, AlertTriangle, HelpCircle, XCircle, ShieldCheck,
} from "lucide-react";

const STATUS_META: Record<string, { color: string; icon: any }> = {
  SUPPORTED: { color: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10", icon: CheckCircle2 },
  PARTIALLY_SUPPORTED: { color: "text-amber-400 border-amber-500/40 bg-amber-500/10", icon: AlertTriangle },
  UNVERIFIED: { color: "text-slate-400 border-slate-600 bg-slate-800/60", icon: HelpCircle },
  CONTRADICTED: { color: "text-rose-400 border-rose-500/40 bg-rose-500/10", icon: XCircle },
};

const CATEGORIES = ["ALL", "TECHNOLOGY", "ARCHITECTURE", "SECURITY", "TESTING", "DEPLOYMENT", "DATABASE", "AI_ML", "API", "PERFORMANCE", "QUALITY", "OTHER"];
const STATUSES = ["ALL", "SUPPORTED", "PARTIALLY_SUPPORTED", "UNVERIFIED", "CONTRADICTED"];

interface ClaimAuditorProps {
  analysisId: string;
}

export const ClaimAuditor: React.FC<ClaimAuditorProps> = ({ analysisId }) => {
  const [result, setResult] = useState<{ analysisId: string; data: ClaimSummary | null; loading: boolean }>({
    analysisId, data: null, loading: true,
  });
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Claim | null>(null);

  useEffect(() => {
    let active = true;
    getClaims(analysisId)
      .then((d) => {
        if (active) setResult({ analysisId, data: d, loading: false });
      })
      .catch(() => {
        if (active) setResult({ analysisId, data: null, loading: false });
      });
    return () => { active = false; };
  }, [analysisId]);

  const loading = result.analysisId !== analysisId || result.loading;
  const data = result.analysisId === analysisId ? result.data : null;

  const openClaim = async (c: Claim) => {
    setSelected(c);
    // Lazily fetch the full detail (evidence + related findings) on click.
    try {
      const res = await fetch(`${API_BASE}/analysis/${analysisId}/claims/${c.id}`);
      if (res.ok) setSelected(await res.json());
    } catch { /* keep summary view */ }
  };

  if (loading) return <div className="text-slate-400 text-sm p-6">Loading claim audit…</div>;
  if (!data) return <div className="text-slate-400 text-sm p-6">No claim data available for this analysis.</div>;

  const { stats } = data;
  const claims = data.claims.filter((c) =>
    (statusFilter === "ALL" || c.status === statusFilter) &&
    (categoryFilter === "ALL" || c.category === categoryFilter) &&
    (!search || c.claim_text.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: "Claims analyzed", value: stats.total, cls: "text-slate-100" },
          { label: "Supported", value: stats.supported, cls: "text-emerald-400" },
          { label: "Partially supported", value: stats.partially_supported, cls: "text-amber-400" },
          { label: "Unverified", value: stats.unverified, cls: "text-slate-400" },
          { label: "Contradicted", value: stats.contradicted, cls: "text-rose-400" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className={`text-2xl font-bold ${s.cls}`}>{s.value}</div>
            <div className="text-xs text-slate-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg text-xs px-3 py-2">
          {STATUSES.map((s) => <option key={s} value={s}>{s === "ALL" ? "All statuses" : s.replace(/_/g, " ")}</option>)}
        </select>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg text-xs px-3 py-2">
          {CATEGORIES.map((c) => <option key={c} value={c}>{c === "ALL" ? "All categories" : c.replace(/_/g, " ")}</option>)}
        </select>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search claims…"
          className="bg-slate-900 border border-slate-700 rounded-lg text-xs px-3 py-2 flex-1 min-w-[200px]" />
      </div>

      <div className="space-y-2">
        {claims.map((c) => {
          const meta = STATUS_META[c.status] ?? STATUS_META.UNVERIFIED;
          const Icon = meta.icon;
          return (
            <button key={c.id} onClick={() => openClaim(c)}
              className="w-full text-left rounded-xl border border-slate-800 bg-slate-900 hover:border-indigo-500/50 transition p-4">
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${meta.color.split(" ")[0]}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-100">{c.claim_text}</div>
                  <div className="flex flex-wrap gap-2 mt-2 text-[11px]">
                    <span className={`px-2 py-0.5 rounded border ${meta.color}`}>{c.status.replace(/_/g, " ")}</span>
                    <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-400">{c.category.replace(/_/g, " ")}</span>
                    <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-400">Confidence: {c.confidence}</span>
                    <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-400">Evidence: {c.evidence_count}</span>
                    {c.source_file && (
                      <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-500">
                        {c.source_file}{c.source_line ? `:${c.source_line}` : ""}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
        {claims.length === 0 && (
          <div className="text-sm text-slate-500 p-6 border border-slate-800 rounded-xl">
            No claims match the current filters.
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={() => setSelected(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-indigo-400" />
              <h3 className="text-sm font-semibold text-slate-100">Claim Verification Detail</h3>
            </div>
            <p className="text-sm text-slate-100">"{selected.claim_text}"</p>
            <div className="text-xs text-slate-400">
              Source: {selected.source_file}{selected.source_line ? `:${selected.source_line}` : ""} · Category: {selected.category} · Status: {selected.status} · Confidence: {selected.confidence}
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-1">Deterministic explanation</div>
              <p className="text-xs text-slate-400">{selected.explanation || "Evidence not detected."}</p>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-1">Repository evidence ({selected.evidence_items?.length ?? 0})</div>
              {(selected.evidence_items ?? []).length === 0 && <p className="text-xs text-slate-500">Evidence not detected.</p>}
              <ul className="space-y-1">
                {(selected.evidence_items ?? []).map((ev) => (
                  <li key={ev.id} className="text-xs text-slate-400 bg-slate-800/60 rounded p-2">
                    <span className="text-indigo-300">{ev.evidence_type}</span> · {ev.source_file || "project-level"}{ev.source_line ? `:${ev.source_line}` : ""} — {ev.evidence_summary}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-1">Related findings ({selected.related_findings?.length ?? 0})</div>
              {(selected.related_findings ?? []).length === 0 && <p className="text-xs text-slate-500">No findings linked to this claim.</p>}
              <ul className="space-y-1">
                {(selected.related_findings ?? []).map((f) => (
                  <li key={f.id} className="text-xs text-slate-400 bg-slate-800/60 rounded p-2">
                    <span className="text-rose-300">{f.severity}</span> · {f.title} ({f.file_path})
                  </li>
                ))}
              </ul>
            </div>
            <button onClick={() => setSelected(null)}
              className="text-xs px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};
