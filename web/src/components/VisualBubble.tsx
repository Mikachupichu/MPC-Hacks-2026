"use client";

import {
  BarChart,
  LineChart,
  AreaChart,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Card,
  Title,
} from "@tremor/react";

import type { VisualizationConfig } from "@/lib/types";

interface VisualBubbleProps {
  title?: string;
  visualizationType: "bar_chart" | "line_chart" | "table" | "text";
  config: VisualizationConfig;
  data: Record<string, unknown>[];
}

export default function VisualBubble({
  title,
  visualizationType,
  config,
  data,
}: VisualBubbleProps) {
  if (!data || data.length === 0) {
    return null;
  }

  const { x_key, y_keys, colors } = config;

  const renderChart = () => {
    switch (visualizationType) {
      case "bar_chart":
        return (
          <BarChart
            className="mt-4 h-72"
            data={data}
            index={x_key || "name"}
            categories={y_keys.length > 0 ? y_keys : ["value"]}
            colors={colors.length > 0 ? (colors as ["#3b82f6"]) : ["#3b82f6"]}
            yAxisWidth={48}
            showAnimation
          />
        );

      case "line_chart":
        return (
          <LineChart
            className="mt-4 h-72"
            data={data}
            index={x_key || "date"}
            categories={y_keys.length > 0 ? y_keys : ["value"]}
            colors={colors.length > 0 ? (colors as ["#10b981"]) : ["#10b981"]}
            yAxisWidth={48}
            showAnimation
          />
        );

      case "table":
        const columns = y_keys.length > 0 ? y_keys : Object.keys(data[0] || {});
        return (
          <Table className="mt-4">
            <TableHead>
              <TableRow>
                {x_key && <TableHeaderCell>{x_key}</TableHeaderCell>}
                {columns.map((col) => (
                  <TableHeaderCell key={col}>{col}</TableHeaderCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row, i) => (
                <TableRow key={i}>
                  {x_key && (
                    <TableCell>{String(row[x_key] ?? "")}</TableCell>
                  )}
                  {columns.map((col) => (
                    <TableCell key={col}>
                      {typeof row[col] === "number"
                        ? (row[col] as number).toLocaleString("en-US", {
                            style: "currency",
                            currency: "CAD",
                          })
                        : String(row[col] ?? "")}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        );

      case "text":
      default:
        return null;
    }
  };

  return (
    <Card className="mt-2">
      {title && <Title>{title}</Title>}
      {renderChart()}
    </Card>
  );
}
