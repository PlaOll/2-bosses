"""Player Crowd Simulation: Flocking/Boids physics, animated runners, and collision hitboxes."""
import math
import random
from pathlib import Path

import pygame
import config as C

# Directory containing 16x32 character sprite sheets
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "16x32"


class Person:
    """Represents an individual runner within the player's crowd cluster."""

    radius = 5.0  # Physical collision hitbox radius in world units

    def __init__(self, dx=0.0, dz=0.0):
        """Initialize runner offset and physics parameters.

        Args:
            dx (float): Initial horizontal offset relative to the crowd center (x).
            dz (float): Initial depth offset relative to the crowd center (z).
        """
        self.dx = dx                                                # Local X offset from crowd center
        self.dz = dz                                                # Local Z offset from crowd center
        self.vx = 0.0                                               # Local X velocity
        self.vz = 0.0                                               # Local Z velocity
        self.speed = random.uniform(0.85, 1.15)                     # Individual speed multiplier for natural variation
        self.anim_t = random.random() * 6.28                        # Animation timer phase
        self.wander_t = random.random() * 6.28                      # Flocking wander phase
        self.poison_time = 0.0                                      # Accumulated time spent in poison
        self.poison_death_time = getattr(C, "POISON_DEATH_TIME", 2.0)  # Seconds before poison is fatal

    def hitbox(self, crowd_x=0.0, crowd_z=0.0):
        """Get circular hitbox representation in world coordinates.

        Args:
            crowd_x (float): World X of crowd cluster center.
            crowd_z (float): World Z of crowd cluster center.

        Returns:
            tuple[float, float, float]: (world_x, world_z, radius).
        """
        return (crowd_x + self.dx, crowd_z + self.dz, self.radius)

    def hitbox_rect(self, crowd_x=0.0, crowd_z=0.0):
        """Get Axis-Aligned Bounding Box (AABB) in world coordinates.

        Returns:
            tuple[float, float, float, float]: (min_x, min_z, max_x, max_z).
        """
        wx, wz = crowd_x + self.dx, crowd_z + self.dz
        return (wx - self.radius, wz - self.radius, wx + self.radius, wz + self.radius)

    def hits(self, other_x, other_z, other_radius=5.0, crowd_x=0.0, crowd_z=0.0):
        """Check circle-circle collision against another entity.

        Returns:
            bool: True if distance <= sum of radii.
        """
        wx, wz = crowd_x + self.dx, crowd_z + self.dz
        return math.hypot(wx - other_x, wz - other_z) <= (self.radius + other_radius)


