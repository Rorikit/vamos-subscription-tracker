import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Bell, CalendarCheck, CalendarDays, ChevronRight, ClipboardList, CreditCard, Dumbbell, GraduationCap, Info, LayoutDashboard, LogOut, ReceiptText, Settings, Ticket, Users, WalletCards } from "lucide-react";

import { useAuth } from "../auth/AuthProvider";
import { notificationService } from "../../shared/api/notificationService";
import { toCurrency, toDate } from "../../shared/api/client";
import type { NotificationSummary } from "../../shared/types/domain";

const navItems = [
  { to: "/dashboard", label: "Панель", icon: LayoutDashboard, roles: ["admin", "operator", "finance"] },
  { to: "/schedule", label: "Расписание", icon: CalendarDays, roles: ["admin", "operator"] },
  { to: "/participants", label: "Участники", icon: Users, roles: ["admin", "operator"] },
  { to: "/memberships", label: "Абонементы", icon: Ticket, roles: ["admin", "operator"] },
  { to: "/teachers", label: "Преподаватели", icon: GraduationCap, roles: ["admin", "operator"] },
  { to: "/practice", label: "Практика", icon: Dumbbell, roles: ["admin", "operator", "finance"] },
  { to: "/payment-obligations", label: "Обязательные платежи", icon: WalletCards, roles: ["admin", "operator"] },
  { to: "/extra-expenses", label: "Внештатные расходы", icon: ReceiptText, roles: ["admin", "operator", "finance"] },
  { to: "/finance", label: "Финансы", icon: CreditCard, roles: ["admin", "finance"] },
  { to: "/audit-logs", label: "Журнал", icon: ClipboardList, roles: ["admin"] },
  { to: "/settings", label: "Настройки", icon: Settings, roles: ["admin"] },
];

type NotificationItem = NotificationSummary["items"][number];

