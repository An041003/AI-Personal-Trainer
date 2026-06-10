function formatMuscle(value) {
  return String(value || "").replace("_", " ");
}

export function FocusMuscles({ muscles, emptyText = "No focus set yet.", compact = false }) {
  const items = Array.isArray(muscles) ? muscles.filter(Boolean) : [];

  if (!items.length) {
    return <p className={compact ? "text-xs text-slate-500" : "text-sm text-slate-500"}>{emptyText}</p>;
  }

  return (
    <div className={compact ? "flex max-w-full flex-nowrap gap-2 overflow-hidden" : "flex flex-wrap gap-2"}>
      {items.map((muscle) => (
        <span
          key={muscle}
          className={
            compact
              ? "shrink-0 whitespace-nowrap rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 ring-1 ring-brand-100"
              : "rounded-full bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 ring-1 ring-brand-100"
          }
        >
          {formatMuscle(muscle)}
        </span>
      ))}
    </div>
  );
}
