"""Enemy Group System: Hostile red runner crowds with chasing AI, sprites, and combat mechanics."""
import math
import random
from pathlib import Path
import pygame
import config as C

# Directory containing 16x32 character sprite sheets
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "16x32"


class EnemyMember:
    """An individual enemy runner in an EnemyGroup cluster."""

    radius = 5.0  # Collision hitbox radius in world units

    def __init__(self, dx=0.0, dz=0.0):
        """Initialize enemy runner offset and physics parameters.

        Args:
            dx (float): Local horizontal offset from group center.
            dz (float): Local forward/backward offset from group center.
        """
        self.dx = dx
        self.dz = dz
        self.vx = 0.0
        self.vz = 0.0
        self.speed = random.uniform(0.85, 1.15)
        self.anim_t = random.random() * 6.28
        self.wander_t = random.random() * 6.28

    def hitbox(self, group_x=0.0, group_z=0.0):
        """Get (world_x, world_z, radius) tuple for this enemy."""
        return (group_x + self.dx, group_z + self.dz, self.radius)

    def hitbox_rect(self, group_x=0.0, group_z=0.0):
        """Get (min_x, min_z, max_x, max_z) bounding box."""
        wx, wz = group_x + self.dx, group_z + self.dz
        return (wx - self.radius, wz - self.radius, wx + self.radius, wz + self.radius)

    def hits(self, other_x, other_z, other_radius=5.0, group_x=0.0, group_z=0.0):
        """Check circle-circle collision against an external coordinate."""
        wx, wz = group_x + self.dx, group_z + self.dz
        return math.hypot(wx - other_x, wz - other_z) <= (self.radius + other_radius)


