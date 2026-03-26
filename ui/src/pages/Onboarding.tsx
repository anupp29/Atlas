import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Shield, ArrowRight, ArrowLeft, CheckCircle2, Users, Server, FileCheck, Zap, Bell, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TrustLevel } from '@/types/atlas';
import { toast } from 'sonner';

interface OnboardingData {
  clientName: string;
  industry: string;
  environment: string;
  services: string[];
  newService: string;
  complianceFlags: string[];
  trustLevel: TrustLevel;
  l1Engineer: string;
  l2Engineer: string;
  l3Engineer: string;
  slaTarget: string;
  notes: string;
}

const industries = ['Financial Services', 'Healthcare', 'Government', 'Transportation', 'Retail', 'Manufacturing', 'Technology', 'Telecommunications'];
const environments = ['Production', 'Production + Staging', 'Production + Staging + Dev'];
const trustLevels: TrustLevel[] = ['Observation', 'L1 Assistance', 'L1 Automation', 'L2 Assistance', 'L2 Automation'];
const complianceOptions = ['PCI-DSS', 'SOX', 'HIPAA', 'GDPR', 'ISO 27001'];

const engineers = {
  l1: ['A. Petrov', 'K. Singh', 'M. Fernandez', 'R. Okonkwo'],
  l2: ['S. Weber', 'J. Kim', 'L. Andersen', 'P. Dubois'],
  l3: ['J. Nakamura', 'T. Müller', 'A. Kowalski', 'C. Rossi'],
};

// Industry-specific service suggestions
const serviceSuggestions: Record<string, string[]> = {
  'Financial Services': ['PaymentGateway', 'TransactionProcessor', 'FraudEngine', 'CoreBanking API', 'KYC/AML Service', 'Card Processing', 'Settlement Engine', 'Reporting API', 'AuthService', 'Redis Cache'],
  'Healthcare': ['PatientPortal', 'EHR System', 'HL7 FHIR API', 'Appointment Scheduler', 'Lab Results Service', 'Prescription Management', 'AuthService', 'DICOM Server', 'Notification Service'],
  'Government': ['CitizenPortal', 'Identity Verification', 'Document Processing', 'Case Management', 'Notification Service', 'AuthService', 'Audit Trail Service', 'API Gateway', 'Data Lake Ingestion'],
  'Transportation': ['TicketingGateway', 'Schedule Service', 'Fleet Management', 'Passenger Information', 'Payment Processing', 'AuthService', 'Real-Time Tracking', 'Notification Service'],
  'Retail': ['ProductCatalog', 'SearchService', 'CartService', 'CheckoutProcessor', 'InventoryManager', 'Redis Cache Cluster', 'CDN Origin', 'Recommendation Engine', 'AuthService'],
  'Manufacturing': ['SCADA Interface', 'Quality Control API', 'Supply Chain Tracker', 'IoT Data Ingestion', 'Production Planner', 'AuthService', 'Reporting Dashboard', 'Alert Manager'],
  'Technology': ['API Gateway', 'User Service', 'Notification Service', 'Analytics Pipeline', 'Search Index', 'AuthService', 'CDN Origin', 'WebSocket Server', 'Queue Processor'],
  'Telecommunications': ['Billing Engine', 'Provisioning Service', 'Network Monitor', 'Customer Portal', 'CDR Processing', 'AuthService', 'SIP Gateway', 'SMS Gateway'],
};

