"""Command-line interface.

    asymmetry init          create tables
    asymmetry seed          load the synthetic corpus
    asymmetry run           run the research pipeline
    asymmetry top           show the current ranking
    asymmetry show NAME     full report for one candidate
    asymmetry report        the daily research report
    asymmetry serve         start the API
"""

from __future__ import annotations

import logging
from datetime import date

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_settings
from .db import models as m
from .db.seed import seed as seed_db
from .db.session import init_db, session_scope
from .pipeline.daily import Pipeline

app = typer.Typer(help="Asymmetry Engine - research platform for asymmetric opportunities.")
console = Console()


def _money(v: float | None) -> str:
    if v is None:
        return "-"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return f"${v/div:,.1f}{unit}"
    return f"${v:,.0f}"


VERDICT_STYLE = {
    "TOP_OPPORTUNITY": "bold green", "INVESTIGATE": "green", "WATCH": "cyan",
    "INTERESTING": "blue", "HIGH_RISK": "yellow", "THESIS_WEAKENING": "yellow",
    "THESIS_INVALIDATED": "red", "REJECTED": "dim red",
}


@app.command()
def init(drop: bool = typer.Option(False, help="Drop existing tables first.")) -> None:
    """Create the database schema."""
    init_db(drop=drop)
    console.print("[green]Schema created.[/green]")


@app.command()
def seed() -> None:
    """Load the synthetic corpus (fictional companies, for demonstration)."""
    with session_scope() as s:
        result = seed_db(s)
    console.print(f"[green]Seeded {result['candidates']} candidates.[/green]")
    console.print("[dim]All seeded companies are fictional demo data.[/dim]")


