import {
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

export function SeriesChart({ series }) {
  if (!Array.isArray(series) || series.length === 0) {
    return null;
  }

  const data = series.map((ms, index) => ({
    sample: index + 1,
    ms,
  }));

  return (
    <LineChart
      width={520}
      height={260}
      data={data}
      margin={{ top: 20, right: 16, bottom: 24, left: 24 }}
    >
      <CartesianGrid stroke="var(--grid)" />
      <XAxis
        dataKey="sample"
        stroke="var(--ink)"
        tick={{ fill: "var(--ink)" }}
        label={{ value: "sample", position: "insideBottom", offset: -8, fill: "var(--ink)" }}
      />
      <YAxis
        stroke="var(--ink)"
        tick={{ fill: "var(--ink)" }}
        label={{ value: "ms", angle: -90, position: "insideLeft", fill: "var(--ink)" }}
      />
      <Line
        type="linear"
        dataKey="ms"
        stroke="var(--accent)"
        dot={{ r: 3, fill: "var(--accent)", stroke: "var(--accent)" }}
        isAnimationActive={false}
      >
        <LabelList dataKey="ms" position="top" fill="var(--ink)" />
      </Line>
    </LineChart>
  );
}
