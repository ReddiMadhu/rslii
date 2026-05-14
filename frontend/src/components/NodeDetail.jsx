import { BarChart2, Columns, Table2, X } from "lucide-react";
import AccordionSection from "./AccordionSection";
import DataTable from "./DataTable";
import SchemaView from "./SchemaView";
import useAnalysisStore from "../store/useAnalysisStore";
import { useEffect, useMemo, useRef, useState } from "react";
import { COLUMN_COLORS } from "./LineageTab";

const MERGE_LEFT_COLOR = "#3b82f6";
const MERGE_RIGHT_COLOR = "#22c55e";

/* ── helper: build a column → category map from runtime data ── */
function buildColumnMeta(rt) {
  const meta = {};
  (rt.cols_derived || []).forEach((c) => (meta[c] = "derived"));
  (rt.cols_joined || []).forEach((c) => (meta[c] = "joined"));
  (rt.cols_removed || []).forEach((c) => (meta[c] = "removed"));
  const renamed = rt.cols_renamed || {};
  Object.values(renamed).forEach((nw) => (meta[nw] = "renamed"));
  const transformed = rt.cols_transformed || {};
  Object.keys(transformed).forEach((c) => (meta[c] = "transformed"));
  return meta;
}

export default function NodeDetail({ result }) {
  const selectedDetailNode = useAnalysisStore((s) => s.selectedDetailNode);
  const setSelectedDetailNode = useAnalysisStore((s) => s.setSelectedDetailNode);
  const [sampleMode, setSampleMode] = useState("output");
  const rootRef = useRef(null);

  const node = useMemo(() => {
    if (!selectedDetailNode || !result?.nodes) return null;
    return result.nodes.find((n) => n.id === selectedDetailNode) || null;
  }, [selectedDetailNode, result]);

  useEffect(() => {
    if (!node || !rootRef.current) return;
    rootRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [node?.id]);

  if (!node) return null;

  const rt = node.runtime || {};
  const columnMeta = useMemo(() => buildColumnMeta(rt), [rt]);
  const isSource = useMemo(() => !result?.edges?.some((e) => e.target === node.id), [result, node.id]);
  const isMerge = useMemo(() => node.method === "merge" || node.method === "join" || node.method === "concat", [node.method]);

  // For merge nodes, find the variable names of the two input DataFrames from edges
  const mergeInputs = useMemo(() => {
    if (!isMerge || !result?.edges) return [];
    const incomingEdges = result.edges.filter((e) => e.target === node.id);
    if (incomingEdges.length < 2) {
      // Single input — left is the incoming variable
      return incomingEdges.length === 1
        ? [{ name: incomingEdges[0].variable || "Left", color: MERGE_LEFT_COLOR }]
        : [];
    }
    return [
      { name: incomingEdges[0].variable || "Left", color: MERGE_LEFT_COLOR },
      { name: incomingEdges[1].variable || "Right", color: MERGE_RIGHT_COLOR },
    ];
  }, [isMerge, result, node.id]);

  return (
    <div
      ref={rootRef}
      className="mt-4 rounded-2xl border p-4 animate-fade-in"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          {node.label}
        </div>
        <button
          type="button"
          className="p-1 rounded-lg hover:bg-white/5"
          aria-label="Close"
          onClick={() => setSelectedDetailNode(null)}
        >
          <X size={16} />
        </button>
      </div>

      {/* ── Metrics (current-state) ── */}
      <AccordionSection title="Metrics" icon={BarChart2} defaultOpen>
        <div className="text-[11px] space-y-1" style={{ color: "var(--text-secondary)" }}>
          <div className="flex items-center gap-2">
            <span>
              Outgoing Rows:{" "}
              <strong style={{ color: "var(--text-primary)" }}>
                {rt.rows_out != null ? rt.rows_out.toLocaleString() : "—"}
              </strong>
            </span>
            {rt.rows_in != null && rt.rows_out != null && rt.rows_in !== rt.rows_out && (
              <span
                className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                style={{
                  background: rt.rows_out < rt.rows_in ? "rgba(239,68,68,0.12)" : "rgba(34,197,94,0.12)",
                  color: rt.rows_out < rt.rows_in ? "#ef4444" : "#22c55e",
                }}
              >
                {rt.rows_out > rt.rows_in ? "+" : ""}
                {(rt.rows_out - rt.rows_in).toLocaleString()}
              </span>
            )}
          </div>
          <div>
            Outgoing Columns:{" "}
            <strong style={{ color: "var(--text-primary)" }}>
              {rt.cols_out ?? "—"}
            </strong>
          </div>
          {!isSource && <div>Filtered: {rt.rows_filtered ?? 0}</div>}
          {!isSource && <div>Deduped: {rt.duplicates_removed ?? 0}</div>}
          {!isSource && <div>Nulls handled: {rt.nulls_handled ?? 0}</div>}
          {!isSource && <div>Duration: {rt.duration_ms ?? "—"} ms</div>}
          {rt.error && <div className="text-red-400">{rt.error}</div>}
        </div>
      </AccordionSection>

      {/* ── Column Changes (colour-coded categories) ── */}
      {!isSource && (
        <AccordionSection title="Column Level Changes" icon={Columns} defaultOpen>
          <ColumnChangeDetail rt={rt} />
        </AccordionSection>
      )}

      <AccordionSection title="Schema" icon={Table2}>
        <SchemaView
          before={rt.dtypes_before}
          after={rt.dtypes_after}
          columnMeta={columnMeta}
          isSource={isSource}
          isMerge={isMerge}
          mergeInputs={mergeInputs}
          joinedColumns={rt.cols_joined || []}
          joinKeys={node.schema_refs || []}
        />
      </AccordionSection>

      {/* ── Sample data (colour-coded headers) ── */}
      <AccordionSection title="Sample data" icon={Table2}>
        <div className="flex gap-2 mb-2">
          <button
            type="button"
            className="text-[10px] px-2 py-1 rounded-lg"
            style={{
              background: sampleMode === "output" ? "var(--primary)" : "var(--bg-secondary)",
              color: sampleMode === "output" ? "white" : "var(--text-muted)",
            }}
            onClick={() => setSampleMode("output")}
          >
            Output
          </button>
          <button
            type="button"
            className="text-[10px] px-2 py-1 rounded-lg"
            style={{
              background: sampleMode === "input" ? "var(--primary)" : "var(--bg-secondary)",
              color: sampleMode === "input" ? "white" : "var(--text-muted)",
            }}
            onClick={() => setSampleMode("input")}
          >
            Input
          </button>
        </div>
        <DataTable
          data={sampleMode === "output" ? rt.sample_output : rt.sample_input}
          columnMeta={sampleMode === "output" ? columnMeta : {}}
        />
      </AccordionSection>
    </div>
  );
}

/* ── Detailed column-change breakdown for the bottom detail panel ── */
function ColumnChangeDetail({ rt }) {
  const derived     = rt.cols_derived || [];
  const joined      = rt.cols_joined || [];
  const removed     = rt.cols_removed || [];
  const renamed     = rt.cols_renamed || {};
  const transformed = rt.cols_transformed || {};
  const dtypesAfter = rt.dtypes_after || {};

  const categories = [
    { key: "derived",     label: "Derived",     items: derived,     type: "list" },
    { key: "joined",      label: "Joined",      items: joined,      type: "list" },
    { key: "removed",     label: "Removed",     items: removed,     type: "list" },
    { key: "renamed",     label: "Renamed",     items: renamed,     type: "map" },
    { key: "transformed", label: "Transformed", items: transformed, type: "dtype" },
  ];

  const hasAnything = categories.some(
    (c) => c.type === "list" ? c.items.length > 0 : Object.keys(c.items).length > 0
  );

  if (!hasAnything) {
    return (
      <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        No column changes detected
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {categories.map(({ key, label, items, type }) => {
        const count = type === "list" ? items.length : Object.keys(items).length;
        if (!count) return null;
        const cc = COLUMN_COLORS[key];
        return (
          <div key={key}>
            <div className="flex items-center gap-1.5 mb-1">
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ background: cc.color }}
              />
              <span className="text-[10px] font-semibold" style={{ color: cc.color }}>
                {label}
              </span>
              <span
                className="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
                style={{ background: cc.bg, color: cc.color }}
              >
                {count}
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {type === "list" &&
                items.map((col) => (
                  <span
                    key={col}
                    className="text-[10px] px-2 py-0.5 rounded-lg font-medium inline-flex items-center gap-1"
                    style={{ background: cc.bg, color: cc.color, border: `1px solid ${cc.color}30` }}
                  >
                    {col}
                    {key === "derived" && dtypesAfter[col] && (
                      <span style={{ opacity: 0.6, fontSize: "9px" }}>{dtypesAfter[col]}</span>
                    )}
                  </span>
                ))}
              {type === "map" &&
                Object.entries(items).map(([old, nw]) => (
                  <span
                    key={old}
                    className="text-[10px] px-2 py-0.5 rounded-lg font-medium"
                    style={{ background: cc.bg, color: cc.color, border: `1px solid ${cc.color}30` }}
                  >
                    {old} → {nw}
                  </span>
                ))}
              {type === "dtype" &&
                Object.entries(items).map(([col, d]) => (
                  <span
                    key={col}
                    className="text-[10px] px-2 py-0.5 rounded-lg font-medium"
                    style={{ background: cc.bg, color: cc.color, border: `1px solid ${cc.color}30` }}
                  >
                    {col}{" "}
                    <span style={{ opacity: 0.7 }}>
                      ({d.from} → {d.to})
                    </span>
                  </span>
                ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
