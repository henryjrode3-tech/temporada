"use client";

import { useState, type ReactNode } from "react";

export interface TabDef {
  id: string;
  label: string;
  /** Small count or marker shown after the label. */
  badge?: string | number;
  /** Renders the badge in a warning tone. */
  alert?: boolean;
}

export function Tabs({
  tabs,
  panels,
}: {
  tabs: TabDef[];
  panels: ReactNode[];
}) {
  const [active, setActive] = useState(tabs[0]?.id ?? "");
  const index = Math.max(
    0,
    tabs.findIndex((t) => t.id === active),
  );

  return (
    <div>
      <div className="sticky top-0 z-20 -mx-4 overflow-x-auto border-b border-neutral-800 bg-neutral-950/95 px-4 backdrop-blur sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div
          role="tablist"
          aria-label="Candidate sections"
          className="flex min-w-max gap-1 py-1"
        >
          {tabs.map((t) => {
            const isActive = t.id === tabs[index].id;
            return (
              <button
                key={t.id}
                role="tab"
                type="button"
                aria-selected={isActive}
                onClick={() => setActive(t.id)}
                className={`whitespace-nowrap rounded-t px-3 py-2 text-[12.5px] transition-colors ${
                  isActive
                    ? "border-b-2 border-amber-400 text-amber-300"
                    : "border-b-2 border-transparent text-neutral-500 hover:text-neutral-200"
                }`}
              >
                {t.label}
                {t.badge !== undefined && t.badge !== 0 ? (
                  <span
                    className={`ml-1.5 rounded px-1 py-px text-[10px] tabular-nums ${
                      t.alert
                        ? "bg-rose-500/15 text-rose-300"
                        : "bg-neutral-800 text-neutral-400"
                    }`}
                  >
                    {t.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
      <div role="tabpanel" className="pt-4">
        {panels[index]}
      </div>
    </div>
  );
}
