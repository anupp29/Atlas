export type UserRole = 'L1' | 'L2' | 'L3' | 'SDM' | 'CLIENT';

export type HealthStatus = 'healthy' | 'warning' | 'critical';

export type IncidentPriority = 'P1' | 'P2' | 'P3';

export type TrustLevel = 'Observation' | 'L1 Assistance' | 'L1 Automation' | 'L2 Assistance' | 'L2 Automation';

export type IncidentStatus = 
  | 'ATLAS Analyzing'
  | 'Awaiting L1'
  | 'Awaiting L2'
  | 'Awaiting L3'
  | 'Awaiting Dual Approval'
  | 'Executing'
  | 'Resolved'
  | 'Failed'
  | 'Rolled Back'
  | 'Escalated to L2'
  | 'Escalated to L3'
  | 'L3 Manual Resolution';

export type ActionClass = 'Class 1' | 'Class 2' | 'Class 3';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface Client {
  id: string;
  name: string;
  health: HealthStatus;
  activeIncidents: number;
  slaCompliance: number;
  trustLevel: TrustLevel;
  lastActivity: string;
  complianceFlags?: ('PCI-DSS' | 'SOX')[];
}

export interface ServiceNode {
  id: string;
  name: string;
  technology: string;
  health: HealthStatus;
  criticality: 'High' | 'Medium' | 'Low';
  triggerMetric?: string;
  triggerValue?: string;
  lastDeployment?: string;
}

export interface Incident {
  id: string;
  clientId: string;
  clientName: string;
  priority: IncidentPriority;
  status: IncidentStatus;
  affectedServices: string[];
  detectedAt: string;
  slaDeadline: string;
  summary: string;
  businessImpact: string;
  services: ServiceNode[];
  deploymentCorrelation?: DeploymentCorrelation;
  historicalMatch?: HistoricalMatch;
  rootCause: RootCauseAssessment;
  alternativeHypotheses: AlternativeHypothesis[];
  recommendedAction: RecommendedAction;
  executionSteps?: ExecutionStep[];
  resolvedAt?: string;
  mttr?: string;
  approvedBy?: string;
}

export interface DeploymentCorrelation {
  changeId: string;
  description: string;
  deployedBy: string;
  deployedAt: string;
  cabRiskRating: 'Low' | 'Medium' | 'High';
  daysAgo: number;
}

export interface HistoricalMatch {
  incidentId: string;
  occurredAt: string;
  similarity: number;
  rootCause: string;
  resolution: string;
}

export interface RootCauseAssessment {
  diagnosis: string;
  confidence: number;
  factors: {
    historicalAccuracy: number;
    rootCauseCertainty: number;
    actionSafetyClass: number;
    evidenceFreshness: number;
  };
  vetoes?: string[];
}

export interface AlternativeHypothesis {
  hypothesis: string;
  evidenceFor: string[];
  evidenceAgainst: string[];
}

export interface RecommendedAction {
  playbookName: string;
  description: string;
  estimatedTime: string;
  riskClass: 'Low' | 'Medium';
  rollbackAvailable: boolean;
}

export interface ExecutionStep {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  timestamp?: string;
}

export interface ActivityFeedEntry {
  id: string;
  timestamp: string;
  clientName: string;
  clientHealth: HealthStatus;
  description: string;
  priority?: IncidentPriority;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  incidentId: string;
  client: string;
  actionType: string;
  actor: string;
  outcome: 'Success' | 'Failed' | 'Rolled Back';
  confidence?: number;
  details?: {
    reasoningChain: string;
    vetoes: string[];
    playbookSteps: string[];
    metricValues: Record<string, number>;
  };
}

export interface Playbook {
  id: string;
  name: string;
  technologyDomain: string;
  actionClass: ActionClass;
  estimatedTime: string;
  lastUsed: string;
  successRate: number;
  description: string;
  preValidation: string[];
  successCriteria: string[];
  rollbackProcedure: string;
  executionHistory: {
    date: string;
    client: string;
    outcome: 'Success' | 'Failed' | 'Rolled Back';
  }[];
}
