import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CalendarCheck, LogIn } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth/AuthProvider";
import { authService } from "../../shared/api/authService";

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("operator");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: authService.login,
    onSuccess: (data) => {
      auth.login(data.access_token, data.operator);
      const target = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";
      navigate(target, { replace: true });
    },
  });

  if (auth.isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({ username, password });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb] px-6">
      <div className="w-full max-w-[420px]">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-mint text-white">
            <CalendarCheck size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-ink">Vamos Subscription Tracker</h1>
            <p className="text-sm text-slate-500">Вход оператора</p>
          </div>
        </div>

        <form className="panel space-y-4 p-6" onSubmit={submit}>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">Логин</span>
            <input className="input" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">Пароль</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              autoFocus
            />
          </label>

          {mutation.isError ? <div className="rounded-md bg-red-50 px-3 py-2 text-sm font-medium text-red-700">{mutation.error.message}</div> : null}

          <button className="btn-primary w-full" disabled={mutation.isPending || !username || !password}>
            <LogIn size={18} />
            {mutation.isPending ? "Входим..." : "Войти"}
          </button>

          <div className="rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
            Первый оператор создается автоматически. По умолчанию: логин <b>operator</b>, пароль <b>vamos123</b>.
          </div>
        </form>
      </div>
    </div>
  );
}
