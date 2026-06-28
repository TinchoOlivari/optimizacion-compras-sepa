import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  children: ReactNode;
}

export function AuthCard({ title, children }: AuthCardProps) {
  return (
    <div className="w-full max-w-[420px] rounded-xl border border-border bg-surface p-6 shadow-card sm:p-8">
      <h1 className="mb-6 text-center text-[28px] font-bold text-text-primary">{title}</h1>
      {children}
    </div>
  );
}
