import { useMemo } from "react";
import { Check, X } from "lucide-react";

/**
 * Real-time password strength indicator with requirement checklist.
 * Shows each policy requirement with pass/fail status and a strength meter bar.
 */
const PASSWORD_RULES = [
  { key: "length", label: "At least 8 characters", test: (pw) => pw.length >= 8 },
  { key: "upper", label: "Uppercase letter (A-Z)", test: (pw) => /[A-Z]/.test(pw) },
  { key: "lower", label: "Lowercase letter (a-z)", test: (pw) => /[a-z]/.test(pw) },
  { key: "digit", label: "Number (0-9)", test: (pw) => /[0-9]/.test(pw) },
  {
    key: "special",
    label: "Special character (!@#$%...)",
    test: (pw) => /[!@#$%^&*()_+\-=\[\]{}|;':",./<>?~`]/.test(pw),
  },
];

function getStrengthLevel(score, total) {
  const ratio = score / total;
  if (ratio <= 0.2) return { label: "Very Weak", color: "#ef4444", width: "20%" };
  if (ratio <= 0.4) return { label: "Weak", color: "#f97316", width: "40%" };
  if (ratio <= 0.6) return { label: "Fair", color: "#eab308", width: "60%" };
  if (ratio <= 0.8) return { label: "Strong", color: "#22c55e", width: "80%" };
  return { label: "Very Strong", color: "#10b981", width: "100%" };
}

export function validatePasswordClient(password) {
  const errors = PASSWORD_RULES.filter((r) => !r.test(password)).map((r) => r.label);
  return { valid: errors.length === 0, errors };
}

export default function PasswordStrengthIndicator({ password }) {
  const results = useMemo(
    () => PASSWORD_RULES.map((rule) => ({ ...rule, passed: rule.test(password || "") })),
    [password]
  );

  const score = results.filter((r) => r.passed).length;
  const strength = getStrengthLevel(score, PASSWORD_RULES.length);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2 animate-fade-in">
      {/* Strength Meter */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: strength.width, backgroundColor: strength.color }}
          />
        </div>
        <span
          className="text-[10px] font-bold uppercase tracking-wider whitespace-nowrap"
          style={{ color: strength.color }}
        >
          {strength.label}
        </span>
      </div>

      {/* Requirements Checklist */}
      <div className="grid grid-cols-1 gap-1">
        {results.map((rule) => (
          <div
            key={rule.key}
            className="flex items-center gap-1.5 text-[10px] transition-all duration-200"
            style={{ color: rule.passed ? "#22c55e" : "rgba(255,255,255,0.35)" }}
          >
            {rule.passed ? (
              <Check size={10} className="flex-shrink-0" />
            ) : (
              <X size={10} className="flex-shrink-0" />
            )}
            <span>{rule.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
