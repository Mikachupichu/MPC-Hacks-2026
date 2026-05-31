"use client";

import { useState } from "react";
import {
  Card,
  Title,
  Text,
  Button,
  TextInput,
} from "@tremor/react";
import Dropdown, { DropdownItem } from "@/components/Dropdown";
import { toast } from "sonner";
import { createTransaction } from "@/lib/api";

// Department → first transaction code mapping (mirrors backend)
const DEPT_TO_CODE: Record<string, number> = {
  Operations: 3001,
  Finance: 108,
  Engineering: 1001,
  Marketing: 1002,
  Sales: 1003,
  HR: 2001,
  Product: 2002,
};

// Category→type mapping
const CATEGORY_TYPE_MAP: Record<number, string> = {
  1: "Operations Expense",
  2: "Interest Charge",
  3: "Cash Advance",
  10: "Cash Advance Fee",
  12: "Card Fee",
  19: "Payment",
};

export default function TransactionForm() {
  const [department, setDepartment] = useState("Operations");
  const [transactionCategory, setTransactionCategory] = useState<number>(1);
  const [amount, setAmount] = useState<number>(0);
  const [merchant, setMerchant] = useState("");
  const [description, setDescription] = useState("");
  const [currency, setCurrency] = useState("CAD");
  const [employee, setEmployee] = useState("");
  const [merchantCity, setMerchantCity] = useState("");
  const [merchantState, setMerchantState] = useState("");
  const [merchantCountry, setMerchantCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const transactionCode = DEPT_TO_CODE[department] || 3001;
  const autoType = CATEGORY_TYPE_MAP[transactionCategory] || "Other";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchant.trim() || amount <= 0) return;

    setSubmitting(true);
    try {
      const txnId = `TXN-MANUAL-${Date.now()}`;
      const result = await createTransaction({
        transaction_id: txnId,
        transaction_code: transactionCode,
        date: new Date().toISOString().split("T")[0],
        merchant: merchant.trim(),
        amount,
        currency,
        employee: employee.trim() || undefined,
        transaction_category: transactionCategory,
        description: description.trim(),
      });

      toast.success(
        `Transaction created! Mapped to ${result.auto_mapped.department} / ${result.auto_mapped.transaction_type}`
      );

      setAmount(0);
      setMerchant("");
      setDescription("");
      setEmployee("");
    } catch (err) {
      toast.error("Failed to create transaction");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-4">
      <Title>Add New Transaction</Title>
      <Text className="mt-1">
        Departments and categories are automatically mapped to transaction codes and types.
      </Text>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Department</label>
            <Dropdown value={department} onValueChange={setDepartment} placeholder="Select Department">
              {Object.keys(DEPT_TO_CODE).map((dept) => (
                <DropdownItem key={dept} value={dept}>
                  {dept}
                </DropdownItem>
              ))}
            </Dropdown>
            <Text className="text-xs text-gray-500 mt-1">
              Code: <strong>{transactionCode}</strong> &middot; Dept: <strong>{department}</strong>
            </Text>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Transaction Category</label>
            <Dropdown
              value={String(transactionCategory)}
              onValueChange={(v) => setTransactionCategory(Number(v))}
              placeholder="Select Category"
            >
              {Object.entries(CATEGORY_TYPE_MAP).map(([cat, type]) => (
                <DropdownItem key={cat} value={cat}>
                  {type}
                </DropdownItem>
              ))}
            </Dropdown>
            <Text className="text-xs text-gray-500 mt-1">
              Auto-maps to type: <strong>{autoType}</strong>
            </Text>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Merchant</label>
            <TextInput
              placeholder="e.g. LOVE'S #0687"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Amount ($)</label>
            <TextInput
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount ? String(amount) : ""}
              onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <TextInput
            placeholder="Transaction description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Employee Name</label>
          <TextInput
            placeholder="e.g. Marcus Johnson (optional — auto-assigned if blank)"
            value={employee}
            onChange={(e) => setEmployee(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Currency</label>
            <Dropdown value={currency} onValueChange={setCurrency} placeholder="Currency">
              <DropdownItem value="CAD">CAD</DropdownItem>
              <DropdownItem value="USD">USD</DropdownItem>
            </Dropdown>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">City</label>
            <TextInput
              placeholder="City"
              value={merchantCity}
              onChange={(e) => setMerchantCity(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">State/Province</label>
            <TextInput
              placeholder="e.g. ON, TX"
              value={merchantState}
              onChange={(e) => setMerchantState(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div className="p-2 bg-blue-50 dark:bg-blue-950 rounded text-xs">
            <Text>
              <strong>{department}</strong> / <strong>{autoType}</strong> (code {transactionCode})
            </Text>
          </div>
          <Button type="submit" loading={submitting} disabled={submitting}>
            Add Transaction
          </Button>
        </div>
      </form>
    </Card>
  );
}
