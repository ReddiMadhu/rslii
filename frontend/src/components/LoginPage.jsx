import { useState } from "react";
import useAuthStore from "../store/useAuthStore";
import { KeyRound, Mail, User, ShieldAlert, Sparkles, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login, register, error: authError, isLoading } = useAuthStore();
  const [isRegistering, setIsRegistering] = useState(false);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    inviteCode: "",
  });
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const { username, email, password, confirmPassword, inviteCode } = form;

    if (!username.trim()) {
      setError("Username is required");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    if (isRegistering) {
      if (!email.trim() || !email.includes("@")) {
        setError("A valid email address is required");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }
      if (!inviteCode.trim()) {
        setError("Invite code is required");
        return;
      }

      try {
        await register(username, email, password, inviteCode);
        // Switch to login on success
        setIsRegistering(false);
        setError(null);
        alert("Registration successful! Please sign in.");
      } catch (err) {
        setError(err.message || "Registration failed");
      }
    } else {
      try {
        await login(username, password);
      } catch (err) {
        setError(err.message || "Login failed");
      }
    }
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const toggleMode = () => {
    setIsRegistering(!isRegistering);
    setError(null);
    setForm({
      username: "",
      email: "",
      password: "",
      confirmPassword: "",
      inviteCode: "",
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#050508]">
      {/* Background Gradients & Glows */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full bg-[rgba(251,78,11,0.06)] blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] rounded-full bg-[rgba(59,130,246,0.04)] blur-[120px] pointer-events-none" />

      {/* Decorative lines */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900/20 via-neutral-950/50 to-neutral-950 pointer-events-none" />

      <div className="w-full max-w-md mx-4 z-10 animate-slide-up">
        {/* Logo and title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[rgba(251,78,11,0.08)] border border-[rgba(251,78,11,0.2)] mb-4">
            <Sparkles size={14} className="text-[#fb4e0b] animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#fb4e0b]">Enterprise Governance</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-[#fb4e0b] via-[#ff6b2e] to-[#ff985a] bg-clip-text text-transparent">
            ETLPulse.AI
          </h1>
          <p className="text-sm mt-2 text-[var(--text-secondary)]">
            {isRegistering ? "Create your developer account" : "Sign in to secure visual lineage validation"}
          </p>
        </div>

        {/* Form Card */}
        <div 
          className="glass glow rounded-2xl border border-[rgba(255,255,255,0.06)] p-8 relative"
          style={{ background: "rgba(15, 15, 22, 0.7)", boxShadow: "0 0 50px rgba(251, 78, 11, 0.05)" }}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Username</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-[var(--text-muted)]">
                  <User size={16} />
                </span>
                <input
                  type="text"
                  name="username"
                  value={form.username}
                  onChange={handleChange}
                  placeholder="e.g. john.doe"
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
                />
              </div>
            </div>

            {/* Email (Registration only) */}
            {isRegistering && (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Email Address</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-[var(--text-muted)]">
                    <Mail size={16} />
                  </span>
                  <input
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="e.g. john@acme.com"
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
                  />
                </div>
              </div>
            )}

            {/* Password */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Password</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-[var(--text-muted)]">
                  <KeyRound size={16} />
                </span>
                <input
                  type="password"
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
                />
              </div>
            </div>

            {/* Confirm Password (Registration only) */}
            {isRegistering && (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Confirm Password</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-[var(--text-muted)]">
                    <KeyRound size={16} />
                  </span>
                  <input
                    type="password"
                    name="confirmPassword"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    placeholder="••••••••"
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
                  />
                </div>
              </div>
            )}

            {/* Invite Code (Registration only) */}
            {isRegistering && (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">Invite Code</label>
                <input
                  type="text"
                  name="inviteCode"
                  value={form.inviteCode}
                  onChange={handleChange}
                  placeholder="e.g. ACME2026"
                  disabled={isLoading}
                  className="w-full px-4 py-2.5 bg-[#0a0a0f] border border-[rgba(255,255,255,0.08)] rounded-xl text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[#fb4e0b] focus:ring-1 focus:ring-[#fb4e0b] transition-all"
                />
              </div>
            )}

            {/* Local Error State */}
            {(error || authError) && (
              <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.15)] text-[#ef4444] text-xs">
                <ShieldAlert size={16} className="flex-shrink-0" />
                <span>{error || authError}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 rounded-xl font-semibold text-white bg-gradient-to-r from-[#fb4e0b] to-[#ff6b2e] hover:from-[#ff6b2e] hover:to-[#ff814d] active:scale-[0.98] transition-all flex items-center justify-center gap-2 border border-[rgba(251,78,11,0.2)]"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>{isRegistering ? "Registering account..." : "Signing in..."}</span>
                </>
              ) : (
                <span>{isRegistering ? "Create Account" : "Sign In"}</span>
              )}
            </button>
          </form>

          {/* Mode Switcher */}
          <div className="mt-6 text-center text-xs">
            <span className="text-[var(--text-muted)]">
              {isRegistering ? "Already have an account? " : "Don't have an account? "}
            </span>
            <button
              type="button"
              onClick={toggleMode}
              disabled={isLoading}
              className="text-[#fb4e0b] hover:text-[#ff6b2e] font-bold transition-colors focus:outline-none"
            >
              {isRegistering ? "Sign In" : "Register"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
