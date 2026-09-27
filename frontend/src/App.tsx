import { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { RepoInput } from "./components/RepoInput";
import { AnalysisProgress } from "./components/AnalysisProgress";
import { HealthDashboard } from "./components/HealthDashboard";
import { FindingsExplorer } from "./components/FindingsExplorer";
import { RecommendationsView } from "./components/RecommendationsView";
import { BeforeAfterDiff } from "./components/BeforeAfterDiff";
import { InterviewPrepView } from "./components/InterviewPrepView";
import { ExplainProjectView } from "./components/ExplainProjectView";
import { ClaimAuditor } from "./components/ClaimAuditor";
import { EvidenceExplorer } from "./components/EvidenceExplorer";
import { TrustReportView } from "./components/TrustReportView";
import { SecurityNotice } from "./components/SecurityNotice";
import { Phase6_9Workspace } from "./components/Phase6_9Workspace";

import { 
  analyzeRepository, getAnalysisStatus, getSampleProjects, triggerSelfAnalysis 
} from "./services/api";
import type { AnalysisResponse, SampleProjectInfo } from "./types/analysis";
import { 
  LayoutDashboard, ShieldAlert, ListChecks, GitCompare, MessageSquare, BookOpen, 
  FileSearch, Network, FileBadge, Sparkles
} from "lucide-react";

export function App() {
  const [samples, setSamples] = useState<SampleProjectInfo[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  // isFetching covers the gap between submit and first analysis object arriving
  const [isFetching, setIsFetching] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    getSampleProjects().then(setSamples).catch(() => {
      // Samples are optional; fail silently so the main input still works.
    });
  }, []);

  // Poll for status updates while analysis is running.
  const analysisId = analysis?.id;
  const analysisStatus = analysis?.status;
  useEffect(() => {
    if (!analysisId || analysisStatus === "COMPLETED" || analysisStatus === "FAILED") {
      return;
    }

    let active = true;
    let timeout: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const updated = await getAnalysisStatus(analysisId);
        if (!active) return;
        setAnalysis(updated);
        if (updated.status !== "COMPLETED" && updated.status !== "FAILED") {
          timeout = setTimeout(poll, 1200);
        }
      } catch {
        // Keep polling — transient network errors should not stop the UI.
        if (active) timeout = setTimeout(poll, 1200);
      }
    };
    timeout = setTimeout(poll, 1200);

    return () => {
      active = false;
      clearTimeout(timeout);
    };
  }, [analysisId, analysisStatus]);

  const handleStartAnalysis = async (url: string) => {
    setStartError(null);
    setIsFetching(true);
    try {
      const initial = await analyzeRepository(url, true);
      setAnalysis(initial);
      setActiveTab("dashboard");
      setSelectedCategory(undefined);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start analysis. Check that the backend is running.";
      setStartError(msg);
    } finally {
      setIsFetching(false);
    }
  };

  const handleSelfReview = async () => {
    setStartError(null);
    setIsFetching(true);
    try {
      const initial = await triggerSelfAnalysis();
      setAnalysis(initial);
      setActiveTab("dashboard");
      setSelectedCategory(undefined);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start self-review.";
      setStartError(msg);
    } finally {
      setIsFetching(false);
    }
  };

  const handleSelectCategory = (cat: string) => {
    setSelectedCategory(cat);
    setActiveTab("findings");
  };

  // True while an analysis request is in-flight or actively running in the backend.
  const isAnalyzing =
    isFetching ||
    (analysis !== null &&
      analysis.status !== "COMPLETED" &&
      analysis.status !== "FAILED");

  const handleReset = () => {
    setAnalysis(null);
    setSelectedCategory(undefined);
    setStartError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      <Navbar
        onSelfReview={handleSelfReview}
        onReset={handleReset}
        isAnalyzing={isAnalyzing}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {startError && !analysis && (
          <div className="max-w-2xl mx-auto mb-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-2">
            <span className="text-rose-400 font-bold shrink-0">Error:</span>
            <span>{startError}</span>
          </div>
        )}

        {!analysis && (
          <RepoInput
            onAnalyze={handleStartAnalysis}
            samples={samples}
            isLoading={isAnalyzing}
          />
        )}

        {analysis && analysis.status !== "COMPLETED" && (
          <div>
            <AnalysisProgress
              stage={analysis.current_stage}
              progressPercent={analysis.progress_percent}
              status={analysis.status}
              error={analysis.error_message}
            />
            {analysis.status === "FAILED" && (
              <div className="text-center -mt-6 mb-10">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-slate-200 transition"
                >
                  Try another repository
                </button>
              </div>
            )}
          </div>
        )}

        {analysis && analysis.status === "COMPLETED" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-1.5 p-1.5 rounded-xl bg-slate-900 border border-slate-800">
              <button
                onClick={() => setActiveTab("dashboard")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "dashboard" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </button>

              <button
                onClick={() => setActiveTab("findings")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "findings" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Findings ({analysis.findings.length})</span>
              </button>

              <button
                onClick={() => setActiveTab("recommendations")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "recommendations" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ListChecks className="w-4 h-4" />
                <span>Roadmap</span>
              </button>

              <button
                onClick={() => setActiveTab("diff")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "diff" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <GitCompare className="w-4 h-4" />
                <span>Before vs After</span>
              </button>

              <button
                onClick={() => setActiveTab("claims")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "claims" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileSearch className="w-4 h-4" />
                <span>Claim Auditor</span>
              </button>

              <button
                onClick={() => setActiveTab("evidence")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "evidence" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Network className="w-4 h-4" />
                <span>Evidence Explorer</span>
              </button>

              <button
                onClick={() => setActiveTab("trust")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "trust" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileBadge className="w-4 h-4" />
                <span>Trust Report</span>
              </button>

              <button
                onClick={() => setActiveTab("interview")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "interview" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Interview Prep</span>
              </button>

              <button
                onClick={() => setActiveTab("explain")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "explain" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <BookOpen className="w-4 h-4" />
                <span>Explain My Project</span>
              </button>

              <button
                onClick={() => setActiveTab("phase6_9")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "phase6_9" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Sparkles className="w-4 h-4" />
                <span>Portfolio & Proof</span>
              </button>
            </div>

            {activeTab === "dashboard" && (
              <HealthDashboard
                analysis={analysis}
                onSelectCategory={handleSelectCategory}
              />
            )}

            {activeTab === "findings" && (
              <FindingsExplorer
                findings={analysis.findings}
                selectedCategory={selectedCategory}
                onClearCategoryFilter={() => setSelectedCategory(undefined)}
                analysisId={analysis.id}
              />
            )}

            {activeTab === "recommendations" && (
              <RecommendationsView
                recommendations={analysis.recommendations}
              />
            )}

            {activeTab === "diff" && (
              <BeforeAfterDiff
                currentAnalysisId={analysis.id}
              />
            )}

            {activeTab === "claims" && (
              <ClaimAuditor analysisId={analysis.id} />
            )}

            {activeTab === "evidence" && (
              <EvidenceExplorer analysisId={analysis.id} />
            )}

            {activeTab === "trust" && (
              <TrustReportView analysisId={analysis.id} />
            )}

            {activeTab === "interview" && (
              <InterviewPrepView
                questions={analysis.interview_questions}
              />
            )}

            {activeTab === "explain" && (
              <ExplainProjectView
                explanation={analysis.project_explanation}
              />
            )}

            {activeTab === "phase6_9" && <Phase6_9Workspace analysisId={analysis.id} />}
          </div>
        )}
      </main>

      <SecurityNotice />
    </div>
  );
}

export default App;
