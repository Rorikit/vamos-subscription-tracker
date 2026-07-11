import { MembershipStatus } from "../types/domain";

const labels: Record<MembershipStatus, string> = {
  active: "Активен",
  finished: "Закончен",
  expired: "Просрочен",
  frozen: "Заморожен",
  cancelled: "Отменен",
};

const styles: Record<MembershipStatus, string> = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  finished: "bg-slate-100 text-slate-700 ring-slate-200",
  expired: "bg-amber-50 text-amber-700 ring-amber-200",
  frozen: "bg-sky-50 text-sky-700 ring-sky-200",
  cancelled: "bg-rose-50 text-rose-700 ring-rose-200",
};

export function StatusBadge({ status }: { status?: MembershipStatus | string | null }) {
  if (!status) {
    return <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">Нет</span>;
  }
  const typedStatus = status as MembershipStatus;
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${styles[typedStatus]}`}>
      {labels[typedStatus] ?? status}
    </span>
  );
}

