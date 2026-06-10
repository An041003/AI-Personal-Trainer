export function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-slate-800">{label}</span>
      {children}
    </label>
  );
}

export function TextInput(props) {
  return <input {...props} className={`input ${props.className || ""}`} />;
}

export function SelectInput({ children, ...props }) {
  return (
    <select {...props} className={`input ${props.className || ""}`}>
      {children}
    </select>
  );
}

export function TextArea(props) {
  return <textarea {...props} className={`input min-h-24 resize-y ${props.className || ""}`} />;
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{message}</div>;
}

export function JsonBlock({ data }) {
  if (!data) return null;
  return <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>;
}
