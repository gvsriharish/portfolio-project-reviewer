import React from "react";
import { ShieldCheck } from "lucide-react";

export const SecurityNotice: React.FC = () => {
  return (
    <footer className="mt-16 py-8 border-t border-slate-800/80 text-center text-xs text-slate-500 max-w-4xl mx-auto px-4 space-y-2">
      <div className="flex items-center justify-center gap-1.5 text-slate-400 font-semibold">
        <ShieldCheck className="w-4 h-4 text-indigo-400" />
        <span>Privacy & Sandboxing Guarantee</span>
      </div>
      <p>
        Only analyze public repositories you are authorized to audit. Repository analysis is performed deterministically via static AST parsing and heuristic pattern matching inside ephemeral, isolated sandboxes.
      </p>
      <p className="text-[11px] text-slate-600">
        Untrusted repository code is never executed directly. Secret tokens are automatically redacted in evidence outputs.
      </p>
    </footer>
  );
};