const steps = [
  { label: 'Client Details', icon: Users, desc: 'Organization profile' },
  { label: 'Services', icon: Server, desc: 'Monitored infrastructure' },
  { label: 'Team Assignment', icon: Users, desc: 'Engineer allocation' },
  { label: 'Compliance & Trust', icon: FileCheck, desc: 'Governance configuration' },
  { label: 'Review & Activate', icon: Zap, desc: 'Final confirmation' },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [notifiedEngineers, setNotifiedEngineers] = useState<string[]>([]);
  const [data, setData] = useState<OnboardingData>({
    clientName: '', industry: '', environment: '', services: [],
    newService: '', complianceFlags: [], trustLevel: 'Observation',
    l1Engineer: '', l2Engineer: '', l3Engineer: '', slaTarget: '99.5', notes: '',
  });

  const update = (partial: Partial<OnboardingData>) => setData(prev => ({ ...prev, ...partial }));

  const addService = (name?: string) => {
    const svc = (name || data.newService).trim();
    if (svc && !data.services.includes(svc)) {
      update({ services: [...data.services, svc], newService: '' });
    }
  };

  const toggleCompliance = (flag: string) => {
    update({
      complianceFlags: data.complianceFlags.includes(flag)
        ? data.complianceFlags.filter(f => f !== flag)
        : [...data.complianceFlags, flag],
    });
  };

  const canAdvance = () => {
    if (step === 0) return data.clientName && data.industry && data.environment;
    if (step === 1) return data.services.length >= 1;
    if (step === 2) return data.l1Engineer && data.l2Engineer && data.l3Engineer;
    if (step === 3) return true;
    return true;
  };

  const suggestions = data.industry ? (serviceSuggestions[data.industry] || []).filter(s => !data.services.includes(s)) : [];

  const handleComplete = () => {
    setIsComplete(true);

    // Simulate notifying engineers
    const assigned = [data.l1Engineer, data.l2Engineer, data.l3Engineer].filter(Boolean);
    let delay = 500;
    assigned.forEach((eng) => {
      setTimeout(() => {
        setNotifiedEngineers(prev => [...prev, eng]);
        toast.success(`${eng} notified`, {
          description: `Assigned to ${data.clientName} — ${data.services.length} services now in their dashboard`,
          icon: <Bell className="h-4 w-4" />,
        });
      }, delay);
      delay += 800;
    });

    setTimeout(() => navigate('/portfolio'), 4000);
  };

  if (isComplete) {
    return (
      <div className="flex items-center justify-center px-4 py-16">
        <div className="max-w-md text-center">
          <div className="h-16 w-16 rounded-full bg-status-healthy/10 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="h-8 w-8 text-status-healthy" />
          </div>
          <h1 className="text-[20px] font-bold text-foreground">Client Onboarded Successfully</h1>
          <p className="text-[13px] text-muted-foreground mt-2 leading-relaxed">
            <span className="font-semibold text-foreground">{data.clientName}</span> has been activated on the ATLAS platform.
            {data.services.length} services are now being monitored.
          </p>

          {/* Notification status */}
          <div className="mt-6 bg-card border border-border rounded-lg p-4 text-left">
            <p className="text-[11px] font-semibold text-foreground uppercase tracking-wider mb-3">Team Notifications</p>
            <div className="space-y-2">
              {[
                { label: 'L1', name: data.l1Engineer },
                { label: 'L2', name: data.l2Engineer },
                { label: 'L3', name: data.l3Engineer },
              ].map(({ label, name }) => {
                const isNotified = notifiedEngineers.includes(name);
                return (
                  <div key={label} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-accent/8 text-accent">{label}</span>
                      <span className="text-[12px] text-foreground">{name}</span>
                    </div>
                    {isNotified ? (
                      <div className="flex items-center gap-1 text-status-healthy">
                        <CheckCircle2 className="h-3 w-3" />
                        <span className="text-[10px] font-medium">Notified</span>
                      </div>
                    ) : (
                      <span className="text-[10px] text-muted-foreground atlas-pulse">Sending...</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground mt-4">Redirecting to Portfolio Overview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-4">
      {/* Step indicator */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((s, i) => {
          const Icon = s.icon;
          const isActive = i === step;
          const isDone = i < step;
          return (
            <div key={s.label} className="flex items-center">
              <div className="flex flex-col items-center gap-1 min-w-[80px]">
                <div className={cn(
                  'h-9 w-9 rounded-full flex items-center justify-center transition-all border-2',
                  isDone && 'bg-status-healthy/10 border-status-healthy/30',
                  isActive && 'bg-accent/10 border-accent',
                  !isActive && !isDone && 'bg-muted border-border',
                )}>
                  {isDone ? <CheckCircle2 className="h-4 w-4 text-status-healthy" /> : <Icon className={cn('h-4 w-4', isActive ? 'text-accent' : 'text-muted-foreground')} />}
                </div>
                <span className={cn('text-[10px] font-medium', isActive ? 'text-accent' : isDone ? 'text-status-healthy' : 'text-muted-foreground')}>{s.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div className={cn('h-[2px] w-8 lg:w-16', isDone ? 'bg-status-healthy/40' : 'bg-border')} />
              )}
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <div className="bg-card border border-border rounded-lg p-6 shadow-sm min-h-[400px]">
        {step === 0 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-[16px] font-semibold text-foreground">Client Details</h2>
              <p className="text-[12px] text-muted-foreground mt-1">Enter the organization's profile information.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Organization Name *</label>
                <Input value={data.clientName} onChange={e => update({ clientName: e.target.value })} placeholder="e.g. FinanceCore Holdings" className="h-10 text-[13px]" />
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Industry *</label>
                <Select value={data.industry} onValueChange={v => update({ industry: v })}>
                  <SelectTrigger className="h-10 text-[13px]"><SelectValue placeholder="Select industry" /></SelectTrigger>
                  <SelectContent>{industries.map(i => <SelectItem key={i} value={i}>{i}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Environment Scope *</label>
                <Select value={data.environment} onValueChange={v => update({ environment: v })}>
                  <SelectTrigger className="h-10 text-[13px]"><SelectValue placeholder="Select scope" /></SelectTrigger>
                  <SelectContent>{environments.map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-[16px] font-semibold text-foreground">Monitored Services</h2>
              <p className="text-[12px] text-muted-foreground mt-1">Add the services and infrastructure ATLAS will monitor for {data.clientName || 'this client'}.</p>
            </div>

            {/* AI-suggested services */}
            {suggestions.length > 0 && (
              <div className="border border-accent/20 bg-accent/[0.03] rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2.5">
                  <Sparkles className="h-3.5 w-3.5 text-accent" />
                  <span className="text-[11px] font-semibold text-accent uppercase tracking-wider">Suggested for {data.industry}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {suggestions.slice(0, 8).map(s => (
                    <button
                      key={s}
                      onClick={() => addService(s)}
                      className="text-[11px] px-2.5 py-1.5 rounded-lg border border-accent/20 text-accent hover:bg-accent/10 transition-colors"
                    >
                      + {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <Input value={data.newService} onChange={e => update({ newService: e.target.value })} placeholder="e.g. PaymentGateway, AuthService, Redis Cluster..." className="h-10 text-[13px] flex-1" onKeyDown={e => e.key === 'Enter' && addService()} />
              <Button onClick={() => addService()} className="bg-accent hover:bg-accent/90 text-accent-foreground h-10 px-4 text-[13px]">Add</Button>
            </div>
            {data.services.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {data.services.map((s, i) => (
                  <div key={i} className="flex items-center justify-between border border-border rounded-lg px-3 py-2.5 bg-muted/20">
                    <div className="flex items-center gap-2">
                      <Server className="h-3.5 w-3.5 text-accent" />
                      <span className="text-[12px] text-foreground font-medium">{s}</span>
                    </div>
                    <button onClick={() => update({ services: data.services.filter((_, j) => j !== i) })} className="text-[10px] text-muted-foreground hover:text-status-critical">×</button>
                  </div>
                ))}
              </div>
            )}
            {data.services.length === 0 && (
              <div className="py-12 text-center border border-dashed border-border rounded-lg">
                <Server className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
                <p className="text-[12px] text-muted-foreground">No services added yet. Add at least one service to monitor.</p>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-[16px] font-semibold text-foreground">Team Assignment</h2>
              <p className="text-[12px] text-muted-foreground mt-1">Assign L1, L2, and L3 engineers to {data.clientName || 'this client'}. They will be notified immediately upon activation.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(['l1', 'l2', 'l3'] as const).map(level => {
                const label = level.toUpperCase();
                const desc = level === 'l1' ? 'First-line triage & approval' : level === 'l2' ? 'Investigation & root cause analysis' : 'Engineering debugging & SRE';
                const key = `${level}Engineer` as keyof OnboardingData;
                return (
                  <div key={level} className="border border-border rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded uppercase', level === 'l3' ? 'bg-status-critical/8 text-status-critical' : level === 'l2' ? 'bg-accent/8 text-accent' : 'bg-status-healthy/8 text-status-healthy')}>{label}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mb-3">{desc}</p>
                    <Select value={data[key] as string} onValueChange={v => update({ [key]: v })}>
                      <SelectTrigger className="h-9 text-[12px]"><SelectValue placeholder={`Assign ${label}`} /></SelectTrigger>
                      <SelectContent>{engineers[level].map(e => <SelectItem key={e} value={e}>{e}</SelectItem>)}</SelectContent>
                    </Select>
                    {data[key] && (
                      <p className="text-[10px] text-muted-foreground mt-2 flex items-center gap-1">
                        <Bell className="h-3 w-3" /> Will be notified on activation
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-[16px] font-semibold text-foreground">Compliance & Trust Configuration</h2>
              <p className="text-[12px] text-muted-foreground mt-1">Set compliance requirements and initial trust level for {data.clientName || 'this client'}.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-2">Compliance Frameworks</label>
                <div className="flex flex-wrap gap-2">
                  {complianceOptions.map(flag => (
                    <button key={flag} onClick={() => toggleCompliance(flag)} className={cn(
                      'px-3 py-1.5 rounded-lg border text-[11px] font-medium transition-colors',
                      data.complianceFlags.includes(flag) ? 'bg-accent/10 border-accent/30 text-accent' : 'border-border text-muted-foreground hover:border-accent/20',
                    )}>{flag}</button>
                  ))}
                </div>
                {data.complianceFlags.includes('PCI-DSS') || data.complianceFlags.includes('SOX') ? (
                  <p className="text-[10px] text-status-warning mt-2">⚠ PCI-DSS/SOX clients require dual-approval for production changes.</p>
                ) : null}
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-2">Initial Trust Level</label>
                <Select value={data.trustLevel} onValueChange={v => update({ trustLevel: v as TrustLevel })}>
                  <SelectTrigger className="h-10 text-[13px]"><SelectValue /></SelectTrigger>
                  <SelectContent>{trustLevels.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground mt-1.5">New clients typically start at "Observation" and progress based on resolution success.</p>
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">SLA Target (%)</label>
                <Input value={data.slaTarget} onChange={e => update({ slaTarget: e.target.value })} className="h-10 text-[13px] font-mono w-24" />
              </div>
              <div>
                <label className="text-[12px] font-medium text-foreground block mb-1.5">Additional Notes</label>
                <Textarea value={data.notes} onChange={e => update({ notes: e.target.value })} placeholder="Special requirements, escalation contacts..." className="h-20 text-[12px]" />
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-[16px] font-semibold text-foreground">Review & Activate</h2>
              <p className="text-[12px] text-muted-foreground mt-1">Confirm the configuration before activating monitoring for {data.clientName}.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-border rounded-lg p-4">
                <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Organization</h3>
                <p className="text-[14px] font-semibold text-foreground">{data.clientName}</p>
                <p className="text-[12px] text-muted-foreground">{data.industry} · {data.environment}</p>
              </div>
              <div className="border border-border rounded-lg p-4">
                <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Services ({data.services.length})</h3>
                <div className="flex flex-wrap gap-1">
                  {data.services.map(s => <span key={s} className="text-[10px] bg-muted px-2 py-0.5 rounded text-foreground font-medium">{s}</span>)}
                </div>
              </div>
              <div className="border border-border rounded-lg p-4">
                <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Engineering Team</h3>
                <div className="space-y-1 text-[12px]">
                  <p><span className="text-muted-foreground">L1:</span> <span className="text-foreground font-medium">{data.l1Engineer}</span></p>
                  <p><span className="text-muted-foreground">L2:</span> <span className="text-foreground font-medium">{data.l2Engineer}</span></p>
                  <p><span className="text-muted-foreground">L3:</span> <span className="text-foreground font-medium">{data.l3Engineer}</span></p>
                </div>
                <p className="text-[10px] text-accent mt-2 flex items-center gap-1">
                  <Bell className="h-3 w-3" /> All engineers will be notified immediately
                </p>
              </div>
              <div className="border border-border rounded-lg p-4">
                <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Governance</h3>
                <p className="text-[12px] text-foreground">Trust: <span className="font-medium">{data.trustLevel}</span></p>
                <p className="text-[12px] text-foreground">SLA: <span className="font-mono font-medium">{data.slaTarget}%</span></p>
                {data.complianceFlags.length > 0 && (
                  <div className="flex gap-1 mt-1.5">
                    {data.complianceFlags.map(f => <span key={f} className="text-[9px] font-semibold bg-status-warning/10 text-status-warning px-1.5 py-0.5 rounded uppercase">{f}</span>)}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button variant="ghost" onClick={() => step > 0 ? setStep(step - 1) : navigate('/portfolio')} className="text-[12px] text-muted-foreground gap-1.5">
          <ArrowLeft className="h-3.5 w-3.5" /> {step > 0 ? 'Previous' : 'Cancel'}
        </Button>
        {step < 4 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canAdvance()} className="bg-accent hover:bg-accent/90 text-accent-foreground text-[13px] h-10 px-6 gap-1.5">
            Continue <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        ) : (
          <Button onClick={handleComplete} className="bg-status-healthy hover:bg-status-healthy/90 text-white text-[13px] h-10 px-8 font-semibold gap-1.5">
            <Zap className="h-4 w-4" /> Activate Monitoring
          </Button>
        )}
      </div>
    </div>
  );
}
