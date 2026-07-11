import { ReactNode } from "react";

type Props = {
  label: string;
  value: ReactNode;
  hint?: string;
};

export function StatCard({ label, value, hint }: Props) {
  return (
    <div className="panel p-5">
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-bold text-ink">{value}</div>
      {hint ? <div className="mt-1 text-sm text-slate-500">{hint}</div> : null}
    </div>
  );
}

