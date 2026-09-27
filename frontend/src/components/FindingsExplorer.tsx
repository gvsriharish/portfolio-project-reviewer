import React, { useState } from "react";
import type { Finding, Severity, EvidenceItem } from "../types/analysis";
import { getFindingEvidence } from "../services/api";
import {
  ShieldAlert,
  FileCode,
  CheckCircle,
  Wrench,
  Search,
  ChevronDown,
  ChevronUp,
  FlaskConical,
} from "lucide-react";

interface FindingsExplorerProps {
  findings: Finding[];
  selectedCategory?: string;
  onClearCategoryFilter: () => void;
  /** Pass the current analysis ID to enable the lazy evidence panel */
  analysisId?: string;
}

const SEVERITY_COLORS: Record<Severity, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/30" },
  HIGH: { bg: "bg-orange-500/10", text: "text-orange-400", border: "border-orange-500/30" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30" },
  LOW: { bg: "bg-sky-500/10", text: "text-sky-400", border: "border-sky-500/30" },
  INFO: { bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/30" },
};

const VERIFICATION_COLORS: Record<string, string> = {
  OBSERVED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  INFERRED: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  UNVERIFIED: "text-slate-400 bg-slate-500/10 border-slate-500/30",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  HIGH: "text-emerald-300",
  MEDIUM: "text-amber-300",
  LOW: "text-slate-400",
};

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  FILE_MATCH: "File",
  PATTERN_MATCH: "Pattern",
  AST_NODE: "AST",
  ABSENCE: "Absence",
  FILE_COUNT: "Count",
  RATIO: "Ratio",
  CONFIG_CHECK: "Config",
};

/**
 * Single evidence panel, lazily loaded when a finding card is expanded.
 */
function EvidencePanel({
  findingId,
  analysisId,
}: {
  findingId: string;
  analysisId: string;
}) {
  const [items, setItems] = useState<EvidenceItem[] | null>(null);
  const [loading, setLoading] = useState(true);

  // Trigger load on first render of this panel.
  React.useEffect(() => {
    let active = true;
    getFindingEvidence(analysisId, findingId)
      .then((data) => { if (active) setItems(data); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [analysisId, findingId]);

  if (loading) {
    return (
      <div className="pt-2 text-xs text-slate-500 animate-pulse">
        Loading evidence…
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="pt-2 text-xs text-slate-600 italic">
        No structured evidence recorded for this finding.
      </div>
    );
  }

  return (
    <div className="pt-3 space-y-2">
      <div className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">
        Structured Evidence ({items.length} item{items.length !== 1 ? "s" : ""})
      </div>
      {items.map((ev) => (
        <div
          key={ev.id}
          className="p-3 rounded-xl bg-slate-950 border border-slate-800/70 text-xs space-y-1"
        >
          {/* Row 1: type badge + verification badge + confidence */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-indigo-300 uppercase tracking-wider">
              {EVIDENCE_TYPE_LABELS[ev.evidence_type] ?? ev.evidence_type}
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                VERIFICATION_COLORS[ev.verification_status] ??
                "text-slate-400 bg-slate-500/10 border-slate-500/30"
              }`}
            >
              {ev.verification_status}
            </span>
            <span
              className={`text-[10px] font-semibold ${
                CONFIDENCE_COLORS[ev.confidence] ?? "text-slate-400"
              }`}
            >
              {ev.confidence} confidence
            </span>
          </div>

          {/* Row 2: file + line */}
          {ev.source_file && (
            <div className="flex items-center gap-1 font-mono text-slate-400">
              <FileCode className="w-3 h-3 text-slate-500 shrink-0" />
              <span>{ev.source_file}</span>
              {ev.source_line != null && (
                <span className="text-indigo-400">:{ev.source_line}</span>
              )}
            </div>
          )}

          {/* Row 3: summary */}
          <div className="text-slate-300 leading-relaxed">
            {ev.evidence_summary}
          </div>
        </div>
      ))}
    </div>
  );
}

export const FindingsExplorer: React.FC<FindingsExplorerProps> = ({
  findings,
  selectedCategory,
  onClearCategoryFilter,
  analysisId,
}) => {
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  // Track which finding IDs have their evidence panel expanded.
  const [expandedEvidence, setExpandedEvidence] = useState<Set<string>>(new Set());

  const filtered = findings.filter((f) => {
    if (selectedCategory && f.category !== selectedCategory) return false;
    if (severityFilter !== "ALL" && f.severity !== severityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        f.title.toLowerCase().includes(q) ||
        f.file_path.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const toggleEvidence = (findingId: string) => {
    setExpandedEvidence((prev) => {
      const next = new Set(prev);
      if (next.has(findingId)) {
        next.delete(findingId);
      } else {
        next.add(findingId);
      }
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>Repository Findings</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
              {filtered.length} of {findings.length}
            </span>
          </h3>
          {selectedCategory && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-indigo-400">
                Filtering by category: <strong>{selectedCategory}</strong>
              </span>
              <button
                onClick={onClearCategoryFilter}
                className="text-[11px] underline text-slate-400 hover:text-slate-200"
              >
                Clear filter
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search findings, files..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-900 border border-slate-700 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFO">Info</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-500 text-sm">
          No findings match the active search or category filters.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((f) => {
            const sevStyle = SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.INFO;
            const evidenceExpanded = expandedEvidence.has(f.id);

            return (
              <div
                key={f.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md space-y-4 hover:border-slate-700 transition"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-xs font-semibold text-slate-400 bg-slate-800/80 px-2.5 py-0.5 rounded">
                      {f.category}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-xs font-mono text-slate-400">
                    <FileCode className="w-3.5 h-3.5 text-slate-500" />
                    <span>{f.file_path}</span>
                    {f.line_number && (
                      <span className="text-indigo-400">:{f.line_number}</span>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="text-base font-bold text-slate-100">{f.title}</h4>
                  <p className="text-xs sm:text-sm text-slate-300 mt-1">
                    {f.description}
                  </p>
                </div>

                {f.evidence && (
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto">
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">
                      Evidence:
                    </div>
                    <code className="text-amber-300/90">{f.evidence}</code>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs">
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800/80 space-y-1">
                    <div className="font-bold text-slate-300 flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                      <span>Why It Matters</span>
                    </div>
                    <p className="text-slate-400 leading-relaxed">{f.why_it_matters}</p>
                  </div>

                  <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-900/30 space-y-1">
                    <div className="font-bold text-indigo-300 flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Recommended Fix</span>
                    </div>
                    <p className="text-slate-300 leading-relaxed">{f.recommended_fix}</p>
                  </div>

                  <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/30 space-y-1">
                    <div className="font-bold text-emerald-300 flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Verification Method</span>
                    </div>
                    <p className="text-slate-300 leading-relaxed">{f.verification_method}</p>
                  </div>
                </div>

                {/* Evidence panel toggle — only shown when an analysisId is available */}
                {analysisId && (
                  <div className="pt-1">
                    <button
                      onClick={() => toggleEvidence(f.id)}
                      className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-indigo-300 transition"
                    >
                      <FlaskConical className="w-3.5 h-3.5" />
                      <span>
                        {evidenceExpanded ? "Hide" : "View"} structured evidence
                      </span>
                      {evidenceExpanded ? (
                        <ChevronUp className="w-3 h-3" />
                      ) : (
                        <ChevronDown className="w-3 h-3" />
                      )}
                    </button>

                    {evidenceExpanded && (
                      <EvidencePanel
                        findingId={f.id}
                        analysisId={analysisId}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
