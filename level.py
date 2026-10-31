"""Level Loading and Track Object Management: Parses JSON levels and updates track entities."""
import json
import random
import re
from pathlib import Path
import pygame

import config as C
from gate import GatePair
from obstacle import Obstacle
from enemy import EnemyGroup

# Default directory path containing level JSON files (level1.json, level2.json, ...)
LEVEL_DIR = Path(__file__).parent / "levels"


def set_level_dir(path):
    """Set custom level directory path (useful for testing or procedural level folders).

    Args:
        path (Path | str): Path to the level directory.
    """
    global LEVEL_DIR
    LEVEL_DIR = Path(path)


class Level:
    """Represents a loaded level, containing track configuration, objects, and theme."""

    def __init__(self, name, start_count, speed, finish_z, objects, theme="plains", boss=None):
        """Initialize level data.

        Args:
            name (str): Display name of the level (e.g. 'Level 1').
            start_count (int): Starting number of runners.
            speed (float): Constant forward running speed in world units per second.
            finish_z (float): Track finish line distance in world units.
            objects (list): List of level objects (GatePair, Obstacle, EnemyGroup) sorted by Z.
            theme (str): Background visual theme ('plains', 'desert', 'jungle').
            boss (str | None): Boss type identifier for this stage ('scorpion', 'plant', or None).
        """
        self.name = name
        self.start_count = start_count
        self.speed = speed
        self.finish_z = finish_z
        self.objects = objects
        self.theme = theme
        self.boss = boss

    def check_reach(self, crowd, next_index):
        """Check if the crowd has crossed any oncoming track objects and trigger on_reach.

        Uses >= check to handle variable dt frame jumps without tunneling through objects.

        Args:
            crowd (Crowd): Active player crowd.
            next_index (int): Index of the next unreached object in self.objects.

        Returns:
            int: Updated next_index.
        """
        while next_index < len(self.objects) and crowd.z >= self.objects[next_index].z:
            self.objects[next_index].on_reach(crowd)
            next_index += 1
        return next_index

    def update_objects(self, dt, crowd):
        """Update physics and logic for all active objects in this level.

        Args:
            dt (float): Delta time in seconds.
            crowd (Crowd): Player crowd instance passed to enemies for homing/chase AI.
        """
        obstacles = [o for o in self.objects if hasattr(o, "on_reach_enemy")]
        for obj in self.objects:
            if isinstance(obj, EnemyGroup):
                obj.update(dt, crowd=crowd, obstacles=obstacles)
            else:
                obj.update(dt)

    def draw_objects(self, screen, camera, font):
        """Render track objects sorted back-to-front (painter's algorithm).

        Args:
            screen (pygame.Surface): Display surface.
            camera (Camera): Active camera for projection.
            font (pygame.font.Font): Font instance for label rendering.
        """
        for obj in sorted(self.objects, key=lambda o: -o.z):
            obj.draw(screen, camera, font)

    def draw_finish_line(self, screen, camera):
        """Render the checkered finish line stripe across the road for non-boss levels.

        Args:
            screen (pygame.Surface): Display surface.
            camera (Camera): Active camera.
        """
        if camera.visible(self.finish_z):
            line_w = C.ROAD_HALF_W
            x1, y, s = camera.project(-line_w, self.finish_z)
            x2, _, _ = camera.project(line_w, self.finish_z)
            pygame.draw.line(screen, C.FINISH_COLOR, (x1, y), (x2, y), max(2, int(12 * s)))


def _get_decimals(val):
    """Get the number of decimal places in a float or string representation."""
    s = str(val)
    if "." in s:
        part = s.rstrip("0").split(".")[1]
        return len(part)
    return 0


