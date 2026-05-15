/**
 * Column-level lineage trace computation.
 *
 * Walks the execution result's per-node column_lineage data to build a
 * focused sub-graph showing a single column's journey through the pipeline.
 */

// ── State constants (match backend) ──────────────────────────────
export const COL_STATES = {
  INTRODUCED: "introduced",
  PASSTHROUGH: "passthrough",
  DERIVED: "derived",
  RENAMED: "renamed",
  AGGREGATED: "aggregated",
  AGG_DROPPED: "agg_dropped",
  JOINED: "joined",
  DROPPED: "dropped",
  TYPE_CHANGED: "type_changed",
  WRITTEN: "written",
};

const STATE_LABELS = {
  introduced: "Introduced",
  passthrough: "Passthrough",
  derived: "Derived",
  renamed: "Renamed",
  aggregated: "Aggregated",
  agg_dropped: "Lost in Aggregation",
  joined: "From Merge",
  dropped: "Dropped",
  type_changed: "Type Changed",
  written: "Written",
};

const STATE_COLORS = {
  introduced: "#3b82f6",
  passthrough: "var(--text-muted)",
  derived: "#fb4e0b",
  renamed: "#3b82f6",
  aggregated: "#a855f7",
  agg_dropped: "#a855f7",
  joined: "#f97316",
  dropped: "#ef4444",
  type_changed: "#eab308",
  written: "#22c55e",
};

export function getStateLabel(state) {
  return STATE_LABELS[state] || state;
}

export function getStateColor(state) {
  return STATE_COLORS[state] || "var(--text-muted)";
}

// ── Edge type styling ────────────────────────────────────────────
export const EDGE_STYLES = {
  passthrough: { stroke: "var(--text-muted)", strokeWidth: 1, strokeDasharray: "6 3" },
  derived: { stroke: "#fb4e0b", strokeWidth: 2.5 },
  renamed: { stroke: "#3b82f6", strokeWidth: 1.5 },
  aggregated: { stroke: "#a855f7", strokeWidth: 1.5, strokeDasharray: "3 3" },
  agg_dropped: { stroke: "#a855f7", strokeWidth: 1, strokeDasharray: "6 3" },
  joined: { stroke: "#f97316", strokeWidth: 1.5 },
  dropped: { stroke: "#ef4444", strokeWidth: 1, strokeDasharray: "6 3" },
  type_changed: { stroke: "#eab308", strokeWidth: 1.5 },
  introduced: { stroke: "#3b82f6", strokeWidth: 1.5 },
};

// ── Build adjacency maps ─────────────────────────────────────────
function buildAdjacency(edges) {
  const fwd = {}; // node -> [downstream nodes]
  const bwd = {}; // node -> [upstream nodes]
  for (const e of edges) {
    (fwd[e.source] ??= []).push(e.target);
    (bwd[e.target] ??= []).push(e.source);
  }
  return { fwd, bwd };
}

// ── Extract sample values for a column from sample_output ────────
function extractSampleValues(sampleOutput, colName) {
  if (!sampleOutput?.length) return [];
  return sampleOutput
    .map((row) => row[colName])
    .filter((v) => v !== undefined && v !== null)
    .slice(0, 5);
}

// ── Compute column trace ─────────────────────────────────────────

/**
 * Compute a focused sub-graph for a single column's journey.
 *
 * @param {object} result - Full execution result with nodes, edges
 * @param {string} column - Column name to trace
 * @param {"upstream"|"downstream"} direction
 * @returns {{ traceNodes: Array, traceEdges: Array, summary: object }}
 */
export function computeColumnTrace(result, column, direction) {
  if (!result?.nodes?.length) return { traceNodes: [], traceEdges: [], summary: null };

  const { nodes, edges } = result;
  const { fwd, bwd } = buildAdjacency(edges);
  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n]));

  const traceNodes = [];
  const traceEdges = [];
  const visited = new Set();

  if (direction === "downstream") {
    _traceDownstream(column, nodes, nodeMap, fwd, traceNodes, traceEdges, visited);
  } else {
    _traceUpstream(column, nodes, nodeMap, bwd, traceNodes, traceEdges, visited);
  }

  const summary = _generateSummary(column, direction, traceNodes);

  return { traceNodes, traceEdges, summary };
}

