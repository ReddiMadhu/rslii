import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { healthCheck, analyzeCode } from "./lib/api";
import { Sun, Moon, Zap, RotateCcw, LayoutDashboard, GitBranch } from "lucide-react";
import useAnalysisStore from "./store/useAnalysisStore";
import UploadZone from "./components/UploadZone";
import SummaryTab from "./components/SummaryTab";
import LineageTab from "./components/LineageTab";
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
      className="p-2 rounded-lg transition-all duration-200 hover:scale-105"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        color: "var(--text-secondary)",
      }}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

function TabButton({ active, icon: Icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
      style={{
        background: active ? "var(--bg-card)" : "transparent",
        color: active ? "var(--text-primary)" : "var(--text-muted)",
        boxShadow: active ? "0 2px 8px rgba(0,0,0,0.15)" : "none",
        border: active ? "1px solid var(--border)" : "1px solid transparent",
      }}
    >
      <Icon size={15} />
      {label}
    </button>
  );
}

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [llmAvailable, setLlmAvailable] = useState(false);
  const {
    result, isLoading, error, activeTab,
    setResult, setLoading, setError, setActiveTab, reset,
  } = useAnalysisStore();

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

  const handleAnalyze = async ({ code, filename, enableLlm = false }) => {
    setLoading(true);
    try {
      const data = await analyzeCode({ code, filename, enableLlm });
      setResult(data);
      const lines = data?.summary?.total_lines ?? "?";
      const nodes = data?.summary?.total_nodes ?? 0;
      const llmBadge = data?.llm_used ? " ✨ AI Enhanced" : "";
      toast.success(`Analysis complete — ${lines} lines, ${nodes} nodes${llmBadge}`);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-primary)" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-3 sticky top-0 z-50"
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-glass)",
          backdropFilter: "blur(20px)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-8 h-8 rounded-lg"
            style={{
              background: "linear-gradient(135deg, var(--primary), var(--primary-light))",
            }}
          >
            <Zap size={16} color="white" />
          </div>
          <h1
            className="text-lg font-bold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            RSLI
          </h1>
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

          {/* Tabs — show only when results exist */}
          {result && (
            <div
              className="flex gap-1 p-1 rounded-lg ml-4"
              style={{ background: "var(--bg-secondary)" }}
            >
              <TabButton
                active={activeTab === "summary"}
                icon={LayoutDashboard}
                label="Summary"
                onClick={() => setActiveTab("summary")}
              />
              <TabButton
                active={activeTab === "lineage"}
                icon={GitBranch}
                label="Lineage"
                onClick={() => setActiveTab("lineage")}
              />
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {result && (
            <button
              onClick={reset}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 hover:scale-105"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <RotateCcw size={13} />
              New Analysis
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

      {/* Main Content */}
      <main className="flex-1 flex flex-col px-6 py-6">
        {/* Error Banner */}
        {error && (
          <div
            className="w-full max-w-5xl mx-auto mb-6 px-4 py-3 rounded-xl text-sm font-medium animate-fade-in"
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "#ef4444",
            }}
          >
            {error}
          </div>
        )}

        {/* Upload zone — centered when no results */}
        {!result ? (
          <div className="flex-1 flex items-center justify-center">
            <UploadZone onAnalyze={handleAnalyze} isLoading={isLoading} llmAvailable={llmAvailable} />
          </div>
        ) : (
          /* Result tabs */
          <div className="animate-fade-in">
            {activeTab === "summary" ? (
              <SummaryTab result={result} />
            ) : (
              <LineageTab result={result} />
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
