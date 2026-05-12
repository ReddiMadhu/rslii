import { useMemo, useCallback } from "react";
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

// ─── Custom Node Component ───
function ETLNodeComponent({ data }) {
  const { expandedNodes, toggleNodeExpanded } = useAnalysisStore();
  const isExpanded = expandedNodes.has(data.nodeId);
  const IconComp = iconMap[data.icon] || HelpCircle;

  return (
    <div style={{ minWidth: 200 }}>
      <Handle type="target" position={Position.Left} style={{ background: data.color, width: 8, height: 8, border: "2px solid var(--bg-primary)" }} />

      {/* Node body */}
      <div
        className="rounded-xl cursor-pointer transition-all duration-200 hover:scale-[1.02]"
        style={{
          background: "var(--bg-card)",
          border: `2px solid ${data.color}40`,
          boxShadow: `0 0 20px ${data.color}10`,
          maxWidth: 280,
        }}
        onClick={() => toggleNodeExpanded(data.nodeId)}
      >
        <div className="flex items-center gap-2.5 px-3 py-2.5">
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
              <div className="rounded-lg overflow-hidden text-[11px]">
                <SyntaxHighlighter
                  language="python"
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    padding: "8px 10px",
                    borderRadius: "8px",
                    fontSize: "11px",
                    background: "var(--bg-secondary)",
                  }}
                >
                  {data.code || "# No source code available"}
                </SyntaxHighlighter>
              </div>
            </div>

            {/* Schema Refs */}
            {data.schemaRefs && data.schemaRefs.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold mb-1" style={{ color: data.color }}>
                  Columns Referenced
                </div>
                <div className="flex flex-wrap gap-1">
                  {data.schemaRefs.map((col) => (
                    <span
                      key={col}
                      className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                      style={{
                        background: `${data.color}15`,
                        color: data.color,
                      }}
                    >
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}
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
  const X_GAP = 320;
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
  const apiNodes = result?.nodes || [];
  const apiEdges = result?.edges || [];

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
        data: {
          nodeId: n.id,
          label: n.label,
          description: n.description,
          descriptionSource: n.description_source,
          code: n.code,
          color: n.color,
          icon: n.icon,
          lineNumber: n.line_number,
          isLoop: n.is_loop,
          schemaRefs: n.schema_refs,
          category: n.category,
        },
      })),
    [apiNodes, positions]
  );

  const flowEdges = useMemo(
    () =>
      apiEdges.map((e, i) => ({
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
          stroke: "var(--text-muted)",
          strokeWidth: 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: "var(--text-muted)",
        },
      })),
    [apiEdges]
  );

  const [nodes, , onNodesChange] = useNodesState(flowNodes);
  const [edges, , onEdgesChange] = useEdgesState(flowEdges);

  return (
    <div
      className="w-full rounded-xl overflow-hidden"
      style={{
        height: "calc(100vh - 200px)",
        minHeight: 500,
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
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
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
