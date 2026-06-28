import type React from "react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useAuthAnonimoSnapshot } from "@/features/auth/hooks/useAuthAnonimoSnapshot";
import { useRegistro } from "@/features/auth/hooks/useRegistro";
import {
  validarConfirmacion,
  validarCorreo,
  validarNombre,
  validarPassword,
} from "@/lib/validaciones/auth";

interface ErroresRegistro {
  nombre?: string;
  correo?: string;
  password?: string;
  confirmacion?: string;
  general?: string;
}

export default function RegistroPage(): React.ReactElement {
  const { cantidadItems } = useAuthAnonimoSnapshot();
  const { registrar, cargando, errorGeneral, errorCorreo, resetError } = useRegistro();
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [errores, setErrores] = useState<ErroresRegistro>({});

  function validarCampos(
    nombreValor: string,
    correoValor: string,
    passwordValor: string,
    confirmacionValor: string,
  ): ErroresRegistro {
    return {
      nombre: validarNombre(nombreValor),
      correo: validarCorreo(correoValor),
      password: validarPassword(passwordValor),
      confirmacion: validarConfirmacion(passwordValor, confirmacionValor),
    };
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const erroresActuales = validarCampos(nombre, correo, password, confirmacion);
    setErrores(erroresActuales);
    if (Object.values(erroresActuales).some(Boolean)) {
      return;
    }

    resetError();
    void registrar({ nombre, correo, password }).catch(() => undefined);
  }

  const puedeEnviar =
    nombre.trim().length > 0 &&
    correo.trim().length > 0 &&
    password.length > 0 &&
    confirmacion.length > 0;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <AuthCard title="Crear cuenta">
        {cantidadItems > 0 ? (
          <div
            role="status"
            className="mb-4 rounded-xl border border-accent bg-accent-light p-3 text-sm text-text-primary"
          >
            Tenés un carrito anónimo con {cantidadItems} producto
            {cantidadItems === 1 ? "" : "s"}. Al crear la cuenta se va a guardar como tu carrito
            activo.
          </div>
        ) : null}

        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <Input
            label="Nombre completo"
            name="nombre"
            type="text"
            autoComplete="name"
            required
            minLength={2}
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            error={errores.nombre}
          />
          <Input
            label="Correo electrónico"
            name="correo"
            type="email"
            autoComplete="email"
            required
            value={correo}
            onChange={(event) => setCorreo(event.target.value)}
            error={errores.correo ?? errorCorreo}
          />
          <Input
            label="Contraseña"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errores.password}
          />
          <Input
            label="Confirmar contraseña"
            name="confirmacion"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirmacion}
            onChange={(event) => setConfirmacion(event.target.value)}
            error={errores.confirmacion}
          />

          {errorGeneral || errores.general ? (
            <p role="alert" className="text-sm text-error">
              {errorGeneral ?? errores.general}
            </p>
          ) : null}

          <Button type="submit" disabled={cargando || !puedeEnviar} className="w-full">
            {cargando ? "Creando..." : "Registrarme"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-text-secondary">
          ¿Ya tenés cuenta?{" "}
          <Link className="font-medium text-primary hover:underline" to="/login">
            Iniciar sesión
          </Link>
        </p>
      </AuthCard>
    </div>
  );
}
