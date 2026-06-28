import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "destructive" | "ghost";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> {
  variant?: ButtonVariant;
  children: ReactNode;
  ariaLabel?: string;
  className?: string;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "border-transparent bg-primary text-white hover:bg-primary-hover",
  secondary: "border-border bg-surface text-primary hover:bg-muted",
  destructive: "border-transparent bg-error text-white hover:opacity-90",
  ghost: "border-transparent bg-transparent text-secondary hover:underline",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { type = "button", variant = "primary", disabled = false, onClick, children, ariaLabel, className, ...rest },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled}
        aria-label={ariaLabel}
        onClick={onClick}
        className={`min-h-[44px] rounded-xl border px-4 text-sm font-semibold leading-none transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${variantClasses[variant]} ${className ?? ""}`}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
