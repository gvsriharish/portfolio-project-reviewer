import { useState, useEffect } from "react";
import { getTrustReport } from "../services/api";
import { API_BASE } from "../services/api";
import type { TrustReport } from "../types/analysis";
import { FileBadge, Download } from "lucide-react";

interface TrustReportViewProps {
  analysisId: string;
}

interface SectionProps {
  id: string;
  title: string;
  children: React.ReactNode;
  open: string | null;
  onToggle: (id: string) => void;
}

// Declared outside the parent component to avoid re-creation on every render.
function Section({ id, title, children, open, onToggle }: SectionProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
      <button
        onClick={() => onToggle(id)}
        className="w-full text-left px-4 py-3 text-sm font-semibold text-slate-100 flex items-center justify-between hover:bg-slate-800/50"
      >
        {title}
        <span className="text-slate-500 text-xs">{open === id ? "−" : "+"}</span>
      </button>
      {open === id && (
        <div className="px-4 pb-4 text-xs text-slate-300 space-y-2">{children}</div>
      )}
    </div>
  );
}

export const TrustReportView: React.FC<TrustReportViewProps> = ({ analysisId }) => {
  const [result, setResult] = useState<{ analysisId: string; report: TrustReport | null; loading: boolean; error: boolean }>({
    analysisId, report: null, loading: true, error: false,
  });
  const [open, setOpen] = useState<string | null>("claims");

  useEffect(() => {
    let active = true;
    getTrustReport(analysisId)
      .then((data) => {
        if (active) setResult({ analysisId, report: data, loading: false, error: false });
      })
      .catch(() => {
        if (active) setResult({ analysisId, report: null, loading: false, error: true });
      });
    return () => { active = false; };
  }, [analysisId]);

  const loading = result.analysisId !== analysisId || result.loading;
  const report = result.analysisId === analysisId ? result.report : null;
  const error = result.analysisId === analysisId && result.error;

  const handleToggle = (id: string) => setOpen((prev) => (prev === id ? null : id));

  if (loading) return <div className="text-slate-400 text-sm p-6">Computing trust report…</div>;
  if (error || !report) return <div className="text-slate-400 text-sm p-6">No trust report available for this analysis.</div>;

  const cs = report.claim_stats;
  const fs = report.finding_stats;
  const es = report.evidence_stats;
  const ec = report.engineering_confidence;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileBadge className="w-5 h-5 text-indigo-400" />
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Project Trust Report</h3>
            <p className="text-[11px] text-slate-500">Internal product metric — not an industry or professional certification.</p>
          </div>
        </div>
        <a
          href={`${API_BASE}/analysis/${analysisId}/trust-report?format=markdown`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg border border-slate-700 hover:border-indigo-500 text-slate-300"
        >
          <Download className="w-3 h-3" /> Markdown
        </a>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="text-2xl font-bold text-indigo-400">{report.project_identity.overall_score}</div>
          <div className="text-xs text-slate-500 mt-1">Internal score</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="text-2xl font-bold text-slate-100">{cs.total}</div>
          <div className="text-xs text-slate-500 mt-1">Claims analyzed</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="text-2xl font-bold text-emerald-400">{cs.supported}</div>
          <div className="text-xs text-slate-500 mt-1">Supported claims</div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="text-2xl font-bold text-rose-400">{cs.contradicted}</div>
          <div className="text-xs text-slate-500 mt-1">Contradicted claims</div>
        </div>
      </div>

      <Section id="claims" title="Claim Verification" open={open} onToggle={handleToggle}>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <div>Supported: <span className="text-emerald-400">{cs.supported}</span></div>
          <div>Partial: <span className="text-amber-400">{cs.partially_supported}</span></div>
          <div>Unverified: <span className="text-slate-400">{cs.unverified}</span></div>
          <div>Contradicted: <span className="text-rose-400">{cs.contradicted}</span></div>
          <div>Total: <span className="text-slate-100">{cs.total}</span></div>
        </div>
        <ul className="space-y-1">
          {report.claims.map((c) => (
            <li key={c.id} className="bg-slate-800/50 rounded p-2">
              <span className={c.status === "SUPPORTED" ? "text-emerald-400" : c.status === "CONTRADICTED" ? "text-rose-400" : "text-slate-400"}>
                {c.status.replace(/_/g, " ")}
              </span>
              {" · "}{c.claim_text}
              {c.evidence_files.length > 0 && (
                <div className="text-slate-500 mt-1">Evidence: {c.evidence_files.join(", ")}</div>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Section id="evidence" title="Engineering Evidence" open={open} onToggle={handleToggle}>
        <div>Evidence items: {es.total} (observed {es.observed}, inferred {es.inferred}, unverified {es.unverified})</div>
        <div>Findings with structured evidence: {es.findings_with_evidence}/{fs.total}</div>
      </Section>

      <Section id="findings" title="Findings by Category" open={open} onToggle={handleToggle}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div>Security: {fs.security}</div>
          <div>Testing: {fs.testing}</div>
          <div>Documentation: {fs.documentation}</div>
          <div>Architecture: {fs.architecture}</div>
          <div>Dependencies: {fs.dependencies}</div>
          <div>Git Hygiene: {fs.git_hygiene}</div>
          <div>Code Quality: {fs.code_quality}</div>
          <div>Critical: <span className="text-rose-400">{fs.critical}</span></div>
        </div>
      </Section>

      <Section id="improvement" title="Improvement" open={open} onToggle={handleToggle}>
        {report.proof_of_improvement ? (
          <div className="space-y-1">
            <div>Score: {report.proof_of_improvement.score.before} → {report.proof_of_improvement.score.after} (score delta alone is not proof)</div>
            <div>Resolved findings: {report.proof_of_improvement.findings.resolved.length}</div>
            <div>Still present: {report.proof_of_improvement.findings.still_present.length}</div>
          </div>
        ) : (
          <div>No prior analysis run for this repository; improvement could not be verified.</div>
        )}
      </Section>

      <Section id="resolved" title="Resolved Findings" open={open} onToggle={handleToggle}>
        {report.resolved_findings.length > 0 ? (
          <ul className="space-y-1">
            {report.resolved_findings.map((r) => (
              <li key={r.finding_key} className="text-emerald-400">✅ {r.title} ({r.category})</li>
            ))}
          </ul>
        ) : (
          <div>{report.resolved_findings_compared_to ? "No resolved findings compared to the previous run." : "No prior analysis run available; resolution could not be verified."}</div>
        )}
      </Section>

      <Section id="risks" title="Remaining Risks" open={open} onToggle={handleToggle}>
        {report.remaining_findings.length > 0 ? (
          <ul className="space-y-1">
            {report.remaining_findings.map((r) => (
              <li key={r.finding_key}><span className="text-rose-400">{r.severity}</span>: {r.title} ({r.file_path || "project-level"})</li>
            ))}
          </ul>
        ) : (
          <div>No critical/high/medium findings remaining.</div>
        )}
      </Section>

      <Section id="confidence" title="Engineering Confidence (internal)" open={open} onToggle={handleToggle}>
        <div>Score: {ec.score ?? "Not measurable"} / 100</div>
        <div className="text-slate-500">{ec.calculation}</div>
        <ul className="space-y-1">
          {Object.entries(ec.factors).map(([k, v]) => (
            <li key={k}>{k.replace(/_/g, " ")}: {v === null ? "no measurable data" : `${v}`}</li>
          ))}
        </ul>
      </Section>

      <Section id="limitations" title="Limitations" open={open} onToggle={handleToggle}>
        <ul className="space-y-1 list-disc pl-4">
          {report.limitations.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </Section>
    </div>
  );
};
