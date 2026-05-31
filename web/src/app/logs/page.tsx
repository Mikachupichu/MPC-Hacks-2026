"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  Title,
  Text,
  Badge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  TextInput,
  Button,
} from "@tremor/react";
import Dropdown, { DropdownItem } from "@/components/Dropdown";
import AeroWindow from "@/components/AeroWindow";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { getTransactions } from "@/lib/api";
import type { Transaction } from "@/lib/types";

const PAGE_SIZE = 50;

const STATUS_COLORS: Record<string, "emerald" | "yellow" | "red" | "gray"> = {
  approved: "emerald",
  pending: "yellow",
  denied: "red",
  not_required: "gray",
};

export default function LogsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState({
    department: "",
    transaction_type: "",
    status: "",
    debit_or_credit: "",
    search: "",
  });

  const fetchTransactions = useCallback(async () => {
    setLoading(true);

    try {
      const params: Record<string, string | number | undefined> = {
        limit: PAGE_SIZE,
        offset,
      };

      if (filters.department) params.department = filters.department;
      if (filters.transaction_type) params.transaction_type = filters.transaction_type;
      if (filters.status) params.status = filters.status;
      if (filters.debit_or_credit) params.debit_or_credit = filters.debit_or_credit;
      if (filters.search.trim()) params.search = filters.search.trim();

      const data = await getTransactions(params);
      setTransactions(data.transactions);
      setTotal(data.total);
    } catch {
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setOffset(0);
  };

  return (
    <div className="w-full px-4 py-8">
      <AeroWindow title="Transaction Logs" className="mx-auto">
        <div className="space-y-6">
          <div>
            <Title>Transaction Logs</Title>
            <Text className="mt-1">
              View all {total.toLocaleString()} transactions in the database.
              Transactions under $50 are marked as <Badge color="gray">Not Required</Badge> per policy.
            </Text>
          </div>

          <Card className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <label className="block text-xs font-medium mb-1">Search</label>
                <TextInput
                  placeholder="Merchant, description, ID..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  icon={Search}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Department</label>
                <Dropdown
                  value={filters.department}
                  onValueChange={(v) => handleFilterChange("department", v)}
                  placeholder="All"
                >
                  <DropdownItem value="">All</DropdownItem>
                  <DropdownItem value="Operations">Operations</DropdownItem>
                  <DropdownItem value="Finance">Finance</DropdownItem>
                  <DropdownItem value="Engineering">Engineering</DropdownItem>
                  <DropdownItem value="Marketing">Marketing</DropdownItem>
                  <DropdownItem value="Sales">Sales</DropdownItem>
                  <DropdownItem value="HR">HR</DropdownItem>
                  <DropdownItem value="Product">Product</DropdownItem>
                </Dropdown>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Type</label>
                <Dropdown
                  value={filters.transaction_type}
                  onValueChange={(v) => handleFilterChange("transaction_type", v)}
                  placeholder="All"
                >
                  <DropdownItem value="">All</DropdownItem>
                  <DropdownItem value="Fuel">Fuel</DropdownItem>
                  <DropdownItem value="Permit">Permit</DropdownItem>
                  <DropdownItem value="Toll">Toll</DropdownItem>
                  <DropdownItem value="Vehicle Maintenance">Vehicle Maintenance</DropdownItem>
                  <DropdownItem value="Car Wash">Car Wash</DropdownItem>
                  <DropdownItem value="Payment">Payment</DropdownItem>
                  <DropdownItem value="Cash Advance">Cash Advance</DropdownItem>
                  <DropdownItem value="Card Fee">Card Fee</DropdownItem>
                  <DropdownItem value="Equipment">Equipment</DropdownItem>
                </Dropdown>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Status</label>
                <Dropdown
                  value={filters.status}
                  onValueChange={(v) => handleFilterChange("status", v)}
                  placeholder="All"
                >
                  <DropdownItem value="">All</DropdownItem>
                  <DropdownItem value="approved">Approved</DropdownItem>
                  <DropdownItem value="pending">Pending</DropdownItem>
                  <DropdownItem value="denied">Denied</DropdownItem>
                  <DropdownItem value="not_required">Not Required</DropdownItem>
                </Dropdown>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Type</label>
                <Dropdown
                  value={filters.debit_or_credit}
                  onValueChange={(v) => handleFilterChange("debit_or_credit", v)}
                  placeholder="All"
                >
                  <DropdownItem value="">All</DropdownItem>
                  <DropdownItem value="Debit">Debit</DropdownItem>
                  <DropdownItem value="Credit">Credit</DropdownItem>
                </Dropdown>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="overflow-x-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>ID</TableHeaderCell>
                    <TableHeaderCell>Date</TableHeaderCell>
                    <TableHeaderCell>Merchant</TableHeaderCell>
                    <TableHeaderCell>Amount</TableHeaderCell>
                    <TableHeaderCell>Employee</TableHeaderCell>
                    <TableHeaderCell>Dept</TableHeaderCell>
                    <TableHeaderCell>Type</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                    <TableHeaderCell>Reasoning</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8">
                        <Text>Loading transactions...</Text>
                      </TableCell>
                    </TableRow>
                  ) : transactions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8">
                        <Text>No transactions found matching your filters.</Text>
                      </TableCell>
                    </TableRow>
                  ) : (
                    transactions.map((txn) => (
                      <TableRow key={txn.transaction_id}>
                        <TableCell className="font-mono text-xs max-w-[100px] truncate">
                          {txn.transaction_id}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">{txn.date}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={txn.merchant}>
                          {txn.merchant}
                        </TableCell>
                        <TableCell className="text-right font-mono whitespace-nowrap">
                          ${txn.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </TableCell>
                        <TableCell className="max-w-[120px] truncate" title={txn.employee}>
                          {txn.employee || "—"}
                        </TableCell>
                        <TableCell>
                          <Badge size="xs">{txn.department}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge size="xs" color="slate">
                            {txn.transaction_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge size="xs" color={STATUS_COLORS[txn.approval_status] || "gray"}>
                            {txn.approval_status === "not_required" ? "Not Required" : txn.approval_status.charAt(0).toUpperCase() + txn.approval_status.slice(1)}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[280px] text-xs text-gray-500" title={txn.reasoning || ""}>
                          <span className="truncate block">
                            {txn.reasoning ?? "—"}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Text className="text-sm text-gray-500">
                Showing {transactions.length} of {total.toLocaleString()} transactions
              </Text>
              <div className="flex items-center gap-2">
                <Button
                  size="xs"
                  variant="secondary"
                  icon={ChevronLeft}
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Text className="text-sm">
                  Page {currentPage} of {Math.max(1, totalPages)}
                </Text>
                <Button
                  size="xs"
                  variant="secondary"
                  icon={ChevronRight}
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </AeroWindow>
    </div>
  );
}
