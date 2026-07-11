import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { financeService } from "../../shared/api/financeService";
import { toCurrency, toDate } from "../../shared/api/client";
import { StatCard } from "../../shared/ui/StatCard";
import { StatusBadge } from "../../shared/ui/StatusBadge";

export function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: financeService.dashboard });
  const active = data?.memberships.filter((membership) => membership.is_currently_active) ?? [];
  const endingSoon = active.filter((membership) => daysLeft(membership.end_date) <= 7 || membership.remaining_lessons <= 2);
  if (isLoading) return <div className="panel p-6">Загрузка...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Главная панель</h1>
        <p className="mt-1 text-sm text-slate-500">Сводка по активным абонементам, занятиям и заработку преподавателей.</p>
      </div>
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Активные абонементы" value={active.length} />
        <StatCard label="Скоро закончатся" value={endingSoon.length} />
        <StatCard label="Выручка" value={toCurrency(data?.summary.total_revenue ?? 0)} />
        <StatCard label="Заработок преподавателей" value={toCurrency(data?.summary.teacher_earnings_total ?? 0)} />
      </div>
      <div className="grid grid-cols-2 gap-6">
        <section className="panel">
          <Header title="Активные абонементы" link="/memberships" />
          <table className="w-full">
            <thead>
              <tr><th className="th">Участник</th><th className="th">Остаток</th><th className="th">До</th><th className="th">Статус</th></tr>
            </thead>
            <tbody>
              {active.slice(0, 7).map((membership) => (
                <tr key={membership.id}>
                  <td className="td">{membership.participant?.full_name}</td>
                  <td className="td">{membership.remaining_lessons} / {membership.total_lessons}</td>
                  <td className="td">{toDate(membership.end_date)}</td>
                  <td className="td"><StatusBadge status={membership.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel">
          <Header title="Заработок преподавателей" link="/finance" />
          <table className="w-full">
            <thead>
              <tr><th className="th">Преподаватель</th><th className="th">Занятий</th><th className="th">Заработано</th></tr>
            </thead>
            <tbody>
              {data?.summary.teacher_earnings.map((item) => (
                <tr key={item.teacher_id}>
                  <td className="td">{item.teacher_name}</td>
                  <td className="td">{item.visits_count}</td>
                  <td className="td font-semibold text-ink">{toCurrency(item.total_earned)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <section className="panel">
          <Header title="Последние оплаты" link="/finance" />
          <table className="w-full">
            <thead>
              <tr><th className="th">Дата</th><th className="th">Участник</th><th className="th">Сумма</th></tr>
            </thead>
            <tbody>
              {data?.payments.map((payment) => (
                <tr key={payment.id}>
                  <td className="td">{toDate(payment.payment_date)}</td>
                  <td className="td">{payment.participant?.full_name}</td>
                  <td className="td">{toCurrency(payment.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel">
          <Header title="Последние списания" link="/participants" />
          <div className="divide-y divide-slate-100">
            {data?.visits.map((visit) => (
              <div key={visit.id} className="flex items-center justify-between px-5 py-4 text-sm">
                <span className="font-medium text-slate-700">{visit.participant?.full_name}</span>
                <span className="text-slate-500">{visit.teacher?.full_name}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Header({ title, link }: { title: string; link: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
      <h2 className="font-bold text-ink">{title}</h2>
      <Link className="text-sm font-semibold text-mint hover:text-teal-700" to={link}>Открыть</Link>
    </div>
  );
}

function daysLeft(value: string) {
  return Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000);
}
