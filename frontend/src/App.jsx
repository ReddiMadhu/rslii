import { useEffect, useMemo, useState } from "react";
import { Toaster, toast } from "sonner";
import { healthCheck, parseCode } from "./lib/api";
import { Sun, Moon, Zap, RotateCcw, LayoutDashboard, GitBranch, Columns3, RefreshCw } from "lucide-react";
import useAnalysisStore, { APP_STATES } from "./store/useAnalysisStore";
import UploadZone from "./components/UploadZone";
import SourceMapper from "./components/SourceMapper";
import SourceValidation from "./components/SourceValidation";
import SummaryTab from "./components/SummaryTab";
import LineageTab from "./components/LineageTab";
import ColumnLineageTab from "./components/ColumnLineageTab";
import NodeDetail from "./components/NodeDetail";
import LandingPage from "./components/LandingPage";

import "./index.css";

function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("rsli-theme") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("rsli-theme", theme);
  }, [theme]);

  return (
    <button
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      className="relative p-2 rounded-xl transition-all duration-300 hover:scale-105 group overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        color: "var(--text-secondary)",
      }}
      aria-label="Toggle theme"
    >
      <div className="absolute inset-0 bg-gradient-to-tr from-[var(--primary)] to-transparent opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
      {theme === "dark" ? (
        <Sun size={18} className="group-hover:text-[var(--primary)] transition-colors" />
      ) : (
        <Moon size={18} className="group-hover:text-[var(--primary)] transition-colors" />
      )}
    </button>
  );
}

