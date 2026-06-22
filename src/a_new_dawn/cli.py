from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from a_new_dawn.content import OPENING_LINE, TITLE_CARD
from a_new_dawn.settings import get_settings
from a_new_dawn.supabase_store import SupabaseStore


app = typer.Typer(help="STAR WARS: A NEW DAWN — a choice-driven CLI RPG.", invoke_without_command=True)
console = Console()


@app.callback()
def _root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print(Panel(
            "[bold yellow]STAR WARS: A NEW DAWN[/bold yellow]\n\n"
            "A choice-driven espionage RPG set in the Galactic Empire.\n\n"
            "[bold]Getting started:[/bold]\n\n"
            "  1. Create an account:\n"
            "     [cyan]a-new-dawn signup <email> <password> <username>[/cyan]\n\n"
            "  2. Or log in if you have one:\n"
            "     [cyan]a-new-dawn login <email> <password>[/cyan]\n\n"
            "  3. Start a new campaign:\n"
            "     [cyan]a-new-dawn new-campaign[/cyan]\n\n"
            "  4. Resume where you left off:\n"
            "     [cyan]a-new-dawn play[/cyan]\n\n"
            "  5. See all commands:\n"
            "     [cyan]a-new-dawn --help[/cyan]",
            title="Welcome",
            border_style="yellow",
            padding=(1, 2),
        ))
settings = get_settings()
store = SupabaseStore()


def _session_file() -> Path:
    path = settings.cli_state_file
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_session(payload: dict[str, Any]) -> None:
    _session_file().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_session() -> dict[str, Any]:
    path = _session_file()
    if not path.exists():
        raise typer.BadParameter("No CLI session found. Run signup or login first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.cli_api_base_url, timeout=180.0)


def _headers() -> dict[str, str]:
    session = _load_session()
    token = session.get("access_token")
    if not token:
        raise typer.BadParameter("No access token found. Run login again.")
    return {"Authorization": f"Bearer {token}"}


def _print_opening(crawl_text: str) -> None:
    console.print(f"[bold blue]{OPENING_LINE}[/bold blue]")
    time.sleep(1.0)
    console.print(Panel.fit(TITLE_CARD, border_style="yellow"))
    time.sleep(1.0)
    for paragraph in crawl_text.split("\n\n"):
        console.print(paragraph.strip(), style="yellow")
        console.print()
        time.sleep(0.8)


def _print_how_to_play() -> None:
    console.print(
        Panel.fit(
            "\n".join(
                [
                    "[bold]How to play[/bold]",
                    "",
                    "1. Read the scene.",
                    "2. Type the number of the choice you want.",
                    "3. Press Enter.",
                    "4. Watch the story, stats, and relationships change.",
                    "",
                    "Tip: some scenes are special action scenes. Those show Heat, Cover, and Intel.",
                    "Your choices matter. They change the ending.",
                ]
            ),
            border_style="cyan",
        )
    )


def _bar(value: int, max_val: int, width: int, color: str, empty_color: str = "grey30") -> Text:
    filled = int((value / max_val) * width)
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * (width - filled), style=empty_color)
    return bar


def _render_set_piece(scene_state: dict[str, Any]) -> None:
    heat = scene_state.get("heat", 0)
    cover = scene_state.get("cover", 0)
    intel = scene_state.get("intel", 0)
    beat_title = scene_state.get("beat_title", "Action")

    heat_color = "bright_red" if heat >= 4 else "yellow" if heat >= 2 else "red"
    cover_color = "bright_green" if cover >= 3 else "yellow" if cover >= 1 else "red"

    danger = heat >= 4 or cover <= 0
    border = "bright_red" if danger else "yellow"
    warning = "\n[bold bright_red]⚠  COVER BLOWN — GET OUT[/bold bright_red]" if cover <= 0 else \
              "\n[bold yellow]⚠  HEAT CRITICAL[/bold yellow]" if heat >= 4 else ""

    heat_bar = _bar(heat, 5, 20, heat_color)
    cover_bar = _bar(cover, 4, 20, cover_color)
    intel_bar = _bar(intel, 3, 20, "cyan")

    content = Text()
    content.append(f"  HEAT   ", style="bold red")
    content.append_text(heat_bar)
    content.append(f"  {heat}/5\n")
    content.append(f"  COVER  ", style="bold green")
    content.append_text(cover_bar)
    content.append(f"  {cover}/4\n")
    content.append(f"  INTEL  ", style="bold cyan")
    content.append_text(intel_bar)
    content.append(f"  {intel}/3")
    if warning:
        content.append(warning)

    console.print(Rule(f"[bold]{beat_title}[/bold]", style=border))
    console.print(Panel(content, border_style=border, padding=(0, 1)))


