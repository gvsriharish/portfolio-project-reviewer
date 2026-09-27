import React, { useState } from "react";
import type { InterviewQuestion } from "../types/analysis";
import { MessageSquare, HelpCircle, Lightbulb } from "lucide-react";

interface InterviewPrepViewProps {
  questions: InterviewQuestion[];
}

export const InterviewPrepView: React.FC<InterviewPrepViewProps> = ({ questions }) => {
  const [activeLevel, setActiveLevel] = useState<string>("ALL");
  const [revealedIds, setRevealedIds] = useState<Record<string, boolean>>({});

  const toggleReveal = (id: string) => {
    setRevealedIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const filtered = activeLevel === "ALL" ? questions : questions.filter(q => q.level === activeLevel);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" />
            <span>Project-Specific Interview Preparation</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Tailored technical interview questions generated exclusively from the detected technologies, architecture, and code patterns in your project.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {["ALL", "Beginner", "Intermediate", "Advanced"].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setActiveLevel(lvl)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                activeLevel === lvl 
                  ? "bg-indigo-600 text-white" 
                  : "bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200"
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {filtered.map((q) => {
          const isRevealed = revealedIds[q.id];
          return (
            <div key={q.id} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    q.level === 'Beginner' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    q.level === 'Intermediate' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                    'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                  }`}>
                    {q.level}
                  </span>
                  <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded font-medium">
                    {q.category}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-base font-bold text-slate-100 flex items-start gap-2">
                  <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-1" />
                  <span>{q.question}</span>
                </h4>
                <p className="text-xs text-slate-400 mt-1 ml-6">
                  <strong>Why recruiters ask this:</strong> {q.context_reason}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800/80">
                <button
                  onClick={() => toggleReveal(q.id)}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5"
                >
                  <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                  <span>{isRevealed ? "Hide Sample Answer Guideline" : "Show Recommended Answer Guideline"}</span>
                </button>

                {isRevealed && (
                  <div className="mt-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed space-y-1">
                    <div className="font-bold text-slate-400 uppercase text-[10px] tracking-wider">How to answer confidently:</div>
                    <p>{q.sample_answer_guideline}</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
