import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Shield, ArrowRight, Zap, Brain, GitBranch, Search, Radio, Radar, Activity, Lock, BarChart3, Users, CheckCircle2, Clock } from 'lucide-react';

const stats = [
  { label: 'Autonomous Resolution', value: '70%', sub: 'Incidents resolved without human intervention' },
  { label: 'Average MTTR', value: '3m 28s', sub: '10× faster than industry average' },
  { label: 'Root Cause Accuracy', value: '94%', sub: 'AI-driven diagnosis precision' },
  { label: 'Clients Monitored', value: '10', sub: 'Mission-critical enterprise environments' },
];

const pipelineSteps = [
  { icon: Radio, label: 'Signal Ingestion', desc: 'Real-time telemetry from 150+ metric streams per client' },
  { icon: Radar, label: 'Anomaly Detection', desc: 'Statistical + ML-based anomaly scoring with noise filtering' },
  { icon: GitBranch, label: 'Dependency Correlation', desc: 'Graph traversal across service topology and deployment history' },
  { icon: Search, label: 'Knowledge Base Search', desc: 'Vector similarity matching against 2,800+ historical incident records' },
  { icon: Brain, label: 'Root Cause Reasoning', desc: 'Multi-hypothesis evaluation with confidence scoring' },
  { icon: Shield, label: 'Action Selection & Governance', desc: 'Playbook matching with compliance veto checks (PCI-DSS, SOX)' },
  { icon: Zap, label: 'Incident Routing', desc: 'Intelligent routing to L1/L2/L3 based on complexity and trust level' },
];

