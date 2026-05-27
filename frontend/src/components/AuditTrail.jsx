import { useState, useEffect } from "react";
import { getApiBase } from "../lib/apiBase";
import { 
  Calendar, 
  Search, 
  Download, 
  ChevronDown, 
  ChevronUp, 
  ShieldAlert, 
  ShieldCheck,
  ShieldWarning,
  FileSpreadsheet, 
  Loader2, 
  ArrowLeft,
  Filter,
  RefreshCw,
  FileCode,
  Clock
} from "lucide-react";

export default function AuditTrail({ onClose }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [username, setUsername] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [expandedRow, setExpandedRow] = useState(null); // id of expanded row
  const [detailsCache, setDetailsCache] = useState({}); // details per log id
  const [detailsLoading, setDetailsLoading] = useState(null); // id currently loading details

  const API_BASE = getApiBase();

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (username) params.append("username", username);
      if (riskLevel) params.append("risk_level", riskLevel);
      if (status) params.append("status", status);
      if (dateFrom) params.append("date_from", dateFrom);
      if (dateTo) params.append("date_to", dateTo);

      const res = await fetch(`${API_BASE}/audit?${params.toString()}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load audit logs");
      const data = await res.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, riskLevel, status]);

  const handleApplyFilters = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const handleResetFilters = () => {
    setUsername("");
    setRiskLevel("");
    setStatus("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const handleExport = (format) => {
    const params = new URLSearchParams({ format });
    if (username) params.append("username", username);
    if (riskLevel) params.append("risk_level", riskLevel);
    if (status) params.append("status", status);
    if (dateFrom) params.append("date_from", dateFrom);
    if (dateTo) params.append("date_to", dateTo);

    window.open(`${API_BASE}/audit/export?${params.toString()}`, "_blank");
  };

  const toggleRow = async (id) => {
    if (expandedRow === id) {
      setExpandedRow(null);
      return;
    }

    setExpandedRow(id);

    // Fetch detail if not cached
    if (!detailsCache[id]) {
      setDetailsLoading(id);
      try {
        const res = await fetch(`${API_BASE}/audit/${id}/details`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          setDetailsCache((prev) => ({ ...prev, [id]: data }));
        }
      } catch (err) {
        console.warn("Failed to load audit log details", err);
      } finally {
        setDetailsLoading(null);
      }
    }
  };

  const getRiskBadge = (level) => {
    if (level === "low") {
      return (
        <span className="inline-flex items-center gap-1 text-[#22c55e] bg-[rgba(34,197,94,0.06)] border border-[#22c55e]/20 px-2 py-0.5 rounded-lg text-[10px] font-bold">
          <ShieldCheck size={11} /> Low
        </span>
      );
    }
    if (level === "medium") {
      return (
        <span className="inline-flex items-center gap-1 text-[#eab308] bg-[rgba(234,179,8,0.06)] border border-[#eab308]/20 px-2 py-0.5 rounded-lg text-[10px] font-bold">
          <ShieldWarning size={11} /> Medium
        </span>
      );
    }
    if (level === "high") {
      return (
        <span className="inline-flex items-center gap-1 text-[#ef4444] bg-[rgba(239,68,68,0.06)] border border-[#ef4444]/20 px-2 py-0.5 rounded-lg text-[10px] font-bold">
          <ShieldAlert size={11} /> High
        </span>
      );
    }
    return <span className="text-[#666677]">—</span>;
  };

  const getStatusBadge = (st) => {
    if (st === "success") {
      return <span className="text-[#22c55e] font-semibold">Success</span>;
    }
    if (st === "failed") {
      return <span className="text-[#ef4444] font-semibold">Failed</span>;
    }
    if (st === "blocked") {
      return <span className="text-[#eab308] font-semibold">Blocked</span>;
    }
    return <span className="text-white font-medium">OK</span>;
  };

  const getEventName = (t) => {
    const map = {
      user_login: "User Login",
      user_register: "User Registration",
      script_parse: "Script Parse",
      script_execute: "Execution Triggered",
      execution_complete: "Execution Completed",
      validation_override: "Validation Override",
      file_upload: "File Uploaded",
      file_download: "File Downloaded",
      llm_call: "AI Enhance Call",
      risk_blocked: "Execution Blocked",
    };
    return map[t] || t;
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fade-in pb-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white leading-tight">Enterprise Audit Trail</h2>
          <p className="text-xs text-[#a0a0b8] mt-0.5">Immutable logs of script parsing, executions, downloads, and auth events.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleExport("csv")}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] text-[#a0a0b8] hover:text-white transition-all text-xs font-semibold cursor-pointer"
          >
            <Download size={14} /> Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] text-[#a0a0b8] hover:text-white transition-all text-xs font-semibold cursor-pointer"
          >
            <FileSpreadsheet size={14} /> Export JSON
          </button>
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] hover:border-[rgba(251,78,11,0.3)] bg-[rgba(15,15,22,0.4)] text-[#a0a0b8] hover:text-white transition-all text-xs font-semibold cursor-pointer"
          >
            <ArrowLeft size={14} /> Back to App
          </button>
        </div>
      </div>

      {/* Filters Form */}
      <form onSubmit={handleApplyFilters} className="glass p-5 rounded-2xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
          <Filter size={14} className="text-[#fb4e0b]" />
          <span>Filters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
          {/* Username search */}
          <div>
            <label className="block text-[10px] font-bold text-[#666677] uppercase tracking-wide mb-1.5">Username</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-[#666677]">
                <Search size={12} />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Search user..."
                className="w-full pl-8 pr-3 py-1.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl text-xs text-white placeholder-[#666677] focus:outline-none focus:border-[#fb4e0b]"
              />
            </div>
          </div>

          {/* Risk select */}
          <div>
            <label className="block text-[10px] font-bold text-[#666677] uppercase tracking-wide mb-1.5">Risk Level</label>
            <select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] cursor-pointer"
            >
              <option value="">All Tiers</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
            </select>
          </div>

          {/* Status select */}
          <div>
            <label className="block text-[10px] font-bold text-[#666677] uppercase tracking-wide mb-1.5">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-[10px] font-bold text-[#666677] uppercase tracking-wide mb-1.5">Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] cursor-pointer"
            />
          </div>

          {/* End Date */}
          <div>
            <label className="block text-[10px] font-bold text-[#666677] uppercase tracking-wide mb-1.5">Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] cursor-pointer"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#161622] hover:bg-[#202030] text-[#a0a0b8] hover:text-white transition-all cursor-pointer"
          >
            Reset
          </button>
          <button
            type="submit"
            className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#fb4e0b] to-[#ff6b2e] hover:from-[#ff6b2e] hover:to-[#ff814d] transition-all"
          >
            Apply Filters
          </button>
        </div>
      </form>

      {/* Logs Table Card */}
      <div className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] overflow-hidden shadow-xl">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <Loader2 size={28} className="animate-spin text-[#fb4e0b]" />
            <span className="text-xs text-[#a0a0b8]">Retrieving audit trail...</span>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 text-xs text-[#666677]">
            No audit log entries matching your filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[rgba(255,255,255,0.02)] text-[#666677] uppercase tracking-wider font-bold border-b border-[rgba(255,255,255,0.06)]">
                  <th className="p-4 w-10"></th>
                  <th className="p-4 w-16">ID</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">User</th>
                  <th className="p-4">Event Type</th>
                  <th className="p-4">Filename</th>
                  <th className="p-4">Risk</th>
                  <th className="p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isExpanded = expandedRow === item.id;
                  const detail = detailsCache[item.id];
                  const detailsLoad = detailsLoading === item.id;

                  return (
                    <>
                      <tr 
                        key={item.id}
                        className={`border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.01)] text-[#a0a0b8] cursor-pointer transition-all ${
                          isExpanded ? "bg-[rgba(255,255,255,0.01)] border-b-0" : ""
                        }`}
                        onClick={() => toggleRow(item.id)}
                      >
                        <td className="p-4 text-center">
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </td>
                        <td className="p-4 font-mono font-bold text-white">#{item.id}</td>
                        <td className="p-4">
                          {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                        </td>
                        <td className="p-4 text-white font-semibold">{item.username}</td>
                        <td className="p-4 font-medium">{getEventName(item.event_type)}</td>
                        <td className="p-4 truncate max-w-[120px]" title={item.filename || ""}>
                          {item.filename || <span className="text-[#666677]">—</span>}
                        </td>
                        <td className="p-4">{getRiskBadge(item.risk_level)}</td>
                        <td className="p-4">{getStatusBadge(item.execution_status)}</td>
                      </tr>

                      {/* Expandable detail row */}
                      {isExpanded && (
                        <tr className="border-b border-[rgba(255,255,255,0.04)] bg-[rgba(255,255,255,0.01)] text-xs text-[#a0a0b8]">
                          <td colSpan={8} className="px-12 pb-6 pt-2">
                            {detailsLoad ? (
                              <div className="flex items-center gap-2 py-4 text-[#666677]">
                                <Loader2 size={12} className="animate-spin text-[#fb4e0b]" />
                                <span>Loading log details...</span>
                              </div>
                            ) : detail ? (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in border-t border-[rgba(255,255,255,0.04)] pt-4">
                                {/* Metadata */}
                                <div className="space-y-3">
                                  <h5 className="font-bold text-white text-xs mb-2">Execution Metrics</h5>
                                  {item.session_id && (
                                    <div className="flex justify-between border-b border-[rgba(255,255,255,0.03)] pb-1.5">
                                      <span className="text-[#666677]">Session ID</span>
                                      <span className="font-mono text-white select-all">{item.session_id}</span>
                                    </div>
                                  )}
                                  {item.duration_ms != null && (
                                    <div className="flex justify-between border-b border-[rgba(255,255,255,0.03)] pb-1.5">
                                      <span className="text-[#666677]">Duration</span>
                                      <span className="text-white font-medium flex items-center gap-1">
                                        <Clock size={11} className="text-[#eab308]" />
                                        {item.duration_ms.toFixed(1)} ms
                                      </span>
                                    </div>
                                  )}
                                  {item.script_hash && (
                                    <div className="flex justify-between border-b border-[rgba(255,255,255,0.03)] pb-1.5">
                                      <span className="text-[#666677]">Script Hash (SHA256)</span>
                                      <span className="font-mono text-[10px] text-white truncate max-w-[200px]" title={item.script_hash}>
                                        {item.script_hash}
                                      </span>
                                    </div>
                                  )}
                                  {item.summary && Object.keys(item.summary).length > 0 && (
                                    <div>
                                      <span className="text-[#666677] block mb-1">Details Summary</span>
                                      <pre className="p-3 bg-[#0a0a0f] border border-[rgba(255,255,255,0.05)] rounded-xl font-mono text-[10px] text-[#a0a0b8] overflow-x-auto whitespace-pre-wrap leading-relaxed">
                                        {JSON.stringify(item.summary, null, 2)}
                                      </pre>
                                    </div>
                                  )}
                                </div>

                                {/* Files and Artifacts */}
                                <div className="space-y-3">
                                  <h5 className="font-bold text-white text-xs mb-2">Outputs &amp; Artifacts</h5>
                                  
                                  {detail.files && detail.files.length > 0 ? (
                                    <div className="space-y-2">
                                      <span className="text-[#666677] text-[11px] block">Generated output files:</span>
                                      <div className="grid grid-cols-1 gap-2">
                                        {detail.files.map((file) => (
                                          <a
                                            key={file}
                                            href={`${API_BASE}/download/${item.session_id}/${encodeURIComponent(file)}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                            className="flex items-center gap-2 p-2.5 rounded-xl border border-[rgba(255,255,255,0.05)] bg-[#0a0a0f] hover:border-[#fb4e0b]/40 hover:text-white transition-all cursor-pointer text-xs"
                                          >
                                            <FileCode size={13} className="text-[#fb4e0b]" />
                                            <span className="truncate flex-1">{file}</span>
                                            <Download size={12} className="opacity-60" />
                                          </a>
                                        ))}
                                      </div>
                                    </div>
                                  ) : item.session_id ? (
                                    <p className="text-[#666677] italic text-xs">
                                      No local output files found. They may have been cleaned up after session expiry (30 mins).
                                    </p>
                                  ) : (
                                    <p className="text-[#666677] italic text-xs">
                                      No outputs generated for this event.
                                    </p>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <p className="text-[#666677] italic text-xs py-2">Details not available.</p>
                            )}
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] text-xs text-[#a0a0b8] hover:text-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
          >
            Prev
          </button>
          
          <span className="text-xs text-[#666677]">
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[#0f0f16] text-xs text-[#a0a0b8] hover:text-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
