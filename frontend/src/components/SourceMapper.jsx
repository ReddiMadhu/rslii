import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  AlertCircle,
  ArrowLeft,
  Cloud,
  Database,
  FileSpreadsheet,
  HardDrive,
  Link2,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "../lib/utils";
import useAnalysisStore, { APP_STATES } from "../store/useAnalysisStore";
import { validateSources } from "../lib/api";
import RiskBadge from "./RiskBadge";

const EXT_BY_FORMAT = {
  csv: [".csv", ".tsv", ".txt"],
  excel: [".xlsx", ".xls"],
  parquet: [".parquet", ".pq"],
  json: [".json"],
  html: [".html", ".htm"],
  xml: [".xml"],
  feather: [".feather"],
  orc: [".orc"],
  stata: [".dta"],
  pickle: [".pkl", ".pickle"],
};

/** Demo connectors — upload path is the only active flow. */
const DATA_SOURCE_CONNECTORS = [
  { id: "postgresql", label: "PostgreSQL", group: "SQL" },
  { id: "mysql", label: "MySQL", group: "SQL" },
  { id: "sqlserver", label: "SQL Server", group: "SQL" },
  { id: "oracle", label: "Oracle", group: "SQL" },
  { id: "sqlite", label: "SQLite", group: "SQL" },
  { id: "snowflake", label: "Snowflake", group: "Warehouse" },
  { id: "bigquery", label: "BigQuery", group: "Warehouse" },
  { id: "redshift", label: "Redshift", group: "Warehouse" },
  { id: "mongodb", label: "MongoDB", group: "NoSQL" },
  { id: "csv_remote", label: "CSV / SFTP", group: "Files" },
  { id: "s3", label: "S3 / Object store", group: "Files" },
  { id: "excel_remote", label: "Excel (SharePoint)", group: "Files" },
];

function extOk(format, filename) {
  const ext = (filename || "").toLowerCase().slice(filename.lastIndexOf("."));
  const allowed = EXT_BY_FORMAT[format];
  if (!allowed || allowed.length === 0) return true;
  return allowed.includes(ext);
}

