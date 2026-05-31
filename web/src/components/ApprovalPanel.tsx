"use client";

import { useEffect, useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  Badge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@tremor/react";
import { toast } from "sonner";
import { resumeApproval, getPendingApprovals } from "@/lib/api";
import type { PendingApproval } from "@/lib/types";
import { CheckCircle, XCircle } from "lucide-react";

export default function ApprovalPanel() {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);

  const fetchApprovals = async () => {
    try {
      const data = await getPendingApprovals();
      setApprovals(data.pending_approvals);
    } catch {
      // Silently fail - approvals may be empty
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDecision = async (
    transactionId: string,
    approved: boolean
  ) => {
    setActing(transactionId);
    try {
      const result = await resumeApproval(transactionId, approved);
      toast.success(result.message);
      setApprovals((prev) =>
        prev.filter((a) => a.transaction_id !== transactionId)
      );
    } catch {
      toast.error("Failed to process decision");
    } finally {
      setActing(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <Title>Pending Approvals</Title>
        <Text className="mt-2">Loading pending approvals...</Text>
      </Card>
    );
  }

  if (approvals.length === 0) {
    return (
      <Card>
        <Title>Pending Approvals</Title>
        <Text className="mt-2 text-green-600">
          No pending approvals. All caught up!
        </Text>
      </Card>
    );
  }

  return (
    <Card>
      <Title>Pending Approvals</Title>
      <Text className="mt-1">
        {approvals.length} transaction{approvals.length !== 1 ? "s" : ""} awaiting your decision
      </Text>

      <Table className="mt-4">
        <TableHead>
          <TableRow>
            <TableHeaderCell>Transaction</TableHeaderCell>
            <TableHeaderCell>Merchant</TableHeaderCell>
            <TableHeaderCell>Amount</TableHeaderCell>
            <TableHeaderCell>Department</TableHeaderCell>
            <TableHeaderCell>Category</TableHeaderCell>
            <TableHeaderCell>AI Recommendation</TableHeaderCell>
            <TableHeaderCell>Actions</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {approvals.map((approval) => {
            const txn = approval.transaction;
            const compliance = approval.compliance_results;
            const isViolation = compliance?.status === "Violation";
            return (
              <TableRow key={approval.transaction_id}>
                <TableCell className="font-mono text-xs">
                  {approval.transaction_id}
                </TableCell>
                <TableCell>{txn.merchant}</TableCell>
                <TableCell>
                  ${txn.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </TableCell>
                <TableCell>{txn.department}</TableCell>
                <TableCell>
                  <Badge color={isViolation ? "red" : "emerald"}>
                    {txn.category}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    <Badge color={isViolation ? "red" : "emerald"}>
                      {compliance?.status || "Pending"}
                    </Badge>
                    {compliance?.reasoning && (
                      <Text className="text-xs text-gray-500 max-w-[200px] truncate">
                        {compliance.reasoning}
                      </Text>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      size="xs"
                      variant="primary"
                      color="emerald"
                      icon={CheckCircle}
                      loading={acting === approval.transaction_id}
                      onClick={() => handleDecision(approval.transaction_id, true)}
                    >
                      Approve
                    </Button>
                    <Button
                      size="xs"
                      variant="secondary"
                      color="red"
                      icon={XCircle}
                      loading={acting === approval.transaction_id}
                      onClick={() => handleDecision(approval.transaction_id, false)}
                    >
                      Deny
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Card>
  );
}
