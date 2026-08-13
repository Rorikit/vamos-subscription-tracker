import type { Operator } from "../../shared/api/authService";
import { useAuth } from "./AuthProvider";

type Role = Operator["role"];

export function RoleRoute({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const auth = useAuth();

  if (!auth.operator) {
    return null;
  }

  if (!roles.includes(auth.operator.role)) {
    return (
      <div className="panel mx-auto mt-10 max-w-2xl p-8">
        <div className="text-sm font-bold uppercase text-coral">403</div>
        <h1 className="mt-2 text-2xl font-bold text-ink">Нет доступа</h1>
        <p className="mt-2 text-sm text-slate-500">У вашей роли нет прав на этот раздел. Обратитесь к администратору.</p>
      </div>
    );
  }

  return <>{children}</>;
}
