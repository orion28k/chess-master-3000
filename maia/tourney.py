import chess
import chess.engine
import subprocess
import os

_lc0Path = 'lc0'
_movetime = 10000


def cpToInt(cpVal):
    if cpVal.is_mate():
        return -1000 if cpVal.relative.mate() < 0 else 1000
    return int(cpVal.relative.cp)


class TourneyEngine:
    def __init__(self, engine, name, movetime=None, nodes=None, depth=None):
        self.engine = engine
        self.name = f"{type(self).__name__} {name}"
        self.limits = chess.engine.Limit(time=movetime, depth=depth, nodes=nodes)

    def __repr__(self):
        return f"<{self.name}>"

    def __str__(self):
        return self.name

    def getMoveWithCP(self, board):
        result = self.getResults(board)
        try:
            cp = cpToInt(result.info['score'])
        except KeyError:
            cp = 0
        return result.move, cp

    def getMove(self, board):
        return self.getResults(board).move

    def getResults(self, board):
        return self.engine.play(board, self.limits, game=board, info=chess.engine.INFO_ALL)

    def getTopMovesCP(self, board, num_moves):
        results = self.engine.analyse(board, self.limits, info=chess.engine.INFO_ALL, multipv=num_moves)
        ret = []
        for m_dict in results:
            cp = cpToInt(m_dict['score']) if 'score' in m_dict else 0
            ret.append((m_dict['pv'][0].uci(), cp))
        return ret

    def __del__(self):
        try:
            self.engine.quit()
        except Exception:
            pass


class LC0Engine(TourneyEngine):
    def __init__(self, weightsPath=None, nodes=None, movetime=_movetime,
                 lc0Path=None, threads=1, backend='blas', backend_opts='',
                 name=None, noise=False, temperature=0, temp_decay=0,
                 extra_flags=None, verbose=False, **kwargs):
        self.weightsPath = weightsPath
        lc0 = lc0Path if lc0Path is not None else _lc0Path

        cmd = [
            lc0,
            f'--weights={weightsPath}',
            f'--threads={threads}',
            f'--backend={backend}',
            f'--backend-opts={backend_opts}',
            f'--temperature={temperature}',
            f'--tempdecay-moves={temp_decay}',
        ]
        if noise:
            cmd.append('--noise')
        if isinstance(noise, float):
            cmd.append(f'--noise-epsilon={noise}')
        if verbose:
            cmd.append('--verbose-move-stats')
        if extra_flags:
            cmd.extend(extra_flags)

        engine = chess.engine.SimpleEngine.popen_uci(cmd, stderr=subprocess.DEVNULL)

        if name is None:
            name = os.path.basename(weightsPath)
        super().__init__(engine, name, movetime=movetime, nodes=nodes)


class RandomEngine(TourneyEngine):
    import random as _random

    def __init__(self, **kwargs):
        import random

        class _Backend:
            def play(self, board, *a, **kw):
                return random.choice(list(board.legal_moves))
            def quit(self):
                pass

        super().__init__(_Backend(), 'random', movetime=None, nodes=None)

    def getMoveWithCP(self, board):
        return self.engine.play(board), 0

    def getMove(self, board):
        return self.engine.play(board)


class StockfishEngine(TourneyEngine):
    def __init__(self, sfPath='stockfish', movetime=_movetime, depth=30, name=None, **kwargs):
        engine = chess.engine.SimpleEngine.popen_uci([sfPath], stderr=subprocess.PIPE)
        engine.configure({'UCI_AnalyseMode': 'false'})
        super().__init__(engine, name or f'd{depth}', movetime=movetime, depth=depth)
