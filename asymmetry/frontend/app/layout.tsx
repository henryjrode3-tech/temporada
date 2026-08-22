import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Asymmetry Engine",
  description:
    "Research tooling for finding obscure, reasonably priced assets that could matter enormously in 5-15 years. Not a trading system.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full">
        <div className="flex min-h-dvh flex-col lg:flex-row">
          <Nav />
          <main className="min-w-0 flex-1">
            <div className="mx-auto w-full max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
              {children}
            </div>
            <footer className="mx-auto w-full max-w-[1500px] px-4 pb-8 pt-4 text-[11px] leading-relaxed text-neutral-600 sm:px-6 lg:px-8">
              Asymmetry Engine is a research instrument. Verdicts describe
              research posture — what to look at next — and never an instruction
              to transact. Scenario multiples, scores and probabilities are model
              estimates conditional on stated assumptions, revised as evidence
              arrives, and frequently wrong.
            </footer>
          </main>
        </div>
      </body>
    </html>
  );
}
