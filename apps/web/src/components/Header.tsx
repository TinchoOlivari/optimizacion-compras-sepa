import type React from "react";
import { Link, NavLink as RouterNavLink, useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { useAppStore } from "@/store/appStore";
import { useAuthStore } from "@/store/authStore";

export function Header(): React.ReactElement {
  const navigate = useNavigate();
  const usuario = useAuthStore((state) => state.usuario);
  const compraGuiadaActivaId = useAppStore((state) => state.compraGuiadaActivaId);

  const nombreVisible = usuario?.nombre ?? usuario?.correo ?? null;

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-4 border-b border-border bg-surface px-4 shadow-sm">
      <nav aria-label="Navegación principal">
        <ul className="m-0 flex list-none items-center gap-6 p-0">
          <HeaderNavLink to="/" label="Home" end />
          {usuario ? (
            <>
              <HeaderNavLink to="/carritos" label="Mis carritos" />
              <HeaderNavLink to="/perfil" label="Perfil" />
            </>
          ) : null}
          {compraGuiadaActivaId ? (
            <li>
              <Link
                to={`/compra-guiada/${compraGuiadaActivaId}`}
                className="rounded-xl bg-accent px-3 py-1.5 text-sm font-semibold text-text-primary no-underline hover:bg-accent-hover"
              >
                Retomar compra
              </Link>
            </li>
          ) : null}
        </ul>
      </nav>

      <div>
        {usuario ? (
          <span className="text-sm font-medium text-text-secondary">{nombreVisible}</span>
        ) : (
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => navigate("/login")}>
              Iniciar sesión
            </Button>
            <Button onClick={() => navigate("/registro")}>Registrarse</Button>
          </div>
        )}
      </div>
    </header>
  );
}

function HeaderNavLink({ to, label, end = false }: { to: string; label: string; end?: boolean }) {
  return (
    <li>
      <RouterNavLink
        to={to}
        end={end}
        className={({ isActive }) =>
          `border-b-2 py-1 text-sm font-medium no-underline hover:text-primary ${
            isActive ? "border-primary text-primary" : "border-transparent text-text-secondary"
          }`
        }
      >
        {label}
      </RouterNavLink>
    </li>
  );
}
