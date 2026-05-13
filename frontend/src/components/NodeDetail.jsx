import { BarChart2, Columns, Table2, FileCode, FileText, GitBranch, X } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import AccordionSection from "./AccordionSection";
import DataTable from "./DataTable";
import SchemaView from "./SchemaView";
import useAnalysisStore from "../store/useAnalysisStore";
import { useEffect, useMemo, useRef, useState } from "react";

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

      <AccordionSection title="Metrics" icon={BarChart2} defaultOpen>
        <div className="text-[11px] space-y-1" style={{ color: "var(--text-secondary)" }}>
          <div>Rows in → out: {rt.rows_in ?? "—"} → {rt.rows_out ?? "—"}</div>
          <div>Cols in → out: {rt.cols_in ?? "—"} → {rt.cols_out ?? "—"}</div>
          <div>Filtered: {rt.rows_filtered ?? 0}</div>
          <div>Deduped: {rt.duplicates_removed ?? 0}</div>
          <div>Nulls handled: {rt.nulls_handled ?? 0}</div>
          <div>Duration: {rt.duration_ms ?? "—"} ms</div>
          {rt.error && <div className="text-red-400">{rt.error}</div>}
        </div>
      </AccordionSection>

      <AccordionSection title="Column changes" icon={Columns} defaultOpen>
        <div className="text-[11px] space-y-1" style={{ color: "var(--text-secondary)" }}>
          <div>Added: {(rt.cols_added || []).join(", ") || "—"}</div>
          <div>Removed: {(rt.cols_removed || []).join(", ") || "—"}</div>
          <div>Renamed: {JSON.stringify(rt.cols_renamed || {})}</div>
        </div>
      </AccordionSection>

      <AccordionSection title="Schema" icon={Table2}>
        <SchemaView before={rt.dtypes_before} after={rt.dtypes_after} />
      </AccordionSection>

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
        <DataTable data={sampleMode === "output" ? rt.sample_output : rt.sample_input} />
      </AccordionSection>

      <AccordionSection title="Source code" icon={FileCode}>
        <div className="rounded-lg overflow-hidden text-[11px]" style={{ border: "1px solid var(--border)" }}>
          <SyntaxHighlighter language="python" style={oneDark} customStyle={{ margin: 0, padding: 10 }}>
            {node.code || "#"}
          </SyntaxHighlighter>
        </div>
      </AccordionSection>

      <AccordionSection title="Description" icon={FileText}>
        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{node.description}</p>
        <span className="text-[10px] text-[var(--text-muted)]">({node.description_source})</span>
      </AccordionSection>

      <AccordionSection title="Lineage" icon={GitBranch}>
        <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          Variable out: <code>{node.variable_out}</code>
        </div>
      </AccordionSection>
    </div>
  );
}
