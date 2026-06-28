import type React from "react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useAuthAnonimoSnapshot } from "@/features/auth/hooks/useAuthAnonimoSnapshot";
import { useLogin } from "@/features/auth/hooks/useLogin";
import { validarCorreo, validarPassword } from "@/lib/validaciones/auth";

interface ErroresLogin {
  correo?: string;
  password?: string;
  general?: string;
}

export default function LoginPage(): React.ReactElement {
  const { cantidadItems } = useAuthAnonimoSnapshot();
  const { login, cargando, errorGeneral, resetError } = useLogin();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [errores, setErrores] = useState<ErroresLogin>({});

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const erroresActuales: ErroresLogin = {
      correo: validarCorreo(correo),
      password: validarPassword(password),
    };
    setErrores(erroresActuales);
    if (erroresActuales.correo || erroresActuales.password) {
      return;
    }

    resetError();
    void login({ correo, password }).catch(() => undefined);
  }

  const puedeEnviar = correo.trim().length > 0 && password.length > 0;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <AuthCard title="Iniciar sesión">
        {cantidadItems > 0 ? (
          <div
            role="status"
            className="mb-4 rounded-xl border border-accent bg-accent-light p-3 text-sm text-text-primary"
          >
            Tenés un carrito anónimo con {cantidadItems} producto
            {cantidadItems === 1 ? "" : "s"}. Al iniciar sesión se va a convertir en tu carrito
            activo.
          </div>
        ) : null}

        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <Input
            label="Correo electrónico"
            name="correo"
            type="email"
            autoComplete="email"
            required
            value={correo}
            onChange={(event) => setCorreo(event.target.value)}
            error={errores.correo}
          />
          <Input
            label="Contraseña"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errores.password}
          />

          {errorGeneral || errores.general ? (
            <p role="alert" className="text-sm text-error">
              {errorGeneral ?? errores.general}
            </p>
          ) : null}

          <Button type="submit" disabled={cargando || !puedeEnviar} className="w-full">
            {cargando ? "Ingresando..." : "Ingresar"}
          </Button>
        </form>

        <div className="mt-4 flex flex-col gap-2 text-center text-sm">
          <Link className="font-medium text-primary hover:underline" to="/recuperar">
            ¿Olvidaste tu contraseña?
          </Link>
          <p className="text-text-secondary">
            ¿No tenés cuenta?{" "}
            <Link className="font-medium text-primary hover:underline" to="/registro">
              Registrarme
            </Link>
          </p>
        </div>
      </AuthCard>
    </div>
  );
}
