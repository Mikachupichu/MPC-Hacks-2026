"use client";

import { useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  TextInput,
  Select,
  SelectItem,
  Textarea,
} from "@tremor/react";
import { toast } from "sonner";
import { createRule, listRules } from "@/lib/api";
import type { ComplianceRule } from "@/lib/types";

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
      // Refresh rules list via parent
      listRules()
        .then(() => {})
        .catch(() => {});
    } catch (err) {
      toast.error("Failed to create rule");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <Title>Create Custom Spending Rule</Title>
      <Text className="mt-1">
        Define a new policy rule that will be used for compliance scanning.
      </Text>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Rule Text</label>
          <Textarea
            placeholder="e.g., Software subscriptions over $500/month must be approved by department head"
            value={text}
            onChange={(e) => setText(e.target.value)}
            required
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Department</label>
            <Select value={department} onValueChange={setDepartment}>
              <SelectItem value="all">All Departments</SelectItem>
              <SelectItem value="Engineering">Engineering</SelectItem>
              <SelectItem value="Marketing">Marketing</SelectItem>
              <SelectItem value="Sales">Sales</SelectItem>
              <SelectItem value="Operations">Operations</SelectItem>
              <SelectItem value="HR">HR</SelectItem>
              <SelectItem value="Finance">Finance</SelectItem>
              <SelectItem value="Product">Product</SelectItem>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Category</label>
            <Select value={category} onValueChange={setCategory}>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="Software">Software</SelectItem>
              <SelectItem value="Travel">Travel</SelectItem>
              <SelectItem value="Meals">Meals</SelectItem>
              <SelectItem value="Entertainment">Entertainment</SelectItem>
              <SelectItem value="Hardware">Hardware</SelectItem>
              <SelectItem value="Office Supplies">Office Supplies</SelectItem>
              <SelectItem value="Services">Services</SelectItem>
              <SelectItem value="Training">Training</SelectItem>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Severity</label>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectItem value="Low">Low</SelectItem>
              <SelectItem value="Medium">Medium</SelectItem>
              <SelectItem value="High">High</SelectItem>
            </Select>
          </div>
        </div>

        <Button type="submit" loading={submitting} disabled={submitting}>
          Create Rule
        </Button>
      </form>
    </Card>
  );
}
