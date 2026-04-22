import random
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine import MaiaGame

app = FastAPI()

sessions: Dict[str, dict] = {}  # session_id -> {game, player_color}


class NewGameRequest(BaseModel):
    elo: int
    player_color: str  # "white", "black", "random"


class MoveRequest(BaseModel):
    session_id: str
    move: str  # UCI format


@app.post("/api/new_game")
def new_game(req: NewGameRequest):
    valid_elos = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    if req.elo not in valid_elos:
        raise HTTPException(400, f"ELO must be one of {valid_elos}")

    color = req.player_color
    if color == "random":
        color = random.choice(["white", "black"])
    if color not in ("white", "black"):
        raise HTTPException(400, "player_color must be 'white', 'black', or 'random'")

    game = MaiaGame(req.elo)
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"game": game, "player_color": color}

    state = game.get_state()
    state["session_id"] = session_id
    state["player_color"] = color
    return state


@app.post("/api/move")
def make_move(req: MoveRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    game: MaiaGame = session["game"]
    player_color = session["player_color"]

    if game.board.is_game_over():
        raise HTTPException(400, "Game is already over")

    try:
        state = game.make_player_move(req.move)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Maia responds if game not over and it's now Maia's turn
    if not state["is_game_over"]:
        maia_turn = "black" if player_color == "white" else "white"
        if state["turn"] == maia_turn:
            state = game.get_maia_move()

    state["player_color"] = player_color
    return state


@app.get("/api/state/{session_id}")
def get_state(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    state = session["game"].get_state()
    state["player_color"] = session["player_color"]
    return state


@app.post("/api/maia_move/{session_id}")
def maia_move(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    game: MaiaGame = session["game"]
    if game.board.is_game_over():
        raise HTTPException(400, "Game is already over")
    state = game.get_maia_move()
    state["player_color"] = session["player_color"]
    return state


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