class EnemyGroup:
    """A cluster of red enemy runners that idles until the player approaches, then charges."""

    # Class-level cached sprites to avoid reloading from disk per instance
    _frames_run = None
    _frames_idle = None
    _frame_width = 32
    _frame_height = 32
    _small_font = None

    def __init__(self, z, count, x=0):
        """Initialize enemy group.

        Args:
            z (float): World Z position along the track.
            count (int): Number of enemies in this group.
            x (float): Initial horizontal center position (default 0).
        """
        self.x = float(x)
        self.z = float(z)
        self._count = max(0, int(count))
        self.used = False                 # Flag indicating group has engaged the crowd
        self.chasing = False              # True when charging toward the player
        self.members = []                 # List of active EnemyMember instances
        self._sync_members()
        self._ensure_sprites_loaded()

    @classmethod
    def _load_sheet(cls, filenames):
        """Attempt loading spritesheet from candidate paths."""
        for fname in filenames:
            candidates = [
                ASSET_DIR / fname,
                Path("assets/16x32") / fname,
            ]
            for p in candidates:
                if p.exists():
                    try:
                        loaded = pygame.image.load(str(p))
                        if pygame.display.get_surface():
                            loaded = loaded.convert_alpha()
                        return loaded
                    except (pygame.error, FileNotFoundError, OSError):
                        continue
        return None

    @classmethod
    def _ensure_sprites_loaded(cls):
        """Load and slice red running and idle animation frames into class cache."""
        if cls._frames_run is not None and cls._frames_idle is not None:
            return

        # 1. Run animation (6 frames, Row 0 facing camera)
        if cls._frames_run is None:
            cls._frames_run = []
            sheet_run = cls._load_sheet(["16x32 Run-Sheet-Red.png", "Run-Sheet-Red.png"])
            if sheet_run is not None:
                orig_w, orig_h = sheet_run.get_size()
                fw = orig_w // 6
                fh = orig_h // 5
                cls._frame_width = fw
                cls._frame_height = fh
                ROW_FRONT = 0
                for i in range(6):
                    rect = pygame.Rect(i * fw, ROW_FRONT * fh, fw, fh)
                    cls._frames_run.append(sheet_run.subsurface(rect))

        # 2. Idle animation (4 frames, Row 0 facing camera)
        if cls._frames_idle is None:
            cls._frames_idle = []
            sheet_idle = cls._load_sheet(["16x32 Idle-Sheet-Red.png", "Idle-Sheet-Red.png"])
            if sheet_idle is not None:
                orig_w, orig_h = sheet_idle.get_size()
                fw = orig_w // 4
                fh = orig_h // 5
                cls._frame_width = fw
                cls._frame_height = fh
                ROW_FRONT = 0
                for i in range(4):
                    rect = pygame.Rect(i * fw, ROW_FRONT * fh, fw, fh)
                    cls._frames_idle.append(sheet_idle.subsurface(rect))

    @property
    def count(self):
        """Current number of living enemies."""
        return self._count

    @count.setter
    def count(self, val):
        self._count = max(0, int(val))
        self._sync_members()

    def _sync_members(self):
        """Synchronize the members list to match current count (up to MAX_DRAWN_PEOPLE)."""
        n = min(self._count, C.MAX_DRAWN_PEOPLE)
        while len(self.members) < n:
            i = len(self.members)
            r = C.PERSON_SPACING * math.sqrt(i)
            a = i * 2.39996  # Golden angle distribution
            self.members.append(EnemyMember(r * math.cos(a), r * math.sin(a)))
        if len(self.members) > n:
            del self.members[n:]

    def radius(self):
        """Approximate bounding radius of the enemy cluster."""
        return C.PERSON_SPACING * math.sqrt(min(self.count, C.MAX_DRAWN_PEOPLE))

    def hitbox(self):
        """Get (x, z, radius) tuple for the whole enemy cluster."""
        return (self.x, self.z, self.radius())

    def get_hitboxes(self):
        """Get list of (world_x, world_z, radius) for each individual enemy member."""
        return [m.hitbox(self.x, self.z) for m in self.members]

    def draw_hitboxes(self, screen, camera, color=(255, 60, 60)):
        """Debug visualizer: Draws circle outlines for each enemy hitbox."""
        for m in self.members:
            wx, wz, r = m.hitbox(self.x, self.z)
            if not camera.visible(wz):
                continue
            sx, sy, scale = camera.project(wx, wz)
            if scale > 0:
                pygame.draw.circle(screen, color, (sx, sy), max(1, int(r * scale)), 1)

    def update(self, dt, crowd=None, obstacles=None):
        """Update enemy chase AI, obstacle collisions, and boids physics per tick.

        Args:
            dt (float): Delta time in seconds.
            crowd (Crowd | None): Player crowd instance used for detection and pursuit.
            obstacles (list | None): Active obstacles that enemies can run into.
        """
        if self.count <= 0:
            self.chasing = False
            return

        # Check collision against obstacles
        if obstacles:
            for obs in obstacles:
                if abs(self.z - obs.z) <= 35.0 and hasattr(obs, "on_reach_enemy"):
                    obs.on_reach_enemy(self)
            if self.count <= 0:
                self.used = True
                self.chasing = False
                return

        # Player distance check & chase AI
        if crowd is not None:
            dist_z = self.z - crowd.z
            dist_threshold = getattr(C, "ENEMY_CHASE_DIST", 450.0)
            if dist_z <= 0:
                self.chasing = False
            elif dist_z <= dist_threshold:
                # Player in range: Charge toward player!
                self.chasing = True
                chase_speed_z = getattr(C, "ENEMY_CHASE_SPEED_Z", 120.0)
                chase_speed_x = getattr(C, "ENEMY_CHASE_SPEED_X", 2.5)
                self.z -= chase_speed_z * dt
                self.x += (crowd.x - self.x) * min(1.0, chase_speed_x * dt)
                limit = C.ROAD_HALF_W - 20
                self.x = max(-limit, min(limit, self.x))
            else:
                self.chasing = False
        else:
            self.chasing = False

        # Flocking physics between enemy members
        target_r = C.PERSON_SPACING * math.sqrt(max(1, len(self.members))) * 0.8
        for m in self.members:
            fx = fz = 0.0
            d = math.hypot(m.dx, m.dz) or 0.001
            if d > target_r * 0.3:
                pull = (d - target_r * 0.3) * C.CROWD_COHESION
                fx -= m.dx / d * pull
                fz -= m.dz / d * pull

            # Separation
            for other in random.sample(self.members, min(len(self.members), 6)):
                if other is m:
                    continue
                ddx, ddz = m.dx - other.dx, m.dz - other.dz
                dist = math.hypot(ddx, ddz) or 0.001
                if dist < C.PERSON_SPACING:
                    push = (C.PERSON_SPACING - dist) * C.CROWD_SEPARATION
                    fx += ddx / dist * push
                    fz += ddz / dist * push

            # Organic wander
            m.wander_t += dt * 2.0
            fx += math.cos(m.wander_t) * C.CROWD_WANDER
            fz += math.sin(m.wander_t * 1.3) * C.CROWD_WANDER

            damp = 1 - min(1.0, 3 * dt)
            m.vx = (m.vx + fx * dt) * damp
            m.vz = (m.vz + fz * dt) * damp
            m.dx += m.vx * m.speed * dt
            m.dz += m.vz * m.speed * dt

        # Animation timing
        anim_speed_mult = 10.0 if self.chasing else 4.0
        for m in self.members:
            m.anim_t += dt * anim_speed_mult * m.speed

    def on_reach(self, crowd):
        """Execute 1:1 casualty combat when the crowd reaches or dodges this enemy group.

        Args:
            crowd (Crowd): The player crowd colliding with enemies.
        """
        if self.count <= 0 or crowd.count <= 0:
            self.chasing = False
            return

        group_dx = abs(crowd.x - self.x)
        combined_r = crowd.radius() + self.radius()

        # Dodge check: If player steered completely clear of enemy radius, no casualties occur
        if group_dx > combined_r:
            self.used = True
            self.chasing = False
            return

        # Direct head-on collision vs glancing collision
        if group_dx <= max(crowd.radius(), self.radius()) * 0.6:
            fight = min(crowd.count, self.count)
            victims = sorted(crowd.people, key=lambda p: -p.dz)[:fight]
        else:
            overlap_ratio = max(0.1, min(1.0, (combined_r - group_dx) / (2.0 * min(crowd.radius(), self.radius()) or 1.0)))
            fight = max(1, min(crowd.count, self.count, int(min(crowd.count, self.count) * overlap_ratio + 0.5)))
            if self.x > crowd.x:
                victims = sorted(crowd.people, key=lambda p: -p.dx)[:fight]
            else:
                victims = sorted(crowd.people, key=lambda p: p.dx)[:fight]

        # Deduct casualties 1:1
        crowd.remove(victims)
        remaining_deduct = max(0, fight - len(victims))
        if remaining_deduct > 0:
            crowd.count = max(0, crowd.count - remaining_deduct)

        self.count = max(0, self.count - fight)
        self.used = True
        self.chasing = False

    def draw(self, screen, camera, font):
        """Render enemies with running or idle animations and overhead count badge.

        Args:
            screen (pygame.Surface): Display surface.
            camera (Camera): Active camera for projection.
            font (pygame.font.Font): Fallback font for enemy count badge.
        """
        # Render if enemies are still alive and within the camera's viewing frustum
        if self.count <= 0 or not camera.visible(self.z):
            return

        # Choose idle vs running sprite frames
        if self.chasing and self._frames_run:
            active_frames = self._frames_run
            bob_mult = 1.5
        elif self._frames_idle:
            active_frames = self._frames_idle
            bob_mult = 0.6
        elif self._frames_run:
            active_frames = self._frames_run
            bob_mult = 1.0
        else:
            active_frames = []
            bob_mult = 0.0

        num_frames = len(active_frames)

        # Draw members sorted by distance
        for m in sorted(self.members, key=lambda m: -m.dz):
            ez = self.z + m.dz
            if not camera.visible(ez):
                continue
            sx, sy, scale = camera.project(self.x + m.dx, ez)
            if scale <= 0:
                continue

            if active_frames:
                frame_idx = int(m.anim_t) % num_frames
                frame_surface = active_frames[frame_idx]

                new_w = max(1, int(self._frame_width * scale))
                new_h = max(1, int(self._frame_height * scale))
                scaled = pygame.transform.scale(frame_surface, (new_w, new_h))

                bob = math.sin(m.anim_t) * bob_mult * scale
                screen.blit(scaled, (sx - new_w // 2, sy - new_h + bob))
            else:
                pygame.draw.circle(screen, (220, 50, 50), (sx, sy), max(1, 5 * scale))

        # Overhead enemy count badge
        if camera.visible(self.z):
            sx, sy, scale = camera.project(self.x, self.z)
            if scale > 0:
                if EnemyGroup._small_font is None:
                    try:
                        EnemyGroup._small_font = pygame.font.Font(None, 20)
                    except Exception:
                        EnemyGroup._small_font = font

                num_font = EnemyGroup._small_font or font
                text = num_font.render(str(self.count), True, C.WHITE)

                badge_scale = max(0.65, min(1.0, scale))
                if badge_scale < 0.95:
                    tw = max(1, int(text.get_width() * badge_scale))
                    th = max(1, int(text.get_height() * badge_scale))
                    text_scaled = pygame.transform.scale(text, (tw, th))
                else:
                    text_scaled = text

                bg = text_scaled.get_rect(center=(sx, sy - 36 * scale)).inflate(6, 2)
                pygame.draw.rect(screen, (210, 45, 45), bg, border_radius=4)
                screen.blit(text_scaled, text_scaled.get_rect(center=bg.center))

    def draw_hitbox(self, screen, camera):
        """Render debug collision hitboxes for all enemy members."""
        if self.count <= 0:
            return
        for m in self.members:
            mz = self.z + m.dz
            if not camera.visible(mz):
                continue
            sx, sy, scale = camera.project(self.x + m.dx, mz)
            if scale <= 0:
                continue
            r = max(2, int(m.radius * scale))
            pygame.draw.circle(screen, (255, 60, 60), (int(sx), int(sy)), r, 1)
            pygame.draw.circle(screen, (255, 60, 60), (int(sx), int(sy)), 1)