def resolve_val(v):
    """Resolve a value from JSON which can be a number, dict, list/range, or string expression.

    Supported formats:
    - Dict with 'min' and 'max': {"type": "random", "min": 10, "max": 15} or {"min": 0.1, "max": 2}
    - Dict with 'range' or 'random': {"range": [10, 30]} or {"random": [10, 30]}
    - Dict with choices: {"choices": [2, 3, 5]} or {"choice": [2, 3, 5]}
    - List of 2 numbers: [10, 20] -> random range
    - List of > 2 numbers: [10, 20, 30] -> random choice
    - Strings: "random(10, 30)", "10..30", "10-30", "10 to 30"
    - Standard numeric types: int or float
    """
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v) if isinstance(v, int) or v.is_integer() else v
    if isinstance(v, dict):
        if "min" in v and "max" in v:
            low = resolve_val(v["min"])
            high = resolve_val(v["max"])
            low, high = min(low, high), max(low, high)
            step = v.get("step")
            if step is not None:
                step = float(resolve_val(step))
                if step > 0:
                    steps = int(round((high - low) / step))
                    val = low + random.randint(0, steps) * step
                    dec = _get_decimals(step)
                    val = round(val, dec)
                    return int(val) if isinstance(val, (int, float)) and val.is_integer() else val
            is_float = isinstance(low, float) or isinstance(high, float)
            if is_float:
                dec = max(_get_decimals(low), _get_decimals(high), 1)
                val = round(random.uniform(low, high), dec)
                return int(val) if val.is_integer() else val
            else:
                return random.randint(int(low), int(high))
        if "range" in v:
            return resolve_val(v["range"])
        if "random" in v and v.get("type") != "random":
            return resolve_val(v["random"])
        if "choice" in v and isinstance(v["choice"], (list, tuple)) and v["choice"]:
            return resolve_val(random.choice(v["choice"]))
        if "choices" in v and isinstance(v["choices"], (list, tuple)) and v["choices"]:
            return resolve_val(random.choice(v["choices"]))
        if "values" in v and isinstance(v["values"], (list, tuple)) and v["values"]:
            return resolve_val(random.choice(v["values"]))
        if "value" in v:
            return resolve_val(v["value"])
    if isinstance(v, (list, tuple)):
        if len(v) == 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
            low, high = min(v[0], v[1]), max(v[0], v[1])
            is_float = isinstance(low, float) or isinstance(high, float)
            if is_float:
                dec = max(_get_decimals(low), _get_decimals(high), 1)
                val = round(random.uniform(low, high), dec)
                return int(val) if val.is_integer() else val
            else:
                return random.randint(int(low), int(high))
        if len(v) == 1:
            return resolve_val(v[0])
        if len(v) > 2 and all(isinstance(x, (int, float)) for x in v):
            return resolve_val(random.choice(v))
    if isinstance(v, str):
        s = v.strip()
        m = re.match(r'^(?:random|rand)\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)$', s, re.I)
        if m:
            low, high = float(m.group(1)), float(m.group(2))
            low, high = min(low, high), max(low, high)
            if "." in m.group(1) or "." in m.group(2):
                dec = max(_get_decimals(low), _get_decimals(high), 1)
                val = round(random.uniform(low, high), dec)
                return int(val) if val.is_integer() else val
            return random.randint(int(low), int(high))
        m = re.match(r'^(-?\d+(?:\.\d+)?)\s*(?:\.\.|__|\~)\s*(-?\d+(?:\.\d+)?)$', s)
        if m:
            low, high = float(m.group(1)), float(m.group(2))
            low, high = min(low, high), max(low, high)
            if "." in m.group(1) or "." in m.group(2):
                dec = max(_get_decimals(low), _get_decimals(high), 1)
                val = round(random.uniform(low, high), dec)
                return int(val) if val.is_integer() else val
            return random.randint(int(low), int(high))
        m = re.match(r'^(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)$', s, re.I)
        if m:
            low, high = float(m.group(1)), float(m.group(2))
            low, high = min(low, high), max(low, high)
            if "." in m.group(1) or "." in m.group(2):
                dec = max(_get_decimals(low), _get_decimals(high), 1)
                val = round(random.uniform(low, high), dec)
                return int(val) if val.is_integer() else val
            return random.randint(int(low), int(high))
        try:
            val = float(s)
            return int(val) if val.is_integer() else val
        except ValueError:
            return s
    return v


