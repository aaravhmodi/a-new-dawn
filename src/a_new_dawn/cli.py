from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from a_new_dawn.content import OPENING_LINE, TITLE_CARD
from a_new_dawn.settings import get_settings
from a_new_dawn.supabase_store import SupabaseStore


app = typer.Typer(help="STAR WARS: A NEW DAWN CLI")
console = Console()
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


def _render_scene(scene: dict[str, Any]) -> None:
    console.print(Panel.fit(f"[bold]{scene['title']}[/bold]\n\n{scene['narration']}"))
    stats = Table(title="Stats")
    stats.add_column("Health")
    stats.add_column("Credits")
    stats.add_column("Light")
    stats.add_column("Dark")
    stats.add_column("Independent")
    info = scene["stats"]
    stats.add_row(
        f"{info['health']}/{info['max_health']}",
        str(info["credits"]),
        str(info["light_score"]),
        str(info["dark_score"]),
        str(info["independent_score"]),
    )
    console.print(stats)

    choices = Table(title=f"Episode {scene['episode_number']} Choices")
    choices.add_column("#")
    choices.add_column("Action")
    choices.add_column("Description")
    for index, choice in enumerate(scene["choices"], start=1):
        choices.add_row(str(index), choice["label"], choice.get("description") or "")
    console.print(choices)


def _play_scene_loop(client: httpx.Client, campaign_id: str, scene: dict[str, Any]) -> None:
    current_scene = scene
    while current_scene:
        _render_scene(current_scene)
        choice_index = typer.prompt(f"Choose an option (1-{len(current_scene['choices'])})", type=int)
        if choice_index < 1 or choice_index > len(current_scene["choices"]):
            raise typer.BadParameter("Choice out of range.")

        selected = current_scene["choices"][choice_index - 1]
        result_response = client.post(
            f"/campaigns/{campaign_id}/choose",
            json={"choice_key": selected["choice_key"]},
            headers=_headers(),
        )
        _raise_with_detail(result_response)
        result = result_response.json()
        console.print(Panel.fit(result["resolution_text"], border_style="green"))
        current_scene = result["next_scene"]

    console.print("[bold green]Campaign segment complete.[/bold green]")


def _check(name: str, ok: bool, detail: str) -> tuple[str, str, str]:
    return (name, "[green]ok[/green]" if ok else "[red]fail[/red]", detail)


def _raise_with_detail(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text.strip() or str(exc)
        raise typer.BadParameter(f"{response.status_code} response from backend: {detail}") from exc


@app.command()
def signup(email: str, password: str, handle: str) -> None:
    with _client() as client:
        response = client.post("/auth/signup", json={"email": email, "password": password, "handle": handle})
        _raise_with_detail(response)
        data = response.json()
        _save_session(data)
    console.print(f"Signed up as {email}.")


@app.command()
def login(email: str, password: str) -> None:
    with _client() as client:
        response = client.post("/auth/login", json={"email": email, "password": password})
        _raise_with_detail(response)
        data = response.json()
        _save_session(data)
    console.print(f"Logged in as {email}.")


@app.command("new-campaign")
def new_campaign(
    player_class: str = typer.Option("smuggler", "--player-class", hidden=True),
    era: str = typer.Option("galactic_civil_war", "--era", hidden=True),
    planet: str = typer.Option("corellia", "--planet", hidden=True),
) -> None:
    console.print(f"[bold blue]{OPENING_LINE}[/bold blue]")
    time.sleep(1.0)
    console.print(Panel.fit(TITLE_CARD, border_style="yellow"))
    console.print("[yellow]Preparing Episode I...[/yellow]")
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


@app.command()
def play() -> None:
    session = _load_session()
    campaign_id = session.get("campaign_id")
    if not campaign_id:
        raise typer.BadParameter("No campaign stored. Run new-campaign first.")

    with _client() as client:
        scene_response = client.get(f"/campaigns/{campaign_id}/current-scene", headers=_headers())
        _raise_with_detail(scene_response)
        scene = scene_response.json()
        _play_scene_loop(client, campaign_id, scene)


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
