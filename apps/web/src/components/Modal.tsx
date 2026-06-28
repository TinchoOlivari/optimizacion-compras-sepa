import { useEffect, useRef, type ReactNode } from "react";

import { Button } from "@/components/Button";

export interface ModalProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children?: ReactNode;
  primaryAction?: {
    label: string;
    onClick: () => void;
    variant?: "primary" | "destructive";
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  primaryAction,
  secondaryAction,
}: ModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    cancelRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby={description ? "modal-description" : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[480px] rounded-xl bg-surface p-5 shadow-card"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="modal-title" className="mb-2 text-lg font-semibold text-text-primary">
          {title}
        </h2>
        {description ? (
          <p id="modal-description" className="mb-4 text-sm text-text-secondary">
            {description}
          </p>
        ) : null}

        {children ? <div className="mb-5">{children}</div> : null}

        <div className="flex justify-end gap-3">
          {secondaryAction ? (
            <Button ref={cancelRef} variant="secondary" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          ) : (
            <Button ref={cancelRef} variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
          )}

          {primaryAction ? (
            <Button variant={primaryAction.variant ?? "primary"} onClick={primaryAction.onClick}>
              {primaryAction.label}
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
