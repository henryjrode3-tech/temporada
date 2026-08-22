import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg py-20 text-center">
      <div className="text-[11px] uppercase tracking-widest text-neutral-600">
        404
      </div>
      <h1 className="mt-2 text-lg font-semibold text-neutral-100">
        No such candidate
      </h1>
      <p className="mt-2 text-[13px] leading-relaxed text-neutral-500">
        This identifier is not in the research set. It may have been screened out
        before it was ever written, or the link may be stale.
      </p>
      <Link
        href="/"
        className="mt-5 inline-block rounded border border-neutral-800 px-3 py-1.5 text-[12px] text-neutral-300 hover:border-amber-500/40 hover:text-amber-300"
      >
        Back to opportunities
      </Link>
    </div>
  );
}
