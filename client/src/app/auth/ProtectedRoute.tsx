import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";

import { authService } from "../../shared/api/authService";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const location = useLocation();

  const profile = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authService.me,
    enabled: auth.isAuthenticated && !auth.operator,
    retry: false,
  });

  useEffect(() => {
    if (profile.data) {
      auth.setOperator(profile.data);
    }
  }, [auth, profile.data]);

  useEffect(() => {
    if (profile.isError) {
      auth.logout();
    }
  }, [auth, profile.isError]);

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!auth.operator && profile.isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb] text-sm font-semibold text-slate-600">Проверяем сессию...</div>;
  }

  return <>{children}</>;
}
