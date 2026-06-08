"""Game runner. Normally launched via `play.py` at the project root, which
also takes care of using the project's virtual environment."""

import datetime
import importlib
import os
import sys

# agents_config.py and agents/ live at the project root, one level up from
# engine/ — add it to sys.path so they can be imported from here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agents_config
import config
import game as _game
import history as _history
import interface as _iface
import viewer

def run_game(verbose: bool = True, history_path: str | None = None) -> tuple:
    """Run a full game and return (score_player0, score_player1).

    If history_path is given, write a JSON history file there.
    Pass history_path='' to auto-generate a timestamped filename.
    """
    # Each player gets its own Agent instance — even when both PLAYER*_AGENT
    # paths name the same module (the cached module object would otherwise be
    # shared), each instance has its own `self` for per-player memory.
    agent0 = importlib.import_module(agents_config.PLAYER0_AGENT).Agent()
    agent1 = importlib.import_module(agents_config.PLAYER1_AGENT).Agent()
    agents = [agent0, agent1]

    state  = _game.GameState()
    frames = [_history.snapshot(state)]   # frame 0: initial state

    if verbose:
        print(f"Game start  —  {config.TOTAL_TICKS} ticks  ({config.GAME_DURATION} s)")
        print(f"  Player 0: {agents_config.PLAYER0_AGENT}")
        print(f"  Player 1: {agents_config.PLAYER1_AGENT}")
        print()

    for tick in range(config.TOTAL_TICKS):
        for player_id in (0, 1):
            ctx = _iface._Context(state, player_id)
            _iface._context = ctx
            try:
                agents[player_id].make_decision()
            except _iface.ActionError as exc:
                if verbose:
                    print(f"[tick {tick:5d}] player {player_id} called two actions: {exc}")
            except _game.GameError as exc:
                if verbose:
                    print(f"[tick {tick:5d}] player {player_id} invalid action: {exc}")
            except Exception as exc:
                if verbose:
                    print(f"[tick {tick:5d}] player {player_id} unhandled exception: {exc}")
            finally:
                _iface._context = None

        state.tick += 1
        frames.append(_history.snapshot(state))

    scores = _game.compute_scores(state)

    if history_path is not None:
        if history_path == "":
            stamp        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = f"history_{stamp}.json"
        _history.save(frames, state.map, history_path)
        if verbose:
            print(f"History saved → {history_path}  ({len(frames)} frames)")

    if verbose:
        p0, p1 = scores
        print(f"Game over after {config.TOTAL_TICKS} ticks.")
        print(f"  Player 0: {p0} pts")
        print(f"  Player 1: {p1} pts")
        if p0 > p1:
            print("  → Player 0 wins!")
        elif p1 > p0:
            print("  → Player 1 wins!")
        else:
            print("  → Tie!")

    return scores


SAVED_GAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_games")

if __name__ == "__main__":
    verbose      = "--quiet" not in sys.argv
    if "--save" in sys.argv or "--view" in sys.argv:
        os.makedirs(SAVED_GAMES_DIR, exist_ok=True)
        stamp        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        history_path = os.path.join(SAVED_GAMES_DIR, f"history_{stamp}.json")
    else:
        history_path = None
    run_game(verbose=verbose, history_path=history_path)
    if "--view" in sys.argv:
        viewer.view_past_game(history_path)
    