def _render_scene(scene: dict[str, Any]) -> None:
    console.print(Panel.fit(f"[bold]{scene['title']}[/bold]\n\n{scene['narration']}"))
    scene_state = scene.get("scene_state")
    if scene_state and scene_state.get("mode") == "set_piece":
        _render_set_piece(scene_state)

    info = scene["stats"]
    hp_pct = info["health"] / info["max_health"]
    hp_color = "bright_green" if hp_pct > 0.6 else "yellow" if hp_pct > 0.3 else "bright_red"
    stats = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
    stats.add_column("HP", style=hp_color)
    stats.add_column("Credits", style="yellow")
    stats.add_column("Light", style="bright_cyan")
    stats.add_column("Dark", style="magenta")
    stats.add_column("Independent", style="white")
    stats.add_row(
        f"{info['health']}/{info['max_health']}",
        f"₹{info['credits']}",
        f"◈ {info['light_score']}",
        f"◈ {info['dark_score']}",
        f"◈ {info['independent_score']}",
    )
    console.print(stats)
    console.print()

    from rich import box as rich_box
    choices = Table(show_header=True, header_style="bold", box=rich_box.ROUNDED, padding=(0, 1), border_style="cyan")
    choices.add_column("[dim]#[/dim]", style="dim", width=3)
    choices.add_column("Action", style="bold white")
    choices.add_column("Description", style="dim")
    for index, choice in enumerate(scene["choices"], start=1):
        choices.add_row(f"[bold cyan]{index}[/bold cyan]", choice["label"], choice.get("description") or "")
    console.print(choices)


def _handle_connect_error(exc: Exception) -> None:
    raise typer.BadParameter("Could not reach the server. Check your connection or try again shortly.") from exc


def _play_scene_loop(client: httpx.Client, campaign_id: str, scene: dict[str, Any]) -> None:
    current_scene = scene
    while current_scene:
        _render_scene(current_scene)
        console.print("[dim]Choose the number of the option you want, then press Enter.[/dim]")
        n = len(current_scene["choices"])
        while True:
            try:
                choice_index = typer.prompt(f"Choose an option (1-{n})", type=int)
                if 1 <= choice_index <= n:
                    break
                console.print(f"[red]Enter a number between 1 and {n}.[/red]")
            except (ValueError, typer.BadParameter):
                console.print("[red]Please enter a valid number.[/red]")

        selected = current_scene["choices"][choice_index - 1]
        with console.status("[bold yellow]Transmitting to Imperial relay...[/bold yellow]", spinner="dots"):
            result_response = client.post(
                f"/campaigns/{campaign_id}/choose",
                json={"choice_key": selected["choice_key"]},
                headers=_headers(),
            )
        _raise_with_detail(result_response)
        result = result_response.json()
        console.print(Rule(style="green dim"))
        console.print(Panel.fit(f"[italic]{result['resolution_text']}[/italic]", border_style="green", padding=(1, 2)))
        if result.get("ending_title"):
            ending_text = result.get("ending_summary") or ""
            console.print()
            console.print(Rule("[bold magenta]— EPISODE COMPLETE —[/bold magenta]", style="magenta"))
            console.print()
            time.sleep(1.0)
            console.print(Panel(
                f"[bold magenta]{result['ending_title']}[/bold magenta]\n\n{ending_text}",
                border_style="magenta",
                padding=(1, 3),
            ))
        next_scene = result["next_scene"]
        current_scene = next_scene if next_scene and next_scene.get("choices") else None

    console.print(Rule(style="dim"))
    console.print("[bold green]Campaign segment complete.[/bold green]")


def _check(name: str, ok: bool, detail: str) -> tuple[str, str, str]:
    return (name, "[green]ok[/green]" if ok else "[red]fail[/red]", detail)


def _friendly_error(status: int, raw: str) -> str:
    if status == 401:
        return "You're not logged in or your session expired. Run: a-new-dawn login <email> <password>"
    if status == 403:
        return "Access denied. Run: a-new-dawn login <email> <password>"
    if status == 404:
        return "Not found. Try starting a new campaign: a-new-dawn new-campaign"
    if status == 400:
        if "invalid_credentials" in raw or "invalid login" in raw.lower():
            return "Wrong email or password. Please try again."
        if "already" in raw.lower():
            return "An account with that email already exists. Try logging in instead."
    if status >= 500:
        return "The server hit an error. Please try again in a moment."
    return raw


