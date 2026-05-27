import { useState } from "react";
import useAuthStore from "../store/useAuthStore";
import { X, KeyRound, Loader2, ShieldAlert } from "lucide-react";

export default function ChangePasswordModal({ onClose }) {
  const { changePassword, isLoading } = useAuthStore();
  const [form, setForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const { currentPassword, newPassword, confirmPassword } = form;

    if (!currentPassword) {
      setError("Current password is required");
      return;
    }
    if (newPassword.length < 6) {
      setError("New password must be at least 6 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }

    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
      setForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.message || "Failed to change password");
    }
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div 
        className="w-full max-w-md rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[#0f0f16] shadow-2xl p-6 relative overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#666677] hover:text-white transition-colors cursor-pointer"
        >
          <X size={18} />
        </button>

        <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
          <KeyRound size={18} className="text-[#fb4e0b]" />
          Change Password
        </h3>
        <p className="text-xs text-[#a0a0b8] mb-5">Ensure your account remains secure.</p>

        {success ? (
          <div className="p-4 rounded-xl bg-[rgba(34,197,94,0.06)] border border-[rgba(34,197,94,0.15)] text-[#22c55e] text-xs font-semibold text-center py-6 animate-fade-in">
            Password changed successfully! Closing...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[#666677] mb-1.5">
                Current Password
              </label>
              <input
                type="password"
                name="currentPassword"
                value={form.currentPassword}
                onChange={handleChange}
                disabled={isLoading}
                placeholder="Enter current password"
                className="w-full px-4 py-2 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[#666677] mb-1.5">
                New Password
              </label>
              <input
                type="password"
                name="newPassword"
                value={form.newPassword}
                onChange={handleChange}
                disabled={isLoading}
                placeholder="At least 6 characters"
                className="w-full px-4 py-2 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[#666677] mb-1.5">
                Confirm New Password
              </label>
              <input
                type="password"
                name="confirmPassword"
                value={form.confirmPassword}
                onChange={handleChange}
                disabled={isLoading}
                placeholder="Repeat new password"
                className="w-full px-4 py-2 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-xs text-white focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.15)] text-[#ef4444] text-xs">
                <ShieldAlert size={14} className="flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#161622] hover:bg-[#202030] text-[#a0a0b8] hover:text-white transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#fb4e0b] to-[#ff6b2e] hover:from-[#ff6b2e] hover:to-[#ff814d] transition-all flex items-center gap-1.5"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Update Password</span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
