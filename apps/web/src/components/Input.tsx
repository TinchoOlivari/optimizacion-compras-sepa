import { forwardRef, type InputHTMLAttributes } from "react";

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "className"> {
  label: string;
  error?: string;
  className?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, className = "", required, ...rest }, ref) => {
    const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className={`flex flex-col gap-1 ${className}`}>
        <label htmlFor={inputId} className="text-[13px] font-semibold text-text-primary">
          {label}
          {required ? <span aria-hidden="true"> *</span> : null}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={`min-h-[44px] rounded-xl border bg-surface px-3 text-base text-text-primary outline-none transition-colors placeholder:text-text-secondary/60 focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60 ${
            error ? "border-error" : "border-border"
          }`}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
          required={required}
          {...rest}
        />
        {error ? (
          <p id={`${inputId}-error`} className="text-sm text-error">
            {error}
          </p>
        ) : null}
      </div>
    );
  },
);

Input.displayName = "Input";
