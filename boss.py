"""Boss Battle System: Scorpion Boss, Venom Plant Boss, projectiles, hazards, and combat mechanics."""
import math
import random
from pathlib import Path
import pygame
import config as C

# Asset filepaths for boss spritesheets
BOSS_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "Bosses sheet" / "scorpion_sheet.png"
PLANT_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "Bosses sheet" / "plant_sheet.png"
PLANT_POISON_POOL_PATH = Path(__file__).resolve().parent / "assets" / "Bosses sheet" / "plant_poison_pool_sheet.png"

# Boss Finite State Machine States
STATE_IDLE = "idle"               # Waiting between attacks
STATE_TELEGRAPH = "telegraph"     # Projecting red warning danger zone on the ground
STATE_ATTACK = "attack"           # Executing attack animation and calculating damage
STATE_HIT = "hit"                 # Flash feedback when struck by runner bullets
STATE_DEFEAT = "defeat"           # Defeat death animation sequence

# Attack Direction / Pattern Types
ATTACK_FRONT = "front"
ATTACK_LEFT = "left"
ATTACK_RIGHT = "right"


class Bullet:
    """Player crowd projectile shot forward at the boss."""

    def __init__(self, x, z, target_x, target_z, damage=0.5):
        """Initialize bullet trajectory towards boss position.

        Args:
            x (float): Starting world X coordinate.
            z (float): Starting world Z coordinate.
            target_x (float): Target boss X coordinate.
            target_z (float): Target boss Z coordinate.
            damage (float): Damage inflicted upon hit.
        """
        self.x = x
        self.z = z
        self.target_x = target_x
        self.target_z = target_z
        self.damage = damage
        self.speed = 850.0  # units per sec
        self.alive = True

        dx = target_x - x
        dz = target_z - z
        dist = math.hypot(dx, dz) or 1.0
        self.vx = (dx / dist) * self.speed
        self.vz = (dz / dist) * self.speed

    def update(self, dt):
        self.x += self.vx * dt
        self.z += self.vz * dt
        if self.z >= self.target_z:
            self.alive = False

    def draw(self, screen, camera):
        if not camera.visible(self.z):
            return
        sx, sy, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return
        # กระสุนวงกลมสีเหลืองขนาดเล็กมาก
        r = max(1, int(2.5 * scale))
        pygame.draw.circle(screen, (255, 235, 50), (int(sx), int(sy)), r)
        if r >= 2:
            pygame.draw.circle(screen, (255, 255, 220), (int(sx), int(sy)), max(1, r - 1))


class HitSpark:
    """อนุภาคประกายไฟเมื่อบอสโดนยิง"""
    def __init__(self, x, z, color=None):
        self.x = x + random.uniform(-25, 25)
        self.z = z + random.uniform(-10, 10)
        self.vx = random.uniform(-60, 60)
        self.vz = random.uniform(-60, 60)
        self.life = 0.25
        self.max_life = 0.25
        self.color = color if color is not None else random.choice([(255, 220, 50), (255, 120, 40), (255, 255, 200)])

    def update(self, dt):
        self.x += self.vx * dt
        self.z += self.vz * dt
        self.life -= dt

    def draw(self, screen, camera):
        if self.life <= 0 or not camera.visible(self.z):
            return
        sx, sy, scale = camera.project(self.x, self.z)
        r = max(1, int(3 * scale * (self.life / self.max_life)))
        pygame.draw.circle(screen, self.color, (int(sx), int(sy)), r)


