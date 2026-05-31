import type {
  ChatMessage,
  ChatResponse,
  ComplianceRule,
  ComplianceResult,
  PendingApproval,
  ReportPayload,
  Transaction,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}/api${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }

  return res.json();
}

// Feature 1: Chat
export async function sendChatMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

// Feature 2: Compliance
export async function scanCompliance(
  department?: string,
  transactionIds?: string[]
): Promise<{ results: Record<string, ComplianceResult>; total_scanned: number; violations_found: number }> {
  return request("/compliance/scan", {
    method: "POST",
    body: JSON.stringify({ department, transaction_ids: transactionIds }),
  });
}

export async function createRule(rule: {
  text: string;
  department: string;
  category: string;
  severity: string;
}): Promise<ComplianceRule> {
  return request<ComplianceRule>("/rules", {
    method: "POST",
    body: JSON.stringify(rule),
  });
}

export async function listRules(): Promise<ComplianceRule[]> {
  return request<ComplianceRule[]>("/rules");
}

// Feature 3: Approval
export async function submitForApproval(): Promise<{ message: string; status: string }> {
  return request("/approve/submit", { method: "POST" });
}

export async function resumeApproval(
  transactionId: string,
  approved: boolean
): Promise<{ transaction_id: string; status: string; message: string }> {
  return request("/approve/resume", {
    method: "POST",
    body: JSON.stringify({ transaction_id: transactionId, approved }),
  });
}

export async function getPendingApprovals(): Promise<{
  pending_approvals: PendingApproval[];
  total: number;
}> {
  return request("/approve/pending");
}

// Feature 4: Reports
export async function compileReport(params: {
  transaction_ids?: string[];
  department?: string;
  date_from?: string;
  date_to?: string;
}): Promise<{ report_payload: ReportPayload; compliance_results: Record<string, ComplianceResult>; error?: string }> {
  return request("/reports/compile", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// Transactions
export async function getTransactions(params: {
  department?: string;
  category?: string;
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<{ transactions: Transaction[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params.department) searchParams.set("department", params.department);
  if (params.category) searchParams.set("category", params.category);
  if (params.status) searchParams.set("status", params.status);
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.offset) searchParams.set("offset", String(params.offset));

  const qs = searchParams.toString();
  return request(`/transactions${qs ? `?${qs}` : ""}`);
}

export async function getDepartments(): Promise<{
  departments: { name: string; count: number; total: number; avg: number }[];
}> {
  return request("/transactions/departments");
}

export async function getCategories(): Promise<{
  categories: { name: string; count: number; total: number; avg: number }[];
}> {
  return request("/transactions/categories");
}
