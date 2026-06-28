import { useEffect, useRef, useState } from "react";

type ImagenEstado = "cargando" | "lista" | "error";

interface ImagenProductoProps {
  src: string;
  alt?: string;
  className?: string;
  onResuelta?: () => void;
}

export function ImagenProducto({ src, alt = "", className = "", onResuelta }: ImagenProductoProps) {
  const [estado, setEstado] = useState<ImagenEstado>("cargando");
  const onResueltaRef = useRef(onResuelta);
  onResueltaRef.current = onResuelta;

  useEffect(() => {
    let cancelado = false;
    let reintentos = 0;
    const maxReintentos = 2;
    let timeout: ReturnType<typeof setTimeout>;

    function cargar(url: string) {
      const imagen = new Image();

      timeout = setTimeout(() => {
        if (cancelado) return;
        reintentos += 1;
        if (reintentos >= maxReintentos) {
          setEstado("error");
          onResueltaRef.current?.();
          return;
        }
        cargar(`${src}${src.includes("?") ? "&" : "?"}_retry=${reintentos}`);
      }, 8000);

      imagen.onload = () => {
        if (cancelado) return;
        clearTimeout(timeout);
        setEstado("lista");
        onResueltaRef.current?.();
      };

      imagen.onerror = () => {
        if (cancelado) return;
        clearTimeout(timeout);
        reintentos += 1;
        if (reintentos >= maxReintentos) {
          setEstado("error");
          onResueltaRef.current?.();
          return;
        }
        cargar(`${src}${src.includes("?") ? "&" : "?"}_retry=${reintentos}`);
      };

      imagen.src = url;
    }

    cargar(src);

    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [src]);

  if (estado === "error") {
    return (
      <div className={`flex items-center justify-center bg-muted ${className}`}>
        <svg
          aria-hidden="true"
          className="h-5 w-5 text-text-secondary/50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
          />
        </svg>
      </div>
    );
  }

  if (estado === "cargando") {
    return <div className={`animate-pulse bg-muted ${className}`} />;
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`animate-fade-in object-cover ${className}`}
      loading="lazy"
    />
  );
}