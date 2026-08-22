import { formatMultiple } from "@/lib/format";
import { Estimate } from "./Estimate";

export function Multiple({
  value,
  dp,
  estimate = false,
  className = "",
}: {
  value: number | null | undefined;
  dp?: number;
  estimate?: boolean;
  className?: string;
}) {
  const body = (
    <span className={`tabular-nums ${className}`}>{formatMultiple(value, dp)}</span>
  );
  return estimate ? <Estimate>{body}</Estimate> : body;
}
