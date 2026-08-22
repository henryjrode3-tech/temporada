import type { ReactNode } from "react";

/**
 * Wraps any figure produced by the model rather than reported by a source.
 * Estimates get a dotted amber underline and a tooltip so they can never be
 * mistaken for a filed number.
 */
export function Estimate({
  children,
  title = "Model estimate — not a reported figure and not a forecast",
  className = "",
}: {
  children: ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={`border-b border-dotted border-amber-400/60 decoration-dotted ${className}`}
    >
      {children}
    </span>
  );
}

/** Small standalone marker for a whole block of estimated figures. */
export function EstimateLegend({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[11px] text-neutral-500 ${className}`}
    >
      <span className="inline-block h-0 w-4 border-b border-dotted border-amber-400/60" />
      model estimate
    </span>
  );
}
