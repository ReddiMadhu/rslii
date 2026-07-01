import { useState, useRef, useEffect } from "react";
import useAuthStore from "../store/useAuthStore";
import { User, LogOut, KeyRound, ShieldAlert, ChevronDown } from "lucide-react";

export default function UserMenu({ onChangePasswordClick, onManageUsersClick }) {
  const { user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!user) return null;

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[rgba(255,255,255,0.06)] bg-[rgba(15,15,22,0.6)] text-[var(--text-secondary)] hover:text-white hover:border-[rgba(251,78,11,0.3)] transition-all cursor-pointer text-[11px]"
      >
        <div className="w-4.5 h-4.5 rounded-full bg-gradient-to-br from-[#fb4e0b] to-[#ff814d] flex items-center justify-center text-white font-bold text-[9px]">
          {user.username.charAt(0).toUpperCase()}
        </div>
        <span className="font-medium max-w-[90px] truncate">{user.username}</span>
        <ChevronDown size={10} className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-52 rounded-xl bg-[#0f0f16] border border-[rgba(255,255,255,0.08)] shadow-2xl py-1.5 z-50 animate-fade-in text-sm">
          <div className="px-4 py-2 border-bottom border-[rgba(255,255,255,0.06)] text-xs text-[var(--text-muted)]">
            Signed in as <strong className="text-white block mt-0.5 truncate">{user.username}</strong>
          </div>

          <button
            onClick={() => {
              setIsOpen(false);
              onChangePasswordClick();
            }}
            className="w-full flex items-center gap-2.5 px-4 py-2 text-left text-[var(--text-secondary)] hover:text-white hover:bg-[rgba(255,255,255,0.03)] transition-all cursor-pointer"
          >
            <KeyRound size={14} />
            <span>Change Password</span>
          </button>

          {user.is_admin && (
            <button
              onClick={() => {
                setIsOpen(false);
                onManageUsersClick();
              }}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-left text-[var(--text-secondary)] hover:text-white hover:bg-[rgba(255,255,255,0.03)] transition-all cursor-pointer border-t border-[rgba(255,255,255,0.04)]"
            >
              <ShieldAlert size={14} className="text-[#fb4e0b]" />
              <span className="font-semibold text-white">Manage Users</span>
            </button>
          )}

          <div className="border-t border-[rgba(255,255,255,0.06)] my-1" />

          <button
            onClick={() => {
              setIsOpen(false);
              logout();
            }}
            className="w-full flex items-center gap-2.5 px-4 py-2 text-left text-[#ef4444] hover:bg-[rgba(239,68,68,0.05)] transition-all cursor-pointer"
          >
            <LogOut size={14} />
            <span>Logout</span>
          </button>
        </div>
      )}
    </div>
  );
}
