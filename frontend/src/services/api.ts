import type { AnalysisResponse, ComparisonResponse, SampleProjectInfo, Finding, EvidenceItem,
  Claim, ClaimSummary, EvidenceGraph, ImprovementReport, TrustReport } from "../types/analysis";
import { normalizeApiBase } from "./apiBase.mjs";

// VITE_API_BASE is the complete API prefix (including /api) at build time.
// The same-origin default works in production behind an /api reverse proxy.
// Strip all trailing slashes so endpoint joining stays consistent.
const configuredApiBase = import.meta.env.VITE_API_BASE?.trim();
export const API_BASE = normalizeApiBase(configuredApiBase);

export async function analyzeRepository(githubUrl: string, useAi: boolean = true): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl, use_ai: useAi }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to submit repository" }));
    throw new Error(err.detail || "Analysis request failed");
  }
  return res.json();
}

export async function getAnalysisStatus(analysisId: string): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch analysis status for ${analysisId}`);
  }
  return res.json();
}

export async function getFindings(analysisId: string, category?: string, severity?: string): Promise<Finding[]> {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (severity) params.append("severity", severity);
  
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/findings?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to load findings");
  return res.json();
}

export async function compareAnalyses(beforeId: string, afterId: string): Promise<ComparisonResponse> {
  const res = await fetch(`${API_BASE}/analysis/compare?before_id=${beforeId}&after_id=${afterId}`);
  if (!res.ok) throw new Error("Comparison request failed");
  return res.json();
}

export async function getSampleProjects(): Promise<SampleProjectInfo[]> {
  const res = await fetch(`${API_BASE}/sample-projects`);
  if (!res.ok) throw new Error("Failed to load sample projects");
  return res.json();
}

export async function triggerSelfAnalysis(): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/self-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) throw new Error("Self-analysis request failed");
  return res.json();
}

/**
 * Fetch structured evidence for a specific finding (lazy-loaded on expand).
 * Returns an empty array if the finding has no evidence items.
 */
export async function getFindingEvidence(
  analysisId: string,
  findingId: string
): Promise<EvidenceItem[]> {
  const res = await fetch(
    `${API_BASE}/analysis/${analysisId}/findings/${findingId}/evidence`
  );
  if (!res.ok) return [];
  return res.json();
}

// ---------------------------------------------------------------------------
// Phases 2–5
// ---------------------------------------------------------------------------

export async function getClaims(analysisId: string): Promise<ClaimSummary> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/claims`);
  if (!res.ok) throw new Error("Failed to load claims");
  return res.json();
}

export async function getClaimDetail(analysisId: string, claimId: string): Promise<Claim> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/claims/${claimId}`);
  if (!res.ok) throw new Error("Failed to load claim detail");
  return res.json();
}

export async function getClaimEvidence(analysisId: string, claimId: string): Promise<EvidenceItem[]> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/claims/${claimId}/evidence`);
  if (!res.ok) return [];
  return res.json();
}

export async function reanalyzeClaims(analysisId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/claims/reanalyze`, { method: "POST" });
  if (!res.ok) throw new Error("Claim re-analysis failed");
  return res.json();
}

export async function getEvidenceGraph(analysisId: string): Promise<EvidenceGraph> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/evidence-graph`);
  if (!res.ok) throw new Error("Failed to load evidence graph");
  return res.json();
}

export async function getImprovementReport(beforeId: string, afterId: string): Promise<ImprovementReport> {
  const res = await fetch(`${API_BASE}/analysis/improvement?before_id=${beforeId}&after_id=${afterId}`);
  if (!res.ok) throw new Error("Improvement report request failed");
  return res.json();
}

export async function getTrustReport(analysisId: string): Promise<TrustReport> {
  const res = await fetch(`${API_BASE}/analysis/${analysisId}/trust-report`);
  if (!res.ok) throw new Error("Failed to load trust report");
  return res.json();
}

export { getPortfolio, getMonitor, startInterview, answerInterview, getPassport, verifyPassport } from './phase6_9';
