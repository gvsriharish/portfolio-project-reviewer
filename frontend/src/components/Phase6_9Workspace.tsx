import { useState, type ReactNode } from 'react';
import { Download, ShieldCheck, Sparkles, Timer, UserRound, ExternalLink, CheckCircle2 } from 'lucide-react';
import { getPortfolio, getMonitor, startInterview, getPassport, verifyPassport, answerInterview, API_BASE } from '../services/api';

type Tab = 'portfolio' | 'monitor' | 'interview' | 'passport';

function Card({ title, children }: { title: string; children: ReactNode }) {
  return <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
    <h3 className="font-semibold text-slate-100">{title}</h3>{children}
  </div>;
}

function Status({ value }: { value: string }) {
  const good = ['VERIFIED', 'SUPPORTED', 'PASS', 'RESOLVED', 'STRONG', 'VALID'].includes(value);
  return <span className={`text-xs px-2 py-1 rounded-full border ${good ? 'border-emerald-700 text-emerald-300' : 'border-amber-700 text-amber-300'}`}>{value}</span>;
}

export function Phase6_9Workspace({ analysisId }: { analysisId: string }) {
  const [tab, setTab] = useState<Tab>('portfolio');
  const [data, setData] = useState<any>(null);
  const [session, setSession] = useState<any>(null);
  const [answer, setAnswer] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  const load = async (next: Tab) => {
    setTab(next); setMessage(''); setLoading(true);
    try {
      if (next === 'portfolio') setData(await getPortfolio(analysisId));
      if (next === 'monitor') setData(await getMonitor(analysisId));
      if (next === 'passport') setData(await getPassport(analysisId));
    } catch (e: any) { setMessage(e.message || 'Unable to load this section.'); }
    finally { setLoading(false); }
  };

  const begin = async () => {
    setLoading(true); setMessage('');
    try { setSession(await startInterview(analysisId, 'Project Defense')); setTab('interview'); }
    catch (e: any) { setMessage(e.message || 'Unable to start interview.'); }
    finally { setLoading(false); }
  };

  return <section className="space-y-5">
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 p-2 rounded-xl bg-slate-900 border border-slate-800">
      {[
        ['portfolio', Sparkles, 'Portfolio'], ['monitor', Timer, 'Monitor'],
        ['interview', UserRound, 'Interview'], ['passport', ShieldCheck, 'Proof Passport']
      ].map(([key, Icon, label]: any) =>
        <button key={key} onClick={() => key === 'interview' ? begin() : load(key)}
          className={`flex items-center justify-center gap-2 px-3 py-3 rounded-lg text-sm ${tab === key ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Icon className="w-4 h-4" />{label}
        </button>
      )}
    </div>

    {loading && <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-300">Loading evidence-backed results…</div>}
    {message && <div className="rounded-xl border border-amber-800 bg-amber-950/30 p-4 text-amber-200">{message}</div>}

    {tab === 'portfolio' && data && <div className="space-y-4">
      <div><p className="text-xs uppercase tracking-wider text-indigo-300">Engineering Portfolio</p><h2 className="text-2xl font-bold">{data.payload.project.name}</h2>
      <p className="text-slate-400 mt-1">{data.payload.hero.description}</p></div>
      <div className="grid md:grid-cols-4 gap-3">
        <Card title="Verified Claims"><b className="text-2xl">{data.payload.hero.verified_claims}</b></Card>
        <Card title="Technologies"><b className="text-2xl">{data.payload.technologies.length}</b></Card>
        <Card title="Findings"><b className="text-2xl">{data.payload.findings.length}</b></Card>
        <Card title="Evidence"><b className="text-2xl">{data.payload.evidence.length}</b></Card>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="PROJECT OVERVIEW"><p className="text-sm text-slate-300">{data.payload.sections.overview}</p></Card>
        <Card title="PROBLEM"><Status value={data.payload.sections.problem.status}/><p className="text-sm text-slate-300">{data.payload.sections.problem.text}</p></Card>
        <Card title="SOLUTION"><Status value={data.payload.sections.solution.status}/><p className="text-sm text-slate-300">{data.payload.sections.solution.text}</p></Card>
        <Card title="ARCHITECTURE"><Status value={data.payload.sections.architecture.status}/><pre className="text-xs text-slate-400 whitespace-pre-wrap">{JSON.stringify(data.payload.sections.architecture.components, null, 2)}</pre></Card>
      </div>
      <Card title="TECH STACK">
        <div className="grid md:grid-cols-2 gap-2">{data.payload.technologies.map((t: any) =>
          <div key={t.technology} className="rounded-lg border border-slate-800 p-3">
            <div className="flex justify-between gap-2"><b>{t.technology}</b><Status value={t.status}/></div>
            <p className="text-xs text-slate-400 mt-1">{t.evidence}</p><p className="text-xs text-slate-600 mt-1">{t.source} · {t.confidence}</p>
          </div>)}</div>
      </Card>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="VERIFIED CLAIMS">{data.payload.claims.slice(0, 8).map((c: any) => <div key={c.claim_id} className="border-b border-slate-800 py-2 text-sm"><Status value={c.verification_status}/><span className="ml-2">{c.content}</span><p className="text-xs text-slate-500 mt-1">{c.source_reference || 'No source recorded'}</p></div>)}</Card>
        <Card title="ENGINEERING FINDINGS">{data.payload.findings.slice(0, 8).map((f: any) => <div key={f.id} className="border-b border-slate-800 py-2"><div className="flex justify-between"><b className="text-sm">{f.title}</b><span className="text-xs text-amber-300">{f.severity}</span></div><p className="text-xs text-slate-400">{f.file_path}</p></div>)}</Card>
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="TESTING"><ul className="text-sm text-slate-300 space-y-1">{data.payload.sections.testing.map((x: string, i: number) => <li key={i}>• {x}</li>)}</ul></Card>
        <Card title="SECURITY"><ul className="text-sm text-slate-300 space-y-1">{data.payload.sections.security.map((x: string, i: number) => <li key={i}>• {x}</li>)}</ul></Card>
        <Card title="IMPROVEMENTS"><ul className="text-sm text-slate-300 space-y-1">{data.payload.sections.improvements.map((x: string, i: number) => <li key={i}>• {x}</li>)}</ul></Card>
        <Card title="LIMITATIONS"><ul className="text-sm text-slate-300 space-y-1">{data.payload.sections.limitations.map((x: string, i: number) => <li key={i}>• {x}</li>)}</ul></Card>
      </div>
      <Card title="EVIDENCE"><button onClick={() => setEvidenceOpen(!evidenceOpen)} className="text-sm text-indigo-300 flex items-center gap-1"><ExternalLink className="w-4 h-4"/> {evidenceOpen ? 'Hide evidence' : 'View evidence'}</button>
        {evidenceOpen && <div className="space-y-2 mt-2">{data.payload.evidence.map((e: any) => <div key={e.id} className="text-sm border border-slate-800 rounded-lg p-3"><Status value={e.verification_status}/><span className="ml-2">{e.summary}</span><p className="text-xs text-slate-500 mt-1">{e.source_file}:{e.source_line || 'project-level'}</p></div>)}</div>}
      </Card>
      <a className="inline-flex items-center gap-2 text-indigo-300" href={`${API_BASE}/portfolio/${analysisId}/export`} download><Download className="w-4 h-4"/>Export Markdown</a>
    </div>}

    {tab === 'monitor' && data && <div className="space-y-4">
      <div><p className="text-xs uppercase tracking-wider text-indigo-300">Engineering Monitor</p><h2 className="text-2xl font-bold">Current → Previous → Change</h2></div>
      <div className="grid md:grid-cols-4 gap-3">{[['Score',data.current.score],['Findings',data.current.finding_count],['Claims',data.current.claim_count],['Evidence',data.current.evidence_count]].map(([k,v]) => <Card key={String(k)} title={String(k)}><b className="text-2xl">{String(v)}</b></Card>)}</div>
      <Card title="CHANGE SUMMARY">{data.comparison ? <div className="grid md:grid-cols-3 gap-2 text-sm">
        <div>New findings: <b>{data.comparison.new_findings.length}</b></div><div>Resolved: <b>{data.comparison.resolved_findings.length}</b></div><div>Changed: <b>{data.comparison.changed_findings.length}</b></div>
        <div>Evidence added: <b>{data.comparison.new_evidence.length}</b></div><div>Evidence removed: <b>{data.comparison.lost_evidence.length}</b></div><div>Score delta: <b>{data.comparison.score_delta}</b></div>
      </div> : <p className="text-slate-400">No previous analysis for this repository.</p>}</Card>
      <Card title="TIMELINE">{data.timeline.map((x: any, i: number) => <div key={x.analysis_id} className="flex gap-3 border-l border-slate-700 pl-4 py-2"><div className="text-xs text-slate-500">Analysis {i + 1}<br/>{x.timestamp}</div><div className="text-sm"><b>Score {x.score}</b><p className="text-slate-400">{x.finding_count} findings · {x.claim_count} claims · {x.evidence_count} evidence · {x.commit_sha || 'COMMIT NOT AVAILABLE'}</p></div></div>)}</Card>
    </div>}

    {tab === 'interview' && session && <div className="space-y-4">
      <div><p className="text-xs uppercase tracking-wider text-indigo-300">Evidence-backed Interview</p><h2 className="text-2xl font-bold">Project Defense</h2></div>
      {session.questions.map((q: any, i: number) => <Card key={i} title={`Question ${i + 1}`}>
        <p className="font-semibold">{q.question}</p><p className="text-xs text-slate-500">Evidence: {q.evidence_reference} · {q.evidence_summary}</p>
        {i === (session.answers?.length || 0) && <><textarea value={answer} onChange={e => setAnswer(e.target.value)} className="mt-2 w-full bg-slate-950 border border-slate-700 rounded-lg p-3" placeholder="Answer using only what the repository supports"/><button onClick={async () => { try { const result = await answerInterview(session.id, i, answer); setMessage(result.evaluation.explanation); setSession({...session, answers:[...(session.answers || []).filter((a:any) => a.question_index !== i), result]}); setAnswer(''); } catch(e:any) { setMessage(e.message || 'Unable to evaluate answer.'); } }} className="mt-2 px-3 py-2 bg-indigo-600 rounded-lg">Evaluate answer</button></>}
      </Card>)}
      {session.answers?.length > 0 && <Card title="INTERVIEW SUMMARY"><p className="text-sm text-slate-300">Answered: {session.answers.length} / {session.questions.length}</p><p className="text-sm text-slate-300">Evidence-aligned: {session.answers.filter((a:any) => a.evaluation?.evidence_alignment).length}</p><p className="text-sm text-slate-300">Unsupported claims: {session.answers.reduce((n:number,a:any) => n + (a.evaluation?.unsupported_claims?.length || 0), 0)}</p><p className="text-xs text-slate-500 mt-2">Potential follow-up questions are generated from repository evidence; they are not guaranteed interview questions.</p></Card>}
    </div>}

    {tab === 'passport' && data && <div className="space-y-4">
      <div><p className="text-xs uppercase tracking-wider text-indigo-300">Project Proof Passport</p><h2 className="text-2xl font-bold">{data.payload.project.name}</h2><p className="text-xs text-slate-500">{data.proof_id} · SHA-256 {data.payload_hash}</p></div>
      <Card title="INTEGRITY"><Status value={data.valid ? 'VALID' : 'MODIFIED'}/><p className="text-sm text-slate-400">The passport is an application-generated evidence package, not a professional, security, academic, or software-quality certification.</p></Card>
      <Card title="IMPROVEMENT HISTORY">{typeof data.payload.improvements === 'string' ? <p className="text-slate-400">{data.payload.improvements}</p> : <div className="grid md:grid-cols-2 gap-2 text-sm"><p>Resolved: {data.payload.improvements.resolved_findings?.length || 0}</p><p>New: {data.payload.improvements.new_findings?.length || 0}</p><p>Changed: {data.payload.improvements.changed_findings?.length || 0}</p><p>Score delta: {data.payload.improvements.score_delta || 0}</p></div>}</Card>
      <Card title="PROOF CONTENT"><div className="grid md:grid-cols-4 gap-2 text-sm"><p>Claims: {data.payload.claims.length}</p><p>Evidence: {data.payload.evidence.length}</p><p>Findings: {data.payload.findings.length}</p><p>Verifications: {data.payload.verifications.length}</p></div></Card>
      <div className="flex gap-2"><button onClick={async () => { try { const result = await verifyPassport(analysisId); setMessage(result.status); } catch(e:any) { setMessage(e.message || 'Unable to verify passport.'); } }} className="px-3 py-2 bg-emerald-700 rounded-lg"><CheckCircle2 className="inline w-4 h-4 mr-1"/>Verify Passport</button><a className="px-3 py-2 bg-slate-800 rounded-lg" href={`${API_BASE}/passport/${analysisId}/export?format=json`} download><Download className="inline w-4 h-4 mr-1"/>JSON</a></div>
    </div>}
  </section>;
}