class ScorpionBoss:
    """Stage 2 Boss: Giant Desert Scorpion featuring directional attacks and telegraph zones."""

    def __init__(self, z, max_hp=1000):
        """Initialize scorpion boss parameters.

        Args:
            z (float): World Z distance where the boss is stationed on the arena.
            max_hp (int): Maximum health points.
        """
        self.x = 0.0
        self.z = z
        self.max_hp = max_hp
        self.hp = max_hp
        self.state = STATE_IDLE
        self.attack_type = None

        # Sprite dimensions (6 rows x 8 cols of 80x80 px frames)
        self.frame_width = 80
        self.frame_height = 80
        self.load_spritesheet()
        
        # ====================================================
        # ⚙️ BOSS SPEED & ATTACK TIMING SETTINGS (Tuning parameters)
        # ====================================================
        self.idle_duration = 1.0        # Pause time between attack cycles in seconds (decrease for higher aggression)
        self.telegraph_duration = 0.65  # Warning telegraph ground indicator duration in seconds
        self.attack_fps = 14.0          # Animation playback speed (FPS) for attack strikes
        self.attack_strike_frame = 4    # Frame index within attack animation where damage check triggers (frame 4 of 8)
        # ตัวจับเวลา Animation และ AI
        self.anim_timer = 0.0
        self.state_timer = 0.0
        self.hit_flash_timer = 0.0
        self.defeat_completed = False

        # การยิงของฝั่งผู้เล่น
        self.shoot_timer = 0.0
        self.shoot_interval = 1.5  # 1.5วินาทีต่อการยิง 1 นัดของแต่ละคน
        self.bullets = []
        self.sparks = []

        # กำหนดโซนอันตราย (Telegraph Zone)
        self.danger_rect = None  # (min_x, max_x)
        self.attack_struck = False

    def load_spritesheet(self):
        try:
            sheet = pygame.image.load(str(BOSS_ASSET_PATH)).convert_alpha()
        except Exception:
            # Fallback หากหาไฟล์ไม่เจอ
            sheet = pygame.Surface((640, 480), pygame.SRCALPHA)
            sheet.fill((200, 50, 50))

        # 1st line (row 0): idle (4 frames)
        # 2nd line (row 1): front attack (8 frames)
        # 3rd line (row 2): 45 degree left attack (8 frames)
        # 4th line (row 3): 45 degree right attack (8 frames)
        # 5th line (row 4): getting hit (4 frames)
        # 6th line (row 5): dead (8 frames)
        def get_row(row_idx, count):
            frames = []
            for col in range(count):
                rect = pygame.Rect(col * self.frame_width, row_idx * self.frame_height,
                                   self.frame_width, self.frame_height)
                frames.append(sheet.subsurface(rect))
            return frames

        self.anim_idle = get_row(0, 4)
        self.anim_attack_front = get_row(1, 8)
        self.anim_attack_left = get_row(2, 8)
        self.anim_attack_right = get_row(3, 8)
        self.anim_hit = get_row(4, 4)
        self.anim_defeat = get_row(5, 8)

    def trigger_hit(self, damage=5):
        if self.state == STATE_DEFEAT:
            return
        self.hp = max(0, self.hp - damage)
        self.hit_flash_timer = 0.1
        if self.hp <= 0:
            self.state = STATE_DEFEAT
            self.anim_timer = 0.0
            self.state_timer = 0.0

    def start_attack(self):
        self.state = STATE_TELEGRAPH
        self.state_timer = 0.0
        self.attack_struck = False

        # 1. Random zone width (e.g. between 180 and 240 units)
        zone_width = random.uniform(180, 240)

        # 2. Pick a random center X between -230 and +230 (within the 340 half-width platform)
        center_x = random.uniform(-230, 230)

        # 3. Create the random danger zone [min_x, max_x]
        min_x = center_x - zone_width / 2
        max_x = center_x + zone_width / 2
        self.danger_rect = (min_x, max_x)

        # 4. Automatically select the animation based on where the random zone landed
        if center_x < -70:
            self.attack_type = ATTACK_LEFT     # 45° Left attack animation
        elif center_x > 70:
            self.attack_type = ATTACK_RIGHT    # 45° Right attack animation
        else:
            self.attack_type = ATTACK_FRONT    # Front attack animation

    def update(self, dt, crowd):
        # 1. จัดการกระสุนและประกายไฟ
        for b in self.bullets:
            b.update(dt)
            if not b.alive:
                self.trigger_hit(b.damage)
                for _ in range(2):
                    self.sparks.append(HitSpark(self.x, self.z))
        self.bullets = [b for b in self.bullets if b.alive]

        for s in self.sparks:
            s.update(dt)
        self.sparks = [s for s in self.sparks if s.life > 0]

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        # 2. ระบบคนในกลุ่มยิงใส่บอส (หน่วงเวลา 1.5 วิ และทำดาเมจ 5 ต่อนัด)
        if self.state != STATE_DEFEAT and crowd.count > 0:
            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_interval:
                self.shoot_timer = 0.0
                # ให้ทุกคนยิงกระสุนออกจากมือขวาพุ่งไปหาบอส
                hand_offset_x = 5.0
                hand_offset_z = 2.0
                for p in crowd.people:
                    bx = crowd.x + p.dx + hand_offset_x
                    bz = crowd.z + p.dz + hand_offset_z
                    self.bullets.append(Bullet(bx, bz, self.x, self.z, damage=0.5))

        # 3. จัดการ State Machine ของบอส
        self.state_timer += dt
        self.anim_timer += dt

        if self.state == STATE_IDLE:
            if self.state_timer >= self.idle_duration:
                self.start_attack()

        elif self.state == STATE_TELEGRAPH:
            if self.state_timer >= self.telegraph_duration:
                self.state = STATE_ATTACK
                self.state_timer = 0.0
                self.anim_timer = 0.0

        elif self.state == STATE_ATTACK:
            # เฟรมโจมตี: เล่นตามความเร็ว self.attack_fps
            frame_idx = int(self.anim_timer * self.attack_fps)
            if frame_idx >= self.attack_strike_frame and not self.attack_struck:
                self.attack_struck = True
                self.execute_attack_damage(crowd)

            if frame_idx >= len(self.anim_attack_front):
                # โจมตีเสร็จสิ้น กลับไป Idle
                self.state = STATE_IDLE
                self.state_timer = 0.0
                self.anim_timer = 0.0
                self.danger_rect = None

        elif self.state == STATE_DEFEAT:
            frame_idx = int(self.anim_timer * 8)
            if frame_idx >= len(self.anim_defeat) - 1:
                self.defeat_completed = True

    def execute_attack_damage(self, target):
        """ตรวจจับคนที่อยู่ในโซนอันตรายตอนบอสฟาด แล้วกำจัดยูนิตเหล่านั้นโดยคำนึงถึง hitbox"""
        if not self.danger_rect:
            return

        min_x, max_x = self.danger_rect
        if hasattr(target, "people") and target.count > 0:
            hit_people = []
            for p in target.people:
                px = target.x + p.dx
                pr = getattr(p, "radius", 5.0)
                if (min_x - pr) <= px <= (max_x + pr):
                    hit_people.append(p)

            if hit_people:
                target.remove(hit_people)

        elif hasattr(target, "members") and target.count > 0:
            hit_enemies = []
            for m in target.members:
                mx = target.x + m.dx
                mr = getattr(m, "radius", 5.0)
                if (min_x - mr) <= mx <= (max_x + mr):
                    hit_enemies.append(m)

            for m in hit_enemies:
                if m in target.members:
                    target.members.remove(m)
            target.count = max(0, target.count - len(hit_enemies))

    def get_current_frame(self):
        if self.state == STATE_IDLE:
            frames = self.anim_idle
            idx = int(self.anim_timer * 6) % len(frames)
            return frames[idx]

        elif self.state == STATE_TELEGRAPH:
            # ใช้ Idle หรือเตรียมพร้อม
            frames = self.anim_idle
            idx = int(self.anim_timer * 10) % len(frames)
            return frames[idx]

        elif self.state == STATE_ATTACK:
            if self.attack_type == ATTACK_FRONT:
                frames = self.anim_attack_front
            elif self.attack_type == ATTACK_LEFT:
                frames = self.anim_attack_left
            else:
                frames = self.anim_attack_right
            idx = min(len(frames) - 1, int(self.anim_timer * self.attack_fps))
            return frames[idx]

        elif self.state == STATE_HIT:
            frames = self.anim_hit
            idx = min(len(frames) - 1, int(self.anim_timer * 10))
            return frames[idx]

        elif self.state == STATE_DEFEAT:
            frames = self.anim_defeat
            idx = min(len(frames) - 1, int(self.anim_timer * 8))
            return frames[idx]

        return self.anim_idle[0]

    def draw_telegraph(self, screen, camera, finish_z):
        """วาดโซนเตือนภัยสีแดงบนพื้น (Telegraph zone) ก่อนบอสโจมตี เพื่อให้ผู้เล่นโยกหลบ"""
        if self.state not in (STATE_TELEGRAPH, STATE_ATTACK) or not self.danger_rect:
            return

        min_x, max_x = self.danger_rect
        near_z = finish_z - 80
        far_z = finish_z + 120

        # คำนวณ 4 มุมของพื้นที่สี่เหลี่ยมคางหมูบนพื้นตามกล้อง 3D
        p1 = camera.project(min_x, near_z)[:2]
        p2 = camera.project(max_x, near_z)[:2]
        p3 = camera.project(max_x, far_z)[:2]
        p4 = camera.project(min_x, far_z)[:2]

        # กระพริบเตือนสีแดง (Telegraph) / กระพริบสีดำเมื่อบอสกำลังจะโจมตีจริง (Attack)
        if self.state == STATE_ATTACK:
            if int(self.state_timer * 20) % 2 == 0:
                color = (0, 0, 0, 230)
                border_color = (0, 0, 0, 255)
            else:
                color = (255, 40, 40, 200)
                border_color = (255, 230, 100, 240)
        else:
            alpha = int(120 + 80 * math.sin(self.state_timer * 15))
            color = (255, 40, 40, alpha)
            border_color = (255, 230, 100, 240)

        poly_surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        pygame.draw.polygon(poly_surf, color, [p1, p2, p3, p4])
        pygame.draw.polygon(poly_surf, border_color, [p1, p2, p3, p4], width=3)
        screen.blit(poly_surf, (0, 0))

    def draw(self, screen, camera):
        # 1. วาดกระสุน
        for b in self.bullets:
            b.draw(screen, camera)

        # 2. วาดประกายไฟ
        for s in self.sparks:
            s.draw(screen, camera)

        # 3. วาดตัวบอส
        if not camera.visible(self.z):
            return

        sx, sy, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return

        # บอสมีขนาดใหญ่ขึ้นในโลกเกม (ขยาย 2.5 เท่าของขนาดปกติ)
        boss_world_w = self.frame_width * 6
        boss_world_h = self.frame_height * 6
        draw_w = max(4, int(boss_world_w * scale))
        draw_h = max(4, int(boss_world_h * scale))

        # เงาใต้ตัวบอส
        shadow_w = int(draw_w * 1.8)
        shadow_h = int(draw_h * 0.72)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 120), (0, 0, shadow_w, shadow_h))
        screen.blit(shadow_surf, (sx - shadow_w // 2, sy - shadow_h // 2))

        # ดึงภาพเฟรมปัจจุบัน
        frame = self.get_current_frame()
        scaled_frame = pygame.transform.scale(frame, (draw_w, draw_h))
        boss_pos = (sx - draw_w // 2, sy - draw_h + int(10 * scale))

        # วาดตัวบอส
        screen.blit(scaled_frame, boss_pos)

        # แฟลชสีขาวเวลารับดาเมจ (เฉพาะบนตัวโมเดลของบอส ไม่ติดกรอบสี่เหลี่ยม)
        if self.hit_flash_timer > 0 and self.state != STATE_DEFEAT:
            mask = pygame.mask.from_surface(scaled_frame)
            flash_surf = mask.to_surface(setcolor=(255, 255, 255, 190), unsetcolor=(0, 0, 0, 0))
            screen.blit(flash_surf, boss_pos)

    def draw_hud(self, screen, font):
        """วาดหลอดเลือดบอส (Boss HP Bar) ด้านบนสุดของหน้าจอ"""
        bar_w = 340
        bar_h = 16
        bar_x = (C.SCREEN_W - bar_w) // 2
        bar_y = 35

        # ชื่อบอส
        name_surf = font.render("=== THE SCORPION ===", True, (255, 215, 60))
        name_rect = name_surf.get_rect(center=(C.SCREEN_W // 2, bar_y - 14))
        screen.blit(name_surf, name_rect)

        # พื้นหลังหลอดเลือด
        bg_rect = pygame.Rect(bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4)
        pygame.draw.rect(screen, (20, 20, 30), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 80, 100), bg_rect, width=2, border_radius=6)

        # หลอดเลือดสีแดง/ส้ม
        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            # ไล่สีแดงสด
            pygame.draw.rect(screen, (230, 40, 40), fill_rect, border_radius=4)

        # ตัวเลข HP (เช่น 1000 / 1000)
        hp_val = int(math.ceil(self.hp))
        hp_text = font.render(f"{hp_val} / {self.max_hp}", True, C.WHITE)
        hp_rect = hp_text.get_rect(center=(C.SCREEN_W // 2, bar_y + bar_h // 2))
        screen.blit(hp_text, hp_rect)


class PoisonBubbleParticle:
    """ฟองอากาศพิษลอยขึ้นจากบ่อพิษหรือตัวละครที่ติดพิษ"""

    def __init__(self, x, z, y_offset=0.0, color=None):
        self.x = x + random.uniform(-4, 4)
        self.z = z + random.uniform(-4, 4)
        self.y = y_offset + random.uniform(0, 6)
        self.vy = random.uniform(25, 45)
        self.vx = random.uniform(-6, 6)
        self.life = random.uniform(0.4, 0.7)
        self.max_life = self.life
        self.color = color if color else random.choice([(195, 110, 255), (145, 60, 220), (220, 165, 255)])
        self.radius = random.uniform(2.0, 3.5)

    def update(self, dt):
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.life -= dt

    def draw(self, screen, camera):
        if self.life <= 0 or not camera.visible(self.z):
            return
        sx, sy_ground, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return
        sy = sy_ground - self.y * scale
        r = max(1, int(self.radius * scale * (self.life / self.max_life)))
        pygame.draw.circle(screen, self.color, (int(sx), int(sy)), r)


class PoisonSplashParticle:
    """ละอองพิษกระจายตัวเมื่อพิษตกกระทบพื้นหรือมีคนตายจากพิษ"""

    def __init__(self, x, z, color=None):
        self.x = x
        self.z = z
        self.vx = random.uniform(-90, 90)
        self.vz = random.uniform(-60, 60)
        self.y = random.uniform(2, 10)
        self.vy = random.uniform(50, 120)
        self.life = random.uniform(0.3, 0.5)
        self.max_life = self.life
        self.color = color if color else random.choice([(180, 70, 240), (120, 230, 80), (220, 140, 255)])

    def update(self, dt):
        self.x += self.vx * dt
        self.z += self.vz * dt
        self.y += self.vy * dt
        self.vy -= 280.0 * dt
        if self.y < 0:
            self.y = 0
            self.vx *= 0.5
            self.vz *= 0.5
        self.life -= dt

    def draw(self, screen, camera):
        if self.life <= 0 or not camera.visible(self.z):
            return
        sx, sy_ground, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return
        sy = sy_ground - self.y * scale
        r = max(1, int(2.5 * scale * (self.life / self.max_life)))
        pygame.draw.circle(screen, self.color, (int(sx), int(sy)), r)


class PoisonSpit:
    """กระสุนพิษที่บอสพ่นออกมาลอยข้ามฟ้ามาตกลงบนพื้น"""

    def __init__(self, start_x, start_z, target_x, target_z, start_y=75.0, flight_time=0.45):
        self.start_x = start_x
        self.start_z = start_z
        self.target_x = target_x
        self.target_z = target_z
        self.start_y = start_y
        self.flight_time = flight_time
        self.elapsed = 0.0
        self.alive = True
        self.curr_x = start_x
        self.curr_z = start_z
        self.curr_y = start_y

    def update(self, dt):
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.flight_time)
        self.curr_x = self.start_x + (self.target_x - self.start_x) * t
        self.curr_z = self.start_z + (self.target_z - self.start_z) * t
        self.curr_y = (1.0 - t) * self.start_y + math.sin(math.pi * t) * 65.0
        if t >= 1.0:
            self.alive = False

    def draw(self, screen, camera):
        if not camera.visible(self.curr_z):
            return
        sx, sy_ground, scale = camera.project(self.curr_x, self.curr_z)
        if scale <= 0:
            return
        sy = sy_ground - self.curr_y * scale

        # เงาบนพื้น
        shadow_r = max(2, int(6 * scale))
        pygame.draw.ellipse(
            screen, (20, 10, 30, 110),
            (int(sx - shadow_r), int(sy_ground - shadow_r * 0.5), shadow_r * 2, int(shadow_r))
        )

        # ก้อนพิษเรืองแสง
        r = max(3, int(8 * scale))
        pygame.draw.circle(screen, (160, 50, 230), (int(sx), int(sy)), r)
        pygame.draw.circle(screen, (210, 120, 255), (int(sx), int(sy)), max(1, r - 2))
        pygame.draw.circle(screen, (130, 255, 90), (int(sx), int(sy)), max(1, r - 4))


class PoisonPool:
    """Ground poison hazard: inflicts fatal poison over time on runners stepping into it."""

    _spawn_frames = None
    _active_frames = None
    _fade_frames = None
    _frames_loaded = False

    @classmethod
    def load_frames(cls):
        if cls._frames_loaded:
            return
        try:
            raw = pygame.image.load(str(PLANT_POISON_POOL_PATH))
            sheet = raw.convert_alpha() if pygame.display.get_surface() else raw
        except Exception:
            sheet = pygame.Surface((768, 144), pygame.SRCALPHA)
            pygame.draw.ellipse(sheet, (140, 40, 200, 200), (0, 0, 768, 144))

        cleaned = []
        for idx in range(14):
            r, c = divmod(idx, 8)
            cell = sheet.subsurface((c * 96, r * 72, 96, 72)).copy()
            m = pygame.mask.from_surface(cell)
            rects = m.get_bounding_rects()
            if rects:
                largest = max(rects, key=lambda rect: rect.w * rect.h)
                clean_cell = pygame.Surface((96, 72), pygame.SRCALPHA)
                clean_cell.blit(cell.subsurface(largest), largest.topleft)
                cleaned.append(clean_cell)
            else:
                cleaned.append(cell)

        cls._spawn_frames = cleaned[0:3]
        cls._active_frames = cleaned[3:12]
        cls._fade_frames = cleaned[12:14]
        cls._frames_loaded = True

    def __init__(self, x, z, duration=6.0, radius_x=34.0, radius_z=30.0):
        self.load_frames()
        self.x = x
        self.z = z
        self.duration = duration
        self.radius_x = radius_x
        self.radius_z = radius_z
        self.timer = 0.0
        self.alive = True
        self.spawn_time = 0.25
        self.fade_time = 0.35
        self.bubble_timer = 0.0
        self.bubbles = []

    @property
    def is_active(self):
        """เป็นบ่อพิษที่ยังสร้างดาเมจได้อยู่หรือไม่ (ยังไม่หมดอายุหรือเริ่มจาง)"""
        return self.alive and (self.timer < self.duration - self.fade_time)

    def contains(self, wx, wz):
        """ตรวจว่าพิกัดโลก (wx, wz) อยู่ในวงรีของบ่อพิษหรือไม่"""
        dx = (wx - self.x) / self.radius_x
        dz = (wz - self.z) / self.radius_z
        return (dx * dx + dz * dz) <= 1.0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.alive = False

        # อัปเดตฟองอากาศในบ่อ
        self.bubble_timer += dt
        if self.bubble_timer >= 0.12 and self.is_active:
            self.bubble_timer = 0.0
            bx = self.x + random.uniform(-self.radius_x * 0.6, self.radius_x * 0.6)
            bz = self.z + random.uniform(-self.radius_z * 0.6, self.radius_z * 0.6)
            self.bubbles.append(PoisonBubbleParticle(bx, bz, y_offset=0.0))

        for b in self.bubbles:
            b.update(dt)
        self.bubbles = [b for b in self.bubbles if b.life > 0]

    def get_frame(self):
        if self.timer < self.spawn_time:
            idx = min(len(self._spawn_frames) - 1, int((self.timer / self.spawn_time) * len(self._spawn_frames)))
            return self._spawn_frames[idx]
        elif self.timer >= self.duration - self.fade_time:
            fade_elapsed = self.timer - (self.duration - self.fade_time)
            idx = min(len(self._fade_frames) - 1, int((fade_elapsed / self.fade_time) * len(self._fade_frames)))
            return self._fade_frames[idx]
        else:
            active_elapsed = self.timer - self.spawn_time
            idx = int(active_elapsed * 9.0) % len(self._active_frames)
            return self._active_frames[idx]

    def draw(self, screen, camera):
        if not camera.visible(self.z):
            return
        sx, sy, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return

        # ขนาดบ่อบนโลกปรับให้สอดคล้องกับระยะที่ตัวละครเดินสุ่ม
        w_world = self.radius_x * 2.0
        h_world = self.radius_z * 2.0
        dw = max(4, int(w_world * scale))
        dh = max(4, int(h_world * scale))

        # 1. แสงเรืองรองสีม่วงรอบบ่อ (Aura)
        aura_w = int(dw * 1.15)
        aura_h = int(dh * 1.15)
        aura_surf = pygame.Surface((aura_w, aura_h), pygame.SRCALPHA)
        pulse = int(70 + 25 * math.sin(self.timer * 7.0))
        pygame.draw.ellipse(aura_surf, (130, 45, 200, pulse), (0, 0, aura_w, aura_h))
        pygame.draw.ellipse(aura_surf, (90, 20, 150, pulse // 2), (0, 0, aura_w, aura_h), width=max(1, int(2 * scale)))
        screen.blit(aura_surf, (sx - aura_w // 2, sy - aura_h // 2))

        # 2. ภาพสไปรต์แอนิเมชันของบ่อพิษ
        frame = self.get_frame()
        scaled_frame = pygame.transform.scale(frame, (dw, dh))
        screen.blit(scaled_frame, (sx - dw // 2, sy - dh // 2))

        # 3. วาดฟองอากาศที่ลอยขึ้นมา
        for b in self.bubbles:
            b.draw(screen, camera)


class PlantBoss:
    """ระบบบอสต้นไม้กินคน / ดอกไม้พิษ (Carnivorous / Venom Plant Boss)"""

    def __init__(self, z, max_hp=2000):
        self.x = 0.0
        self.z = z
        self.max_hp = max_hp
        self.hp = max_hp
        self.state = STATE_IDLE
        self.attack_mode = "chop"    # "chop" (งับกัด) หรือ "spit" (พ่นบ่อพิษ)
        self.attack_type = ATTACK_FRONT

        self.frame_width = 160
        self.frame_height = 160
        self.load_spritesheet()

        # Attack timing settings
        self.idle_duration = 1.0
        self.telegraph_duration = 0.65
        self.attack_fps = 11.0
        self.attack_strike_frame = 5
        self.attack_struck = False

        # Timers
        self.anim_timer = 0.0
        self.state_timer = 0.0
        self.hit_flash_timer = 0.0
        self.defeat_completed = False
        self.defeat_timer = 0.0

        # Player shooting
        self.shoot_timer = 0.0
        self.shoot_interval = 1.5
        self.bullets = []
        self.sparks = []

        # Danger zone / Telegraph
        self.danger_rect = None
        self.spit_target = None
        self.spit_secondary_target = None

        # Poison Pools & Spits
        self.poison_pools = []
        self.spits = []
        self.death_particles = []

    def load_spritesheet(self):
        try:
            raw = pygame.image.load(str(PLANT_ASSET_PATH))
            sheet = raw.convert_alpha() if pygame.display.get_surface() else raw
        except Exception:
            sheet = pygame.Surface((1920, 1440), pygame.SRCALPHA)
            sheet.fill((50, 120, 40))

        def get_row(row_idx, count):
            frames = []
            for col in range(count):
                rect = pygame.Rect(
                    col * self.frame_width, row_idx * self.frame_height,
                    self.frame_width, self.frame_height
                )
                frames.append(sheet.subsurface(rect))
            return frames

        # 9 แถว ขนาด 160x160:
        self.anim_idle = get_row(0, 8)
        self.anim_chop_front = get_row(1, 10)
        self.anim_chop_left = get_row(2, 10)
        self.anim_chop_right = get_row(3, 10)
        self.anim_spit_front = get_row(4, 12)
        self.anim_spit_left = get_row(5, 12)
        self.anim_spit_right = get_row(6, 12)
        self.anim_hit = get_row(7, 4)
        self.anim_defeat = get_row(8, 12)

        # เตรียม frames บ่อพิษไว้ล่วงหน้า
        PoisonPool.load_frames()

    def trigger_hit(self, damage=5):
        if self.state == STATE_DEFEAT:
            return
        self.hp = max(0, self.hp - damage)
        self.hit_flash_timer = 0.1
        if self.hp <= 0:
            self.state = STATE_DEFEAT
            self.anim_timer = 0.0
            self.state_timer = 0.0

    def start_attack(self, crowd_x=0.0, crowd_z=None):
        self.state = STATE_TELEGRAPH
        self.state_timer = 0.0
        self.attack_struck = False

        # นับจำนวนบ่อพิษที่ยังทำงานอยู่ รวมกับกระสุนพิษที่กำลังลอยในอากาศ
        current_toxic_count = len([p for p in self.poison_pools if p.is_active]) + len(self.spits)

        # จำกัดจำนวนบ่อพิษสูงสุดไม่เกิน 2 บ่อ: หากมีครบ 2 บ่อแล้ว จะไม่ออกท่าพ่นพิษเพิ่ม (ใช้ท่างับกัดแทน)
        if current_toxic_count >= 2:
            self.attack_mode = "chop"
        else:
            self.attack_mode = random.choice(["chop", "spit"])

        if self.attack_mode == "chop":
            # ท่างับกัด (รักษารูปแบบเดิม มีหน้า ซ้าย ขวา)
            zone_width = random.uniform(180, 240)
            center_x = random.uniform(-230, 230)
            min_x = center_x - zone_width / 2
            max_x = center_x + zone_width / 2
            self.danger_rect = (min_x, max_x)
            self.spit_target = None
            self.spit_secondary_target = None

            if center_x < -70:
                self.attack_type = ATTACK_LEFT
            elif center_x > 70:
                self.attack_type = ATTACK_RIGHT
            else:
                self.attack_type = ATTACK_FRONT

            self.attack_fps = 11.5
            self.attack_strike_frame = 5

        else:
            # ท่าพ่นบ่อพิษลงบนพื้น
            target_z = (crowd_z if crowd_z is not None else self.z - 260) + random.uniform(-10, 10)
            target_x = max(-240, min(240, crowd_x + random.uniform(-35, 35)))
            self.spit_target = (target_x, target_z)

            # พ่นบ่อที่ 2 เสริมเฉพาะเมื่อมีโควต้าว่างพอให้บ่อพิษรวมไม่เกิน 2 บ่อ
            available_slots = 2 - current_toxic_count
            if available_slots >= 2 and random.random() < 0.35:
                offset_side = random.choice([-80, 80])
                sec_x = max(-250, min(250, target_x + offset_side))
                self.spit_secondary_target = (sec_x, target_z + random.uniform(-15, 15))
            else:
                self.spit_secondary_target = None

            # กำหนด danger_rect ให้ครอบคลุมเป้าหมายตามขนาดบ่อใหม่
            self.danger_rect = (target_x - 35, target_x + 35)

            if target_x < -70:
                self.attack_type = ATTACK_LEFT
            elif target_x > 70:
                self.attack_type = ATTACK_RIGHT
            else:
                self.attack_type = ATTACK_FRONT

            self.attack_fps = 10.5
            self.attack_strike_frame = 5

    def launch_spit(self):
        """ยิงกระสุนพิษลอยไปสร้างบ่อพิษที่เป้าหมาย"""
        if self.spit_target:
            tx, tz = self.spit_target
            self.spits.append(PoisonSpit(self.x, self.z - 20, tx, tz, start_y=75.0, flight_time=0.45))
        if self.spit_secondary_target:
            stx, stz = self.spit_secondary_target
            self.spits.append(PoisonSpit(self.x, self.z - 20, stx, stz, start_y=75.0, flight_time=0.52))

    def update(self, dt, crowd):
        # 1. จัดการกระสุนและประกายไฟของผู้เล่น
        for b in self.bullets:
            b.update(dt)
            if not b.alive:
                self.trigger_hit(b.damage)
                for _ in range(2):
                    self.sparks.append(HitSpark(self.x, self.z, color=(140, 255, 80)))
        self.bullets = [b for b in self.bullets if b.alive]

        for s in self.sparks:
            s.update(dt)
        self.sparks = [s for s in self.sparks if s.life > 0]

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        # 2. ผู้เล่นระดมยิงใส่บอส
        crowd_count = getattr(crowd, "count", len(getattr(crowd, "people", [])))
        if self.state != STATE_DEFEAT and crowd_count > 0:
            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_interval:
                self.shoot_timer = 0.0
                hand_offset_x = 5.0
                hand_offset_z = 2.0
                members = getattr(crowd, "people", getattr(crowd, "members", []))
                for p in members:
                    bx = getattr(crowd, "x", 0.0) + getattr(p, "dx", 0.0) + hand_offset_x
                    bz = getattr(crowd, "z", 0.0) + getattr(p, "dz", 0.0) + hand_offset_z
                    self.bullets.append(Bullet(bx, bz, self.x, self.z, damage=0.5))

        # 3. อัปเดตกระสุนพ่นพิษในอากาศ
        for spit in self.spits:
            spit.update(dt)
            if not spit.alive:
                # จำกัดจำนวนบ่อพิษไม่ให้เกิน 2 บ่อ (ถ้าครบ 2 บ่อแล้วให้บ่อเก่าสุดสลายตัวทันที)
                active_pools = [p for p in self.poison_pools if p.is_active]
                if len(active_pools) >= 2:
                    oldest = min(active_pools, key=lambda p: p.duration - p.timer)
                    oldest.timer = max(oldest.timer, oldest.duration - oldest.fade_time)

                self.poison_pools.append(PoisonPool(spit.target_x, spit.target_z))
                for _ in range(8):
                    self.death_particles.append(PoisonSplashParticle(spit.target_x, spit.target_z))
        self.spits = [s for s in self.spits if s.alive]

        # 4. อัปเดตบ่อพิษบนพื้น และรับประกันจำนวนบ่อไม่เกิน 2 บ่อ
        for pool in self.poison_pools:
            pool.update(dt)
        self.poison_pools = [p for p in self.poison_pools if p.alive]
        while len(self.poison_pools) > 2:
            self.poison_pools.pop(0)

        for p in self.death_particles:
            p.update(dt)
        self.death_particles = [p for p in self.death_particles if p.life > 0]

        # 5. ตรวจจับการยืนในบ่อพิษ และการสะสม/สลายของพิษ
        members = getattr(crowd, "people", None)
        if members is not None and len(members) > 0:
            death_time = getattr(C, "POISON_DEATH_TIME", 2.0)
            victims = []
            for p in members:
                wx = crowd.x + p.dx
                wz = crowd.z + p.dz

                # ตรวจว่ายืนอยู่ในบ่อพิษใดบ่อหนึ่งที่กำลังทำงานอยู่หรือไม่
                in_poison = any(pool.is_active and pool.contains(wx, wz) for pool in self.poison_pools)

                if in_poison:
                    # ยืนในบ่อพิษ -> สะสมระยะเวลา
                    p.poison_time = getattr(p, "poison_time", 0.0) + dt
                    if p.poison_time >= death_time:
                        victims.append(p)
                else:
                    # ออกนอกบ่อพิษ -> ค่อยๆ สลายตัวด้วยอัตราเวลา 1:1 กับที่ยืนมา
                    current_t = getattr(p, "poison_time", 0.0)
                    if current_t > 0:
                        p.poison_time = max(0.0, current_t - dt)

            # คนที่สะสมพิษจนเต็มตัวจะตายทันที
            if victims:
                for v in victims:
                    for _ in range(6):
                        self.death_particles.append(
                            PoisonSplashParticle(crowd.x + v.dx, crowd.z + v.dz, color=(205, 130, 255))
                        )
                crowd.remove(victims)

        # 6. อัปเดตสถานะ AI บอส
        self.state_timer += dt
        self.anim_timer += dt

        if self.state == STATE_IDLE:
            if self.state_timer >= self.idle_duration:
                cx = getattr(crowd, "x", 0.0)
                cz = getattr(crowd, "z", None)
                self.start_attack(cx, cz)

        elif self.state == STATE_TELEGRAPH:
            if self.state_timer >= self.telegraph_duration:
                self.state = STATE_ATTACK
                self.state_timer = 0.0
                self.anim_timer = 0.0

        elif self.state == STATE_ATTACK:
            frame_idx = int(self.anim_timer * self.attack_fps)
            if frame_idx >= self.attack_strike_frame and not self.attack_struck:
                self.attack_struck = True
                if self.attack_mode == "chop":
                    self.execute_attack_damage(crowd)
                else:
                    self.launch_spit()

            max_frames = 10 if self.attack_mode == "chop" else 12
            if frame_idx >= max_frames:
                self.state = STATE_IDLE
                self.state_timer = 0.0
                self.anim_timer = 0.0
                self.danger_rect = None
                self.spit_target = None
                self.spit_secondary_target = None

        elif self.state == STATE_DEFEAT:
            self.defeat_timer += dt
            if self.defeat_timer >= 2.0:
                self.defeat_completed = True

    def execute_attack_damage(self, target):
        """คำนวณดาเมจการงับกัด (Chop) ต่อฝูงผู้เล่น"""
        if not self.danger_rect:
            return

        min_x, max_x = self.danger_rect
        if hasattr(target, "people") and target.count > 0:
            hit_people = []
            for p in target.people:
                px = target.x + p.dx
                pr = getattr(p, "radius", 5.0)
                if (min_x - pr) <= px <= (max_x + pr):
                    hit_people.append(p)
            if hit_people:
                target.remove(hit_people)

        elif hasattr(target, "members") and target.count > 0:
            hit_enemies = []
            for m in target.members:
                mx = target.x + m.dx
                mr = getattr(m, "radius", 5.0)
                if (min_x - mr) <= mx <= (max_x + mr):
                    hit_enemies.append(m)
            for m in hit_enemies:
                if m in target.members:
                    target.members.remove(m)
            target.count = max(0, target.count - len(hit_enemies))

    def get_current_frame(self):
        """ดึงเฟรมแอนิเมชันของบอสตามสถานะปัจจุบัน"""
        if self.state == STATE_IDLE:
            if self.hit_flash_timer > 0 and len(self.anim_hit) > 0:
                idx = min(len(self.anim_hit) - 1, int((0.1 - self.hit_flash_timer) * 30))
                return self.anim_hit[idx]
            idx = int(self.anim_timer * 7.5) % len(self.anim_idle)
            return self.anim_idle[idx]

        elif self.state == STATE_TELEGRAPH:
            idx = int(self.anim_timer * 9.0) % len(self.anim_idle)
            return self.anim_idle[idx]

        elif self.state == STATE_ATTACK:
            if self.attack_mode == "chop":
                if self.attack_type == ATTACK_LEFT:
                    frames = self.anim_chop_left
                elif self.attack_type == ATTACK_RIGHT:
                    frames = self.anim_chop_right
                else:
                    frames = self.anim_chop_front
            else:
                if self.attack_type == ATTACK_LEFT:
                    frames = self.anim_spit_left
                elif self.attack_type == ATTACK_RIGHT:
                    frames = self.anim_spit_right
                else:
                    frames = self.anim_spit_front

            idx = min(len(frames) - 1, int(self.anim_timer * self.attack_fps))
            return frames[idx]

        elif self.state == STATE_DEFEAT:
            idx = min(len(self.anim_defeat) - 1, int(self.defeat_timer * 6.0))
            return self.anim_defeat[idx]

        return self.anim_idle[0]

    def draw_telegraph(self, screen, camera, finish_z):
        """วาดโซนอันตรายล่วงหน้า (Telegraph) ก่อนการโจมตี"""
        if self.state not in (STATE_TELEGRAPH, STATE_ATTACK):
            return

        if self.attack_mode == "chop" and self.danger_rect:
            min_x, max_x = self.danger_rect
            near_z = finish_z - 80
            far_z = finish_z + 120

            p1 = camera.project(min_x, near_z)[:2]
            p2 = camera.project(max_x, near_z)[:2]
            p3 = camera.project(max_x, far_z)[:2]
            p4 = camera.project(min_x, far_z)[:2]

            if self.state == STATE_ATTACK:
                if int(self.state_timer * 20) % 2 == 0:
                    color = (0, 0, 0, 230)
                    border_color = (0, 0, 0, 255)
                else:
                    color = (180, 40, 220, 200)
                    border_color = (120, 255, 60, 240)
            else:
                alpha = int(120 + 80 * math.sin(self.state_timer * 15))
                color = (200, 40, 60, alpha)
                border_color = (100, 230, 80, 240)

            poly_surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
            pygame.draw.polygon(poly_surf, color, [p1, p2, p3, p4])
            pygame.draw.polygon(poly_surf, border_color, [p1, p2, p3, p4], width=3)
            screen.blit(poly_surf, (0, 0))

        elif self.attack_mode == "spit":
            targets = [t for t in [self.spit_target, self.spit_secondary_target] if t is not None]
            for tx, tz in targets:
                rad_x = 35.0
                rad_z = 31.0
                pts = []
                num_pts = 16
                for i in range(num_pts):
                    ang = (i / num_pts) * 2 * math.pi
                    wx = tx + math.cos(ang) * rad_x
                    wz = tz + math.sin(ang) * rad_z
                    pts.append(camera.project(wx, wz)[:2])

                alpha = int(110 + 70 * math.sin(self.state_timer * 16))
                color = (160, 40, 220, alpha)
                border_color = (120, 255, 60, 230)

                poly_surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
                pygame.draw.polygon(poly_surf, color, pts)
                pygame.draw.polygon(poly_surf, border_color, pts, width=3)

                # วงระลอกคลื่นด้านใน
                inner_pts = []
                inner_scale = 0.5 + 0.3 * (0.5 + 0.5 * math.sin(self.state_timer * 12))
                for i in range(num_pts):
                    ang = (i / num_pts) * 2 * math.pi
                    wx = tx + math.cos(ang) * (rad_x * inner_scale)
                    wz = tz + math.sin(ang) * (rad_z * inner_scale)
                    inner_pts.append(camera.project(wx, wz)[:2])
                pygame.draw.polygon(poly_surf, (200, 80, 255, 180), inner_pts, width=2)

                screen.blit(poly_surf, (0, 0))

    def draw(self, screen, camera):
        # 1. วาดบ่อพิษบนพื้นก่อนตัวละครและบอส
        for pool in self.poison_pools:
            pool.draw(screen, camera)

        # 2. วาดกระสุนพ่นพิษในอากาศ
        for spit in self.spits:
            spit.draw(screen, camera)

        # 3. วาดละอองพิษและประกายไฟ
        for p in self.death_particles:
            p.draw(screen, camera)
        for s in self.sparks:
            s.draw(screen, camera)

        # 4. วาดกระสุนคนยิง
        for b in self.bullets:
            b.draw(screen, camera)

        if not camera.visible(self.z):
            return

        sx, sy, scale = camera.project(self.x, self.z)
        if scale <= 0:
            return

        # ขนาดตัวบอส
        boss_world_w = self.frame_width * 3.0
        boss_world_h = self.frame_height * 3.0
        draw_w = max(4, int(boss_world_w * scale))
        draw_h = max(4, int(boss_world_h * scale))

        # เงาของบอสบนพื้น
        shadow_w = int(draw_w * 1.5)
        shadow_h = int(draw_h * 0.5)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 120), (0, 0, shadow_w, shadow_h))
        screen.blit(shadow_surf, (sx - shadow_w // 2, sy - shadow_h // 2))

        # ดึงภาพเฟรมปัจจุบัน
        frame = self.get_current_frame()
        scaled_frame = pygame.transform.scale(frame, (draw_w, draw_h))

        sink_offset = 0
        if self.state == STATE_DEFEAT:
            sink_offset = int(min(1.0, self.defeat_timer / 2.0) * draw_h * 0.3)

        boss_pos = (sx - draw_w // 2, sy - draw_h + int(10 * scale) + sink_offset)
        screen.blit(scaled_frame, boss_pos)

        # แฟลชสีขาวเวลารับดาเมจ
        if self.hit_flash_timer > 0 and self.state != STATE_DEFEAT:
            mask = pygame.mask.from_surface(scaled_frame)
            flash_surf = mask.to_surface(setcolor=(255, 255, 255, 190), unsetcolor=(0, 0, 0, 0))
            screen.blit(flash_surf, boss_pos)

    def draw_hud(self, screen, font):
        """วาดหลอดเลือดบอส (Boss HP Bar) ด้านบนสุดของหน้าจอ"""
        bar_w = 340
        bar_h = 16
        bar_x = (C.SCREEN_W - bar_w) // 2
        bar_y = 35

        name_surf = font.render("=== VENOM PLANT ===", True, (130, 240, 80))
        name_rect = name_surf.get_rect(center=(C.SCREEN_W // 2, bar_y - 14))
        screen.blit(name_surf, name_rect)

        bg_rect = pygame.Rect(bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4)
        pygame.draw.rect(screen, (20, 20, 30), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (70, 100, 70), bg_rect, width=2, border_radius=6)

        hp_ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            pygame.draw.rect(screen, (80, 200, 60), fill_rect, border_radius=4)

        hp_val = int(math.ceil(self.hp))
        hp_text = font.render(f"{hp_val} / {self.max_hp}", True, C.WHITE)
        hp_rect = hp_text.get_rect(center=(C.SCREEN_W // 2, bar_y + bar_h // 2))
        screen.blit(hp_text, hp_rect)


BOSS_MAP = {
    "scorpion": ScorpionBoss,
    "plant": PlantBoss,
}


def get_boss_class(name):
    """Retrieve boss class corresponding to a level string ('scorpion' or 'plant').

    Args:
        name (str | None): Boss identifier.

    Returns:
        type | None: ScorpionBoss or PlantBoss class, or None if not found.
    """
    if not name:
        return None
    return BOSS_MAP.get(str(name).lower())


def spawn_boss(boss_identifier, finish_z, z_offset=260):
    """Factory function to instantiate the correct boss for a level with default HP and positioning.

    Args:
        boss_identifier (str | type | None): Boss class or name string ('scorpion', 'plant').
        finish_z (float): Track end distance where arena begins.
        z_offset (float): Forward distance offset on arena platform (default +260).

    Returns:
        ScorpionBoss | PlantBoss | None: Configured boss instance.
    """
    if isinstance(boss_identifier, type):
        boss_class = boss_identifier
    else:
        boss_class = get_boss_class(boss_identifier)

    if not boss_class:
        return None

    z = finish_z + z_offset
    hp = 1000 if boss_class == ScorpionBoss else 1500
    return boss_class(z=z, max_hp=hp)




