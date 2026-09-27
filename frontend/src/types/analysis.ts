export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export type EvidenceType =
  | "FILE_MATCH"
  | "PATTERN_MATCH"
  | "AST_NODE"
  | "ABSENCE"
  | "FILE_COUNT"
  | "RATIO"
  | "CONFIG_CHECK";

export type VerificationStatus = "OBSERVED" | "INFERRED" | "UNVERIFIED";
export type EvidenceConfidence = "HIGH" | "MEDIUM" | "LOW";

export interface EvidenceItem {
  id: string;
  finding_id: string;
  category: string;
  source_file: string;
  source_line?: number | null;
  evidence_type: EvidenceType;
  evidence_summary: string;
  confidence: EvidenceConfidence;
  verification_status: VerificationStatus;
}

export interface Finding {
  id: string;
  category: string;
  severity: Severity;
  title: string;
  file_path: string;
  line_number?: number | null;
  evidence: string;
  description: string;
  why_it_matters: string;
  recommended_fix: string;
  verification_method: string;
  /** Structured evidence items — only present when include_evidence=true is requested */
  evidence_items?: EvidenceItem[];
}

export interface CategoryScore {
  category: string;
  score: number;
  max_score: number;
  findings_count: number;
  severity_counts: Record<Severity, number>;
  penalty_breakdown: string[];
  summary: string;
}

export interface Recommendation {
  id: string;
  priority_group: "Fix First" | "Improve Next" | "Portfolio Improvements";
  rank: number;
  title: string;
  action: string;
  reason: string;
  verification: string;
}

export interface InterviewQuestion {
  id: string;
  level: "Beginner" | "Intermediate" | "Advanced";
  category: string;
  question: string;
  context_reason: string;
  sample_answer_guideline: string;
}

export interface ComponentItem {
  name: string;
  tier: string;
  path: string;
  status: "OBSERVED" | "INFERRED";
  details: string;
}

export interface KeyFileItem {
  file_path: string;
  purpose: string;
  significance: string;
}

export interface ProjectExplanation {
  summary: string;
  architecture_narrative: string;
  main_components: ComponentItem[];
  data_flow: string[];
  key_files: KeyFileItem[];
  technical_decisions: string[];
  limitations: string[];
}

export interface AnalysisResponse {
  id: string;
  repo_url: string;
  repo_name: string;
  owner: string;
  status: "QUEUED" | "FETCHING" | "SCANNING" | "ANALYZING" | "AI_PROCESSING" | "COMPLETED" | "FAILED";
  current_stage: string;
  progress_percent: number;
  overall_score: number;
  category_scores: Record<string, CategoryScore>;
  languages: string[];
  frameworks: string[];
  architecture_summary: {
    components: ComponentItem[];
    is_monorepo?: boolean;
  };
  findings: Finding[];
  recommendations: Recommendation[];
  interview_questions: InterviewQuestion[];
  project_explanation?: ProjectExplanation | null;
  duration_seconds: number;
  error_message?: string | null;
  is_sample: boolean;
  created_at?: string;
}

export interface CategoryDelta {
  category: string;
  before_score: number;
  after_score: number;
  delta: number;
  findings_before: number;
  findings_after: number;
}

export interface ComparisonResponse {
  before_id: string;
  after_id: string;
  before_repo: string;
  after_repo: string;
  overall_score_before: number;
  overall_score_after: number;
  overall_score_delta: number;
  category_deltas: Record<string, CategoryDelta>;
  resolved_findings: Finding[];
  new_findings: Finding[];
  persistent_findings: Finding[];
  changed_findings?: Finding[];
  verification_results?: VerificationResult[];
  summary: string;
}

export interface VerificationResult {
  id: string;
  finding_key: string;
  method: string;
  result: string;
  details: string;
  recommendation_id?: string | null;
}

export interface SampleProjectInfo {
  id: string;
  name: string;
  description: string;
  expected_score_range: string;
  key_traits: string[];
}

// ---------------------------------------------------------------------------
// Phases 2–5 — Claim Auditor, Evidence Graph, Improvement, Trust Report
// ---------------------------------------------------------------------------

