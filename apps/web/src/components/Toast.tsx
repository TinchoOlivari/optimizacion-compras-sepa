import { useToastStore } from "@/store/toastStore";

export function ToastContainer() {
  const toasts = useToastStore((state) => state.toasts);

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed right-4 top-4 z-[100] flex max-w-[360px] flex-col gap-3"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  );
}

function ToastItem({ toast }: { toast: { id: string; message: string; variant?: import("@/store/toastStore").ToastVariant } }) {
  const removeToast = useToastStore((state) => state.removeToast);
  const classes = variantClasses[toast.variant ?? "info"];

  return (
    <div
      role="status"
      className={`flex items-center justify-between gap-3 rounded-xl p-3 pr-4 shadow-toast ${classes}`}
    >
      <span className="text-sm text-text-primary">{toast.message}</span>
      <button
        type="button"
        onClick={() => removeToast(toast.id)}
        aria-label="Cerrar notificación"
        className="border-0 bg-transparent p-1 text-base leading-none text-text-secondary hover:text-text-primary"
      >
        ×
      </button>
    </div>
  );
}

const variantClasses: Record<import("@/store/toastStore").ToastVariant, string> = {
  info: "border border-border bg-surface",
  success: "border border-green-300 bg-success-light",
  warning: "border border-yellow-300 bg-accent-light",
  error: "border border-red-300 bg-error-light",
};
