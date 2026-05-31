"use client";

import { useEffect, useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  Badge,
  Grid,
  Col,
} from "@tremor/react";
import { toast } from "sonner";
import { resumeApproval, getPendingApprovals } from "@/lib/api";
import type { PendingApproval } from "@/lib/types";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

export default function ApprovalPanel() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(true);

  const fetchApprovals = async () => {
    try {
      const data = await getPendingApprovals();
      setApprovals(data.pending_approvals);
    } catch {
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDecision = async (transactionId: string, approved: boolean) => {
    setActing(transactionId);
    try {
      const result = await resumeApproval(transactionId, approved);
      toast.success(result.message);
      setApprovals((prev) => prev.filter((a) => a.transaction_id !== transactionId));
    } catch {
      toast.error("Failed to process decision");
    } finally {
      setActing(null);
    }
  };

  return (
    <Card className={approvals.length > 0 ? "ring-2 ring-amber-400 dark:ring-amber-600" : "" + " p-4"}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Title>Pending Approvals</Title>
          {approvals.length > 0 && (
            <Badge color="amber" size="xs">{approvals.length}</Badge>
          )}
        </div>
        {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
      </button>

      {!collapsed && (
        <>
          {loading ? (
            <Text className="mt-2">Loading pending approvals...</Text>
          ) : approvals.length === 0 ? (
            <Text className="mt-2 text-emerald-600">No pending approvals. All caught up!</Text>
          ) : (
            <>
              <Text className="mt-1 mb-4 text-gray-500 text-sm">
                {approvals.length} transaction{approvals.length !== 1 ? "s" : ""} awaiting your decision
              </Text>

              <div className="space-y-4">
                {approvals.map((approval) => {
                  const txn = approval.transaction;
                  const compliance = approval.compliance_results;
                  const isViolation = compliance?.status === "Violation";
                  const empCtx = approval.employee_context;
                  const deptCtx = approval.department_context;

                  return (
                    <Card key={approval.transaction_id} className="border border-gray-200 dark:border-gray-700">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <Title className="text-base">{txn.merchant}</Title>
                            <Badge color={isViolation ? "red" : "emerald"} size="xs">
                              {compliance?.status || "Pending"}
                            </Badge>
                            {isViolation && <AlertTriangle className="h-4 w-4 text-red-500" />}
                          </div>
                          <Text className="text-sm text-gray-500 mt-0.5">
                            {approval.transaction_id} &middot; {txn.date} &middot; {txn.transaction_type}
                          </Text>
                        </div>
                        <Text className="text-xl font-bold">
                          ${(txn.amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </Text>
                      </div>

                      {/* Context grid */}
                      <Grid numItems={1} numItemsSm={3} className="gap-4 mt-4">
                        <Col>
                          <Text className="text-xs font-medium text-gray-500 uppercase tracking-wide">Transaction</Text>
                          <div className="mt-1 space-y-1 text-sm">
                            <Text>Department: <Badge size="xs">{txn.department || "—"}</Badge></Text>
                            <Text>Employee: <span className="font-medium">{txn.employee || "—"}</span></Text>
                            <Text>Type: {txn.transaction_type}</Text>
                            <Text className="text-xs text-gray-400 italic">{txn.description}</Text>
                          </div>
                        </Col>

                        <Col>
                          <Text className="text-xs font-medium text-gray-500 uppercase tracking-wide">Employee YTD</Text>
                          <div className="mt-1 space-y-1 text-sm">
                            {empCtx ? (
                              <>
                                <Text>Spent: <span className="font-semibold">${(empCtx.total_spent_ytd || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></Text>
                                <Text>Transactions: {empCtx.transaction_count}</Text>
                                {empCtx.recent_transactions && empCtx.recent_transactions.length > 0 && (
                                  <Text className="text-xs text-gray-400">
                                    Last: {empCtx.recent_transactions[0].merchant} (${(empCtx.recent_transactions[0].amount || 0).toFixed(2)})
                                  </Text>
                                )}
                              </>
                            ) : (
                              <Text className="text-gray-400">No history</Text>
                            )}
                          </div>
                        </Col>

                        <Col>
                          <Text className="text-xs font-medium text-gray-500 uppercase tracking-wide">Department YTD</Text>
                          <div className="mt-1 space-y-1 text-sm">
                            {deptCtx ? (
                              <>
                                <Text>Spent: <span className="font-semibold">${(deptCtx.total_spent_ytd || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></Text>
                                {deptCtx.annual_budget && (
                                  <>
                                    <Text>Budget: <span className="font-semibold">${deptCtx.annual_budget.toLocaleString("en-US", { minimumFractionDigits: 0 })}</span></Text>
                                    <Text>Remaining: <span className={`font-semibold ${(deptCtx.budget_remaining ?? 0) < 0 ? "text-red-600" : "text-emerald-600"}`}>
                                      ${((deptCtx.budget_remaining ?? 0)).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                                    </span></Text>
                                  </>
                                )}
                                {typeof deptCtx.budget_used_pct === "number" && (
                                  <div className="mt-1 h-1.5 w-full rounded-full bg-gray-200">
                                    <div
                                      className={`h-1.5 rounded-full ${deptCtx.budget_used_pct > 90 ? "bg-red-500" : deptCtx.budget_used_pct > 70 ? "bg-amber-500" : "bg-emerald-500"}`}
                                      style={{ width: `${Math.min(deptCtx.budget_used_pct, 100)}%` }}
                                    />
                                  </div>
                                )}
                              </>
                            ) : (
                              <Text className="text-gray-400">No data</Text>
                            )}
                          </div>
                        </Col>
                      </Grid>

                      {/* AI Recommendation */}
                      {compliance?.reasoning && (
                        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950/40 rounded-md border-l-4 border-blue-500 text-sm">
                          <Text className="font-medium text-xs text-blue-700 dark:text-blue-300 uppercase tracking-wide mb-1">
                            AI Recommendation
                          </Text>
                          <Text className="text-blue-900 dark:text-blue-100">{compliance.reasoning}</Text>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={XCircle}
                          loading={acting === approval.transaction_id}
                          onClick={() => handleDecision(approval.transaction_id, false)}
                          className="!text-red-600 !border-red-300 hover:!bg-red-50 dark:!border-red-800 dark:hover:!bg-red-950"
                        >
                          Decline
                        </Button>
                        <Button
                          size="sm"
                          variant="primary"
                          icon={CheckCircle}
                          loading={acting === approval.transaction_id}
                          onClick={() => handleDecision(approval.transaction_id, true)}
                          className="!text-white !bg-blue-600 hover:!bg-blue-700"
                        >
                          Approve
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </>
          )}
        </>
      )}
    </Card>
  );
}
