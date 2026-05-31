"use client";

import { useState, useEffect } from "react";
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
import RulesForm from "@/components/RulesForm";
import ApprovalPanel from "@/components/ApprovalPanel";
import TransactionForm from "@/components/TransactionForm";
import { scanCompliance, listRules, getTransactionCodes } from "@/lib/api";
import type { ComplianceRule, TransactionCode } from "@/lib/types";
import { Shield, Plus, List } from "lucide-react";

type TabView = "rules" | "add-txn";

export default function AdminPage() {
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [scanning, setScanning] = useState(false);
  const [lastScanResult, setLastScanResult] = useState<{
    total_scanned: number;
    violations_found: number;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<TabView>("rules");

  const fetchRules = async () => {
    try {
      const data = await listRules();
      setRules(data);
    } catch {}
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await scanCompliance();
      setLastScanResult({
        total_scanned: result.total_scanned,
        violations_found: result.violations_found,
      });
      toast.success(
        `Scan complete: ${result.violations_found} violations out of ${result.total_scanned} transactions`
      );
    } catch (err) {
      toast.error("Scan failed. Is the database seeded?");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div>
        <Title>Admin: Policy & Approval Center</Title>
        <Text>
          Manage expense policies, create custom rules, add transactions, scan for compliance, and approve transactions.
        </Text>
      </div>

      {/* Compliance Scan */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <Title>Compliance Scan</Title>
            <Text className="mt-1">
              Scan all transactions against company policy and custom rules.
            </Text>
          </div>
          <div className="flex items-center gap-4">
            {lastScanResult && (
              <div className="text-right">
                <Text className="text-sm">
                  Last scan:{" "}
                  <span className="font-semibold">
                    {lastScanResult.violations_found} violations
                  </span>{" "}
                  / {lastScanResult.total_scanned} transactions
                </Text>
              </div>
            )}
            <Button
              icon={Shield}
              loading={scanning}
              onClick={handleScan}
              color="orange"
            >
              {scanning ? "Scanning..." : "Run Compliance Scan"}
            </Button>
          </div>
        </div>
      </Card>

      {/* Approvals */}
      <ApprovalPanel />

      {/* Tab: Rules vs Add Transaction */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
        <button
          onClick={() => setActiveTab("rules")}
          className={`flex items-center gap-2 px-4 py-2 rounded-t text-sm font-medium transition-colors ${
            activeTab === "rules"
              ? "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-b-2 border-blue-500"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <List className="h-4 w-4" />
          Custom Rules
        </button>
        <button
          onClick={() => setActiveTab("add-txn")}
          className={`flex items-center gap-2 px-4 py-2 rounded-t text-sm font-medium transition-colors ${
            activeTab === "add-txn"
              ? "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-b-2 border-blue-500"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Plus className="h-4 w-4" />
          Add Transaction
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "rules" && (
        <div className="space-y-6">
          <RulesForm onRuleCreated={fetchRules} />

          <Card>
            <Title>Existing Rules ({rules.length})</Title>
            <Table className="mt-4">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Rule</TableHeaderCell>
                  <TableHeaderCell>Department</TableHeaderCell>
                  <TableHeaderCell>Category/Type</TableHeaderCell>
                  <TableHeaderCell>Severity</TableHeaderCell>
                  <TableHeaderCell>Source</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rules.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Text className="text-center text-gray-500">
                        No rules found.
                      </Text>
                    </TableCell>
                  </TableRow>
                ) : (
                  rules.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="max-w-md">
                        <Text className="truncate">{rule.text}</Text>
                      </TableCell>
                      <TableCell>
                        <Badge>{rule.department}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge>{rule.category || "—"}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          color={
                            rule.severity === "High"
                              ? "red"
                              : rule.severity === "Medium"
                              ? "yellow"
                              : "emerald"
                          }
                        >
                          {rule.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge color={rule.source === "baseline" ? "blue" : "slate"} size="xs">
                          {rule.source === "baseline" ? "Baseline" : "Custom"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {activeTab === "add-txn" && (
        <Card>
          <TransactionForm />
        </Card>
      )}
    </div>
  );
}
