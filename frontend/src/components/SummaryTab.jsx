import {
  Database, HardDrive, Filter, GitMerge, BarChart2, Shuffle,
  Sparkles, Columns, ArrowUpDown, Zap, AlertTriangle, FileCode,
  Layers, Code, Download,
} from "lucide-react";
import {
  getDownloadUrl,
  getStaticHtmDownloadUrl,
  STATIC_HTM_OUTPUT_NAME,
} from "../lib/api";

const iconMap = {
  database: Database,
  "hard-drive": HardDrive,
  filter: Filter,
  "git-merge": GitMerge,
  "bar-chart-2": BarChart2,
  shuffle: Shuffle,
  sparkles: Sparkles,
  columns: Columns,
  "arrow-up-down": ArrowUpDown,
  zap: Zap,
  "help-circle": AlertTriangle,
};

function MetricCard({ icon: Icon, label, value, color, delay = 0 }) {
  return (
    <div
      className="flex items-center gap-3 p-4 rounded-2xl transition-all duration-300 hover:scale-[1.02] hover:-translate-y-1 group relative overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        animation: `fadeIn 0.4s ease-out ${delay}ms both`,
      }}
    >
      {/* Glow border effect on hover */}
      <div className="absolute inset-0 border-2 border-transparent group-hover:border-[var(--primary)] rounded-2xl opacity-0 group-hover:opacity-50 transition-all duration-300 pointer-events-none" />
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${color}15`, color }}
      >
        <Icon size={18} />
      </div>
      <div>
        <div
          className="text-2xl font-bold leading-tight"
          style={{ color: "var(--text-primary)" }}
        >
          {value}
        </div>
        <div
          className="text-xs font-medium mt-0.5"
          style={{ color: "var(--text-muted)" }}
        >
          {label}
        </div>
      </div>
    </div>
  );
}

function SourceTargetCard({ title, icon: Icon, items, color, delay = 0 }) {
  return (
    <div
      className="p-5 rounded-2xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(251,78,11,0.05)] group"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        animation: `fadeIn 0.4s ease-out ${delay}ms both`,
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} style={{ color }} />
        <span
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {title}
        </span>
        <span
          className="text-xs px-1.5 py-0.5 rounded-full ml-auto"
          style={{
            background: `${color}15`,
            color,
          }}
        >
          {items.length}
        </span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          None detected
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 rounded-xl transition-colors duration-200"
              style={{
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
              }}
            >
              <span
                className="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
                style={{ background: `${color}20`, color }}
              >
                {item.format}
              </span>
              <span
                className="text-sm font-medium truncate"
                style={{ color: "var(--text-primary)" }}
              >
                {item.name?.replace(/^(Read|Write)\s\w+:\s/, "") || "unknown"}
              </span>
              <span
                className="text-xs ml-auto shrink-0"
                style={{ color: "var(--text-muted)" }}
              >
                Line {item.line}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SummaryTab({ result }) {
  if (!result?.summary) {
    return (
      <div className="text-center py-12" style={{ color: "var(--text-muted)" }}>
        No summary data available
      </div>
    );
  }

  const { summary } = result;
  const metrics = summary.metrics || {};

  const metricCards = [
    { icon: Filter, label: "Filters", value: metrics.filters || 0, color: "#eab308" },
    { icon: GitMerge, label: "Joins / Merges", value: metrics.joins || 0, color: "#f97316" },
    { icon: BarChart2, label: "Aggregations", value: metrics.aggregations || 0, color: "#a855f7" },
    { icon: Sparkles, label: "Cleaning Ops", value: metrics.cleaning || 0, color: "#14b8a6" },
    { icon: Shuffle, label: "Reshapes", value: metrics.reshapes || 0, color: "#ef4444" },
    { icon: Columns, label: "Column Ops", value: metrics.column_ops || 0, color: "#64748b" },
    { icon: ArrowUpDown, label: "Sort / Index", value: metrics.sort_index || 0, color: "#92400e" },
    { icon: Zap, label: "Apply / Map", value: metrics.apply_map || 0, color: "#ec4899" },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {summary.total_duration_ms != null && (
        <div
          className="px-4 py-3 rounded-2xl text-sm font-medium flex flex-wrap gap-4"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        >
          <span>
            Status: <strong>{summary.status || "completed"}</strong>
          </span>
          <span>Duration: {summary.total_duration_ms} ms</span>
          <span>
            Nodes: {summary.nodes_completed ?? 0}/{summary.total_nodes ?? 0} completed
          </span>
        </div>
      )}

      {/* Row 1: Sources & Targets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SourceTargetCard
          title="Data Sources"
          icon={Database}
          items={summary.sources || []}
          color="#3b82f6"
          delay={0}
        />
        <SourceTargetCard
          title="Data Targets"
          icon={HardDrive}
          items={summary.targets || []}
          color="#22c55e"
          delay={50}
        />
      </div>

      {/* Row 2: Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metricCards.map((card, i) => (
          <MetricCard key={card.label} {...card} delay={100 + i * 40} />
        ))}
      </div>

      <div
        className="p-5 rounded-2xl"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Download size={16} style={{ color: "var(--primary)" }} />
          Output downloads
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={getStaticHtmDownloadUrl()}
            download={STATIC_HTM_OUTPUT_NAME}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold px-3 py-2 rounded-xl hover:opacity-90 transition-opacity"
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              color: "var(--primary)",
            }}
          >
            {STATIC_HTM_OUTPUT_NAME}
          </a>
          {(result?.output_files || []).map((o) => {
            const href =
              result.session_id && o.name
                ? getDownloadUrl(result.session_id, o.name)
                : o.download_url || "#";
            return (
              <a
                key={o.name}
                href={href}
                download={o.name}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-semibold px-3 py-2 rounded-xl hover:opacity-90 transition-opacity"
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  color: "var(--primary)",
                }}
              >
                {o.name}
              </a>
            );
          })}
        </div>
        {!(result?.output_files?.length > 0) && (
          <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
            No pipeline output files were written. Claim Center HTM is always available above.
          </p>
        )}
      </div>

      {/* Row 3: Script Metadata */}
      <div
        className="flex items-center justify-between px-6 py-4 rounded-2xl"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
          animation: "fadeIn 0.4s ease-out 450ms both",
        }}
      >
        {[
          { icon: Layers, label: "Total Nodes", value: summary.total_nodes || 0 },
          { icon: Code, label: "Lines of Code", value: summary.total_lines || 0 },
          { icon: FileCode, label: "Pipelines", value: summary.pipeline_count || 0 },
          { icon: AlertTriangle, label: "Warnings", value: summary.warning_count || 0 },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <item.icon size={14} style={{ color: "var(--text-muted)" }} />
            <span
              className="text-xs font-medium"
              style={{ color: "var(--text-muted)" }}
            >
              {item.label}:
            </span>
            <span
              className="text-sm font-bold"
              style={{
                color:
                  item.label === "Warnings" && item.value > 0
                    ? "#ef4444"
                    : "var(--text-primary)",
              }}
            >
              {item.value}
            </span>
          </div>
        ))}
        {result?.llm_used && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
            style={{
              background: "rgba(168, 85, 247, 0.1)",
              border: "1px solid rgba(168, 85, 247, 0.2)",
            }}
          >
            <Sparkles size={12} style={{ color: "#a855f7" }} />
            <span
              className="text-xs font-semibold"
              style={{ color: "#a855f7" }}
            >
              AI Enhanced
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