@app.command()
def run(
    limit: int = typer.Option(12, help="Maximum candidates to analyse deeply."),
    as_of: str = typer.Option("", help="Historical mode: analyse as of YYYY-MM-DD."),
    verbose: bool = typer.Option(False, "-v"),
) -> None:
    """Run the research pipeline."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    cutoff = date.fromisoformat(as_of) if as_of else None
    settings = get_settings()

    console.print(f"[dim]Reasoner: {settings.llm_mode}[/dim]")
    if cutoff:
        console.print(f"[yellow]Historical mode: only facts published on or before {cutoff}.[/yellow]")

    with session_scope() as s:
        pipeline = Pipeline(s, as_of=cutoff)
        result = pipeline.run_daily(limit=limit)

    console.print(Panel.fit(
        f"Analysed: [bold]{result['analysed']}[/bold]\n"
        f"Screened out: [bold]{result['rejected']}[/bold]\n"
        f"Theses invalidated: [bold]{len(result['invalidated'])}[/bold]\n"
        f"Spend: [bold]${result['budget']['spent_usd']:.4f}[/bold] "
        f"({result['budget']['calls']} calls, {result['budget']['cache_hits']} cached)",
        title="Pipeline complete",
    ))


@app.command()
def top(limit: int = typer.Option(15)) -> None:
    """Show the current ranking."""
    table = Table(title="Asymmetric opportunities (research output, not advice)")
    for col, just in (("#", "right"), ("Name", "left"), ("Sector", "left"),
                      ("Cap", "right"), ("Asym", "right"), ("Overall", "right"),
                      ("Risk", "right"), ("Conf", "right"), ("Verdict", "left")):
        table.add_column(col, justify=just)

    with session_scope() as s:
        rows = (
            s.query(m.Candidate).filter(m.Candidate.rank.isnot(None))
            .order_by(m.Candidate.rank.asc()).limit(limit).all()
        )
        for c in rows:
            move = ""
            if c.previous_rank and c.rank and c.previous_rank != c.rank:
                delta = c.previous_rank - c.rank
                move = f" [green]+{delta}[/green]" if delta > 0 else f" [red]{delta}[/red]"
            table.add_row(
                f"{c.rank}{move}", c.name, c.sector or "-",
                _money(c.current_market_cap),
                f"{c.asymmetry_score or 0:.0f}", f"{c.overall_score or 0:.0f}",
                f"{c.risk_score or 0:.1f}", f"{c.confidence_score or 0:.0f}",
                f"[{VERDICT_STYLE.get(c.verdict or '', 'white')}]{c.verdict or '-'}[/]",
            )
    console.print(table)


@app.command()
def show(name: str) -> None:
    """Full research report for one candidate (matched by name or ticker)."""
    with session_scope() as s:
        cand = (
            s.query(m.Candidate)
            .filter((m.Candidate.name.ilike(f"%{name}%")) | (m.Candidate.ticker == name.upper()))
            .first()
        )
        if cand is None:
            console.print(f"[red]No candidate matching {name!r}.[/red]")
            raise typer.Exit(1)

        from .api.serializers import serialize_candidate_detail
        d = serialize_candidate_detail(s, cand)

        ticker_suffix = f"({d['ticker']})" if d["ticker"] else ""
        console.print(Panel.fit(
            f"[bold]{d['name']}[/bold] {ticker_suffix}\n"
            f"{d['sector']} / {d['industry']}\n\n{d['description']}\n\n"
            f"Valuation: {_money(d['current_market_cap'])}   "
            f"Revenue: {_money(d['revenue'])}\n"
            f"Asymmetry: [bold]{d['asymmetry_score']:.0f}/100[/bold]   "
            f"Overall: {d['overall_score']:.0f}/100   "
            f"Risk: {d['risk_score']:.1f}/10   "
            f"Confidence: {d['confidence_score']:.0f}%\n"
            f"Verdict: [{VERDICT_STYLE.get(d['verdict'] or '', 'white')}]{d['verdict']}[/] "
            f"- {d['verdict_reason']}",
            title="Research result",
        ))

        sc = d.get("scenarios")
        if sc:
            t = Table(title=f"Scenarios ({sc['years']:.0f}-year horizon)")
            for col in ("Scenario", "P", "Revenue", "Future cap", "Per-share", "CAGR", ""):
                t.add_column(col, justify="right" if col != "Scenario" else "left")
            for row in sc["scenarios"]:
                t.add_row(
                    row["name"].replace("_", " ").title(),
                    f"{row['probability']:.0%}",
                    _money(row["revenue"]), _money(row["future_market_cap"]),
                    f"{row['per_share_multiple']:.2f}x",
                    f"{row['per_share_cagr']*100:.1f}%",
                    "[yellow]clamped[/yellow]" if row["was_clamped"] else "",
                )
            console.print(t)
            console.print(
                f"Median outcome [bold]{sc['median_multiple']:.2f}x[/bold] | "
                f"Expected {sc['expected_multiple']:.2f}x | "
                f"P(loss) {sc['probability_of_loss']:.0%} | "
                f"Payoff ratio {sc['payoff_ratio']:.1f}:1"
            )
            if sc.get("is_tail_dominated"):
                console.print(
                    f"[yellow]Warning: {sc['tail_contribution']:.0%} of the expected value "
                    f"comes from the single least likely scenario. Read the median instead.[/yellow]"
                )
            for row in sc["scenarios"]:
                if row["was_clamped"]:
                    console.print(f"[dim]  {row['name']}: {row['clamp_reason']}[/dim]")

        rv = d.get("reverse_valuation")
        if rv:
            console.print(Panel.fit(rv["verdict"], title="What today's price already assumes"))

        if d["red_flags"]["flags"]:
            t = Table(title=f"Red flags (score {d['red_flags']['red_flag_score']:.0f}/100)")
            t.add_column("Severity"); t.add_column("Flag"); t.add_column("Detail")
            for f in d["red_flags"]["flags"]:
                colour = {"critical": "red", "high": "yellow",
                          "medium": "cyan", "low": "dim"}.get(f["severity"], "white")
                t.add_row(f"[{colour}]{f['severity']}[/]", f["title"], f["detail"])
            console.print(t)

        if d["signals"]:
            t = Table(title="Detected signals")
            t.add_column("Type"); t.add_column("Strength"); t.add_column("Description")
            for sig in d["signals"][:10]:
                t.add_row(sig["signal_type"], sig["strength"], sig["description"])
            console.print(t)

        th = d.get("thesis")
        if th:
            console.print(Panel.fit(
                th["statement"] + "\n\n" + "\n".join(
                    f"  [{'green' if c['status']=='holding' else 'yellow' if c['status']=='at_risk' else 'red' if c['status']=='broken' else 'dim'}]"
                    f"{c['status']:9s}[/] {c['text']}"
                    for c in th["conditions"]
                ),
                title=f"Thesis ({th['status']})",
            ))

        history = d.get("score_history") or []
        explained = [h for h in history if h.get("change_reason")]
        if explained:
            console.print(Panel.fit(
                "\n".join(f"  {h['at']}  {h['change_reason']}" for h in explained[-4:]),
                title="Why the standing changed",
            ))

        console.print("[dim]Research output. Model estimates under stated assumptions. "
                      "Not investment advice.[/dim]")


@app.command()
def report() -> None:
    """Print the daily research report."""
    from .api.app import daily_report
    with session_scope() as s:
        r = daily_report(db=s)

    console.print(Panel.fit(f"Daily research report - {r['generated_at']}"))
    if r["new_discoveries"]:
        console.print("\n[bold]New discoveries[/bold]")
        for d in r["new_discoveries"]:
            console.print(f"  {d['name']} ({d['sector']}) - {d['verdict']}")
    if r["biggest_movers"]:
        console.print("\n[bold]Biggest rank moves[/bold]")
        for d in r["biggest_movers"]:
            arrow = "up" if d["change"] > 0 else "down"
            console.print(f"  {d['name']}: #{d['previous_rank']} -> #{d['rank']} ({arrow})")
    if r["strongest_signals"]:
        console.print("\n[bold]Strongest signals[/bold]")
        for sig in r["strongest_signals"]:
            console.print(f"  {sig['candidate_name']}: {sig['description']}")
    if r["biggest_red_flags"]:
        console.print("\n[bold]Highest red-flag scores[/bold]")
        for d in r["biggest_red_flags"]:
            console.print(f"  {d['name']}: {d['red_flag_score']:.0f}/100 ({d['verdict']})")
    if r["thesis_invalidations"]:
        console.print("\n[bold red]Thesis invalidations[/bold red]")
        for d in r["thesis_invalidations"]:
            console.print(f"  {d['candidate_name']}: {d['reason']}")
    console.print(f"\n[dim]{r['disclaimer']}[/dim]")


@app.command()
def serve(
    host: str = typer.Option("", help="Defaults to the configured host."),
    port: int = typer.Option(0, help="Defaults to the configured port."),
    reload: bool = typer.Option(False),
) -> None:
    """Start the API server."""
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "asymmetry.api.app:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=reload,
    )


@app.command("ingest-github")
def ingest_github(
    repo: str = typer.Argument(..., help="GitHub repository as owner/name."),
    candidate: str = typer.Option("", help="Attach the series to this candidate."),
) -> None:
    """Pull real weekly commit and contributor history from GitHub.

    Replaces synthetic series with actual developer activity, so acceleration
    detection runs on real data. Note that GitHub serves a rolling 52-week
    window rather than an archive, so this supports live detection but cannot
    support a historical backtest.
    """
    from .core.signals import SignalType, TimeSeriesPoint, detect_acceleration
    from .sources.github_activity import (
        GitHubActivityError,
        activity_to_series,
        fetch_repo_activity,
    )

    try:
        activity = fetch_repo_activity(repo)
    except GitHubActivityError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Could not reach the GitHub API: {exc}[/red]")
        console.print("[dim]Some networks block api.github.com. "
                      "Set GITHUB_TOKEN to raise rate limits.[/dim]")
        raise typer.Exit(1)

    series = activity_to_series(activity)
    console.print(
        f"[green]{activity.full_name}[/green]: {activity.stars:,} stars, "
        f"{len(activity.commit_series)} weeks of commit history."
    )
    if not activity.has_history:
        console.print("[yellow]Too little history to detect acceleration.[/yellow]")
        raise typer.Exit(0)

    for name, points in series.items():
        ts = [TimeSeriesPoint(date.fromisoformat(d), v) for d, v in points]
        signal = detect_acceleration(SignalType(name), ts)
        if signal:
            console.print(f"  [bold]{name}[/bold]: {signal.description}")
        else:
            console.print(f"  [dim]{name}: no acceleration detected[/dim]")

    if candidate:
        with session_scope() as s:
            cand = (
                s.query(m.Candidate)
                .filter((m.Candidate.name.ilike(f"%{candidate}%"))
                        | (m.Candidate.ticker == candidate.upper()))
                .first()
            )
            if cand is None:
                console.print(f"[red]No candidate matching {candidate!r}.[/red]")
                raise typer.Exit(1)
            extra = dict(cand.extra or {})
            extra.setdefault("series", {}).update(series)
            extra["github_repo"] = activity.full_name
            cand.extra = extra
        console.print(f"[green]Attached to {candidate}. Re-run `asymmetry run`.[/green]")


@app.command("second-order")
def second_order(
    driver: str = typer.Argument("AI compute demand", help="Trend to trace upstream from."),
    min_depth: int = typer.Option(2, help="How far from the driver to start looking."),
) -> None:
    """Trace a trend upstream to the unglamorous things it depends on.

    When a trend is obvious, the obvious way to express it is crowded. The
    interesting position is usually several layers upstream, in something the
    trend cannot proceed without.
    """
    from .core.techgraph import TechGraph

    graph = TechGraph()
    if graph.get(driver) is None:
        console.print(f"[red]Unknown node {driver!r}.[/red] Known drivers:")
        for d in graph.to_dict()["drivers"]:
            console.print(f"  - {d}")
        raise typer.Exit(1)

    console.print(Panel.fit(
        "\n".join(" -> ".join(c) for c in graph.chain_from(driver)[:6]),
        title=f"Dependency chains from {driver}",
    ))

    table = Table(title="Second-order candidates (further = less likely to be priced in)")
    for col in ("Depth", "Node", "Bottleneck", "Why"):
        table.add_column(col, justify="right" if col == "Depth" else "left")
    for t in graph.second_order_targets(driver, min_depth=min_depth)[:10]:
        table.add_row(
            str(t["depth"]), t["name"],
            "[yellow]yes[/yellow]" if t["is_bottleneck"] else "-",
            t["description"] or t["category"],
        )
    console.print(table)

    console.print("\n[bold]Discovery queries[/bold]")
    for q in graph.discovery_queries(driver, limit=8):
        console.print(f"  - {q}")


@app.command()
def sources() -> None:
    """List configured sources and what each is trusted for."""
    from .sources import REQUIRES_CREDENTIALS, build_registry

    table = Table(title="Sources")
    for col in ("Name", "Type", "Tier", "Reliability", "Citable as evidence"):
        table.add_column(col)
    for s in build_registry(use_mock=False).all():
        table.add_row(
            s.name, s.source_type, str(int(s.tier)), f"{s.reliability_score:.2f}",
            "yes" if s.tier.is_citable_evidence else "[red]no - discovery only[/red]",
        )
    console.print(table)

    console.print("\n[bold]Not implemented, and why[/bold]")
    for name, why in REQUIRES_CREDENTIALS.items():
        console.print(f"  [cyan]{name}[/cyan]: {why}")


if __name__ == "__main__":
    app()
