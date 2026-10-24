"""High Scores & Star Rating System: Handles scoring rules, progression, and disk persistence.

Ratings:
- 0 Stars: Level lost (count <= 0).
- 1 Star:  Level won.
- 2 Stars: Level won with crowd >= 25% of the theoretical maximum (best_count).
- 3 Stars: Level won with crowd >= 50% of the theoretical maximum (best_count).
"""
import json
from pathlib import Path

# Local file path for saving player high scores and unlocked progress
SCORE_FILE = Path(__file__).parent / "highscores.json"

# Threshold fractions of theoretical maximum crowd needed for 2 and 3 stars
TWO_STAR = 0.25      # >= 25% of best_count earns 2 stars
THREE_STAR = 0.50    # >= 50% of best_count earns 3 stars


def stars(won, count, best):
    """Calculate the number of stars earned (0 to 3) for a level attempt.

    Args:
        won (bool): Whether the level was successfully completed.
        count (int): Final crowd count at finish.
        best (int): Theoretical maximum crowd possible for this level.

    Returns:
        int: Star rating from 0 to 3.
    """
    if not won or count <= 0:
        return 0
    if best <= 0:
        return 1
    ratio = count / best
    if ratio >= THREE_STAR:
        return 3
    if ratio >= TWO_STAR:
        return 2
    return 1


def load_scores(path=None):
    """Load score records from disk.

    Args:
        path (Path | str | None): Optional custom file path. Defaults to SCORE_FILE.

    Returns:
        dict: Mapping of level filename -> {"count": int, "stars": int}.
              Returns empty dict if file is missing or corrupted.
    """
    try:
        with open(path or SCORE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record(level_file, count, star_count, path=None):
    """Save high score if the new count exceeds the previous record.

    Args:
        level_file (str): Filename of the completed level.
        count (int): Final crowd count achieved.
        star_count (int): Number of stars earned in this run.
        path (Path | str | None): Optional custom score file path.

    Returns:
        bool: True if this run set a new high score record; False otherwise.
    """
    scores = load_scores(path)
    old = scores.get(level_file, {"count": 0, "stars": 0})
    if count <= old.get("count", 0):
        return False
    scores[level_file] = {"count": count, "stars": max(star_count, old.get("stars", 0))}
    try:
        with open(path or SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass  # If file cannot be written (e.g. read-only env), game continues gracefully
    return True


def is_unlocked(level_files, i, scores):
    """Check standard progression unlocking condition.

    Level 0 is always unlocked. Subsequent levels require winning the preceding level.

    Args:
        level_files (list[str]): Ordered list of all level filenames.
        i (int): Index of the level to test.
        scores (dict): Loaded scores dictionary.

    Returns:
        bool: True if level is unlocked; False if locked.
    """
    return i == 0 or level_files[i - 1] in scores


def is_level_unlocked(level_files, i, scores, unlock_all=False):
    """Check whether a level is unlocked, factoring in the debug/presentation override.

    Args:
        level_files (list[str]): Ordered list of level filenames.
        i (int): Level index.
        scores (dict): Scores dictionary.
        unlock_all (bool): Debug flag (toggled with 'U' key) to unlock all levels.

    Returns:
        bool: True if playable.
    """
    if i >= len(level_files):
        return False
    return unlock_all or is_unlocked(level_files, i, scores)


def next_unlocked_level(level_files, current, step, scores, unlock_all=False):
    """Find the next unlocked level index when navigating menus with keys.

    Skips locked levels and wraps around cyclically.

    Args:
        level_files (list[str]): Ordered list of level filenames.
        current (int): Currently selected index.
        step (int): Navigation direction (+1 for down/next, -1 for up/previous).
        scores (dict): Scores dictionary.
        unlock_all (bool): Debug unlock override.

    Returns:
        int: Next playable level index.
    """
    n = len(level_files)
    if n == 0:
        return 0
    idx = current
    for _ in range(n):
        idx = (idx + step) % n
        if is_level_unlocked(level_files, idx, scores, unlock_all):
            return idx
    return current


def finish_level_result(level_file, won, count, best, current_scores):
    """Calculate endgame results, update saved records, and return refreshed state.

    Args:
        level_file (str): Filename of the level just played.
        won (bool): True if level was won; False if crowd died.
        count (int): Final crowd count.
        best (int): Theoretical best crowd count for the level.
        current_scores (dict): Existing scores dictionary.

    Returns:
        tuple[tuple, dict]:
            - result: (star_count, old_record, new_record_flag)
            - updated_scores: Refreshed dictionary from disk.
    """
    star_count = stars(won, count, best)
    old = current_scores.get(level_file)
    new_record = won and record(level_file, count, star_count)
    updated_scores = load_scores()
    result = (star_count, old, new_record)
    return result, updated_scores
