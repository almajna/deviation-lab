import { lazy, Suspense, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Laboratory } from './Laboratory';
import './site.css';

const ReplayLab = lazy(() => import('./ReplayLab'));

function App() {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  return <>
    <a className="site-skip" href="#laboratory">Skip to interactive laboratory</a>
    <header className="site-header"><div className="site-container site-header-inner">
      <a className="site-brand" href="#top" aria-label="DEVIATION, home">DEVIATION<span aria-hidden="true"> /</span></a>
      <nav className="site-nav" aria-label="Main navigation"><a href="#laboratory">Laboratory</a><a href="#research">Research</a><a href="#method">Method</a></nav>
      <a className="site-source" href="https://github.com/almajna/deviation-lab">Source <span aria-hidden="true">↗</span></a>
    </div></header>
    <main id="top">
      <section className="site-hero site-container" aria-labelledby="hero-title">
        <div className="site-hero-copy"><p className="site-overline"><span className="site-dot" />An interactive research laboratory</p>
          <h1 id="hero-title">Who gets the <em>compute?</em></h1>
          <p className="site-lede">AI systems have limited resources. When several tasks compete, an allocator must decide where compute is most valuable—and whether to trust the reports behind that decision.</p>
          <div className="site-actions"><a className="site-primary" href="#laboratory">Try the laboratory <span aria-hidden="true">↘</span></a><a className="site-text-link" href="#research">Explore the evidence <span aria-hidden="true">↗</span></a></div>
        </div>
        <div className="site-hero-visual" aria-label="Allocation objective: maximize expected quality subject to a compute budget">
          <div className="site-visual-head"><span>THE ALLOCATION PROBLEM</span><span>01 / 03</span></div>
          <div className="site-orbit" aria-hidden="true"><div className="site-orbit-ring site-ring-one"/><div className="site-orbit-ring site-ring-two"/><div className="site-orbit-ring site-ring-three"/><div className="site-orbit-axis site-axis-h"/><div className="site-orbit-axis site-axis-v"/><div className="site-orbit-core">x<sub>im</sub></div><div className="site-orbit-node site-node-a"/><div className="site-orbit-node site-node-b"/><div className="site-orbit-node site-node-c"/></div>
          <div className="site-formula"><span>max</span> ∑<sub>i,m</sub> q̂<sub>im</sub>x<sub>im</sub><small>subject to &nbsp; ∑<sub>i,m</sub> c<sub>im</sub>x<sub>im</sub> ≤ B</small></div>
          <div className="site-visual-foot"><span>REPORTS → ALLOCATION</span><span>CONSTRAINED BY BUDGET</span></div>
        </div>
      </section>
      <div className="site-ticker"><div className="site-container site-ticker-inner"><span>01 / SIMULATE</span><span>02 / INSPECT THE MATH</span><span>03 / EXPLORE RECORDED EVIDENCE</span><span>NO LIVE INFERENCE</span></div></div>
      <section className="site-lab-section" id="laboratory" aria-label="Interactive synthetic allocation laboratory"><div className="site-container"><Laboratory /></div></section>
      <section className="site-research site-container" id="research" aria-labelledby="research-title"><div className="site-section-heading"><div><p className="site-overline">02 / Recorded research</p><h2 id="research-title">The evidence has<br/><em>the final word.</em></h2></div><p>These replays are separate from the hypothetical laboratory above. They trace controlled experiments and their limitations.</p></div>
        <div className="site-evidence-grid"><article className="site-evidence-card"><div className="site-card-top"><span>01 / ROUTING</span><span className="site-verdict">INCONCLUSIVE</span></div><h3>Can reported tokens affect routing?</h3><p>A controlled offline LiteLLM experiment tests whether provider-reported token counts influence later routing. The frozen success criterion was not established across the original run and independent rerun.</p><span className="site-card-bottom">PINNED ROUTER · RECORDED TRACES</span></article>
        <article className="site-evidence-card"><div className="site-card-top"><span>02 / ECONOMICS</span><span>RECORDED MODEL DECISIONS</span></div><h3>How did a model report?</h3><p>Inspect genuine recorded Qwen decisions in a synthetic allocation game and compare them with a retrospective conditional benchmark. The credits and game are simulated.</p><span className="site-card-bottom">RECORDED DECISIONS · BOUNDED CERTIFICATE</span></article></div>
        <div className="site-replay-action"><p>Examine the recorded traces, controls, calculations and source links.</p><button type="button" className="site-primary site-button" aria-expanded={evidenceOpen} aria-controls="recorded-evidence" onClick={() => setEvidenceOpen(!evidenceOpen)}>{evidenceOpen ? 'Close recorded evidence' : 'Open recorded evidence'} <span aria-hidden="true">{evidenceOpen ? '−' : '+'}</span></button></div>
        <div id="recorded-evidence">{evidenceOpen && <Suspense fallback={<p role="status">Loading recorded evidence…</p>}><ReplayLab /></Suspense>}</div>
      </section>
      <section className="site-method" id="method" aria-labelledby="method-title"><div className="site-container site-method-inner"><div><p className="site-overline">03 / Method</p><h2 id="method-title">Inspect the decision.<br/><em>Question the claim.</em></h2></div><div><p>DEVIATION studies allocation mechanisms under explicitly stated information, budgets and incentives. A synthetic demonstration illustrates a modeled mechanism; it is not evidence of a production vulnerability.</p><p>Recorded experiments retain their assumptions, negative findings and links to reproducible evidence. A bounded certificate applies only to its documented model and action space.</p><div className="site-method-links"><a href="https://github.com/almajna/deviation-lab">Repository ↗</a><a href="https://github.com/almajna/deviation-lab/pull/39">LiteLLM research ↗</a></div></div></div></section>
    </main><footer className="site-footer"><div className="site-container site-footer-inner"><a className="site-brand" href="#top">DEVIATION<span> /</span></a><span>RESOURCE ALLOCATION UNDER PRESSURE</span><a href="https://github.com/almajna/deviation-lab">VIEW SOURCE ↗</a></div></footer>
  </>;
}

createRoot(document.getElementById('root')!).render(<App />);
