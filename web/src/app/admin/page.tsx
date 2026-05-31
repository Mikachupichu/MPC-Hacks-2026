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
  Col,
  Grid,
} from "@tremor/react";
import { toast } from "sonner";
import RulesForm from "@/components/RulesForm";
import ApprovalPanel from "@/components/ApprovalPanel";
import { scanCompliance, listRules } from "@/lib/api";
import type { ComplianceRule } from "@/lib/types";
import { Shield, AlertTriangle } from "lucide-react";

export default function AdminPage() {
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [scanning, setScanning] = useState(false);
  const [lastScanResult, setLastScanResult] = useState<{
    total_scanned: number;
    violations_found: number;
  } | null>(null);

  const fetchRules = async () => {
    try {
      const data = await listRules();
      setRules(data);
    } catch {
      // Rules endpoint may not have data yet
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      // Scan all departments
      const result = await scanCompliance();
      setLastScanResult({
        total_scanned: result.total_scanned,
        violations_found: result.violations_found,
      });
      toast.success(
        `Scan complete: ${result.violations_found} violations found out of ${result.total_scanned} transactions`
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
          Manage expense policies, create custom rules, scan for compliance, and approve transactions.
        </Text>
      </div>

      {/* Compliance Scan Action */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <Title>Compliance Scan</Title>
            <Text className="mt-1">
              Run a compliance scan across all transactions against company policy and custom rules.
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

      {/* Two-column layout for Rules + Approvals */}
      <Grid numItems={1} numItemsLg={2} className="gap-6">
        <Col>
          <RulesForm onRuleCreated={fetchRules} />
        </Col>
        <Col>
          <ApprovalPanel />
        </Col>
      </Grid>

      {/* Existing Rules List */}
      <Card>
        <Title>Custom Rules ({rules.length})</Title>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeaderCell>Rule</TableHeaderCell>
              <TableHeaderCell>Department</TableHeaderCell>
              <TableHeaderCell>Category</TableHeaderCell>
              <TableHeaderCell>Severity</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Text className="text-center text-gray-500">
                    No custom rules yet. Create one above.
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
                    <Badge>{rule.category}</Badge>
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
                      icon={rule.severity === "High" ? AlertTriangle : undefined}
                    >
                      {rule.severity}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
