import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  useNodesState,
  useEdgesState,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Columns3,
  Search,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Database,
  Sparkles,
  Merge,
  Trash2,
  ArrowRightLeft,
  Type,
  Eye,
  Loader2,
} from "lucide-react";
import { getApiBase } from "../lib/apiBase";
import useAnalysisStore from "../store/useAnalysisStore";
import {
  computeColumnTrace,
  getStateLabel,
  getStateColor,
  EDGE_STYLES,
  COL_STATES,
} from "../lib/columnTrace";

/* ================================================================
   Custom ReactFlow node — Column Trace Node (collapsible)
   ================================================================ */
function ColumnTraceNodeComponent({ data }) {
  const [expanded, setExpanded] = useState(false);
  const d = data;
  const stateColor = getStateColor(d.state);
  const stateLabel = getStateLabel(d.state);

  const isTerminal =
    d.state === "dropped" ||
    d.state === "agg_dropped" ||
    d.status === "failed";
  const isFailed = d.status === "failed";

  // Prefer column-specific journey summary; fall back to pipeline operation description
  const narrativeText = (d.journeySummary || d.description || "").trim();
  const narrativeSource = d.journeySummary ? d.journeySummarySource : d.descriptionSource;
  const narrativeIsAi = narrativeSource === "llm";

  return (
    <div
      className="column-trace-node"
      style={{
        borderColor: isFailed ? "#ef4444" : stateColor,
        borderStyle: isTerminal ? "dashed" : "solid",
        opacity: isFailed ? 0.8 : 1,
      }}
    >
      {/* Header */}
      <div className="ctn-header">
        <div className="ctn-name-row">
          <div className="ctn-dot" style={{ background: stateColor }} />
          <span className="ctn-col-name">{d.column}</span>
          <span className="ctn-dtype">({d.dtype || "?"})</span>
          <span
            className="ctn-badge"
            style={{ background: stateColor + "22", color: stateColor, borderColor: stateColor + "44" }}
          >
            {stateLabel}
          </span>
        </div>
        <div className="ctn-op-label">{d.operationLabel}</div>
      </div>

      {/* Collapsed metrics */}
      {!expanded && (
        <div className="ctn-metrics-compact">
          {d.rowsIn != null && d.rowsOut != null && (
            <span>
              {d.rowsIn.toLocaleString()} → {d.rowsOut.toLocaleString()} outgoing rows
            </span>
          )}
          {d.rowsOut != null && d.rowsIn == null && (
            <span>{d.rowsOut.toLocaleString()} outgoing rows</span>
          )}
          {d.nullCount > 0 && (
            <span style={{ color: "#eab308" }}>⚠ {d.nullCount} nulls</span>
          )}
        </div>
      )}

      {narrativeText && (
        <div className="ctn-description">
          <div className="ctn-description-header">
            {narrativeIsAi && <Sparkles size={11} style={{ color: "#a855f7" }} />}
            {narrativeIsAi && <span className="ctn-ai-badge">AI</span>}
          </div>
          <p className="ctn-description-text">{narrativeText}</p>
        </div>
      )}

      {/* Expanded detail */}
      {expanded && (
        <div className="ctn-detail">
          {d.rowsIn != null && (
            <div className="ctn-row">
              <span className="ctn-label">Outgoing Rows</span>
              <span>
                {d.rowsIn.toLocaleString()} → {d.rowsOut?.toLocaleString() ?? "?"}{" "}
                {d.rowsIn !== d.rowsOut && (
                  <span
                    style={{
                      color:
                        d.rowsOut < d.rowsIn ? "#ef4444" : "#22c55e",
                    }}
                  >
                    ({d.rowsOut < d.rowsIn ? "" : "+"}
                    {(d.rowsOut - d.rowsIn).toLocaleString()})
                  </span>
                )}
              </span>
            </div>
          )}
          {d.rowsOut != null && d.rowsIn == null && (
            <div className="ctn-row">
              <span className="ctn-label">Outgoing Rows</span>
              <span>{d.rowsOut.toLocaleString()}</span>
            </div>
          )}
          <div className="ctn-row">
            <span className="ctn-label">Nulls</span>
            <span>{d.nullCount}</span>
          </div>
          {d.from?.length > 0 && d.state !== "passthrough" && (
            <div className="ctn-row">
              <span className="ctn-label">From</span>
              <span className="ctn-from-cols">{d.from.join(", ")}</span>
            </div>
          )}
          {d.sampleValues?.length > 0 && (
            <div className="ctn-sample">
              <span className="ctn-label">Sample</span>
              <div className="ctn-sample-values">
                {d.sampleValues.map((v, i) => (
                  <span key={i} className="ctn-sample-val">
                    {String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {d.code && (
            <div className="ctn-code">
              <code>{d.code}</code>
            </div>
          )}
        </div>
      )}

      {/* Failed node banner */}
      {isFailed && (
        <div className="ctn-failed">
          <AlertTriangle size={12} />
          <span>Trace ends — remaining operations not executed</span>
        </div>
      )}

      {/* Merge annotation */}
      {d.state === "joined" && (
        <div className="ctn-merge-note">
          This column was brought in from another dataset during the merge
        </div>
      )}

      {d.state === "agg_dropped" && (
        <div className="ctn-merge-note" style={{ color: "#a855f7" }}>
          This column was not included in the aggregation and was automatically removed
        </div>
      )}

      {/* Expand indicator */}
      <button
        type="button"
        className="ctn-expand-hint"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={expanded ? "Collapse details" : "Expand details"}
      >
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {/* Handles */}
      <Handle 
        type="target" 
        position={d.direction === "upstream" ? Position.Bottom : Position.Top} 
        style={{ background: stateColor, width: 8, height: 8 }} 
      />
      <Handle 
        type="source" 
        position={d.direction === "upstream" ? Position.Top : Position.Bottom} 
        style={{ background: stateColor, width: 8, height: 8 }} 
      />
    </div>
  );
}

const nodeTypes = { columnTrace: ColumnTraceNodeComponent };

/* ================================================================
   State Icon helper
   ================================================================ */
function StateIcon({ state, size = 14 }) {
  switch (state) {
    case "introduced": return <Database size={size} />;
    case "derived": return <Sparkles size={size} />;
    case "renamed": return <ArrowRightLeft size={size} />;
    case "joined": return <Merge size={size} />;
    case "dropped": return <Trash2 size={size} />;
    case "agg_dropped": return <AlertTriangle size={size} />;
    case "type_changed": return <Type size={size} />;
    default: return <Eye size={size} />;
  }
}

/* ================================================================
   Journey Summary Card
   ================================================================ */
function JourneySummary({ summary, overallSummary, llmUsed, isLoading }) {
  if (!summary) return null;

  // Use LLM overall_summary if available, else use template narrative
  const displayNarrative = overallSummary || summary.narrative || "";

  return (
    <div className="journey-summary-card">
      <div className="js-header">
        <div className="js-title">
          <Columns3 size={16} style={{ color: "#fb4e0b" }} />
          <span className="js-col-name">{summary.column}</span>
          <span className="js-dtype">({summary.dtype})</span>
          {llmUsed && (
            <span className="js-ai-badge">
              <Sparkles size={10} />
              AI Summary
            </span>
          )}
        </div>
        <span className="js-direction-badge">
          {summary.direction === "downstream" ? (
            <>Source {"->"}  Target</>
          ) : (
            <>Target {"->"}  Source</>
          )}
        </span>
      </div>
      <div className="js-narrative">
        {isLoading && !displayNarrative ? (
          <div className="js-narrative-loading">
            <Loader2 size={14} className="ctn-spinner" />
            <span>Generating journey summary...</span>
          </div>
        ) : (
          <p className="js-narrative-text">{displayNarrative}</p>
        )}
      </div>
      {summary.totalOperations > 0 && (
        <div className="js-meta">
          <span>{summary.totalOperations} operation{summary.totalOperations > 1 ? "s" : ""}</span>
          {summary.wasDropped && <span className="js-meta-tag dropped">Dropped</span>}
          {summary.wasAggregated && <span className="js-meta-tag aggregated">Aggregated</span>}
          {summary.wasDerived && <span className="js-meta-tag derived">Derived</span>}
          {summary.wasRenamed && <span className="js-meta-tag renamed">Renamed</span>}
          {summary.wasJoined && <span className="js-meta-tag joined">Joined</span>}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   Main Column Lineage Tab
   ================================================================ */
export default function ColumnLineageTab({ result }) {
  const columnTraceColumn = useAnalysisStore((s) => s.columnTraceColumn);
  const columnTraceDirection = useAnalysisStore((s) => s.columnTraceDirection);
  const columnTraceData = useAnalysisStore((s) => s.columnTraceData);
  const setColumnTrace = useAnalysisStore((s) => s.setColumnTrace);
  const setColumnTraceData = useAnalysisStore((s) => s.setColumnTraceData);
  const resetColumnTrace = useAnalysisStore((s) => s.resetColumnTrace);

  const [selectedCol, setSelectedCol] = useState("");
  const [direction, setDirection] = useState("downstream");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [journeySummaryData, setJourneySummaryData] = useState(null);
  const [journeySummaryLoading, setJourneySummaryLoading] = useState(false);
  const journeySummaryCache = useRef({});
  const pipelineCode = useAnalysisStore((s) => s.pipelineCode);

  const discovered = result?.discovered_columns;
  const hasColumns =
    discovered &&
    ((discovered.source?.length || 0) + (discovered.output?.length || 0)) > 0;

  // Compute trace when column + direction are set
  useEffect(() => {
    if (!selectedCol || !result) return;
    const trace = computeColumnTrace(result, selectedCol, direction);
    setColumnTraceData(trace);
    setJourneySummaryData(null);
  }, [selectedCol, direction, result]);

  // Show loading as soon as a column is selected (until summaries are ready)
  useEffect(() => {
    if (!selectedCol) {
      setJourneySummaryLoading(false);
      return;
    }
    const cacheKey = `${selectedCol}:${direction}`;
    if (!journeySummaryCache.current[cacheKey]) {
      setJourneySummaryLoading(true);
    }
  }, [selectedCol, direction]);

  // Fetch GenAI / template journey summaries after trace is computed
  useEffect(() => {
    if (!columnTraceData?.traceNodes?.length || !selectedCol) {
      if (!columnTraceData?.traceNodes?.length) setJourneySummaryLoading(false);
      return;
    }

    const cacheKey = `${selectedCol}:${direction}`;
    if (journeySummaryCache.current[cacheKey]) {
      setJourneySummaryData(journeySummaryCache.current[cacheKey]);
      setJourneySummaryLoading(false);
      return;
    }

    let cancelled = false;
    setJourneySummaryLoading(true);

    const fetchSummary = async () => {
      try {
        const resp = await fetch(`${getApiBase()}/column-journey-summary`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            column: selectedCol,
            direction,
            trace_nodes: columnTraceData.traceNodes,
            source_code: pipelineCode || "",
            session_id: result?.session_id || null,
          }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!cancelled) {
          journeySummaryCache.current[cacheKey] = data;
          setJourneySummaryData(data);
        }
      } catch (err) {
        console.warn("Column journey summary fetch failed:", err);
      } finally {
        if (!cancelled) setJourneySummaryLoading(false);
      }
    };

    fetchSummary();
    return () => { cancelled = true; };
  }, [columnTraceData, selectedCol, direction, pipelineCode]);

  const hasTraceNodes = (columnTraceData?.traceNodes?.length ?? 0) > 0;
  const showSummaryLoading = Boolean(selectedCol && hasTraceNodes && journeySummaryLoading);

  // Build ReactFlow nodes and edges from trace data (after summaries are ready)
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!columnTraceData?.traceNodes?.length || journeySummaryLoading) {
      return { flowNodes: [], flowEdges: [] };
    }

    const nodeSummaries = journeySummaryData?.node_summaries || {};
    const summarySource = journeySummaryData?.llm_used ? "llm" : "template";

    const fNodes = columnTraceData.traceNodes.map((tn, i) => ({
      id: tn.id,
      type: "columnTrace",
      position: { x: 60, y: i * 280 },
      data: {
        ...tn,
        direction,
        journeySummary: nodeSummaries[tn.id] || "",
        journeySummarySource: summarySource,
      },
      sourcePosition: direction === "upstream" ? Position.Top : Position.Bottom,
      targetPosition: direction === "upstream" ? Position.Bottom : Position.Top,
    }));

    const fEdges = columnTraceData.traceEdges.map((te, i) => {
      const style = EDGE_STYLES[te.type] || EDGE_STYLES.passthrough;
      return {
        id: `ce-${i}`,
        source: te.source,
        target: te.target,
        label: te.label || "",
        type: "smoothstep",
        style: {
          stroke: style.stroke,
          strokeWidth: style.strokeWidth || 1,
          strokeDasharray: style.strokeDasharray || undefined,
        },
        labelStyle: { fill: style.stroke, fontSize: 13, fontWeight: 600 },
        labelBgStyle: { fill: "var(--bg-card)", stroke: style.stroke, strokeWidth: 0.5 },
        animated: te.type === "derived",
      };
    });

    return { flowNodes: fNodes, flowEdges: fEdges };
  }, [columnTraceData, journeySummaryData, journeySummaryLoading]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);
  const flowRef = useRef(null);

  const fitColumnTraceView = useCallback(() => {
    const rf = flowRef.current;
    if (!rf) return;
    rf.fitView({
      padding: 0.18,
      duration: 200,
      minZoom: 0.86,
      maxZoom: 1.26,
    });
    const vp = rf.getViewport();
    rf.setViewport(
      {
        x: vp.x,
        y: vp.y,
        zoom: Math.min(vp.zoom * 1.2, 1.75),
      },
      { duration: 200 }
    );
  }, []);

  const onFlowInit = useCallback(
    (instance) => {
      flowRef.current = instance;
      fitColumnTraceView();
    },
    [fitColumnTraceView]
  );

  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges]);

  useEffect(() => {
    if (!flowNodes.length) return;
    const t = window.setTimeout(fitColumnTraceView, 80);
    return () => window.clearTimeout(t);
  }, [flowNodes.length, flowEdges.length, fitColumnTraceView]);

  // Filter columns for search
  const filteredSource = useMemo(() => {
    if (!discovered?.source) return [];
    const q = searchFilter.toLowerCase();
    return q ? discovered.source.filter((c) => c.name.toLowerCase().includes(q)) : discovered.source;
  }, [discovered, searchFilter]);

  const filteredOutput = useMemo(() => {
    if (!discovered?.output) return [];
    const q = searchFilter.toLowerCase();
    return q ? discovered.output.filter((c) => c.name.toLowerCase().includes(q)) : discovered.output;
  }, [discovered, searchFilter]);

  // Empty / disabled state
  if (!hasColumns) {
    return (
      <div className="clt-empty">
        <Columns3 size={40} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
        <p>No column data available</p>
        <p className="clt-empty-sub">Execute the pipeline to enable column-level lineage tracing</p>
      </div>
    );
  }

  return (
    <div className="column-lineage-tab">
      {/* Controls bar */}
      <div className="clt-controls">
        {/* Column dropdown */}
        <div className="clt-dropdown-wrap">
          <button
            className="clt-dropdown-btn"
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            <Columns3 size={14} />
            <span>{selectedCol || "Select a column..."}</span>
            <ChevronDown size={14} className={dropdownOpen ? "clt-chevron-open" : ""} />
          </button>

          {dropdownOpen && (
            <div className="clt-dropdown-menu">
              <div className="clt-dropdown-search">
                <Search size={13} />
                <input
                  type="text"
                  placeholder="Search columns..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  autoFocus
                />
              </div>
              {direction === "downstream" && filteredSource.length > 0 && (
                <>
                  <div className="clt-dropdown-section">Source Columns</div>
                  {filteredSource.map((c) => (
                    <button
                      key={`src-${c.name}`}
                      className={`clt-dropdown-item ${selectedCol === c.name ? "active" : ""}`}
                      onClick={() => {
                        setSelectedCol(c.name);
                        setDropdownOpen(false);
                        setSearchFilter("");
                      }}
                    >
                      <span className="clt-col-dot" style={{ background: "#3b82f6" }} />
                      <span>{c.name}</span>
                      <span className="clt-col-dtype">{c.dtype}</span>
                    </button>
                  ))}
                </>
              )}
              {direction === "upstream" && filteredOutput.length > 0 && (
                <>
                  <div className="clt-dropdown-section">Target Columns</div>
                  {filteredOutput.map((c) => (
                    <button
                      key={`out-${c.name}`}
                      className={`clt-dropdown-item ${selectedCol === c.name ? "active" : ""}`}
                      onClick={() => {
                        setSelectedCol(c.name);
                        setDropdownOpen(false);
                        setSearchFilter("");
                      }}
                    >
                      <span className="clt-col-dot" style={{ background: "#22c55e" }} />
                      <span>{c.name}</span>
                      <span className="clt-col-dtype">{c.dtype}</span>
                    </button>
                  ))}
                </>
              )}
              {((direction === "downstream" && filteredSource.length === 0) || (direction === "upstream" && filteredOutput.length === 0)) && (
                <div className="clt-dropdown-empty">No matching columns</div>
              )}
            </div>
          )}
        </div>

        {/* Direction toggle */}
        <div className="clt-direction-toggle">
          <button
            className={`clt-dir-btn ${direction === "downstream" ? "active" : ""}`}
            onClick={() => { setDirection("downstream"); setSelectedCol(""); }}
          >
            Source {"->"} Target
          </button>
          <button
            className={`clt-dir-btn ${direction === "upstream" ? "active" : ""}`}
            onClick={() => { setDirection("upstream"); setSelectedCol(""); }}
          >
            Target {"->"} Source
          </button>
        </div>
      </div>

      {/* No column selected state */}
      {!selectedCol && (
        <div className="clt-prompt">
          <Columns3 size={32} style={{ color: "var(--text-muted)", opacity: 0.5 }} />
          <p>Select a column from the dropdown above to trace its lineage</p>
        </div>
      )}

      {/* Trace result */}
      {selectedCol && columnTraceData && (
        <div className="clt-trace-container">
          {showSummaryLoading ? (
            <div className="clt-summary-loading">
              <Loader2 size={32} className="ctn-spinner" />
              <p>Generating AI column journey summaries...</p>
            </div>
          ) : (
            <>
              <JourneySummary
                summary={columnTraceData.summary}
                overallSummary={journeySummaryData?.overall_summary}
                llmUsed={journeySummaryData?.llm_used}
                isLoading={false}
              />

              {hasTraceNodes ? (
                <div className="clt-graph">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    onInit={onFlowInit}
                    proOptions={{ hideAttribution: true }}
                    minZoom={0.4}
                    maxZoom={1.75}
                    nodesConnectable={false}
                  >
                    <Background color="var(--text-muted)" gap={20} size={0.5} style={{ opacity: 0.15 }} />
                    <Controls
                      showInteractive={false}
                      style={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                      }}
                    />
                  </ReactFlow>
                </div>
              ) : (
                <div className="clt-no-trace">
                  <AlertTriangle size={20} style={{ color: "#eab308" }} />
                  <p>Column "{selectedCol}" was not found in the execution trace</p>
                  <p className="clt-empty-sub">This column may not have been referenced during execution</p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
