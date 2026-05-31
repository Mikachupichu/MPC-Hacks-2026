export interface VisualizationConfig {
  x_key: string;
  y_keys: string[];
  colors: string[];
}

export interface ChatResponse {
  explanation: string;
  visualization_type: "bar_chart" | "line_chart" | "table" | "text";
  config: VisualizationConfig;
  data: Record<string, unknown>[];
}

export interface Transaction {
  transaction_id: string;
  date: string;
  merchant: string;
  amount: number;
  currency: string;
  department: string;
  employee: string;
  employee_id: string;
  category: string;
  description: string;
  items: { description: string; amount: number }[];
  notes: { author: string; text: string; timestamp: string }[];
  tags: string[];
  compliance_history: ComplianceRecord[];
  approval_status: "pending" | "approved" | "denied" | "not_required";
  payment_method: "corporate_card" | "personal";
  is_reimbursable: boolean;
}

export interface ComplianceRecord {
  scanned_at: string;
  status: "Compliant" | "Violation";
  severity: "Low" | "Medium" | "High";
  reasoning: string;
}

export interface ComplianceResult {
  transaction_id: string;
  status: "Compliant" | "Violation";
  severity: "Low" | "Medium" | "High";
  reasoning: string;
}

export interface ComplianceRule {
  id: string;
  text: string;
  department: string;
  category: string;
  severity: string;
}

export interface ReportPayload {
  report_title: string;
  generated_at: string;
  executive_summary: {
    text: string;
    total_transactions: number;
    total_spent: number;
    compliant_count: number;
    violation_count: number;
    compliance_rate: number;
    total_pending: number;
  };
  compliance_health: {
    status: "Good" | "Needs Attention" | "Critical";
    by_department: { department: string; compliant: number; violations: number; total: number }[];
    by_category: { category: string; compliant: number; violations: number; total: number }[];
  };
  sections: ReportSection[];
}

export interface ReportSection {
  title: string;
  visualization_type: "bar_chart" | "line_chart" | "table" | "text";
  config: VisualizationConfig;
  data: Record<string, unknown>[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string | ChatResponse;
}

export interface PendingApproval {
  transaction_id: string;
  transaction: Transaction;
  compliance_results: ComplianceResult;
  status: string;
}
