import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";


export function ProfileCompletionNotice({ completeness, showLink = true }) {
  if (!completeness) return null;

  if (completeness.isComplete) {
    return (
      <div className="rounded border border-brand-100 bg-brand-50/70 px-4 py-3 text-sm text-brand-800">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2 size={16} />
          Profile complete
        </div>
      </div>
    );
  }

  return (
    <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <div className="flex flex-wrap items-center gap-2">
        <AlertCircle size={16} />
        <p className="font-semibold">Complete your profile to use workout, nutrition, and AI advice accurately.</p>
        {showLink ? (
          <Link className="font-semibold text-amber-950 underline underline-offset-2" to="/profile">
            Go to profile
          </Link>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {completeness.missingFields.map((item) => (
          <span key={item.field} className="rounded border border-amber-200 bg-white px-2 py-1 text-xs font-medium">
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}