// ── Downstream trace ─────────────────────────────────────────────
function _traceDownstream(column, nodes, nodeMap, fwd, traceNodes, traceEdges, visited) {
  // Walk nodes in order, tracking the column name (may change on rename)
  const orderedNodes = nodes.filter((n) => n.status === "completed");
  const queue = []; // [{nodeId, colName}]

  // Find first node where column appears
  for (const node of orderedNodes) {
    const cl = node.runtime?.column_lineage;
    if (!cl) continue;
    const mapping = cl[column];
    if (mapping && (mapping.state === "introduced" || mapping.state === "passthrough")) {
      queue.push({ nodeId: node.id, colName: column });
      break;
    }
  }

  while (queue.length) {
    const { nodeId, colName } = queue.shift();
    const key = `${nodeId}:${colName}`;
    if (visited.has(key)) continue;
    visited.add(key);

    const node = nodeMap[nodeId];
    if (!node) continue;
    const cl = node.runtime?.column_lineage;
    if (!cl) continue;
    const mapping = cl[colName];
    if (!mapping) continue;

    // Create trace node
    const traceNode = _buildTraceNode(node, colName, mapping);
    traceNodes.push(traceNode);

    // If this column was dropped or agg_dropped, it terminates here
    if (mapping.state === "dropped" || mapping.state === "agg_dropped") {
      continue;
    }

    // Follow downstream edges
    const downstreamIds = fwd[nodeId] || [];
    for (const nextId of downstreamIds) {
      const nextNode = nodeMap[nextId];
      if (!nextNode?.runtime?.column_lineage) continue;

      // Check if column passes through (possibly renamed)
      const nextCl = nextNode.runtime.column_lineage;
      // Direct passthrough / aggregated / type_changed
      if (nextCl[colName]) {
        const nextState = nextCl[colName].state;
        traceEdges.push({
          source: key,
          target: `${nextId}:${colName}`,
          type: nextState,
          label: _edgeLabel(nextState, colName, colName),
        });
        queue.push({ nodeId: nextId, colName });
      }

      // Check if column was renamed at next node
      for (const [nextCol, nextMapping] of Object.entries(nextCl)) {
        if (nextMapping.state === "renamed" && nextMapping.from?.includes(colName)) {
          traceEdges.push({
            source: key,
            target: `${nextId}:${nextCol}`,
            type: "renamed",
            label: `${colName} → ${nextCol}`,
          });
          queue.push({ nodeId: nextId, colName: nextCol });
        }
        // Check if column was used to derive a new column
        if (nextMapping.state === "derived" && nextMapping.from?.includes(colName)) {
          traceEdges.push({
            source: key,
            target: `${nextId}:${nextCol}`,
            type: "derived",
            label: `derived`,
          });
          queue.push({ nodeId: nextId, colName: nextCol });
        }
      }

      // Check if column was dropped/agg_dropped at next node
      if (nextCl[colName] && (nextCl[colName].state === "dropped" || nextCl[colName].state === "agg_dropped")) {
        const droppedKey = `${nextId}:${colName}`;
        if (!visited.has(droppedKey)) {
          traceEdges.push({
            source: key,
            target: droppedKey,
            type: nextCl[colName].state,
            label: nextCl[colName].state === "agg_dropped" ? "lost in aggregation" : "dropped",
          });
          queue.push({ nodeId: nextId, colName });
        }
      }
    }
  }
}

// ── Upstream trace ───────────────────────────────────────────────
function _traceUpstream(column, nodes, nodeMap, bwd, traceNodes, traceEdges, visited) {
  const orderedNodes = nodes.filter((n) => n.status === "completed");
  const queue = [];

  // Find last node where column appears
  for (let i = orderedNodes.length - 1; i >= 0; i--) {
    const node = orderedNodes[i];
    const cl = node.runtime?.column_lineage;
    if (!cl) continue;
    if (cl[column] && cl[column].state !== "dropped" && cl[column].state !== "agg_dropped") {
      queue.push({ nodeId: node.id, colName: column });
      break;
    }
  }

  while (queue.length) {
    const { nodeId, colName } = queue.shift();
    const key = `${nodeId}:${colName}`;
    if (visited.has(key)) continue;
    visited.add(key);

    const node = nodeMap[nodeId];
    if (!node) continue;
    const cl = node.runtime?.column_lineage;
    if (!cl) continue;
    const mapping = cl[colName];
    if (!mapping) continue;

    const traceNode = _buildTraceNode(node, colName, mapping);
    traceNodes.push(traceNode);

    // If introduced, this is the origin — stop
    if (mapping.state === "introduced") continue;
    // If joined, this is the origin from merge — stop
    if (mapping.state === "joined") continue;

    // Follow upstream based on "from" field
    const fromCols = mapping.from || [];
    const upstreamIds = bwd[nodeId] || [];

    for (const prevId of upstreamIds) {
      const prevNode = nodeMap[prevId];
      if (!prevNode?.runtime?.column_lineage) continue;
      const prevCl = prevNode.runtime.column_lineage;

      for (const fromCol of fromCols) {
        if (prevCl[fromCol]) {
          traceEdges.push({
            source: `${prevId}:${fromCol}`,
            target: key,
            type: mapping.state,
            label: _edgeLabel(mapping.state, fromCol, colName),
          });
          queue.push({ nodeId: prevId, colName: fromCol });
        }
      }
    }
  }
}

