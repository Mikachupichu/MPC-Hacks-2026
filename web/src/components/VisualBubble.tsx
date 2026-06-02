"use client";

import { useMemo } from "react";
import {
  BarChart,
  LineChart,
  AreaChart,
  DonutChart,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Card,
  Title,
  CustomTooltipProps,
} from "@tremor/react";

import type { VisualizationConfig } from "@/lib/types";

interface VisualBubbleProps {
  title?: string;
  visualizationType: "bar_chart" | "line_chart" | "area_chart" | "donut_chart" | "table" | "text";
  config: VisualizationConfig;
  data: Record<string, unknown>[];
}

const dollarFmt = (v: number) =>
  "$" + v.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });

function humanizeLabel(label: string): string {
  return label
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

function formatDateLabel(label: string): string {
  if (!label || label.length < 7) return label;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const fullDate = /^(\d{4})-(\d{2})-(\d{2})/.exec(label);
  if (fullDate) {
    return `${months[parseInt(fullDate[2]) - 1] || fullDate[2]} ${parseInt(fullDate[3])}`;
  }
  const yearMonth = /^(\d{4})-(\d{2})$/.exec(label);
  if (yearMonth) {
    return `${months[parseInt(yearMonth[2]) - 1] || yearMonth[2]} ${yearMonth[1]}`;
  }
  return label;
}

function formatTableValue(val: unknown): string {
  if (typeof val === "number") {
    return "$" + val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return String(val ?? "");
}

function ChartTooltip({ payload, active, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-gray-200 bg-white px-3 py-2 shadow-lg dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <div className="mt-1 space-y-0.5">
        {payload.map((entry: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2 text-sm">
            {payload.length > 1 && (
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color || "#3b82f6" }}
              />
            )}
            {payload.length > 1 && (
              <span className="text-gray-600 dark:text-gray-300">{humanizeLabel(String(entry.name ?? ""))}</span>
            )}
            <span className="font-semibold tabular-nums">
              ${(entry.value ?? 0).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function VisualBubble({ title, visualizationType, config, data }: VisualBubbleProps) {
  const { x_key, y_keys, colors } = config;
  const indexKey = x_key || "name";
  const categoriesRaw = y_keys.length > 0
    ? y_keys
    : (data.length > 0
        ? Object.keys(data[0]).filter((k) => k !== indexKey && typeof data[0][k] === "number").slice(0, 3)
        : ["value"]);
  const isSingleCategory = categoriesRaw.length <= 1;

  const categoryLabels = useMemo(() => categoriesRaw.map(humanizeLabel), [categoriesRaw]);

  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((row) => {
      const newRow = { ...row };
      const val = row[indexKey];
      if (typeof val === "string") {
        newRow[indexKey] = formatDateLabel(val);
      }
      return newRow;
    });
  }, [data, indexKey]);

  // Tremor color names — these map to fill-{color}-500 CSS classes via Tremor internals
  // Must match safelist in globals.css
  const TREMOR_COLORS = [
    "blue", "cyan", "amber", "rose", "violet", "emerald",
    "orange", "purple", "teal", "pink", "indigo", "lime",
    "sky", "fuchsia", "green", "yellow", "red",
  ];
  const palette: string[] = TREMOR_COLORS.slice(0, Math.max(data.length, 1));

  const needsRotation = processedData.length > 5;
  const chartHeight = needsRotation ? "h-80" : "h-64";
  const rotateLabelX = needsRotation
    ? { angle: -40, verticalShift: 20, xAxisHeight: 90 }
    : undefined;
  const chartPadding = { left: 5, right: 10, bottom: needsRotation ? 20 : 10, top: 10 };

  if (!data || data.length === 0) return null;

  const header = title ? (
    <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
      <Title className="text-base font-semibold tracking-tight">{title}</Title>
    </div>
  ) : null;

  const cardClass = "mt-3 overflow-visible border-0 bg-white shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800";

  const renderChart = () => {
    switch (visualizationType) {
      case "donut_chart":
        return (
          <Card className={cardClass}>
            {header}
            <div className="mt-4 flex justify-center px-4">
              <DonutChart
                className="h-80 max-w-lg"
                data={processedData}
                index={indexKey as string}
                category={categoriesRaw[0] || "value"}
                colors={palette}
                variant="donut"
                valueFormatter={dollarFmt}
                showAnimation
                showLabel={false}
                showTooltip
                customTooltip={ChartTooltip}
              />
            </div>
          </Card>
        );

      case "area_chart":
        return (
          <Card className={cardClass}>
            {header}
            <div className="px-1 pb-2">
              <AreaChart
                className={`mt-4 ${chartHeight}`}
                data={processedData}
                index={indexKey as string}
                categories={categoriesRaw as string[]}
                colors={palette}
                valueFormatter={dollarFmt}
                showAnimation
                showLegend={!isSingleCategory}
                showGridLines
                yAxisWidth={72}
                rotateLabelX={rotateLabelX}
                padding={chartPadding}
                allowDecimals={false}
                customTooltip={ChartTooltip}
                showGradient={!isSingleCategory}
                curveType="natural"
                stack={!isSingleCategory}
              />
            </div>
          </Card>
        );

      case "line_chart":
        return (
          <Card className={cardClass}>
            {header}
            <div className="px-1 pb-2">
              <LineChart
                className={`mt-4 ${chartHeight}`}
                data={processedData}
                index={indexKey as string}
                categories={categoriesRaw as string[]}
                colors={palette}
                valueFormatter={dollarFmt}
                showAnimation
                showLegend={!isSingleCategory}
                showGridLines
                yAxisWidth={72}
                rotateLabelX={rotateLabelX}
                padding={chartPadding}
                allowDecimals={false}
                customTooltip={ChartTooltip}
                curveType="natural"
                connectNulls
              />
            </div>
          </Card>
        );

      case "bar_chart":
        return (
          <Card className={cardClass}>
            {header}
            <div className="px-1 pb-2">
              <BarChart
                className={`mt-4 ${chartHeight}`}
                data={processedData}
                index={indexKey as string}
                categories={categoriesRaw as string[]}
                colors={palette}
                valueFormatter={dollarFmt}
                showAnimation
                showLegend={!isSingleCategory}
                showGridLines
                yAxisWidth={72}
                rotateLabelX={rotateLabelX}
                padding={chartPadding}
                allowDecimals={false}
                customTooltip={ChartTooltip}
                barCategoryGap={needsRotation ? "15%" : "30%"}
              />
            </div>
          </Card>
        );

      case "table": {
        return (
          <Card className={cardClass}>
            {header}
            <div className="px-1 pb-2">
              <div className="mt-4 max-h-96 overflow-y-auto">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell className="sticky top-0 bg-white dark:bg-gray-900">
                        {humanizeLabel(indexKey)}
                      </TableHeaderCell>
                      {categoryLabels.map((col) => (
                        <TableHeaderCell key={col} className="sticky top-0 bg-white text-right dark:bg-gray-900">
                          {col}
                        </TableHeaderCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {processedData.map((row, i) => (
                      <TableRow key={i} className={i % 2 === 0 ? "" : "bg-gray-50 dark:bg-gray-900/50"}>
                        <TableCell className="font-medium">{String(row[indexKey] ?? "")}</TableCell>
                        {categoriesRaw.map((key) => (
                          <TableCell key={key} className="text-right font-mono text-sm tabular-nums">
                            {formatTableValue(row[key])}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </Card>
        );
      }

      case "text":
      default:
        return null;
    }
  };

  return renderChart();
}
