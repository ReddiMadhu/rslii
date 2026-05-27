import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileCode, Clipboard, X, Loader2, Sparkles, AlertOctagon } from "lucide-react";
import { cn } from "../lib/utils";
import useAnalysisStore from "../store/useAnalysisStore";

export default function UploadZone({ onParse, onAnalyze, isLoading, llmAvailable = false, hideLlm = false }) {
  const [mode, setMode] = useState("upload"); // "upload" | "paste"
  const [code, setCode] = useState("");
  const [fileName, setFileName] = useState(null);
  const [enableLlm, setEnableLlm] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (!file) return;
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        setCode(text);
        setMode("paste"); // switch to paste view so user can see the code
      };
      reader.readAsText(file);
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/x-python": [".py"] },
    maxFiles: 1,
    disabled: isLoading,
  });

  const handleAnalyze = () => {
    if (!code.trim()) return;
    const payload = { code: code.trim(), filename: fileName, enableLlm: hideLlm ? false : enableLlm };
    if (onParse) {
      onParse({ code: payload.code, filename: payload.filename });
    } else if (onAnalyze) {
      onAnalyze(payload);
    }
  };

  const handleClear = () => {
    setCode("");
    setFileName(null);
    setMode("upload");
  };

  const parseResult = useAnalysisStore((s) => s.parseResult);
  const isBlocked = parseResult?.risk?.blocked;
  const lineCount = code.trim() ? code.trim().split("\n").length : 0;
  const canAnalyze = code.trim().length > 0 && !isLoading && !isBlocked;

  return (
    <div className="w-full max-w-3xl mx-auto animate-fade-in space-y-4">
      {isBlocked && (
        <div className="p-5 rounded-2xl border border-[#ef4444] bg-[rgba(239,68,68,0.06)] animate-fade-in">
          <div className="flex items-start gap-3">
            <AlertOctagon size={20} className="text-[#ef4444] mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-sm font-bold text-white leading-tight">
                Execution Blocked (High Risk Script)
              </h4>
              <p className="text-xs text-[#a0a0b8] mt-1 leading-relaxed">
                This script contains operations flagged as High Risk under your organization's governance guidelines. Execution is disabled until the following items are resolved:
              </p>
              <ul className="list-disc pl-4 mt-2.5 space-y-1.5 text-xs text-[#a0a0b8]">
                {parseResult.risk.reasons.map((r, idx) => (
                  <li key={idx} className="marker:text-[#ef4444]">{r}</li>
                ))}
              </ul>
              <button
                onClick={() => {
                  useAnalysisStore.setState({ parseResult: null });
                  handleClear();
                }}
                className="mt-4 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(15,15,22,0.4)] text-xs font-semibold text-[#a0a0b8] hover:text-white hover:border-[#ef4444]/40 transition-all cursor-pointer"
              >
                Reset & Clear Block
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Mode Tabs */}
      <div
        className="flex gap-1 p-1 rounded-xl mb-4 w-fit"
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border)",
        }}
      >
        <button
          onClick={() => setMode("upload")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 relative overflow-hidden",
          )}
          style={{
            background: mode === "upload" ? "var(--bg-card)" : "transparent",
            color: mode === "upload" ? "var(--text-primary)" : "var(--text-muted)",
            boxShadow: mode === "upload" ? "0 4px 12px rgba(0,0,0,0.15)" : "none",
          }}
        >
          {mode === "upload" && (
            <div className="absolute inset-0 bg-gradient-to-r from-[var(--primary)] to-transparent opacity-10" />
          )}
          <Upload size={15} className={mode === "upload" ? "text-[var(--primary)]" : ""} />
          Upload
        </button>
        <button
          onClick={() => setMode("paste")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 relative overflow-hidden",
          )}
          style={{
            background: mode === "paste" ? "var(--bg-card)" : "transparent",
            color: mode === "paste" ? "var(--text-primary)" : "var(--text-muted)",
            boxShadow: mode === "paste" ? "0 4px 12px rgba(0,0,0,0.15)" : "none",
          }}
        >
          {mode === "paste" && (
            <div className="absolute inset-0 bg-gradient-to-r from-[var(--primary)] to-transparent opacity-10" />
          )}
          <Clipboard size={15} className={mode === "paste" ? "text-[var(--primary)]" : ""} />
          Paste
        </button>
      </div>

      {/* Upload / Paste Area */}
      {mode === "upload" ? (
        <div
          {...getRootProps()}
          className={cn(
            "relative flex flex-col items-center justify-center gap-4 p-12 rounded-3xl cursor-pointer transition-all duration-500 overflow-hidden group",
            isDragActive ? "scale-[1.02]" : "hover:scale-[1.01]"
          )}
          style={{
            background: "var(--bg-glass)",
            backdropFilter: "blur(20px)",
            border: isDragActive
              ? "2px dashed var(--primary)"
              : "2px dashed var(--border)",
            boxShadow: isDragActive
              ? "0 0 50px rgba(251, 78, 11, 0.15)"
              : "none",
          }}
        >
          {/* Subtle pulse background on hover */}
          <div className="absolute inset-0 bg-[var(--primary)] opacity-0 group-hover:opacity-5 transition-opacity duration-500" />
          <input {...getInputProps()} />
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center transition-transform duration-300"
            style={{
              background: isDragActive
                ? "linear-gradient(135deg, var(--primary), var(--primary-light))"
                : "var(--bg-card)",
              border: isDragActive ? "none" : "1px solid var(--border)",
              transform: isDragActive ? "scale(1.1) rotate(-5deg)" : "none",
            }}
          >
            <FileCode
              size={28}
              style={{
                color: isDragActive ? "white" : "var(--text-secondary)",
              }}
            />
          </div>
          <div className="text-center">
            <p
              className="text-base font-medium mb-1"
              style={{ color: "var(--text-primary)" }}
            >
              {isDragActive ? "Drop your Python file here" : "Drag & drop a .py file"}
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              or click to browse • Max 2000 lines
            </p>
          </div>
        </div>
      ) : (
        <div className="relative">
          {/* Textarea */}
          <div
            className="relative rounded-2xl overflow-hidden"
            style={{
              background: "var(--bg-glass)",
              backdropFilter: "blur(20px)",
              border: "1px solid var(--border)",
            }}
          >
            {/* Header bar */}
            <div
              className="flex items-center justify-between px-4 py-2.5"
              style={{
                borderBottom: "1px solid var(--border)",
                background: "var(--bg-secondary)",
              }}
            >
              <div className="flex items-center gap-2">
                <FileCode size={14} style={{ color: "var(--text-muted)" }} />
                <span
                  className="text-xs font-medium"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {fileName || "untitled.py"}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {lineCount > 0 && (
                  <span
                    className="text-xs"
                    style={{
                      color: lineCount > 2000 ? "#ef4444" : "var(--text-muted)",
                    }}
                  >
                    {lineCount} lines
                  </span>
                )}
                {code && (
                  <button
                    onClick={handleClear}
                    className="p-1 rounded-md transition-colors hover:bg-white/5"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
            <textarea
              value={code}
              onChange={(e) => {
                setCode(e.target.value);
                if (!fileName) setFileName(null);
              }}
              placeholder="Paste your Python ETL script here..."
              className="w-full resize-none focus:outline-none"
              style={{
                background: "transparent",
                color: "var(--text-primary)",
                padding: "16px",
                minHeight: "260px",
                maxHeight: "400px",
                fontFamily: "'Geist Mono', 'Fira Code', 'Consolas', monospace",
                fontSize: "13px",
                lineHeight: "1.6",
                caretColor: "var(--primary)",
              }}
              spellCheck={false}
            />
          </div>
        </div>
      )}

      {/* Analyze Button */}
      <div className="flex items-center justify-between mt-4">
        <div>
          {lineCount > 2000 && (
            <p className="text-sm font-medium" style={{ color: "#ef4444" }}>
              File exceeds 2000-line limit
            </p>
          )}
        </div>

        {/* LLM toggle + Analyze button */}
        <div className="flex items-center gap-3">
          {llmAvailable && !hideLlm && (
            <button
              onClick={() => setEnableLlm((v) => !v)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200"
              style={{
                background: enableLlm ? "rgba(168, 85, 247, 0.15)" : "var(--bg-card)",
                border: enableLlm
                  ? "1px solid rgba(168, 85, 247, 0.3)"
                  : "1px solid var(--border)",
                color: enableLlm ? "#a855f7" : "var(--text-muted)",
              }}
              title="Enhance descriptions with AI"
            >
              <Sparkles size={13} />
              AI Enhance
            </button>
          )}
        <button
          onClick={handleAnalyze}
          disabled={!canAnalyze || lineCount > 2000}
          className={cn(
            "relative flex items-center gap-2 px-8 py-3 rounded-2xl text-sm font-bold text-white transition-all duration-300 overflow-hidden",
            canAnalyze && lineCount <= 2000 ? "hover:scale-105 hover:shadow-[0_0_30px_rgba(251,78,11,0.4)]" : ""
          )}
          style={{
            background:
              canAnalyze && lineCount <= 2000
                ? "linear-gradient(135deg, var(--primary), var(--primary-dark))"
                : "var(--bg-card)",
            color: canAnalyze && lineCount <= 2000 ? "white" : "var(--text-muted)",
            border: canAnalyze && lineCount <= 2000 ? "none" : "1px solid var(--border)",
            opacity: canAnalyze && lineCount <= 2000 ? 1 : 0.5,
            cursor: canAnalyze && lineCount <= 2000 ? "pointer" : "not-allowed",
          }}
        >
          {canAnalyze && lineCount <= 2000 && (
            <div className="absolute inset-0 bg-white opacity-0 hover:opacity-20 transition-opacity duration-300" />
          )}
          {isLoading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Upload size={16} />
              Analyze Pipeline
            </>
          )}
        </button>
      </div>
      </div>
    </div>
  );
}
