import { useState, useEffect } from "react";
import { getApiBase } from "../lib/apiBase";
import { User, ShieldAlert, KeyRound, Ban, CheckCircle, Loader2, ArrowLeft } from "lucide-react";

export default function AdminUsers({ onClose }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null); // stores user_id being updated
  const [tempPassword, setTempPassword] = useState(null);
  const [tempPassUser, setTempPassUser] = useState(null);

  const API_BASE = getApiBase();

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/users`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load users list");
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleResetPassword = async (userId, username) => {
    setActionLoading(userId);
    setError(null);
    setTempPassword(null);
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/reset-password`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to reset password");
      const data = await res.json();
      setTempPassword(data.temporary_password);
      setTempPassUser(username);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (userId, currentlyActive) => {
    setActionLoading(userId);
    setError(null);
    const endpoint = currentlyActive ? "deactivate" : "activate";
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/${endpoint}`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error(`Failed to ${currentlyActive ? 'deactivate' : 'activate'} user`);
      await fetchUsers(); // reload list
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-[#0f0f16] border border-[rgba(255,255,255,0.08)] rounded-2xl animate-fade-in shadow-2xl relative">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-4 mb-6">
        <div className="flex items-center gap-3">
          <ShieldAlert size={20} className="text-[#fb4e0b]" />
          <div>
            <h2 className="text-lg font-bold text-white leading-tight">User Management</h2>
            <p className="text-xs text-[#a0a0b8] mt-0.5">Admin tools to reset passwords and manage access.</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.06)] hover:border-[rgba(251,78,11,0.3)] bg-[rgba(15,15,22,0.4)] text-[#a0a0b8] hover:text-white transition-all text-xs font-semibold cursor-pointer"
        >
          <ArrowLeft size={14} />
          Back to App
        </button>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-xl bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.15)] text-[#ef4444] text-xs">
          <ShieldAlert size={14} className="flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Temporary Password Modal / Overlay */}
      {tempPassword && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[#0f0f16] shadow-2xl p-6 text-center animate-slide-up">
            <KeyRound size={32} className="mx-auto text-[#22c55e] mb-3" />
            <h3 className="text-sm font-bold text-white mb-2">Temporary Password Generated</h3>
            <p className="text-xs text-[#a0a0b8] mb-4">
              Password for user <strong className="text-white">{tempPassUser}</strong> has been reset.
            </p>
            <div className="p-3 bg-[#0a0a0f] border border-[rgba(255,255,255,0.06)] rounded-xl font-mono text-white text-sm font-bold select-all mb-4">
              {tempPassword}
            </div>
            <p className="text-[10px] text-[#666677] mb-5">
              Copy this password and share it securely. The user will be prompted to change it.
            </p>
            <button
              onClick={() => {
                setTempPassword(null);
                setTempPassUser(null);
              }}
              className="w-full py-2 rounded-xl text-xs font-bold text-white bg-[#22c55e] hover:bg-[#1f9b4c] transition-all cursor-pointer"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Users Table */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 size={24} className="animate-spin text-[#fb4e0b]" />
          <span className="text-xs text-[#a0a0b8]">Fetching users registry...</span>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[rgba(255,255,255,0.06)]">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[rgba(255,255,255,0.02)] text-[#666677] uppercase tracking-wider font-bold border-b border-[rgba(255,255,255,0.06)]">
                <th className="p-4">Username</th>
                <th className="p-4">Email</th>
                <th className="p-4">Created At</th>
                <th className="p-4">Last Login</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isUpdating = actionLoading === u.id;
                return (
                  <tr 
                    key={u.id} 
                    className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.01)] text-[#a0a0b8]"
                  >
                    <td className="p-4 font-semibold text-white flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-[rgba(255,255,255,0.04)] flex items-center justify-center text-[10px] text-white">
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <span>{u.username}</span>
                      {u.is_admin && (
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-[rgba(251,78,11,0.12)] text-[#fb4e0b]">
                          Admin
                        </span>
                      )}
                    </td>
                    <td className="p-4 font-mono">{u.email}</td>
                    <td className="p-4">
                      {u.created_at ? new Date(u.created_at).toLocaleString() : "Never"}
                    </td>
                    <td className="p-4">
                      {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                    </td>
                    <td className="p-4">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[#22c55e]">
                          <CheckCircle size={12} /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[#ef4444]">
                          <Ban size={12} /> Deactivated
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      {isUpdating ? (
                        <div className="inline-flex items-center justify-end w-32 py-1.5">
                          <Loader2 size={14} className="animate-spin text-[#fb4e0b]" />
                        </div>
                      ) : (
                        <div className="inline-flex items-center gap-2">
                          <button
                            onClick={() => handleResetPassword(u.id, u.username)}
                            className="px-2.5 py-1.5 rounded-lg border border-[rgba(255,255,255,0.06)] hover:border-[#fb4e0b]/40 hover:text-white transition-all font-semibold flex items-center gap-1 cursor-pointer"
                          >
                            <KeyRound size={12} />
                            Reset PW
                          </button>
                          
                          {/* Disable deactivation of yourself */}
                          <button
                            onClick={() => handleToggleActive(u.id, u.is_active)}
                            className={`px-2.5 py-1.5 rounded-lg border transition-all font-semibold flex items-center gap-1 cursor-pointer ${
                              u.is_active
                                ? "border-[rgba(239,68,68,0.15)] text-[#ef4444] hover:bg-[rgba(239,68,68,0.05)]"
                                : "border-[rgba(34,197,94,0.15)] text-[#22c55e] hover:bg-[rgba(34,197,94,0.05)]"
                            }`}
                          >
                            {u.is_active ? (
                              <>
                                <Ban size={12} />
                                Deactivate
                              </>
                            ) : (
                              <>
                                <CheckCircle size={12} />
                                Activate
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
