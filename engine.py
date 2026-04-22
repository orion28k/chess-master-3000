import os
import chess

from maia.model_loader import load_model_config

MAIA_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_files')


class MaiaGame:
    def __init__(self, elo: int):
        model_dir = os.path.join(MAIA_MODELS_DIR, str(elo))
        self.model, self.config = load_model_config(model_dir)
        self.board = chess.Board()

    def _state(self) -> dict:
        result = None
        if self.board.is_game_over():
            outcome = self.board.outcome()
            result = outcome.result() if outcome else '1/2-1/2'
        return {
            'fen': self.board.fen(),
            'legal_moves': [m.uci() for m in self.board.legal_moves],
            'turn': 'white' if self.board.turn == chess.WHITE else 'black',
            'is_game_over': self.board.is_game_over(),
            'result': result,
        }

    def make_player_move(self, uci: str) -> dict:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            raise ValueError(f"Invalid UCI move: {uci}")
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move: {uci}")
        self.board.push(move)
        return self._state()

    def get_maia_move(self) -> dict:
        move_obj, cp = self.model.getMoveWithCP(self.board)
        self.board.push(move_obj)
        state = self._state()
        state['maia_move'] = move_obj.uci()
        state['maia_cp'] = cp
        return state

    def get_state(self) -> dict:
        return self._state()

    def reset(self):
        self.board = chess.Board()
