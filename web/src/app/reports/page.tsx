"use client";

import { useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  Badge,
  Grid,
  Metric,
  Col,
} from "@tremor/react";
import Dropdown, { DropdownItem } from "@/components/Dropdown";
import { toast } from "sonner";
import VisualBubble from "@/components/VisualBubble";
import { compileReport, getDepartments } from "@/lib/api";
import type { ReportPayload } from "@/lib/types";
import AeroWindow from "@/components/AeroWindow";
import { FileText, Loader2 } from "lucide-react";

export default function ReportsPage() {
  const [department, setDepartment] = useState("all");
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load departments for the selector (simplified - just use known list)
  const departments = [
    "All",
    "Engineering",
    "Marketing",
    "Sales",
    "Operations",
    "HR",
    "Finance",
    "Product",
  ];

  const handleGenerateReport = async () => {
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const params: { department?: string } = {};
      if (department !== "all") {
        params.department = department;
      }

      const result = await compileReport(params);
      if (result.error) {
        setError(result.error);
        toast.error(result.error);
      } else {
        setReport(result.report_payload);
        toast.success("Report generated successfully");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to generate report";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full px-4 py-8">
      <AeroWindow title="Expense Report" className="mx-auto">
        <div className="space-y-8 overflow-hidden">
          <div className="overflow-y-auto max-h-[70vh] space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <Title>Expense Reports</Title>
                <Text>
                  Generate comprehensive, corporate-ready financial reports from your expense data.
                </Text>
              </div>
            </div>

            {/* Report Controls */}
      <Card className="p-4">
            <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Department</label>
            <Dropdown value={department} onValueChange={setDepartment} placeholder="All Departments">
              {departments.map((d) => (
                <DropdownItem key={d} value={d}>
                  {d === "all" ? "All Departments" : d}
                </DropdownItem>
              ))}
            </Dropdown>
          </div>
          <Button
            icon={loading ? Loader2 : FileText}
            loading={loading}
            onClick={handleGenerateReport}
            size="lg"
          >
            {loading ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </Card>

      {/* Loading State */}
      {loading && (
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-3">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-500" />
              <Text>Analyzing transactions and compiling report...</Text>
            </div>
          </div>
        </Card>
      )}

      {/* Error State */}
      {error && !loading && (
        <Card>
          <div className="py-8 text-center">
            <Text className="text-red-500">{error}</Text>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={handleGenerateReport}
            >
              Try Again
            </Button>
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!report && !loading && !error && (
        <Card>
          <div className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <Title>No Report Generated Yet</Title>
            <Text className="mt-2">
              Select a department and click "Generate Report" to create an expense summary.
            </Text>
          </div>
        </Card>
      )}

      {/* Report Content */}
      {report && (
        <>
          {/* Executive Summary */}
          <Card>
            <Title>{report.report_title}</Title>
            <Text className="text-sm text-gray-500 mt-1">
              Generated: {new Date(report.generated_at).toLocaleString()}
            </Text>

            <Grid numItems={1} numItemsSm={2} numItemsLg={4} className="gap-4 mt-6">
              <Card decoration="top" decorationColor="blue">
                <Text>Total Spent</Text>
                <Metric>
                  ${report.executive_summary.total_spent.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </Metric>
              </Card>
              <Card decoration="top" decorationColor="emerald">
                <Text>Total Transactions</Text>
                <Metric>{report.executive_summary.total_transactions}</Metric>
              </Card>
              <Card decoration="top" decorationColor="emerald">
                <Text>Compliance Rate</Text>
                <Metric>{report.executive_summary.compliance_rate}%</Metric>
              </Card>
              <Card decoration="top" decorationColor={report.executive_summary.violation_count > 0 ? "red" : "emerald"}>
                <Text>Violations</Text>
                <Metric>{report.executive_summary.violation_count}</Metric>
              </Card>
            </Grid>

            {report.executive_summary.text && (
              <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <Text className="whitespace-pre-wrap">
                  {report.executive_summary.text}
                </Text>
              </div>
            )}
          </Card>

          {/* Compliance Health */}
          <Card>
            <div className="flex items-center justify-between">
              <Title>Compliance Health</Title>
              <Badge
                size="xl"
                color={
                  report.compliance_health.status === "Good"
                    ? "emerald"
                    : report.compliance_health.status === "Needs Attention"
                    ? "yellow"
                    : "red"
                }
              >
                {report.compliance_health.status}
              </Badge>
            </div>

            <Grid numItems={1} numItemsLg={2} className="gap-6 mt-6">
              <Card>
                <Title>By Department</Title>
                {report.compliance_health.by_department.length > 0 ? (
                  <VisualBubble
                    title="Department Spending"
                    visualizationType="bar_chart"
                    config={{
                      x_key: "department",
                      y_keys: ["total"],
                      colors: ["#3b82f6"],
                    }}
                    data={report.compliance_health.by_department.map((d) => ({
                      department: d.department,
                      total: d.total,
                    }))}
                  />
                ) : (
                  <Text className="mt-2">No department data available.</Text>
                )}
              </Card>
              <Card>
                <Title>By Category</Title>
                {report.compliance_health.by_category.length > 0 ? (
                  <VisualBubble
                    title="Category Spending"
                    visualizationType="bar_chart"
                    config={{
                      x_key: "category",
                      y_keys: ["total"],
                      colors: ["#10b981"],
                    }}
                    data={report.compliance_health.by_category.map((c) => ({
                      category: c.category,
                      total: c.total,
                    }))}
                  />
                ) : (
                  <Text className="mt-2">No category data available.</Text>
                )}
              </Card>
            </Grid>
          </Card>

          {/* Report Sections */}
          {report.sections.length > 0 && (
            <div className="space-y-4">
              <Title>Detailed Analysis</Title>
              {report.sections.map((section, i) => (
                <Card key={i}>
                  <Title>{section.title}</Title>
                  {section.summary && (
                    <div className="mt-2 mb-2 p-3 bg-blue-50 dark:bg-blue-950/40 rounded-md border-l-4 border-blue-500">
                      <Text className="text-sm text-blue-800 dark:text-blue-200">{section.summary}</Text>
                    </div>
                  )}
                  <VisualBubble
                    title=""
                    visualizationType={section.visualization_type}
                    config={section.config}
                    data={section.data}
                  />
                </Card>
              ))}
            </div>
          )}
        </>
      )}
        </div>
      </div>
    </AeroWindow>
  </div>
  );
}
