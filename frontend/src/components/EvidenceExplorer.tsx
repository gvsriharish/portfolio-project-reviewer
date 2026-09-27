import { useState, useEffect } from "react";
import { getEvidenceGraph } from "../services/api";
import type { EvidenceGraph } from "../types/analysis";
import { Network, FileText, ShieldAlert, MessageSquareQuote, Wrench, BadgeCheck } from "lucide-react";

interface EvidenceExplorerProps {
  analysisId: string;
}

type NodeSelection =
  | { kind: "claim"; id: string }
  | { kind: "evidence"; id: string }
  | { kind: "finding"; id: string }
  | { kind: "recommendation"; id: string }
  | { kind: "verification"; id: string }
  | null;

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({ analysisId }) => {
  const [result, setResult] = useState<{ analysisId: string; graph: EvidenceGraph | null; loading: boolean }>({
    analysisId, graph: null, loading: true,
  });
  const [selection, setSelection] = useState<NodeSelection>(null);

  useEffect(() => {
    let active = true;
    getEvidenceGraph(analysisId)
      .then((g) => {
        if (active) setResult({ analysisId, graph: g, loading: false });
      })
      .catch(() => {
        if (active) setResult({ analysisId, graph: null, loading: false });
      });
    return () => { active = false; };
  }, [analysisId]);

  const loading = result.analysisId !== analysisId || result.loading;
  const graph = result.analysisId === analysisId ? result.graph : null;

  if (loading) return <div className="text-slate-400 text-sm p-6">Building evidence graph…</div>;
  if (!graph) return <div className="text-slate-400 text-sm p-6">No evidence graph available for this analysis.</div>;

  const { nodes, edges, counts } = graph;
  const findingsById = new Map(nodes.findings.map((n) => [n.id, n]));
  const claimsById = new Map(nodes.claims.map((n) => [n.id, n]));
  const evidenceById = new Map(nodes.evidence.map((n) => [n.id, n]));
  const recsById = new Map(nodes.recommendations.map((n) => [n.id, n]));
  const verifsById = new Map(nodes.verifications.map((n) => [n.id, n]));

  const claimsForEvidence = (eid: string) =>
    edges.claim_evidence.filter((e) => e.evidence_id === eid).map((e) => claimsById.get(e.claim_id)!).filter(Boolean);
  void claimsForEvidence;
  const evidenceForClaim = (cid: string) =>
    edges.claim_evidence.filter((e) => e.claim_id === cid).map((e) => evidenceById.get(e.evidence_id)!).filter(Boolean);
  const findingsForEvidence = (eid: string) =>
    edges.evidence_finding.filter((e) => e.evidence_id === eid).map((e) => findingsById.get(e.finding_id)!).filter(Boolean);
  const evidenceForFinding = (fid: string) =>
    edges.evidence_finding.filter((e) => e.finding_id === fid).map((e) => evidenceById.get(e.evidence_id)!).filter(Boolean);
  void evidenceForFinding;
  const recsForFinding = (fid: string) =>
    edges.finding_recommendation.filter((e) => e.finding_id === fid).map((e) => recsById.get(e.recommendation_id)!).filter(Boolean);
  const verifsForRec = (rid: string) =>
    edges.recommendation_verification.filter((e) => e.recommendation_id === rid).map((e) => verifsById.get(e.verification_id)!).filter(Boolean);

  const Card = ({ children, onClick, highlight }: any) => (
    <button onClick={onClick}
      className={`text-left w-full rounded-lg border p-3 text-xs transition ${highlight ? "border-indigo-500 bg-indigo-500/10" : "border-slate-800 bg-slate-900 hover:border-indigo-500/50"}`}>
      {children}
    </button>
  );

  const selectedClaim = selection?.kind === "claim" ? claimsById.get(selection.id) : null;
  const selectedEvidence = selection?.kind === "evidence" ? evidenceById.get(selection.id) : null;
  const selectedFinding = selection?.kind === "finding" ? findingsById.get(selection.id) : null;
  const selectedRec = selection?.kind === "recommendation" ? recsById.get(selection.id) : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Network className="w-4 h-4 text-indigo-400" />
        Claim → Evidence → Finding → Recommendation → Verification
        <span className="ml-auto text-slate-500">{counts.claims} claims · {counts.evidence} evidence · {counts.findings} findings</span>
      </div>

      {/* Relationship panel: pick a claim and walk the chain */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1"><MessageSquareQuote className="w-3 h-3" /> Claims</div>
          {nodes.claims.slice(0, 12).map((c) => (
            <Card key={c.id} onClick={() => setSelection({ kind: "claim", id: c.id })} highlight={selection?.id === c.id}>
              <div className="text-slate-200 line-clamp-2">{c.claim_text}</div>
              <div className={`mt-1 ${c.status === "SUPPORTED" ? "text-emerald-400" : c.status === "CONTRADICTED" ? "text-rose-400" : "text-slate-500"}`}>{c.status.replace(/_/g, " ")}</div>
            </Card>
          ))}
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1"><FileText className="w-3 h-3" /> Evidence</div>
          {(selectedClaim ? evidenceForClaim(selectedClaim.id) : nodes.evidence.slice(0, 6)).map((ev) => (
            <Card key={ev.id} onClick={() => setSelection({ kind: "evidence", id: ev.id })} highlight={selection?.id === ev.id}>
              <div className="text-indigo-300">{ev.evidence_type}</div>
              <div className="text-slate-300">{ev.source_file || "project-level"}{ev.source_line ? `:${ev.source_line}` : ""}</div>
              <div className="text-slate-500 line-clamp-2">{ev.evidence_summary}</div>
            </Card>
          ))}
          {selectedClaim && evidenceForClaim(selectedClaim.id).length === 0 && (
            <div className="text-[11px] text-slate-500 p-3">Evidence not detected.</div>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> Findings</div>
          {(selectedEvidence ? findingsForEvidence(selectedEvidence.id) : nodes.findings.slice(0, 6)).map((f) => (
            <Card key={f.id} onClick={() => setSelection({ kind: "finding", id: f.id })} highlight={selection?.id === f.id}>
              <div className="text-rose-300">{f.severity}</div>
              <div className="text-slate-200">{f.title}</div>
              <div className="text-slate-500">{f.file_path}{f.line_number ? `:${f.line_number}` : ""}</div>
            </Card>
          ))}
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1"><Wrench className="w-3 h-3" /> Recommendations</div>
          {(selectedFinding ? recsForFinding(selectedFinding.id) : nodes.recommendations.filter((r) => r.finding_id).slice(0, 6)).map((r) => (
            <Card key={r.id} onClick={() => setSelection({ kind: "recommendation", id: r.id })} highlight={selection?.id === r.id}>
              <div className="text-slate-200">{r.title}</div>
              <div className="text-slate-500">{r.status}</div>
            </Card>
          ))}
          {selectedFinding && recsForFinding(selectedFinding.id).length === 0 && (
            <div className="text-[11px] text-slate-500 p-3">No finding-backed recommendation linked.</div>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-[11px] font-semibold text-slate-300 flex items-center gap-1"><BadgeCheck className="w-3 h-3" /> Verification</div>
          {(selectedRec ? verifsForRec(selectedRec.id) : nodes.verifications.slice(0, 6)).map((v) => (
            <Card key={v.id} highlight={selection?.id === v.id}>
              <div className={v.result === "PASS" ? "text-emerald-400" : v.result === "FAIL" ? "text-rose-400" : "text-slate-400"}>{v.result}</div>
              <div className="text-slate-400">{v.details || v.method}</div>
            </Card>
          ))}
          {nodes.verifications.length === 0 && (
            <div className="text-[11px] text-slate-500 p-3">No verification runs recorded yet. Re-analyze after fixing to verify changes.</div>
          )}
        </div>
      </div>
    </div>
  );
};
