interface CantidadStepperProps {
  cantidad: number;
  onDecrement: () => void;
  onIncrement: () => void;
  labelMenos: string;
  labelMas: string;
}

export function CantidadStepper({
  cantidad,
  onDecrement,
  onIncrement,
  labelMenos,
  labelMas,
}: CantidadStepperProps) {
  return (
    <div className="flex flex-shrink-0 items-center gap-2">
      <button
        type="button"
        onClick={onDecrement}
        aria-label={labelMenos}
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-muted text-text-primary hover:bg-slate-200"
      >
        -
      </button>
      <span className="min-w-[1.5rem] text-center text-sm">{cantidad}</span>
      <button
        type="button"
        onClick={onIncrement}
        aria-label={labelMas}
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-muted text-text-primary hover:bg-slate-200"
      >
        +
      </button>
    </div>
  );
}