export default function SourceMapper({ llmAvailable = false }) {
  const parseResult = useAnalysisStore((s) => s.parseResult);
  const pipelineCode = useAnalysisStore((s) => s.pipelineCode);
  const pipelineFilename = useAnalysisStore((s) => s.pipelineFilename);
  const fileMappings = useAnalysisStore((s) => s.fileMappings);
  const clearFileMapping = useAnalysisStore((s) => s.clearFileMapping);
  const setEnableLlmForExecute = useAnalysisStore((s) => s.setEnableLlmForExecute);
  const enableLlmForExecute = useAnalysisStore((s) => s.enableLlmForExecute);
  const setAppState = useAnalysisStore((s) => s.setAppState);
  const setError = useAnalysisStore((s) => s.setError);
  const setValidationLoading = useAnalysisStore((s) => s.setValidationLoading);
  const setValidationResult = useAnalysisStore((s) => s.setValidationResult);
  const clearValidationOverrides = useAnalysisStore((s) => s.clearValidationOverrides);

  const [connectionMode, setConnectionMode] = useState("upload");

  const sources = parseResult?.sources || [];
  const required = useMemo(
    () => sources.filter((s) => s.requires_upload),
    [sources]
  );
  const ready = useMemo(
    () => connectionMode === "upload" && required.every((s) => fileMappings[s.id]),
    [connectionMode, required, fileMappings]
  );

  const switchConnectionMode = useCallback(
    (next) => {
      setConnectionMode(next);
      if (next === "datasource") {
        required.forEach((s) => clearFileMapping(s.id));
      }
    },
    [required, clearFileMapping]
  );

  const handleValidate = useCallback(async () => {
    if (connectionMode !== "upload") {
      toast.info("Demo mode: switch to Upload Excel / files to continue.", {
        description: "Data-source connections are preview-only in this build.",
      });
      return;
    }
    if (!ready || !pipelineCode) return;
    const fileMapping = {};
    const filesByFieldName = {};
    for (const s of required) {
      const f = fileMappings[s.id];
      const logical = f.name;
      fileMapping[s.id] = logical;
      filesByFieldName[`file_${logical}`] = f;
    }
    clearValidationOverrides();
    setValidationLoading(true);
    setAppState(APP_STATES.SOURCE_VALIDATION);
    try {
      const data = await validateSources({
        code: pipelineCode,
        filename: pipelineFilename || "pipeline.py",
        fileMapping,
        filesByFieldName,
        enableLlm: enableLlmForExecute,
      });
      setValidationResult(data);
      toast.success("Source validation complete");
    } catch (e) {
      setError(e.message);
      toast.error(e.message);
      setAppState(APP_STATES.SOURCE_MAPPING);
    }
  }, [
    connectionMode,
    ready,
    pipelineCode,
    pipelineFilename,
    required,
    fileMappings,
    enableLlmForExecute,
    setError,
    setAppState,
    setValidationLoading,
    setValidationResult,
    clearValidationOverrides,
  ]);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div
        className="p-5 rounded-2xl space-y-4"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              Map data files
            </h2>
            <RiskBadge />
          </div>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {parseResult?.summary?.total_nodes ?? 0} operations
          </span>
        </div>

        <div className="space-y-3">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Choose one way to supply data for this pipeline. This demo uses{" "}
            <strong className="font-medium text-[var(--text-secondary)]">Upload Excel / files</strong>.
          </p>
          <DataConnectionToggle mode={connectionMode} onChange={switchConnectionMode} />
        </div>

        {connectionMode === "datasource" ? (
          <DataSourceConnectorPanel />
        ) : (
          <>
            <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              Drop a file for each required source (CSV, Excel, Parquet, and more).
            </p>
            <div className="space-y-4">
              {sources.map((s) => (
                <SourceSlot key={s.id} source={s} />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setAppState(APP_STATES.UPLOAD_SCRIPT)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
          }}
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <div className="flex items-center gap-3">
          {llmAvailable && (
            <button
              type="button"
              onClick={() => setEnableLlmForExecute(!enableLlmForExecute)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium",
                enableLlmForExecute ? "ring-1 ring-purple-500/40" : ""
              )}
              style={{
                background: enableLlmForExecute ? "rgba(168,85,247,0.12)" : "var(--bg-card)",
                border: "1px solid var(--border)",
                color: enableLlmForExecute ? "#a855f7" : "var(--text-muted)",
              }}
            >
              <Sparkles size={14} />
              AI Enhance
            </button>
          )}
          <button
            type="button"
            disabled={!ready}
            onClick={handleValidate}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white disabled:opacity-40"
            style={{
              background: "linear-gradient(135deg, var(--primary), var(--primary-dark))",
            }}
          >
            <ShieldCheck size={16} />
            Validate &amp; Continue
          </button>
        </div>
      </div>
    </div>
  );
}

function DataConnectionToggle({ mode, onChange }) {
  return (
    <div
      className="inline-flex p-0.5 rounded-lg w-full"
      style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
    >
      <button
        type="button"
        onClick={() => onChange("upload")}
        className={cn(
          "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-xs font-semibold transition-colors",
          mode === "upload" ? "text-white" : ""
        )}
        style={
          mode === "upload"
            ? { background: "linear-gradient(135deg, var(--primary), var(--primary-dark))" }
            : { color: "var(--text-muted)" }
        }
      >
        <FileSpreadsheet size={14} />
        Upload Excel / files
      </button>
      <button
        type="button"
        onClick={() => onChange("datasource")}
        className={cn(
          "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-xs font-semibold transition-colors",
          mode === "datasource" ? "text-white" : ""
        )}
        style={
          mode === "datasource"
            ? { background: "linear-gradient(135deg, var(--primary), var(--primary-dark))" }
            : { color: "var(--text-muted)" }
        }
      >
        <Link2 size={14} />
        Connect data source
      </button>
    </div>
  );
}

function DataSourceConnectorPanel() {
  const groups = [...new Set(DATA_SOURCE_CONNECTORS.map((c) => c.group))];

  return (
    <div
      className="rounded-xl p-4 space-y-4"
      style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
    >
      <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        SQL databases, warehouses, and cloud files—select a connector (preview only in this demo).
      </p>

      {groups.map((group) => (
        <div key={group} className="space-y-2">
          <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            {group}
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {DATA_SOURCE_CONNECTORS.filter((c) => c.group === group).map((connector) => (
              <ConnectorButton key={connector.id} connector={connector} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConnectorButton({ connector }) {
  return (
    <button
      type="button"
      disabled
      className={cn(
        "flex items-center gap-2 px-3 py-2.5 rounded-lg text-left text-xs font-medium transition-colors",
        "opacity-60 cursor-not-allowed"
      )}
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        color: "var(--text-primary)",
      }}
    >
      <ConnectorIcon id={connector.id} />
      <span className="truncate">{connector.label}</span>
    </button>
  );
}

function ConnectorIcon({ id }) {
  const props = {
    size: 14,
    className: "shrink-0",
    style: { color: "var(--primary)" },
  };
  if (id === "s3" || id === "csv_remote") return <Cloud {...props} />;
  if (id === "excel_remote") return <FileSpreadsheet {...props} />;
  if (id === "mongodb") return <HardDrive {...props} />;
  return <Database {...props} />;
}

function SourceSlot({ source }) {
  const fileMappings = useAnalysisStore((s) => s.fileMappings);
  const setFileMapping = useAnalysisStore((s) => s.setFileMapping);
  const clearFileMapping = useAnalysisStore((s) => s.clearFileMapping);
  const mapped = fileMappings[source.id];
  const [fmtLabel, fmtClass] = formatBadge(source.format);

  const onDrop = useCallback(
    (accepted) => {
      const f = accepted[0];
      if (!f) return;
      if (source.requires_upload && !extOk(source.format, f.name)) {
        return;
      }
      setFileMapping(source.id, f);
    },
    [source, setFileMapping]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: !source.requires_upload,
  });

  if (!source.requires_upload) {
    return (
      <div
        className="p-3 rounded-xl text-xs flex items-start gap-2"
        style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
      >
        <Database size={14} className="shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold" style={{ color: "var(--text-primary)" }}>
            {source.method} — {fmtLabel}
          </div>
          <div style={{ color: "var(--text-muted)" }}>
            {source.skip_reason || "No file upload required"}
          </div>
        </div>
      </div>
    );
  }

  const badExt = mapped && !extOk(source.format, mapped.name);

  return (
    <div
      className="p-4 rounded-xl space-y-2"
      style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2">
        <span
          className="text-[10px] font-bold uppercase px-2 py-0.5 rounded"
          style={{ background: `${fmtClass}22`, color: fmtClass }}
        >
          {source.format}
        </span>
        <span className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
          {source.filename || source.path || "file"}
        </span>
        <span className="text-[10px] ml-auto" style={{ color: "var(--text-muted)" }}>
          line {source.line}
        </span>
      </div>

      <div
        {...getRootProps()}
        className={cn(
          "border border-dashed rounded-lg p-4 text-center text-xs cursor-pointer transition-colors",
          isDragActive ? "border-[var(--primary)]" : "border-[var(--border)]",
          badExt ? "border-red-500/60" : ""
        )}
        style={{ color: "var(--text-muted)" }}
      >
        <input {...getInputProps()} />
        {mapped ? (
          <div className="flex items-center justify-center gap-2">
            <span style={{ color: "var(--text-primary)" }}>{mapped.name}</span>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                clearFileMapping(source.id);
              }}
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Upload size={16} className="opacity-60" />
            <span>Drop {source.format.toUpperCase()} file here or click to browse</span>
          </div>
        )}
      </div>

      {badExt && (
        <div className="flex items-center gap-1 text-xs text-red-400">
          <AlertCircle size={12} />
          Extension does not match expected format
        </div>
      )}
    </div>
  );
}

function formatBadge(format) {
  const f = (format || "unknown").toLowerCase();
  const map = {
    csv: ["CSV", "#3b82f6"],
    excel: ["Excel", "#22c55e"],
    parquet: ["Parquet", "#a855f7"],
    json: ["JSON", "#eab308"],
  };
  return map[f] || [f, "#64748b"];
}