const capabilities = [
  { icon: Activity, title: 'Real-Time Monitoring', desc: 'Continuous observability across all client environments with intelligent alerting and early warning detection.' },
  { icon: Brain, title: '7-Stage Intelligence Pipeline', desc: 'From signal ingestion through root cause reasoning to automated resolution — a complete AI-driven operations chain.' },
  { icon: Lock, title: 'Governance & Compliance', desc: 'Built-in PCI-DSS and SOX compliance workflows with dual-approval chains and immutable audit trails.' },
  { icon: BarChart3, title: 'Portfolio Analytics', desc: 'Cross-client SLA tracking, MTTR trends, trust level progression, and autonomous resolution metrics.' },
  { icon: Users, title: 'Role-Based Workspaces', desc: 'L1 triage consoles, L2 analysis workspaces, L3 engineering debug environments — each optimized for their workflow.' },
  { icon: CheckCircle2, title: 'Automated Resolution', desc: 'Pre-approved, versioned playbooks with automated execution, live metric recovery tracking, and auto-rollback.' },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="h-16 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <svg className="h-9 w-9 shrink-0" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="36" height="36" rx="7" fill="#1a2744"/>
              <path d="M18 26 L10 26 L18 10 L26 26 Z" fill="none" stroke="#0066CC" strokeWidth="1.8" strokeLinejoin="round"/>
              <path d="M18 26 L14 26 L18 18 L22 26 Z" fill="#0066CC"/>
              <circle cx="18" cy="10" r="1.8" fill="#38bdf8"/>
            </svg>
            <div>
              <span className="text-[15px] font-bold tracking-[0.15em] text-foreground">ATLAS</span>
              <span className="text-[9px] text-muted-foreground ml-2 uppercase tracking-[0.08em]">by Atos</span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <a href="#capabilities" className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">Capabilities</a>
            <a href="#pipeline" className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">Intelligence</a>
            <a href="#roles" className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">Roles</a>
            <Button onClick={() => navigate('/login')} className="bg-accent hover:bg-accent/90 text-accent-foreground text-[13px] h-9 px-5">
              Sign In <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent/8 border border-accent/15 mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span className="text-[11px] font-medium text-accent">Autonomous IT Operations Platform</span>
          </div>
          <h1 className="text-[42px] font-bold text-foreground leading-[1.15] tracking-tight">
            Intelligent Incident Detection,<br />Analysis & Resolution
          </h1>
          <p className="text-[16px] text-muted-foreground mt-5 max-w-2xl mx-auto leading-relaxed">
            ATLAS monitors mission-critical enterprise infrastructure, detects cascading incidents in real-time,
            and resolves them autonomously — with full transparency and compliance governance.
          </p>
          <div className="flex items-center justify-center gap-3 mt-8">
            <Button onClick={() => navigate('/login')} className="bg-accent hover:bg-accent/90 text-accent-foreground text-[14px] h-11 px-8 font-semibold">
              Access Platform <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
            <Button variant="outline" onClick={() => document.getElementById('pipeline')?.scrollIntoView({ behavior: 'smooth' })} className="text-[14px] h-11 px-6">
              Explore Intelligence
            </Button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 px-6 border-t border-border bg-card">
        <div className="max-w-6xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-[32px] font-bold text-foreground tabular-nums">{stat.value}</p>
              <p className="text-[13px] font-semibold text-foreground mt-1">{stat.label}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">{stat.sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-[28px] font-bold text-foreground">Platform Capabilities</h2>
            <p className="text-[14px] text-muted-foreground mt-2">Enterprise-grade AIOps for mission-critical infrastructure</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {capabilities.map((cap) => (
              <div key={cap.title} className="bg-card border border-border rounded-lg p-5">
                <div className="h-9 w-9 rounded-lg bg-accent/8 flex items-center justify-center mb-3">
                  <cap.icon className="h-4.5 w-4.5 text-accent" />
                </div>
                <h3 className="text-[14px] font-semibold text-foreground">{cap.title}</h3>
                <p className="text-[12px] text-muted-foreground mt-1.5 leading-relaxed">{cap.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="py-20 px-6 bg-card border-t border-b border-border">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-[28px] font-bold text-foreground">7-Stage Intelligence Pipeline</h2>
            <p className="text-[14px] text-muted-foreground mt-2">From anomaly detection to autonomous resolution in under 5 seconds</p>
          </div>
          <div className="space-y-0">
            {pipelineSteps.map((step, i) => (
              <div key={step.label} className="flex items-start gap-4 py-4 border-b border-border last:border-0">
                <div className="flex items-center gap-3 shrink-0">
                  <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center text-[12px] font-bold text-accent">
                    {i + 1}
                  </div>
                  <step.icon className="h-4 w-4 text-accent" />
                </div>
                <div>
                  <h3 className="text-[13px] font-semibold text-foreground">{step.label}</h3>
                  <p className="text-[12px] text-muted-foreground mt-0.5">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Roles */}
      <section id="roles" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-[28px] font-bold text-foreground">Role-Based Workspaces</h2>
            <p className="text-[14px] text-muted-foreground mt-2">Every role gets a purpose-built interface</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { role: 'L1 Engineer', desc: 'Compact triage console for rapid approve/escalate decisions. Simplified briefings, operator checklists, clear decision signals.', color: 'bg-accent/8 text-accent' },
              { role: 'L2 Engineer', desc: 'Full analysis workspace with dependency graphs, historical matching, confidence breakdowns, and alternative hypothesis evaluation.', color: 'bg-accent/8 text-accent' },
              { role: 'L3 / SRE', desc: 'Engineering debug environment with code diffs, configuration regressions, stack traces, and runtime failure signatures.', color: 'bg-status-critical/8 text-status-critical' },
              { role: 'Service Delivery Manager', desc: 'Portfolio oversight with cross-client SLA tracking, MTTR trends, trust level management, and client onboarding.', color: 'bg-primary/8 text-primary' },
              { role: 'Client Portal', desc: 'Read-only transparency view with plain-English status updates, incident history, and SLA compliance metrics.', color: 'bg-status-healthy/8 text-status-healthy' },
            ].map((r) => (
              <div key={r.role} className="bg-card border border-border rounded-lg p-5">
                <span className={`text-[10px] font-semibold px-2 py-1 rounded uppercase tracking-wider ${r.color}`}>{r.role}</span>
                <p className="text-[12px] text-muted-foreground mt-3 leading-relaxed">{r.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 bg-primary">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-[24px] font-bold text-primary-foreground">Ready to transform your IT operations?</h2>
          <p className="text-[14px] text-primary-foreground/60 mt-3">
            ATLAS is deployed and operational. Sign in to access your dashboard.
          </p>
          <Button onClick={() => navigate('/login')} className="bg-accent hover:bg-accent/90 text-accent-foreground text-[14px] h-11 px-8 font-semibold mt-6">
            Sign In to ATLAS <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-border bg-card">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground">ATLAS AIOps Platform — Atos SE</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground">© {new Date().getFullYear()} Internal Use Only</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
