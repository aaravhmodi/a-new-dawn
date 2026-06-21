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


app = typer.Typer(help="STAR WARS: A NEW DAWN CLI")
console = Console()
settings = get_settings()


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
    return httpx.Client(base_url=settings.cli_api_base_url, timeout=60.0)


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


@app.command()
def signup(email: str, password: str, handle: str) -> None:
    with _client() as client:
        response = client.post("/auth/signup", json={"email": email, "password": password, "handle": handle})
        response.raise_for_status()
        data = response.json()
        _save_session(data)
    console.print(f"Signed up as {email}.")


@app.command()
def login(email: str, password: str) -> None:
    with _client() as client:
        response = client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        data = response.json()
        _save_session(data)
    console.print(f"Logged in as {email}.")


@app.command("new-campaign")
def new_campaign(player_class: str = "smuggler", era: str = "galactic_civil_war", planet: str = "corellia") -> None:
    with _client() as client:
        response = client.post(
            "/campaigns",
            json={"player_class": player_class, "era": era, "planet": planet},
            headers=_headers(),
        )
        response.raise_for_status()
        campaign = response.json()
        _print_opening(campaign["story_arc"].get("opening_crawl", ""))

        scene_response = client.get(f"/campaigns/{campaign['campaign_id']}/current-scene", headers=_headers())
        scene_response.raise_for_status()
        scene = scene_response.json()

    session = _load_session()
    session["campaign_id"] = campaign["campaign_id"]
    _save_session(session)
    _render_scene(scene)


@app.command()
def play() -> None:
    session = _load_session()
    campaign_id = session.get("campaign_id")
    if not campaign_id:
        raise typer.BadParameter("No campaign stored. Run new-campaign first.")

    with _client() as client:
        scene_response = client.get(f"/campaigns/{campaign_id}/current-scene", headers=_headers())
        scene_response.raise_for_status()
        scene = scene_response.json()

        while scene:
            _render_scene(scene)
            choice_index = typer.prompt("Choose an option", type=int)
            if choice_index < 1 or choice_index > len(scene["choices"]):
                raise typer.BadParameter("Choice out of range.")

            selected = scene["choices"][choice_index - 1]
            result_response = client.post(
                f"/campaigns/{campaign_id}/choose",
                json={"choice_key": selected["choice_key"]},
                headers=_headers(),
            )
            result_response.raise_for_status()
            result = result_response.json()
            console.print(Panel.fit(result["resolution_text"], border_style="green"))
            scene = result["next_scene"]

    console.print("[bold green]Campaign segment complete.[/bold green]")
