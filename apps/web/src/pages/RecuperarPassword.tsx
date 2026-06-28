import type React from "react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useRecuperarPassword } from "@/features/auth/hooks/useRecuperarPassword";
import { validarCorreo } from "@/lib/validaciones/auth";

export default function RecuperarPasswordPage(): React.ReactElement {
  const { solicitar, enviando, mensaje, error: errorApi, reset } = useRecuperarPassword();
  const [correo, setCorreo] = useState("");
  const [errorValidacion, setErrorValidacion] = useState<string | undefined>();

  async function onSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const errorCorreo = validarCorreo(correo);
    setErrorValidacion(errorCorreo);
    reset();
    if (errorCorreo) return;

    try {
      await solicitar(correo);
    } catch {
      // El hook expone errorApi para el render.
    }
  }

  const error = errorValidacion ?? errorApi;

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <AuthCard title="Recuperar contraseña">
        <p className="mb-5 text-sm text-text-secondary">
          Ingresá tu correo electrónico y te enviaremos un enlace para que puedas definir una nueva contraseña.
        </p>

        <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-4">
          <Input
            label="Correo electrónico"
            name="correo"
            type="email"
            autoComplete="email"
            required
            placeholder="tu@correo.com"
            value={correo}
            onChange={(event) => setCorreo(event.target.value)}
            error={error}
          />

          {mensaje ? (
            <p role="status" className="text-sm text-success">
              {mensaje}
            </p>
          ) : null}

          <Button type="submit" disabled={enviando || correo.trim().length === 0} className="w-full">
            {enviando ? "Enviando..." : "Enviar enlace"}
          </Button>
        </form>

        <div className="mt-5 text-center">
          <Link to="/login" className="text-sm text-text-secondary hover:text-primary">
            Volver
          </Link>
        </div>
      </AuthCard>
    </main>
  );
}
