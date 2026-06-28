const RE_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validarCorreo(correo: string): string | undefined {
  if (!correo.trim()) return "El correo es obligatorio.";
  if (!RE_CORREO.test(correo)) return "Ingresá un correo válido.";
  return undefined;
}

export function validarPassword(password: string): string | undefined {
  if (!password) return "La contraseña es obligatoria.";
  if (password.length < 8) return "La contraseña debe tener al menos 8 caracteres.";
  return undefined;
}

export function validarConfirmacion(password: string, confirmacion: string): string | undefined {
  if (!confirmacion) return "La confirmación es obligatoria.";
  if (confirmacion !== password) return "Las contraseñas no coinciden.";
  return undefined;
}

export function validarNombre(nombre: string): string | undefined {
  if (!nombre.trim()) return "El nombre es obligatorio.";
  if (nombre.trim().length < 2) return "El nombre debe tener al menos 2 caracteres.";
  return undefined;
}