def resolve_gate_spec(spec):
    """Resolve a gate specification [operator, value] which may have random values or operators."""
    if not isinstance(spec, (list, tuple)) or len(spec) == 0:
        return ("+", 10)

    if len(spec) >= 3 and isinstance(spec[1], (int, float)) and isinstance(spec[2], (int, float)):
        op = spec[0]
        low, high = min(spec[1], spec[2]), max(spec[1], spec[2])
        is_float = isinstance(low, float) or isinstance(high, float)
        if is_float:
            dec = max(_get_decimals(low), _get_decimals(high), 1)
            val = round(random.uniform(low, high), dec)
            val = int(val) if val.is_integer() else val
        else:
            val = random.randint(int(low), int(high))
    else:
        op = spec[0]
        val = resolve_val(spec[1]) if len(spec) > 1 else 10

    if isinstance(op, (list, tuple)):
        op = random.choice(op)
    elif isinstance(op, str) and op.lower() in ("random", "rand", "?"):
        op = random.choice(["+", "x", "-"])

    if op not in ("+", "-", "x", "/"):
        op = "+"

    if op in ("x", "/"):
        if isinstance(val, (int, float)) and val == 0:
            val = 1
    elif op == "+":
        if isinstance(val, (int, float)) and val < 0:
            op, val = "-", abs(val)
    elif op == "-":
        if isinstance(val, (int, float)) and val < 0:
            op, val = "+", abs(val)

    return (op, val)


def build_object(data):
    """Instantiate a game object from a JSON dictionary definition.

    Args:
        data (dict): Object definition dictionary containing 'type' and object-specific keys.

    Returns:
        GatePair | Obstacle | EnemyGroup: Instantiated track entity.

    Raises:
        ValueError: If 'type' is not recognized.
    """
    kind = data["type"]
    if kind == "gate_pair":
        z = resolve_val(data["z"])
        left = resolve_gate_spec(data["left"])
        right = resolve_gate_spec(data["right"])
        return GatePair(z, left, right)
    if kind == "obstacle":
        return Obstacle(
            resolve_val(data.get("x", 0)),
            resolve_val(data["z"]),
            resolve_val(data.get("width", 150)),
            resolve_val(data.get("damage", 1))
        )
    if kind == "enemy":
        return EnemyGroup(
            resolve_val(data["z"]),
            resolve_val(data["count"]),
            resolve_val(data.get("x", 0))
        )
    raise ValueError(f"unknown object type: {kind!r}")


def load_level(filename):
    """Load and parse a level JSON file into a Level instance.

    Track objects are automatically sorted in ascending order along the Z axis.

    Args:
        filename (str): Name of the JSON file (e.g. 'level1.json').

    Returns:
        Level: Loaded level instance.
    """
    with open(LEVEL_DIR / filename, encoding="utf-8") as f:
        data = json.load(f)
    objects = sorted((build_object(o) for o in data["objects"]), key=lambda o: o.z)
    theme = data.get("theme", "plains")
    boss = data.get("boss", None)
    start_count = max(1, int(resolve_val(data.get("start_count", 5))))
    speed = float(resolve_val(data.get("speed", 300)))
    finish_z = float(resolve_val(data.get("finish_z", 6200)))
    name = str(data.get("name", "Level"))
    return Level(name, start_count, speed, finish_z, objects, theme=theme, boss=boss)


def list_levels():
    """List all level JSON filenames in LEVEL_DIR sorted numerically (level2 before level10).

    Returns:
        list[str]: Sorted list of level filenames.
    """
    def number(path):
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return int(digits) if digits else 0
    return [p.name for p in sorted(LEVEL_DIR.glob("*.json"), key=lambda p: (number(p), p.name))]


def best_count(level):
    """Calculate the theoretical maximum possible crowd count at the finish line.

    Assumes optimal gate selection at every gate pair and zero obstacle collisions.
    Used as the baseline to evaluate star ratings (2 stars >= 25%, 3 stars >= 50%).

    Args:
        level (Level): Level instance to evaluate.

    Returns:
        int: Maximum achievable final crowd count.
    """
    count = level.start_count
    for obj in level.objects:
        if isinstance(obj, GatePair):
            count = max(obj.left.apply(count), obj.right.apply(count))
        elif isinstance(obj, EnemyGroup):
            count = max(0, count - obj.count)
    return count