// ── Build a trace node ───────────────────────────────────────────
function _buildTraceNode(node, colName, mapping) {
  const runtime = node.runtime || {};
  const sampleValues = extractSampleValues(runtime.sample_output, colName);
  const prevNulls = runtime.null_counts
    ? null // we'd need the prev node's null count — approximate from column_lineage
    : null;

  return {
    id: `${node.id}:${colName}`,
    nodeId: node.id,
    column: colName,
    state: mapping.state,
    dtype: mapping.dtype || "",
    nullCount: mapping.null_count ?? 0,
    from: mapping.from || [],
    operationLabel: node.label || "",
    operationCategory: node.category || "",
    operationColor: node.color || "",
    operationIcon: node.icon || "",
    code: node.code || "",
    description: node.description || "",
    descriptionSource: node.description_source || "template",
    lineNumber: node.line_number,
    rowsIn: runtime.rows_in,
    rowsOut: runtime.rows_out,
    sampleValues,
    status: node.status,
    error: runtime.error,
  };
}

// ── Edge labels ──────────────────────────────────────────────────
function _edgeLabel(state, fromCol, toCol) {
  switch (state) {
    case "passthrough": return "";
    case "derived": return "derived";
    case "renamed": return `${fromCol} → ${toCol}`;
    case "aggregated": return "⚠️ aggregated";
    case "agg_dropped": return "lost in aggregation";
    case "joined": return "from merge";
    case "dropped": return "dropped";
    case "type_changed": return "type changed";
    default: return "";
  }
}

// ── Journey summary generation ───────────────────────────────────
function _generateSummary(column, direction, traceNodes) {
  if (!traceNodes.length) return null;

  const states = traceNodes.map((n) => n.state);
  const firstNode = traceNodes[0];
  const lastNode = traceNodes[traceNodes.length - 1];

  // Key events
  const wasAggregated = states.includes("aggregated");
  const wasDerived = states.includes("derived");
  const wasRenamed = states.includes("renamed");
  const wasDropped = states.includes("dropped") || states.includes("agg_dropped");
  const wasJoined = states.includes("joined");
  const wasTypeCast = states.includes("type_changed");

  // Derived downstream columns (columns derived FROM this column)
  const derivedCols = traceNodes
    .filter((n) => n.state === "derived" && n.column !== column)
    .map((n) => n.column);

  // Count passthroughs
  const passthroughCount = states.filter((s) => s === "passthrough").length;

  // Build flowing narrative (2-3 sentences, not bullet points)
  const parts = [];

  // Origin sentence
  if (direction === "downstream") {
    const dtypeStr = firstNode.dtype ? ` as a ${firstNode.dtype} field` : "";
    const rowStr = firstNode.rowsOut != null
      ? ` with ${firstNode.rowsOut.toLocaleString()} rows`
      : "";
    parts.push(
      `The column "${column}" originates at the ${firstNode.operationLabel} step${dtypeStr}${rowStr}.`
    );
  } else {
    const dtypeStr = firstNode.dtype ? ` as a ${firstNode.dtype} field` : "";
    const rowStr = firstNode.rowsOut != null
      ? ` containing ${firstNode.rowsOut.toLocaleString()} rows`
      : "";
    parts.push(
      `The column "${column}" appears in the final output at the ${firstNode.operationLabel} step${dtypeStr}${rowStr}.`
    );
  }

  // Key transformations sentence
  const events = [];
  if (wasDerived) {
    const dn = traceNodes.find((n) => n.state === "derived");
    if (dn?.from?.length) {
      events.push(`calculated from ${dn.from.join(", ")}`);
    } else {
      events.push("derived through a computation");
    }
  }
  if (wasRenamed) {
    const rn = traceNodes.find((n) => n.state === "renamed");
    if (rn?.from?.[0]) events.push(`renamed from "${rn.from[0]}"`);
  }
  if (wasJoined) events.push("brought in from a merged dataset");
  if (wasAggregated) events.push("summarised during the grouping step");
  if (wasTypeCast) events.push("had its data type converted");

  if (events.length) {
    parts.push("Along the way, it was " + events.join(", ") + ".");
  }

  // Destination sentence
  if (wasDropped) {
    const dropNode = traceNodes.find(
      (n) => n.state === "dropped" || n.state === "agg_dropped"
    );
    const reason =
      dropNode?.state === "agg_dropped"
        ? "lost during the aggregation step"
        : "explicitly removed";
    parts.push(`This column was ${reason} at ${dropNode?.operationLabel || "a later step"} and does not appear in the final output.`);
  } else if (lastNode) {
    if (direction === "downstream") {
      const lastCat = lastNode.operationCategory;
      if (lastCat === "target") {
        parts.push(`It is ultimately written to the output at ${lastNode.operationLabel}.`);
      } else {
        parts.push(`It passes through ${traceNodes.length} operation${traceNodes.length > 1 ? "s" : ""} in total.`);
      }
    } else {
      parts.push(`Tracing back, it originates at ${lastNode.operationLabel}.`);
    }
  }

  const narrative = parts.join(" ");

  return {
    column,
    direction,
    dtype: firstNode.dtype || lastNode?.dtype || "",
    totalOperations: traceNodes.length,
    passthroughCount,
    derivedCols,
    wasAggregated,
    wasRenamed,
    wasDropped,
    wasJoined,
    wasTypeCast,
    narrative,
    // Keep lines as empty array for backward compat, but narrative is primary
    lines: [],
  };
}