export type ClaimStatus = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNVERIFIED" | "CONTRADICTED";
export type ClaimCategory =
  | "TECHNOLOGY" | "ARCHITECTURE" | "SECURITY" | "TESTING" | "DEPLOYMENT"
  | "DATABASE" | "AI_ML" | "API" | "PERFORMANCE" | "FEATURE" | "QUALITY" | "OTHER";

export interface Claim {
  id: string;
  claim_text: string;
  normalized_claim: string;
  source_file: string;
  source_line?: number | null;
  category: ClaimCategory;
  status: ClaimStatus;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  explanation: string;
  evidence_count: number;
  related_findings?: Finding[];
  evidence_items?: EvidenceItem[];
  created_at?: string;
}

export interface ClaimStats {
  total: number;
  supported: number;
  partially_supported: number;
  unverified: number;
  contradicted: number;
}

export interface ClaimSummary {
  stats: ClaimStats;
  claims: Claim[];
}

export interface GraphNode {
  id: string;
  [key: string]: any;
}

export interface EvidenceGraph {
  analysis_id: string;
  run: { id: string; repo_url: string; repo_name: string; status: string; overall_score: number } | null;
  nodes: {
    claims: GraphNode[];
    evidence: GraphNode[];
    findings: GraphNode[];
    recommendations: GraphNode[];
    verifications: GraphNode[];
  };
  edges: {
    claim_evidence: { claim_id: string; evidence_id: string }[];
    claim_finding: { claim_id: string; finding_id: string }[];
    evidence_finding: { evidence_id: string; finding_id: string }[];
    finding_recommendation: { finding_id: string; recommendation_id: string }[];
    recommendation_verification: { recommendation_id: string; verification_id: string }[];
  };
  counts: { claims: number; evidence: number; findings: number; recommendations: number; verifications: number };
}

export interface FindingDelta {
  finding_key: string;
  status: "RESOLVED" | "STILL_PRESENT" | "NEW" | "CHANGED";
  category: string;
  title: string;
  before_severity?: string | null;
  after_severity?: string | null;
  before_id?: string | null;
  after_id?: string | null;
  match_method: "finding_key" | "title_fallback";
}

export interface MetricDelta {
  before: number | null;
  after: number | null;
  delta: number | null;
  verified: boolean;
  display: string;
}

export interface ImprovementReport {
  before_id: string;
  after_id: string;
  before_repo: string;
  after_repo: string;
  score: { before: number; after: number; delta: number; note: string };
  category_changes: { category: string; before_score: number | null; after_score: number | null; delta: number | null; verified: boolean }[];
  findings: { resolved: FindingDelta[]; still_present: FindingDelta[]; new: FindingDelta[]; changed: FindingDelta[] };
  claim_stats: { before: ClaimStats; after: ClaimStats };
  claim_changes: { claim_text: string; category: string; before_status: string | null; after_status: string | null; change: string; verified: boolean }[];
  metrics: Record<string, MetricDelta>;
  timeline: { step: number; event: string; [key: string]: any }[];
}

export interface TrustReport {
  analysis_id: string;
  project_identity: { repo_url: string; repo_name: string; owner: string; analyzed_at?: string; overall_score: number; languages: string[]; frameworks: string[] };
  claim_stats: ClaimStats;
  claims: { id: string; claim_text: string; category: string; status: ClaimStatus; confidence: string; source_file: string; source_line?: number | null; evidence_count: number; evidence_files: string[] }[];
  finding_stats: Record<string, number>;
  evidence_stats: Record<string, number>;
  resolved_findings: { finding_key: string; title: string; category: string; severity?: string | null }[];
  resolved_findings_compared_to: string | null;
  remaining_findings: { finding_key: string; title: string; category: string; severity: string; file_path: string }[];
  proof_of_improvement: ImprovementReport | null;
  engineering_confidence: { score: number | null; scale: string; calculation: string; factors: Record<string, number | null>; factor_definitions: string[] };
  limitations: string[];
  report_format: string;
}
