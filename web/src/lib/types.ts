export interface VisualizationConfig {
  x_key: string;
  y_keys: string[];
  colors: string[];
}

export type ChartType = "bar_chart" | "line_chart" | "area_chart" | "donut_chart" | "table" | "text";

export interface ChatResponse {
  explanation: string;
  visualization_type: ChartType;
  config: VisualizationConfig;
  data: Record<string, unknown>[];
  conversation_id?: string;
}


export interface Transaction {
  transaction_id: string;
  transaction_code: number;
  date: string;
  merchant: string;
  amount: number;
  currency: string;
  department: string;
  employee: string;
  transaction_category: number;
  transaction_type: string;
  description: string;
  items: { description: string; amount: number }[];
  notes: { author: string; text: string; timestamp: string }[];
  tags: string[];
  compliance_history: ComplianceRecord[];
  approval_status: "pending" | "approved" | "denied" | "not_required";
  reasoning: string | null;
  payment_method: "corporate_card" | "personal";
  is_reimbursable: boolean;
  merchant_city?: string;
  merchant_state?: string;
  merchant_country?: string;
  merchant_category_code?: number | null;
  debit_or_credit?: string;
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
  code: number | null;
  department: string;
  category: string | null;
  severity: string;
  source?: "baseline" | "custom";
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
  summary?: string;
  visualization_type: "bar_chart" | "line_chart" | "area_chart" | "table" | "text";
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
  employee_context?: {
    employee: string;
    total_spent_ytd: number;
    transaction_count: number;
    recent_transactions?: { transaction_id?: string; amount?: number; merchant?: string; date?: string }[];
  };
  department_context?: {
    department: string;
    total_spent_ytd: number;
    monthly_avg_spend: number;
    transaction_count: number;
    annual_budget?: number;
    monthly_budget?: number;
    budget_remaining?: number;
    budget_used_pct?: number;
  };
  status: string;
}

export interface TransactionCode {
  code: number;
  department: string;
  count: number;
  total: number;
}

export interface TransactionType {
  name: string;
  count: number;
  total: number;
  min_amount: number;
  max_amount: number;
  avg_amount: number;
}
