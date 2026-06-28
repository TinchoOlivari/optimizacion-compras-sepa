import type React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "@/store/authStore";

export function AuthGuard(): React.ReactElement {
  const token = useAuthStore((state) => state.token);
  const location = useLocation();

  if (!token) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return <Outlet />;
}