function TabButton({ active, icon: Icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 overflow-hidden"
      style={{
        background: active ? "var(--bg-card)" : "transparent",
        color: active ? "var(--primary)" : "var(--text-muted)",
        boxShadow: active ? "0 4px 12px rgba(0,0,0,0.15)" : "none",
        border: active ? "1px solid var(--border)" : "1px solid transparent",
      }}
    >
      {active && (
        <div className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ background: "var(--primary)" }} />
      )}
      <Icon size={15} className={active ? "animate-pulse" : ""} />
      {label}
    </button>
  );
}

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [llmAvailable, setLlmAvailable] = useState(false);
  const appState = useAnalysisStore((s) => s.appState);
  const parseResult = useAnalysisStore((s) => s.parseResult);
  const executionProgress = useAnalysisStore((s) => s.executionProgress);
  const liveExecSummary = useAnalysisStore((s) => s.liveExecSummary);
  const result = useAnalysisStore((s) => s.result);
  const isLoading = useAnalysisStore((s) => s.isLoading);
  const error = useAnalysisStore((s) => s.error);
  const activeTab = useAnalysisStore((s) => s.activeTab);
  const selectedDetailNode = useAnalysisStore((s) => s.selectedDetailNode);
  const setParsed = useAnalysisStore((s) => s.setParsed);
  const setLoading = useAnalysisStore((s) => s.setLoading);
  const setError = useAnalysisStore((s) => s.setError);
  const setActiveTab = useAnalysisStore((s) => s.setActiveTab);
  const setAppState = useAnalysisStore((s) => s.setAppState);
  const reset = useAnalysisStore((s) => s.reset);

  const displayResult = useMemo(() => {
    if (appState === APP_STATES.EXECUTING && parseResult?.nodes) {
      const nodes = parseResult.nodes.map((n) => {
        const p = executionProgress[n.id];
        let status = n.status;
        let runtime = n.runtime;
        if (p?.status === "executing") status = "executing";
        if (p?.status === "completed") {
          status = "completed";
          runtime = { ...p.metrics };
        }
        if (p?.status === "failed") {
          status = "failed";
          runtime = { ...(runtime || {}), error: p.error };
        }
        return { ...n, status, runtime };
      });
      return {
        nodes,
        edges: parseResult.edges,
        summary: {
          ...parseResult.summary,
          ...(liveExecSummary || {}),
        },
        warnings: parseResult.warnings || [],
      };
    }
    return result;
  }, [appState, parseResult, executionProgress, liveExecSummary, result]);

  const showTabs = result || appState === APP_STATES.EXECUTING;

  useEffect(() => {
    healthCheck()
      .then((data) => {
        setBackendStatus("connected");
        setLlmAvailable(data?.llm_available ?? false);
      })
      .catch(() => {
        setBackendStatus("error");
        toast.error("Backend unreachable — start the FastAPI server on port 8000");
      });
  }, []);

  const handleParse = async ({ code, filename }) => {
    setLoading(true);
    try {
      const data = await parseCode({ code, filename });
      setParsed(data, code, filename);
      const need = (data.sources || []).filter((s) => s.requires_upload).length;
      toast.success(`Parsed — ${need} file slot(s) to map`);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  };

  if (appState === APP_STATES.LANDING) {
    return (
      <>
        <LandingPage themeToggle={<ThemeToggle />} />
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            },
          }}
        />
      </>
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col animate-fade-in"
      style={{ background: "var(--bg-primary)" }}
    >
      <header
        className="flex items-center justify-between px-6 py-3 sticky top-0 z-50"
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-glass)",
          backdropFilter: "blur(20px)",
        }}
      >
        <div className="flex items-center gap-3">
          <img src="/etlpulse_ai_logo.svg" alt="ETLPulse.AI" className="h-8 w-auto" />
          <span
            className="text-[10px] font-medium px-2 py-0.5 rounded-full"
            style={{
              background: "var(--bg-card)",
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
            }}
          >
            ETL Analyzer
          </span>

          {showTabs && (
            <div
              className="flex gap-1 p-1 rounded-lg ml-4"
              style={{ background: "var(--bg-secondary)" }}
            >
              <TabButton
                active={activeTab === "summary"}
                icon={LayoutDashboard}
                label="Pipeline overview"
                onClick={() => setActiveTab("summary")}
              />
              <TabButton
                active={activeTab === "lineage"}
                icon={GitBranch}
                label="Lineage explorer"
                onClick={() => setActiveTab("lineage")}
              />
              <button
                onClick={() => appState === APP_STATES.RESULTS && setActiveTab("column-lineage")}
                disabled={appState !== APP_STATES.RESULTS}
                className="relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 overflow-hidden"
                style={{
                  background: activeTab === "column-lineage" ? "var(--bg-card)" : "transparent",
                  color: appState !== APP_STATES.RESULTS
                    ? "var(--text-muted)"
                    : activeTab === "column-lineage"
                    ? "var(--primary)"
                    : "var(--text-muted)",
                  boxShadow: activeTab === "column-lineage" ? "0 4px 12px rgba(0,0,0,0.15)" : "none",
                  border: activeTab === "column-lineage" ? "1px solid var(--border)" : "1px solid transparent",
                  opacity: appState !== APP_STATES.RESULTS ? 0.4 : 1,
                  cursor: appState !== APP_STATES.RESULTS ? "not-allowed" : "pointer",
                }}
                title={appState !== APP_STATES.RESULTS ? "Execute pipeline to enable column lineage" : ""}
              >
                {activeTab === "column-lineage" && (
                  <div className="absolute bottom-0 left-0 right-0 h-[2px]" style={{ background: "var(--primary)" }} />
                )}
                <Columns3 size={15} className={activeTab === "column-lineage" ? "animate-pulse" : ""} />
                Column-level Journey
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {appState === APP_STATES.RESULTS && (
            <button
              onClick={() => setAppState(APP_STATES.SOURCE_MAPPING)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-300 hover:-translate-y-0.5 group"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <RefreshCw size={13} className="group-hover:text-[var(--primary)] transition-colors" />
              <span className="group-hover:text-[var(--text-primary)] transition-colors">Re-execute</span>
            </button>
          )}
          {(result || parseResult) && (
            <button
              onClick={reset}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-300 hover:-translate-y-0.5 group"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <RotateCcw size={13} className="group-hover:text-[var(--primary)] transition-colors" />
              <span className="group-hover:text-[var(--text-primary)] transition-colors">New Analysis</span>
            </button>
          )}

          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
            }}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{
                background:
                  backendStatus === "connected"
                    ? "#22c55e"
                    : backendStatus === "error"
                    ? "#ef4444"
                    : "#eab308",
              }}
            />
            {backendStatus === "connected"
              ? "API Connected"
              : backendStatus === "error"
              ? "API Error"
              : "Checking..."}
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex flex-col px-6 py-6">
        {error && (
          <div
            className="w-full max-w-7xl mx-auto mb-6 px-4 py-3 rounded-xl text-sm font-medium animate-fade-in"
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "#ef4444",
            }}
          >
            {error}
          </div>
        )}

        {appState === APP_STATES.UPLOAD_SCRIPT && (
          <div className="flex-1 flex items-center justify-center">
            <UploadZone onParse={handleParse} isLoading={isLoading} llmAvailable={llmAvailable} hideLlm />
          </div>
        )}

        {appState === APP_STATES.SOURCE_MAPPING && (
          <div className="flex-1 flex items-center justify-center">
            <SourceMapper llmAvailable={llmAvailable} />
          </div>
        )}

        {appState === APP_STATES.SOURCE_VALIDATION && (
          <div className="flex-1 flex items-start justify-center py-6 overflow-y-auto w-full">
            <SourceValidation llmAvailable={llmAvailable} />
          </div>
        )}

        {showTabs && displayResult && (
          <div className="animate-fade-in w-full max-w-7xl mx-auto">
            {activeTab === "summary" ? (
              <SummaryTab result={displayResult} />
            ) : activeTab === "column-lineage" ? (
              <ColumnLineageTab result={displayResult} />
            ) : (
              <LineageTab result={displayResult} />
            )}
            {selectedDetailNode &&
              activeTab !== "column-lineage" &&
              (appState === APP_STATES.RESULTS || appState === APP_STATES.EXECUTING) && (
              <NodeDetail result={displayResult} />
            )}
          </div>
        )}
      </main>

      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          },
        }}
      />
    </div>
  );
}

export default App;
