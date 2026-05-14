import { useMemo, useCallback, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Database, HardDrive, Filter, GitMerge, BarChart2, Shuffle,
  Sparkles, Columns, ArrowUpDown, Zap, HelpCircle, Repeat,
  ChevronDown, ChevronUp,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import useAnalysisStore from "../store/useAnalysisStore";

// ─── Icon Map ───
const iconMap = {
  "database": Database,
  "hard-drive": HardDrive,
  "filter": Filter,
  "git-merge": GitMerge,
  "bar-chart-2": BarChart2,
  "shuffle": Shuffle,
  "sparkles": Sparkles,
  "columns": Columns,
  "arrow-up-down": ArrowUpDown,
  "zap": Zap,
  "help-circle": HelpCircle,
};

// ─── Column-change colour palette ───
export const COLUMN_COLORS = {
  derived:     { bg: "rgba(34,197,94,0.12)",  color: "#22c55e", label: "Derived" },
  joined:      { bg: "rgba(59,130,246,0.12)", color: "#3b82f6", label: "Joined" },
  removed:     { bg: "rgba(239,68,68,0.12)",  color: "#ef4444", label: "Removed" },
  renamed:     { bg: "rgba(249,115,22,0.12)", color: "#f97316", label: "Renamed" },
  transformed: { bg: "rgba(234,179,8,0.15)",  color: "#eab308", label: "Transformed" },
};

// ─── Column Change Badges (shared between node expansion & detail panel) ───
function ColumnChangeBadges({ rt, color }) {
  const sections = [];

  const derived = rt.cols_derived || [];
  const joined  = rt.cols_joined || [];
  const removed = rt.cols_removed || [];
  const renamed = rt.cols_renamed || {};
  const transformed = rt.cols_transformed || {};

  if (derived.length) sections.push({ key: "derived", items: derived });
  if (joined.length)  sections.push({ key: "joined",  items: joined });
  if (removed.length) sections.push({ key: "removed", items: removed });
  if (Object.keys(renamed).length) sections.push({ key: "renamed", items: renamed });
  if (Object.keys(transformed).length) sections.push({ key: "transformed", items: transformed });

  if (!sections.length) return null;

  return (
    <div className="space-y-1.5">
      <div className="text-[10px] font-semibold" style={{ color }}>Column Changes</div>
      {sections.map(({ key, items }) => {
        const c = COLUMN_COLORS[key];
        return (
          <div key={key}>
            <div className="text-[9px] font-semibold mb-0.5" style={{ color: c.color }}>{c.label}</div>
            <div className="flex flex-wrap gap-1">
              {key === "renamed"
                ? Object.entries(items).map(([old, nw]) => (
                    <span key={old} className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: c.bg, color: c.color }}>
                      {old} → {nw}
                    </span>
                  ))
                : key === "transformed"
                ? Object.entries(items).map(([col, d]) => (
                    <span key={col} className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: c.bg, color: c.color }}>
                      {col} <span style={{ opacity: 0.7 }}>({d.from} → {d.to})</span>
                    </span>
                  ))
                : items.map((col) => (
                    <span key={col} className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ background: c.bg, color: c.color }}>
                      {col}
                    </span>
                  ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
function ETLNodeComponent({ data }) {
  const expandedNodes = useAnalysisStore((state) => state.expandedNodes);
  const toggleNodeExpanded = useAnalysisStore((state) => state.toggleNodeExpanded);
  const setSelectedDetailNode = useAnalysisStore((state) => state.setSelectedDetailNode);
  const isExpanded = expandedNodes.has(data.nodeId);
  const IconComp = iconMap[data.icon] || HelpCircle;

  const exec = data.execStatus;
  const borderColor =
    exec === "failed"
      ? "#ef4444"
      : exec === "completed"
      ? "var(--primary)"
      : exec === "executing"
      ? "#22c55e"
      : exec === "not_reached"
      ? "var(--text-muted)"
      : isExpanded
      ? data.color
      : "var(--border)";
  const rt = data.runtime;
  return (
    <div style={{ minWidth: 200 }}>
      <Handle type="target" position={Position.Left} style={{ background: data.color, width: 8, height: 8, border: "2px solid var(--bg-primary)" }} />

      {/* Node body */}
      <div
        className="nodrag nopan rounded-xl cursor-pointer transition-all duration-300 hover:-translate-y-1 group"
        style={{
          background: "var(--bg-card)",
          border: `2px solid ${borderColor}`,
          boxShadow: isExpanded ? `0 0 20px ${data.color}20` : "0 4px 12px rgba(0,0,0,0.1)",
          maxWidth: 280,
          opacity: exec === "not_reached" ? 0.65 : 1,
        }}
        onClick={(e) => {
          e.stopPropagation();
          toggleNodeExpanded(data.nodeId);
        }}
      >
        <div className="flex items-center gap-2.5 px-3 py-2.5 relative overflow-hidden rounded-t-xl">
          {/* Subtle gradient background for the header */}
          <div 
            className="absolute inset-0 opacity-10 group-hover:opacity-20 transition-opacity" 
            style={{ background: `linear-gradient(90deg, ${data.color}, transparent)` }}
          />
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${data.color}20`, color: data.color }}
          >
            <IconComp size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <div
              className="text-xs font-semibold truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {data.label}
            </div>
            <div
              className="text-[10px] mt-0.5"
              style={{ color: "var(--text-muted)" }}
            >
              Line {data.lineNumber}
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {data.isLoop && (
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center"
                style={{ background: `${data.color}20`, color: data.color }}
                title="Inside loop"
              >
                <Repeat size={10} />
              </div>
            )}
            {isExpanded ? (
              <ChevronUp size={14} style={{ color: "var(--text-muted)" }} />
            ) : (
              <ChevronDown size={14} style={{ color: "var(--text-muted)" }} />
            )}
          </div>
        </div>

        {/* Expanded detail panel */}
        {isExpanded && (
          <div
            className="px-3 pb-3 pt-1 space-y-2"
            style={{ borderTop: `1px solid ${data.color}20` }}
          >
            {/* Description */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="text-[10px] font-semibold" style={{ color: data.color }}>
                  Description
                </div>
                {data.descriptionSource === "llm" && (
                  <span
                    className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                    style={{
                      background: "rgba(168, 85, 247, 0.15)",
                      color: "#a855f7",
                    }}
                  >
                    AI
                  </span>
                )}
              </div>
              <div className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {data.description}
              </div>
            </div>

            {/* Source Code */}
            <div>
              <div className="text-[10px] font-semibold mb-1" style={{ color: data.color }}>
                Source Code
              </div>
              <div className="rounded-lg overflow-hidden text-[11px]" style={{ border: "1px solid var(--border)" }}>
                <SyntaxHighlighter
                  language="python"
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    padding: "10px",
                    background: "var(--bg-primary)",
                  }}
                >
                  {data.code || "# No source code available"}
                </SyntaxHighlighter>
              </div>
            </div>

            {/* Runtime Metrics — current-state format */}
            {rt && typeof rt.rows_out === "number" && (
              <div className="text-[10px] space-y-1" style={{ color: "var(--text-secondary)" }}>
                <div className="flex items-center gap-2">
                  <span>Outgoing Rows: <strong style={{ color: "var(--text-primary)" }}>{rt.rows_out.toLocaleString()}</strong></span>
                  {rt.rows_in != null && rt.rows_in !== rt.rows_out && (
                    <span
                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{
                        background: rt.rows_out < rt.rows_in ? "rgba(239,68,68,0.12)" : "rgba(34,197,94,0.12)",
                        color: rt.rows_out < rt.rows_in ? "#ef4444" : "#22c55e",
                      }}
                    >
                      {rt.rows_out > rt.rows_in ? "+" : ""}{(rt.rows_out - rt.rows_in).toLocaleString()}
                    </span>
                  )}
                </div>
                <div>Outgoing Columns: <strong style={{ color: "var(--text-primary)" }}>{rt.cols_out}</strong></div>
                {rt.duration_ms != null && <div>Duration: {rt.duration_ms} ms</div>}
              </div>
            )}

            {/* Categorised Column Changes */}
            {rt && !data.isSource && <ColumnChangeBadges rt={rt} color={data.color} />}

            {rt?.error && (
              <div className="text-[10px] text-red-400 break-all">{rt.error}</div>
            )}
            <button
              type="button"
              className="nodrag text-[10px] font-semibold mt-1 px-2 py-1 rounded-lg"
              style={{ background: "var(--bg-secondary)", color: "var(--primary)" }}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedDetailNode(data.nodeId);
              }}
            >
              View Details
            </button>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} style={{ background: data.color, width: 8, height: 8, border: "2px solid var(--bg-primary)" }} />
    </div>
  );
}

const nodeTypes = { etlNode: ETLNodeComponent };

// ─── Layout Algorithm ───
function layoutNodes(apiNodes, apiEdges) {
  // Build adjacency and compute levels (depth from sources)
  const incoming = {};
  const outgoing = {};
  apiNodes.forEach((n) => {
    incoming[n.id] = [];
    outgoing[n.id] = [];
  });
  apiEdges.forEach((e) => {
    if (outgoing[e.source]) outgoing[e.source].push(e.target);
    if (incoming[e.target]) incoming[e.target].push(e.source);
  });

  // Topological sort for levels
  const levels = {};
  const visited = new Set();

  function dfs(nodeId, depth) {
    if (visited.has(nodeId)) {
      levels[nodeId] = Math.max(levels[nodeId] || 0, depth);
      return;
    }
    visited.add(nodeId);
    levels[nodeId] = Math.max(levels[nodeId] || 0, depth);
    (outgoing[nodeId] || []).forEach((child) => dfs(child, depth + 1));
  }

  // Start from source nodes (no incoming edges)
  const sources = apiNodes.filter((n) => incoming[n.id].length === 0);
  sources.forEach((s) => dfs(s.id, 0));

  // Also process any unvisited nodes
  apiNodes.forEach((n) => {
    if (!visited.has(n.id)) dfs(n.id, 0);
  });

  // Group by level
  const byLevel = {};
  Object.entries(levels).forEach(([id, level]) => {
    if (!byLevel[level]) byLevel[level] = [];
    byLevel[level].push(id);
  });

  // Group by pipeline for vertical offset
  const pipelineOffsets = {};
  let pipelineY = 0;
  const pipelineIds = [...new Set(apiNodes.map((n) => n.pipeline_id))].sort();
  pipelineIds.forEach((pid, idx) => {
    const nodesInPipeline = apiNodes.filter((n) => n.pipeline_id === pid);
    pipelineOffsets[pid] = pipelineY;
    pipelineY += Math.max(nodesInPipeline.length, 1) * 100 + 80;
  });

  // Position nodes
  const NODE_WIDTH = 280;
  const X_GAP = 340;
  const Y_GAP = 100;
  const positions = {};

  Object.entries(byLevel).forEach(([level, nodeIds]) => {
    // Group by pipeline within each level
    const byPipeline = {};
    nodeIds.forEach((id) => {
      const n = apiNodes.find((n) => n.id === id);
      const pid = n?.pipeline_id ?? 0;
      if (!byPipeline[pid]) byPipeline[pid] = [];
      byPipeline[pid].push(id);
    });

    Object.entries(byPipeline).forEach(([pid, ids]) => {
      ids.forEach((id, idx) => {
        positions[id] = {
          x: parseInt(level) * X_GAP + 50,
          y: (pipelineOffsets[parseInt(pid)] || 0) + idx * Y_GAP + 50,
        };
      });
    });
  });

  return positions;
}

// ─── Main Component ───
export default function LineageTab({ result }) {
  const selectedDetailNode = useAnalysisStore((s) => s.selectedDetailNode);
  const apiNodes = result?.nodes || [];
  const apiEdges = result?.edges || [];

  const statusById = useMemo(
    () => Object.fromEntries(apiNodes.map((n) => [n.id, n.status])),
    [apiNodes]
  );

  const positions = useMemo(
    () => layoutNodes(apiNodes, apiEdges),
    [apiNodes, apiEdges]
  );

  const flowNodes = useMemo(
    () =>
      apiNodes.map((n) => ({
        id: n.id,
        type: "etlNode",
        position: positions[n.id] || { x: 0, y: 0 },
        zIndex: useAnalysisStore.getState().expandedNodes.has(n.id) ? 1000 : 0,
        data: {
          nodeId: n.id,
          label: n.label,
          isSource: !apiEdges.some(e => e.target === n.id),
          description: n.description,
          descriptionSource: n.description_source,
          code: n.code,
          color: n.color,
          icon: n.icon,
          lineNumber: n.line_number,
          isLoop: n.is_loop,
          schemaRefs: n.schema_refs,
          category: n.category,
          execStatus: n.status,
          runtime: n.runtime,
        },
      })),
    [apiNodes, positions]
  );

  const flowEdges = useMemo(
    () =>
      apiEdges.map((e, i) => {
        const src = statusById[e.source];
        const tgt = statusById[e.target];
        const edgeComplete = src === "completed" && tgt === "completed";
        const stroke = edgeComplete ? "var(--primary)" : "var(--text-muted)";
        const strokeWidth = edgeComplete ? 2 : 1.5;
        return {
          id: `edge_${i}`,
          source: e.source,
          target: e.target,
          type: "smoothstep",
          animated: false,
          label: e.variable || "",
          labelStyle: {
            fill: "var(--text-muted)",
            fontSize: 10,
            fontWeight: 500,
          },
          labelBgStyle: {
            fill: "var(--bg-card)",
            fillOpacity: 0.9,
          },
          labelBgPadding: [4, 2],
          style: {
            stroke,
            strokeWidth,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: stroke,
          },
        };
      }),
    [apiEdges, statusById]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  return (
    <div
      className="w-full rounded-xl overflow-hidden"
      style={{
        height: selectedDetailNode ? "min(52vh, 480px)" : "calc(100vh - 200px)",
        minHeight: selectedDetailNode ? 320 : 500,
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
      >
        <Background
          color="var(--border)"
          gap={20}
          size={1}
        />
        <Controls
          showInteractive={false}
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
        />
      </ReactFlow>
    </div>
  );
}
