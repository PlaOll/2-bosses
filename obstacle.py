"""Road Obstacles: Hazards placed on the road that eliminate runners upon physical contact."""
import math
import random
import pygame
import config as C


class Obstacle:
    """Represents a stationary or oscillating road barrier."""

    def __init__(self, x, z, width, damage):
        """Initialize an obstacle.

        Args:
            x (float): Initial horizontal center position in world units.
            z (float): Forward distance position in world units.
            width (float): Physical width of the barrier in world units.
            damage (int): Legacy damage parameter (retained for backward compatibility).
        """
        if isinstance(x, dict):
            from level import resolve_val
            x = resolve_val(x)
        if isinstance(z, dict):
            from level import resolve_val
            z = resolve_val(z)
        if isinstance(width, dict):
            from level import resolve_val
            width = resolve_val(width)
        if isinstance(damage, dict):
            from level import resolve_val
            damage = resolve_val(damage)
        self.x = float(x)
        self.z = float(z)
        self.width = float(width)
        self.damage = int(damage)
        self.used = False
        self.start_x = float(x)                                 # Anchor X point for oscillation
        self.time_accumulator = random.uniform(0, 6.28)        # Random initial oscillation phase

    def update(self, dt):
        """Oscillate horizontally along the road based on elapsed time.

        Args:
            dt (float): Delta time in seconds since previous frame.
        """
        self.time_accumulator += dt
        # Sine oscillation around start_x
        self.x = self.start_x + math.sin(self.time_accumulator * 2.0) * 120

    def hits(self, crowd_x, unit_radius=0.0):
        """Test if a position is within the obstacle's horizontal span.

        Args:
            crowd_x (float): World X coordinate to test.
            unit_radius (float): Extra tolerance radius.

        Returns:
            bool: True if inside the obstacle span.
        """
        return abs(crowd_x - self.x) <= (self.width / 2 + unit_radius)

    def on_reach(self, crowd):
        """Eliminate any player runners whose individual hitboxes touch the obstacle.

        Args:
            crowd (Crowd): The player crowd instance.
        """
        victims = [
            p for p in crowd.people
            if abs(crowd.x + p.dx - self.x) <= (self.width / 2 + getattr(p, "radius", 5.0))
        ]
        crowd.remove(victims)

    def on_reach_enemy(self, enemy):
        """Eliminate enemy group members that collide with this obstacle.

        Args:
            enemy (EnemyGroup): The colliding enemy group.
        """
        if hasattr(enemy, "members") and enemy.count > 0:
            victims = [
                m for m in enemy.members
                if abs(enemy.x + m.dx - self.x) <= (self.width / 2 + getattr(m, "radius", 5.0))
            ]
            for m in victims:
                if m in enemy.members:
                    enemy.members.remove(m)
            enemy.count = max(0, enemy.count - len(victims))

    def draw(self, screen, camera, font):
        """Draw the obstacle rectangle projected into perspective space.

        Args:
            screen (pygame.Surface): Surface to render onto.
            camera (Camera): Active camera for projection.
            font (pygame.font.Font): Font instance (unused here, matches draw interface).
        """
        if not camera.visible(self.z):
            return
        x1, y, scale = camera.project(self.x - self.width / 2, self.z)
        x2, _, _ = camera.project(self.x + self.width / 2, self.z)
        h = 25 * scale
        pygame.draw.rect(screen, C.OBSTACLE_COLOR, (x1, y - h, x2 - x1, h))

    def draw_hitbox(self, screen, camera):
        """Render debug collision hitbox bounding box for the obstacle."""
        if not camera.visible(self.z):
            return
        x1, y, scale = camera.project(self.x - self.width / 2, self.z)
        x2, _, _ = camera.project(self.x + self.width / 2, self.z)
        h = 25 * scale
        rect = pygame.Rect(x1, y - h, x2 - x1, h)
        pygame.draw.rect(screen, (255, 220, 0), rect, width=2)
        pygame.draw.line(screen, (255, 60, 0), (x1, y), (x2, y), width=2)