def _raise_with_detail(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raw = response.text.strip() or str(exc)
        raise typer.BadParameter(_friendly_error(response.status_code, raw)) from exc


@app.command()
def signup(email: str, password: str, handle: str) -> None:
    try:
        with _client() as client:
            response = client.post("/auth/signup", json={"email": email, "password": password, "handle": handle})
            _raise_with_detail(response)
            data = response.json()
            _save_session(data)
        console.print(f"[green]Account created. Welcome, {handle}![/green]")
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _handle_connect_error(exc)


@app.command()
def login(email: str, password: str) -> None:
    try:
        with _client() as client:
            response = client.post("/auth/login", json={"email": email, "password": password})
            _raise_with_detail(response)
            data = response.json()
            _save_session(data)
        console.print(f"[green]Logged in as {email}.[/green]")
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _handle_connect_error(exc)


@app.command("new-campaign")
def new_campaign(
    player_class: str = typer.Option("smuggler", "--player-class", hidden=True),
    era: str = typer.Option("galactic_civil_war", "--era", hidden=True),
    planet: str = typer.Option("corellia", "--planet", hidden=True),
) -> None:
    _print_how_to_play()
    console.print(f"[bold blue]{OPENING_LINE}[/bold blue]")
    time.sleep(1.0)
    console.print(Panel.fit(TITLE_CARD, border_style="yellow"))
    console.print("[yellow]Preparing Episode I...[/yellow]")
    try:
        with _client() as client:
            response = client.post(
                "/campaigns",
                json={"player_class": player_class, "era": era, "planet": planet},
                headers=_headers(),
            )
            _raise_with_detail(response)
            campaign = response.json()
            for paragraph in campaign["story_arc"].get("opening_crawl", "").split("\n\n"):
                console.print(paragraph.strip(), style="yellow")
                console.print()
                time.sleep(0.8)

            scene_response = client.get(f"/campaigns/{campaign['campaign_id']}/current-scene", headers=_headers())
            _raise_with_detail(scene_response)
            scene = scene_response.json()

            session = _load_session()
            session["campaign_id"] = campaign["campaign_id"]
            _save_session(session)
            _play_scene_loop(client, campaign["campaign_id"], scene)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _handle_connect_error(exc)


@app.command()
def play() -> None:
    session = _load_session()
    campaign_id = session.get("campaign_id")
    if not campaign_id:
        raise typer.BadParameter("No campaign stored. Run new-campaign first.")

    _print_how_to_play()
    try:
        with _client() as client:
            scene_response = client.get(f"/campaigns/{campaign_id}/current-scene", headers=_headers())
            _raise_with_detail(scene_response)
            scene = scene_response.json()
            _play_scene_loop(client, campaign_id, scene)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _handle_connect_error(exc)


@app.command("guide")
def guide() -> None:
    _print_how_to_play()
    console.print("[dim]Start a campaign with: a-new-dawn new-campaign[/dim]")


@app.command()
def doctor() -> None:
    results: list[tuple[str, str, str]] = []
    cfg = settings

    results.append(_check("SUPABASE_URL", bool(cfg.supabase_url), cfg.supabase_url or "missing"))
    results.append(
        _check(
            "SUPABASE_PUBLISHABLE_KEY",
            bool(cfg.resolved_publishable_key),
            "set" if cfg.resolved_publishable_key else "missing",
        )
    )
    results.append(
        _check(
            "SUPABASE_SERVER_KEY",
            bool(cfg.resolved_server_key),
            "set" if cfg.resolved_server_key else "missing",
        )
    )
    results.append(_check("LLM_PROVIDER", bool(cfg.llm_provider), cfg.llm_provider))

    try:
        store.healthcheck_rest()
        results.append(_check("Supabase REST", True, "reachable"))
    except Exception as exc:
        results.append(_check("Supabase REST", False, str(exc)))

    try:
        response = httpx.get(cfg.resolved_supabase_jwks_url, timeout=15.0)
        response.raise_for_status()
        keys = response.json().get("keys", [])
        results.append(_check("Supabase JWKS", True, f"{len(keys)} keys"))
    except Exception as exc:
        results.append(_check("Supabase JWKS", False, str(exc)))

    provider = cfg.llm_provider.lower()
    try:
        if provider == "gemini":
            response = httpx.post(
                f"{cfg.gemini_base_url}/models/{cfg.gemini_model}:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": cfg.gemini_api_key or "",
                },
                json={"contents": [{"parts": [{"text": "Reply with the single word OK."}]}]},
                timeout=30.0,
            )
            response.raise_for_status()
            results.append(_check("Gemini", True, cfg.gemini_model))
        elif provider == "ollama":
            response = httpx.get(f"{cfg.ollama_base_url[:-4]}/api/tags" if cfg.ollama_base_url.endswith("/api") else f"{cfg.ollama_base_url}/tags", timeout=15.0)
            response.raise_for_status()
            results.append(_check("Ollama", True, cfg.ollama_model))
        elif provider == "modelrelay":
            response = httpx.get(f"{cfg.modelrelay_base_url}/models", timeout=15.0)
            response.raise_for_status()
            results.append(_check("ModelRelay", True, cfg.modelrelay_model))
        else:
            if not cfg.openai_api_key:
                raise ValueError("OPENAI_API_KEY missing")
            results.append(_check("OpenAI", True, cfg.openai_model))
    except Exception as exc:
        results.append(_check(provider.title(), False, str(exc)))

    table = Table(title="A New Dawn Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for row in results:
        table.add_row(*row)
    console.print(table)
