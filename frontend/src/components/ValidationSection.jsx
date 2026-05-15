export default function ValidationSection({ needsAction, children }) {
  return (
    <div
      className="rounded-xl"
      style={{
        border: "1px solid var(--border)",
        borderLeftWidth: needsAction ? 3 : 1,
        borderLeftColor: needsAction ? "#ef4444" : "var(--border)",
        background: needsAction ? "rgba(239,68,68,0.04)" : "transparent",
      }}
    >
      {children}
    </div>
  );
}
