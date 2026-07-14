import { NavLink, Outlet } from "react-router-dom";
import { CalendarCheck, CreditCard, LayoutDashboard, LogOut, Settings, Ticket, Users } from "lucide-react";

import { useAuth } from "../auth/AuthProvider";

const navItems = [
  { to: "/dashboard", label: "Панель", icon: LayoutDashboard },
  { to: "/participants", label: "Участники", icon: Users },
  { to: "/memberships", label: "Абонементы", icon: Ticket },
  { to: "/finance", label: "Финансы", icon: CreditCard },
  { to: "/settings", label: "Настройки", icon: Settings },
];

export function AppLayout() {
  const auth = useAuth();

  return (
    <div className="flex min-h-screen bg-[#f6f8fb]">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-200 bg-white">
        <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-mint text-white">
            <CalendarCheck size={21} />
          </div>
          <div>
            <div className="text-base font-bold text-ink">Vamos</div>
            <div className="text-xs font-medium text-slate-500">Subscription Tracker</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex h-11 items-center gap-3 rounded-md px-3 text-sm font-semibold transition ${
                  isActive ? "bg-mint text-white" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="ml-64 flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-8 backdrop-blur">
          <div>
            <div className="text-lg font-bold text-ink">Vamos Subscription Tracker</div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-semibold text-ink">{auth.operator?.full_name ?? "Оператор"}</div>
              <div className="text-xs text-slate-500">{auth.operator?.username}</div>
            </div>
            <button className="btn-secondary h-9 px-3" onClick={auth.logout} title="Выйти">
              <LogOut size={17} />
              Выйти
            </button>
          </div>
        </header>
        <div className="flex-1 p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