class Crowd:
    """Manages the full cluster of player runners, flocking physics, and directional rendering."""

    def __init__(self, count):
        """Initialize crowd cluster and load runner spritesheet.

        Args:
            count (int): Starting number of runners.
        """
        self.x = 0.0                                    # Crowd center X position in world units
        self.z = 0.0                                    # Crowd center Z position in world units
        self.target_x = None                            # Target X for mouse steering (if used)
        self.people = []                                # List of active Person instances
        self.reformation_timer = 0.0                    # Timer delay before cluster collapses inward after taking hits
        self.pending_rebalance = False                  # Flag to re-center center of mass after damage

        # ----------------------------------------------------------------------
        # Spritesheet loading and directional frame slicing
        # ----------------------------------------------------------------------
        dummy = pygame.Surface((16 * 6, 32 * 5), pygame.SRCALPHA)
        pygame.draw.rect(dummy, (0, 255, 0), (0, 0, 16 * 6, 32 * 5))
        self.sheet_straight = dummy

        candidates = [
            ASSET_DIR / "Run-Sheet.png",
            ASSET_DIR / "Run.png",
            ASSET_DIR / "16x32 Run-Sheet.png",
            ASSET_DIR / "16x32 Run.png",
            Path("assets/16x32/Run-Sheet.png"),
            Path("assets/16x32/Run.png"),
        ]

        for candidate in candidates:
            try:
                if candidate.exists():
                    loaded = pygame.image.load(str(candidate)).convert_alpha()
                    self.sheet_straight = loaded
                    break
            except (pygame.error, FileNotFoundError, OSError):
                continue

        self.total_columns = 6  # 6 frames per running animation cycle
        self.total_rows = 5     # 5 directional rows in spritesheet

        orig_w, orig_h = self.sheet_straight.get_size()
        self.frame_width = orig_w // self.total_columns
        self.frame_height = orig_h // self.total_rows

        ROW_STRAIGHT = 4  # Bottom row: Running straight ahead (facing away from camera)
        ROW_RIGHT = 3     # Row 3: Running angled rightwards

        self.frames_straight = []
        self.frames_left = []
        self.frames_right = []
        self.total_frames = self.total_columns

        for i in range(self.total_frames):
            x_pos = i * self.frame_width
            # Straight frames
            rect_s = pygame.Rect(x_pos, ROW_STRAIGHT * self.frame_height, self.frame_width, self.frame_height)
            self.frames_straight.append(self.sheet_straight.subsurface(rect_s))

            # Right frames
            rect_r = pygame.Rect(x_pos, ROW_RIGHT * self.frame_height, self.frame_width, self.frame_height)
            frame_right = self.sheet_straight.subsurface(rect_r)
            self.frames_right.append(frame_right)

            # Left frames (horizontally mirrored from right frames)
            frame_left = pygame.transform.flip(frame_right, True, False)
            self.frames_left.append(frame_left)

        self.set_count(count)

    @property
    def count(self):
        """Current number of active runners."""
        return len(self.people)

    @count.setter
    def count(self, n):
        self.set_count(n)

    def set_count(self, n):
        """Adjust total number of runners, spawning new ones or trimming excess.

        Args:
            n (int): Target crowd count.
        """
        n = max(0, int(n))
        old_count = len(self.people)
        while len(self.people) < n:
            self.people.append(Person(random.uniform(-5, 5), random.uniform(-5, 5)))
        if n < old_count:
            del self.people[n:]
            self.reformation_timer = getattr(C, "REFORMATION_DELAY", 0.5)
            self.pending_rebalance = True
        else:
            del self.people[n:]

    def add(self, n):
        """Add n runners to the crowd."""
        self.set_count(self.count + n)

    def remove(self, people):
        """Remove specific Person instances from the crowd (e.g. casualties from obstacles or enemies).

        Args:
            people (list[Person]): Victims to remove.
        """
        gone = set(map(id, people))
        self.people = [p for p in self.people if id(p) not in gone]
        self.reformation_timer = getattr(C, "REFORMATION_DELAY", 0.5)
        self.pending_rebalance = True

    def radius(self):
        """Approximate bounding radius of the full crowd cluster based on current count.

        Returns:
            float: Radius in world units.
        """
        return C.PERSON_SPACING * math.sqrt(min(self.count, C.MAX_DRAWN_PEOPLE))

    def hitbox(self):
        """Get (x, z, radius) for the full crowd cluster."""
        return (self.x, self.z, self.radius())

    def get_hitboxes(self):
        """Get list of (world_x, world_z, radius) for every runner."""
        return [p.hitbox(self.x, self.z) for p in self.people]

    def draw_hitboxes(self, screen, camera, color=(0, 255, 100)):
        """Debug visualizer: Draws circle outlines for each individual runner hitbox."""
        for p in self.people[:C.MAX_DRAWN_PEOPLE]:
            wx, wz, r = p.hitbox(self.x, self.z)
            if not camera.visible(wz):
                continue
            sx, sy, scale = camera.project(wx, wz)
            if scale > 0:
                pygame.draw.circle(screen, color, (sx, sy), max(1, int(r * scale)), 1)

    def move(self, direction, dt, forward_speed=0):
        """Handle steering input from keyboard controls.

        Args:
            direction (int): -1 (left), +1 (right), or 0 (neutral).
            dt (float): Delta time in seconds.
            forward_speed (float): Current forward running speed.
        """
        if direction:
            self.target_x = None
            side = max(C.CROWD_SIDE_SPEED, forward_speed * C.CROWD_SIDE_RATIO)
            self.x += direction * side * dt

    def update(self, dt):
        """Update crowd flocking physics, road clamping, and animation frames per tick.

        Args:
            dt (float): Delta time in seconds.
        """
        # 1. Mouse follow (if mouse target set)
        if self.target_x is not None:
            self.x += (self.target_x - self.x) * min(1.0, 10 * dt)

        # 2. Road boundaries clamp
        road_w = getattr(self, "road_half_w", C.ROAD_HALF_W)
        limit = max(0.0, road_w - self.radius())
        self.x = max(-limit, min(limit, self.x))

        # 3. Calculate steering velocity for directional sprite selection
        if hasattr(self, "last_x") and dt > 0:
            self.crowd_vx = (self.x - self.last_x) / dt
        else:
            self.crowd_vx = 0.0
        self.last_x = self.x

        # 4. Delayed cluster reformation after casualties
        if self.reformation_timer > 0:
            self.reformation_timer -= dt
            if self.reformation_timer <= 0:
                self.reformation_timer = 0.0
                if self.pending_rebalance and self.count > 0:
                    avg_dx = sum(p.dx for p in self.people) / self.count
                    avg_dz = sum(p.dz for p in self.people) / self.count
                    self.x += avg_dx
                    for p in self.people:
                        p.dx -= avg_dx
                        p.dz -= avg_dz
                    self.pending_rebalance = False

        is_reforming = (self.reformation_timer <= 0.0)

        # 5. Boids / Flocking physics simulation
        target_r = C.PERSON_SPACING * math.sqrt(self.count) * 0.8
        for p in self.people:
            fx = fz = 0.0
            # Cohesion: pull towards center (active after delay)
            if is_reforming:
                d = math.hypot(p.dx, p.dz) or 0.001
                if d > target_r * 0.3:
                    pull = (d - target_r * 0.3) * C.CROWD_COHESION
                    fx -= p.dx / d * pull
                    fz -= p.dz / d * pull

            # Separation: repel nearby neighbors
            for q in random.sample(self.people, min(self.count, 8)):
                if q is p:
                    continue
                ddx, ddz = p.dx - q.dx, p.dz - q.dz
                dist = math.hypot(ddx, ddz) or 0.001
                if dist < C.PERSON_SPACING:
                    push = (C.PERSON_SPACING - dist) * C.CROWD_SEPARATION
                    fx += ddx / dist * push
                    fz += ddz / dist * push

            # Wander: natural organic jitter
            p.wander_t += dt * random.uniform(1.0, 3.0)
            fx += math.cos(p.wander_t) * C.CROWD_WANDER
            fz += math.sin(p.wander_t * 1.3) * C.CROWD_WANDER

            damp = 1 - min(1.0, 3 * dt)
            p.vx = (p.vx + fx * dt) * damp
            p.vz = (p.vz + fz * dt) * damp
            p.dx += p.vx * p.speed * dt
            p.dz += p.vz * p.speed * dt

            p.anim_t += dt * 8 * p.speed

    def draw(self, screen, camera, font):
        """Render all visible runners back-to-front with perspective scaling, bobbing, and count badge.

        Args:
            screen (pygame.Surface): Display surface.
            camera (Camera): Active camera for projection.
            font (pygame.font.Font): Font used for rendering crowd count badge.
        """
        # Sort runners by distance (furthest dz first)
        for p in sorted(self.people[:C.MAX_DRAWN_PEOPLE], key=lambda p: -p.dz):
            if not camera.visible(self.z + p.dz):
                continue
            sx, sy, scale = camera.project(self.x + p.dx, self.z + p.dz)
            if scale <= 0:
                continue

            # Select directional animation based on steering velocity
            if getattr(self, "crowd_vx", 0) < -50:
                current_frames = self.frames_left
            elif getattr(self, "crowd_vx", 0) > 50:
                current_frames = self.frames_right
            else:
                current_frames = self.frames_straight

            frame_index = int(p.anim_t) % self.total_frames
            frame_surface = current_frames[frame_index]

            # Perspective scale
            new_w = max(1, int(self.frame_width * scale))
            new_h = max(1, int(self.frame_height * scale))
            scaled_sprite = pygame.transform.scale(frame_surface, (new_w, new_h))

            # Running vertical bobbing bounce
            bob = math.sin(p.anim_t) * 1.5 * scale
            char_x = sx - new_w // 2
            char_y = sy - new_h + bob
            screen.blit(scaled_sprite, (char_x, char_y))

            # Poison tint effect (gradually fills upward with light purple)
            poison_t = getattr(p, "poison_time", 0.0)
            death_t = getattr(p, "poison_death_time", getattr(C, "POISON_DEATH_TIME", 2.0))
            if poison_t > 0:
                ratio = min(1.0, max(0.0, poison_t / death_t))
                purple_h = min(new_h, max(1, int(new_h * ratio)))
                mask = pygame.mask.from_surface(scaled_sprite)
                alpha = int(140 + 100 * ratio)
                tint_surf = mask.to_surface(setcolor=(205, 130, 255, alpha), unsetcolor=(0, 0, 0, 0))
                y_start = new_h - purple_h
                tint_sub = tint_surf.subsurface((0, y_start, new_w, purple_h))
                screen.blit(tint_sub, (char_x, char_y + y_start))

        # Floating crowd count badge above the group
        if camera.visible(self.z):
            sx, sy, scale = camera.project(self.x, self.z)
            if scale > 0:
                text = font.render(str(self.count), True, C.WHITE)
                bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
                pygame.draw.rect(screen, C.PLAYER_COLOR, bg, border_radius=6)
                screen.blit(text, text.get_rect(center=bg.center))
