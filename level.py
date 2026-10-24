"""Level Loading and Track Object Management: Parses JSON levels and updates track entities."""
import json
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
        return GatePair(data["z"], tuple(data["left"]), tuple(data["right"]))
    if kind == "obstacle":
        return Obstacle(data["x"], data["z"], data["width"], data["damage"])
    if kind == "enemy":
        return EnemyGroup(data["z"], data["count"], data.get("x", 0))
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
    return Level(data["name"], data["start_count"], data["speed"], data["finish_z"], objects, theme=theme, boss=boss)


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
