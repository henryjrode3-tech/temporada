import { formatMoney } from "@/lib/format";
import { Estimate } from "./Estimate";

export function Money({
  value,
  estimate = false,
  signed = false,
  className = "",
}: {
  value: number | null | undefined;
  estimate?: boolean;
  signed?: boolean;
  className?: string;
}) {
  const text = formatMoney(value, { signed });
  const body = <span className={`tabular-nums ${className}`}>{text}</span>;
  return estimate ? <Estimate>{body}</Estimate> : body;
}
