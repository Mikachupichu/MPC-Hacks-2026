"use client";

import { useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  Textarea,
} from "@tremor/react";
import Dropdown, { DropdownItem } from "@/components/Dropdown";
import { toast } from "sonner";
import { createRule } from "@/lib/api";
import type { ComplianceRule } from "@/lib/types";

const DEPARTMENTS = [
  { value: "all", label: "All Departments" },
  { value: "Operations", label: "Operations" },
  { value: "Finance", label: "Finance" },
  { value: "Engineering", label: "Engineering" },
  { value: "Marketing", label: "Marketing" },
  { value: "Sales", label: "Sales" },
  { value: "HR", label: "HR" },
  { value: "Product", label: "Product" },
];

const TYPE_OPTIONS = [
  "all", "Fuel", "Permit", "Toll", "Vehicle Maintenance", "Car Wash", "Shipping",
  "Equipment", "Telecom", "Lodging", "Meals", "Transportation", "Office Supplies",
  "Software", "Services", "Cash Advance", "Operations Expense",
  "Interest Charge", "Cash Advance Fee", "Card Fee", "Payment", "Other",
];

interface RulesFormProps {
  onRuleCreated?: (rule: ComplianceRule) => void;
}

export default function RulesForm({ onRuleCreated }: RulesFormProps) {
  const [text, setText] = useState("");
  const [department, setDepartment] = useState("all");
  const [category, setCategory] = useState("all");
  const [severity, setSeverity] = useState("Medium");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setSubmitting(true);
    try {
      const rule = await createRule({
        text: text.trim(),
        department,
        category,
        severity,
      });
      toast.success("Rule created successfully");
      setText("");
      onRuleCreated?.(rule);
    } catch (err) {
      toast.error("Failed to create rule");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-4">
      <Title>Create Custom Spending Rule</Title>
      <Text className="mt-1">
        Rules target specific departments and transaction types. The transaction code is auto-assigned from the department.
      </Text>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Rule Text</label>
          <Textarea
            placeholder="e.g., Fuel expenses over $500 must be reviewed"
            value={text}
            onChange={(e) => setText(e.target.value)}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Department</label>
            <Dropdown value={department} onValueChange={setDepartment} placeholder="All Departments">
              {DEPARTMENTS.map((d) => (
                <DropdownItem key={d.value} value={d.value}>
                  {d.label}
                </DropdownItem>
              ))}
            </Dropdown>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Transaction Type / Category</label>
            <Dropdown value={category} onValueChange={setCategory} placeholder="All Types">
              {TYPE_OPTIONS.map((t) => (
                <DropdownItem key={t} value={t}>
                  {t === "all" ? "All Types" : t}
                </DropdownItem>
              ))}
            </Dropdown>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Severity</label>
            <Dropdown value={severity} onValueChange={setSeverity} placeholder="Medium">
              <DropdownItem value="Low">Low</DropdownItem>
              <DropdownItem value="Medium">Medium</DropdownItem>
              <DropdownItem value="High">High</DropdownItem>
            </Dropdown>
          </div>
        </div>

        <Button type="submit" loading={submitting} disabled={submitting}>
          Create Rule
        </Button>
      </form>
    </Card>
  );
}