export function AppLayout() {
  const auth = useAuth();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const role = auth.operator?.role ?? "operator";
  const visibleNavItems = navItems.filter((item) => item.roles.includes(role));
  const notifications = useQuery({
    queryKey: ["notifications", "summary"],
    queryFn: () => notificationService.summary(),
    retry: false,
    refetchInterval: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
  });
  const paymentNotification = notifications.data?.items.find((item) => item.type === "expense_payment_due");

  return (
    <div className="flex min-h-screen bg-[#f6f8fb]">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-200 bg-white">
        <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-mint text-white"><CalendarCheck size={21} /></div>
          <div><div className="text-base font-bold text-ink">Vamos</div><div className="text-xs font-medium text-slate-500">Subscription Tracker</div></div>
        </div>
        <nav className="space-y-1 p-3">
          {visibleNavItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `flex h-11 items-center gap-3 rounded-md px-3 text-sm font-semibold transition ${isActive ? "bg-mint text-white" : "text-slate-600 hover:bg-slate-100"}`}>
              <item.icon size={18} />{item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="ml-64 flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-8 backdrop-blur">
          <div className="text-lg font-bold text-ink">Vamos Subscription Tracker</div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <button type="button" className="relative flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50" onClick={() => setNotificationsOpen((value) => !value)} aria-label="Уведомления" aria-expanded={notificationsOpen}>
                <Bell size={18} />
                {paymentNotification ? <span className={`absolute -right-2 -top-2 flex min-h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white ${paymentNotification.severity === "error" ? "bg-red-600" : paymentNotification.severity === "warning" ? "bg-amber-500" : "bg-sky-600"}`}>{paymentNotification.count > 99 ? "99+" : paymentNotification.count}</span> : null}
              </button>
              {notificationsOpen ? (
                <div className="absolute right-0 top-12 w-[390px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">
                  <div className="border-b border-slate-100 px-4 py-3"><div className="font-bold text-ink">Уведомления</div><div className="mt-0.5 text-xs text-slate-500">Обязательные платежи текущего месяца</div></div>
                  {notifications.isLoading ? <div className="px-4 py-6 text-sm text-slate-500">Проверяем платежи...</div> : null}
                  {notifications.isError ? <div className="px-4 py-6 text-sm text-red-700">Не удалось загрузить уведомления.</div> : null}
                  {!notifications.isLoading && !notifications.isError && paymentNotification ? (
                    <Link to={paymentNotification.action} onClick={() => setNotificationsOpen(false)} className="flex gap-3 px-4 py-4 transition hover:bg-slate-50">
                      <NotificationIcon notification={paymentNotification} />
                      <div className="min-w-0 flex-1"><div className="text-sm font-bold text-ink">{notificationTitle(paymentNotification)}</div><div className="mt-1 text-sm leading-5 text-slate-600">{notificationDetails(paymentNotification)}</div><div className="mt-2 flex items-center gap-1 text-xs font-semibold text-mint">Открыть платежи <ChevronRight size={14} /></div></div>
                    </Link>
                  ) : null}
                  {!notifications.isLoading && !notifications.isError && !paymentNotification ? <div className="px-4 py-6 text-sm text-slate-500">Платежей, требующих внимания, нет.</div> : null}
                </div>
              ) : null}
            </div>
            <div className="text-right"><div className="text-sm font-semibold text-ink">{auth.operator?.full_name ?? "Оператор"}</div><div className="text-xs text-slate-500">{auth.operator?.username} · {roleLabel(role)}</div></div>
            <button className="btn-secondary h-9 px-3" onClick={auth.logout} title="Выйти"><LogOut size={17} />Выйти</button>
          </div>
        </header>
        <div className="flex-1 p-8">
          {paymentNotification ? <PaymentAlert notification={paymentNotification} /> : null}
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function PaymentAlert({ notification }: { notification: NotificationItem }) {
  const classes = notification.severity === "error" ? "border-red-200 bg-red-50 text-red-900" : notification.severity === "warning" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-sky-200 bg-sky-50 text-sky-900";
  return (
    <div className={`mb-5 flex items-center gap-3 rounded-md border px-4 py-3 ${classes}`} role="status" aria-live="polite">
      <NotificationIcon notification={notification} />
      <div className="min-w-0 flex-1"><div className="text-sm font-bold">{notificationTitle(notification)}</div><div className="mt-0.5 text-sm">{notificationDetails(notification)}</div></div>
      <Link to={notification.action} className="btn-secondary h-9 shrink-0 bg-white px-3">Открыть платежи <ChevronRight size={16} /></Link>
    </div>
  );
}

function NotificationIcon({ notification }: { notification: NotificationItem }) {
  if (notification.severity === "error") return <AlertCircle className="mt-0.5 shrink-0 text-red-600" size={20} />;
  if (notification.severity === "warning") return <AlertCircle className="mt-0.5 shrink-0 text-amber-600" size={20} />;
  return <Info className="mt-0.5 shrink-0 text-sky-600" size={20} />;
}

function notificationTitle(notification: NotificationItem) {
  if (notification.overdue_count) return "Есть просроченные обязательные платежи";
  if (notification.due_today_count) return "Сегодня срок обязательных платежей";
  return "Скоро срок обязательных платежей";
}

function notificationDetails(notification: NotificationItem) {
  const parts: string[] = [];
  if (notification.overdue_count) parts.push(`просрочено: ${notification.overdue_count}`);
  if (notification.due_today_count) parts.push(`на сегодня: ${notification.due_today_count}`);
  if (notification.upcoming_count) parts.push(`в ближайшие 3 дня: ${notification.upcoming_count}`);
  const amount = notification.amount ? ` на сумму ${toCurrency(notification.amount)}` : "";
  const dueDate = notification.nearest_due_date ? ` Ближайший срок: ${toDate(notification.nearest_due_date)}.` : "";
  return `Требуют внимания ${notification.count} платежей${amount} (${parts.join(", ")}).${dueDate}`;
}

function roleLabel(role: string) {
  const labels: Record<string, string> = { admin: "Администратор", operator: "Оператор", finance: "Финансист" };
  return labels[role] ?? role;
}
