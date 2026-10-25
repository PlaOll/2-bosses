"""Main Game Entry Point: State machine, event handling, and core loop execution.

Run:
    python main.py

States:
    MENU     --(Select level: Space/Return/Click)--> PLAYING
    PLAYING  --(Reach finish line)---------------> WIN
             +--(Crowd count reaches 0)----------> LOSE
    WIN/LOSE --(R: Restart)----------------------> PLAYING
             --(M: Menu)-------------------------> MENU
"""
import sys
from pathlib import Path
import pygame

import config as C
import ui
import scores
from camera import Camera
from crowd import Crowd
from level import load_level, list_levels, best_count
from boss import get_boss_class, spawn_boss
from theme import get_theme

# Game State Constants
MENU, PLAYING, WIN, LOSE = "menu", "playing", "win", "lose"


class Game:
    """Core Game Controller: orchestrates window lifecycle, inputs, updates, and rendering."""

    def __init__(self):
        """Initialize Pygame display, fonts, camera, progression, and initial level state."""
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.dt = 1.0 / C.FPS                   # Initial delta time per frame
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 64)
        self.camera = Camera()
        self.level_files = list_levels()
        self.level_names = [(f, load_level(f).name) for f in self.level_files]
        self.selected = 0                       # Currently highlighted level index in the menu
        self.scores = scores.load_scores()      # High scores dictionary loaded from disk
        self.unlock_all = False                 # Toggle with 'U' key in menu to unlock all stages for debugging
        self.show_hitboxes = False              # Toggle with 'F' key to show hitboxes
        self.state = MENU                       # Current state machine state
        self.reset()

    def reset(self):
        """Reset or load all gameplay objects and environment assets for the selected level."""
        self.level = load_level(self.level_files[self.selected])
        self.theme = get_theme(getattr(self.level, "theme", "plains"))
        self.road_rows = self.theme.make_road_rows()
        self.tuft_sprites = self.theme.make_tuft_sprites()
        self.clouds = self.theme.make_clouds()
        self.result = None                      # Endgame result tuple: (stars, old_score, is_new_record)
        self.best = best_count(self.level)      # Calculated prior to play (enemies reduce count on contact)
        self.crowd = Crowd(self.level.start_count)
        self.camera.z = 0.0
        self.camera.follow_x = 0.0
        self.next_index = 0                     # Index of oncoming track object in level.objects
        self.boss = None                        # Active boss instance (spawned when reaching finish line)
        self.is_boss_fight = False              # True during active arena combat
        self.boss_class = get_boss_class(getattr(self.level, "boss", None))
        self.has_boss = self.boss_class is not None
        self.tufts, self.tuft_zs = self.theme.generate_tufts(self.level.finish_z, len(self.tuft_sprites))

    # ==========================================================================
    # Input & Event Handling
    # ==========================================================================
    def handle_events(self):
        """Process keyboard, mouse, and system window events per frame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.show_hitboxes = not self.show_hitboxes

                if self.state == MENU:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.move_selection(-1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.move_selection(1)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.start_level()
                    elif event.key == pygame.K_u:
                        self.unlock_all = not self.unlock_all
                        if not self.unlocked(self.selected):
                            self.selected = 0
                elif self.state in (WIN, LOSE):
                    if event.key == pygame.K_r:
                        self.start_level()
                    elif event.key == pygame.K_m:
                        # If won, automatically highlight the newly unlocked next level
                        if self.state == WIN and self.unlocked(self.selected + 1):
                            self.selected += 1
                        self.reset()
                        self.state = MENU

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == MENU:
                clicked = ui.get_clicked_menu_level(event.pos, self.level_files, self.scores, self.unlock_all)
                if clicked is not None:
                    self.selected = clicked
                    self.start_level()

        # Continuous runner movement input during PLAYING
        if self.state == PLAYING:
            keys = pygame.key.get_pressed()
            direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            speed = 250 if self.is_boss_fight else self.level.speed
            self.crowd.move(direction, self.dt, speed)

    def unlocked(self, i):
        """Check if level index i is playable."""
        return scores.is_level_unlocked(self.level_files, i, self.scores, self.unlock_all)

    def move_selection(self, step):
        """Cycle menu selection to the next unlocked level."""
        self.selected = scores.next_unlocked_level(
            self.level_files, self.selected, step, self.scores, self.unlock_all
        )

    def start_level(self):
        """Transition into PLAYING state."""
        self.reset()
        self.state = PLAYING

    def finish_level(self, won):
        """Triggered once when the level ends: records high score and computes star rating."""
        filename = self.level_files[self.selected]
        count = self.crowd.count if won else 0
        self.result, self.scores = scores.finish_level_result(
            filename, won, count, self.best, self.scores
        )
        self.state = WIN if won else LOSE

    # ==========================================================================
    # State Updates
    # ==========================================================================
    def update(self):
        """Update physics, camera tracking, collisions, and boss battle state."""
        if self.state != PLAYING:
            return

        # ---------------- Boss Battle Phase ----------------
        if self.is_boss_fight:
            # Lock camera and crowd forward Z progress to the arena platform
            self.camera.z = self.level.finish_z - C.CROWD_OFFSET
            self.crowd.z = self.level.finish_z
            self.crowd.road_half_w = 340  # Broaden side-stepping boundary on arena platform
            self.crowd.update(self.dt)
            self.camera.follow(self.crowd.x, self.dt, speed=6.0)

            if self.boss:
                self.boss.update(self.dt, self.crowd)
                if self.crowd.count <= 0:
                    self.finish_level(False)
                elif self.boss.defeat_completed:
                    self.finish_level(True)
            return

        # ---------------- Normal Running Phase ----------------
        self.camera.z += self.level.speed * self.dt
        self.crowd.z = self.camera.z + C.CROWD_OFFSET
        self.crowd.update(self.dt)
        self.camera.follow(self.crowd.x, self.dt)

        # Trigger object contact (gates, obstacles, enemies)
        self.next_index = self.level.check_reach(self.crowd, self.next_index)
        self.level.update_objects(self.dt, self.crowd)

        # Win/Loss and Boss transition checks
        if self.crowd.count <= 0:
            self.finish_level(False)
        elif self.has_boss and self.crowd.z >= self.level.finish_z:
            self.is_boss_fight = True
            self.crowd.z = self.level.finish_z
            self.crowd.road_half_w = 340
            self.camera.z = self.level.finish_z - C.CROWD_OFFSET
            self.boss = spawn_boss(self.level.boss, self.level.finish_z)
        elif not self.has_boss and self.crowd.all_crossed(self.level.finish_z):
            self.finish_level(True)


    # ==========================================================================
    # Rendering
    # ==========================================================================
    def draw_world(self):
        """Render all 3D perspective world elements in depth-sorted painter's order."""
        cam = self.camera

        # 1. Environment background (sky, terrain bands, road scanlines, tufts)
        self.theme.draw_background(
            self.screen, cam, self.level, self.is_boss_fight,
            self.tufts, self.tuft_zs, self.tuft_sprites, self.road_rows, self.clouds
        )

        # 2. Boss Arena or Finish Line
        if self.has_boss and (cam.visible(self.level.finish_z) or cam.visible(self.level.finish_z + 300)):
            self.theme.draw_arena(self.screen, cam, self.level.finish_z)
        elif not self.has_boss:
            self.level.draw_finish_line(self.screen, cam)

        # 3. Track objects (sorted from furthest to nearest)
        self.level.draw_objects(self.screen, cam, self.font)

        # 4. Boss entity and telegraph danger zones
        if self.boss:
            self.boss.draw_telegraph(self.screen, cam, self.level.finish_z)
            self.boss.draw(self.screen, cam)

        # 5. Player crowd (nearest to camera)
        self.crowd.draw(self.screen, cam, self.font)

        # 6. Debug collision hitboxes
        if self.show_hitboxes:
            self.draw_hitboxes()

    def draw_hitboxes(self):
        """Render collision wireframes and hitboxes for all active game entities."""
        cam = self.camera

        # 1. Track objects (gates, obstacles, enemies)
        for obj in self.level.objects:
            if hasattr(obj, "draw_hitbox"):
                obj.draw_hitbox(self.screen, cam)

        # 2. Boss
        if self.boss and hasattr(self.boss, "draw_hitbox"):
            self.boss.draw_hitbox(self.screen, cam)

        # 3. Player Crowd
        if hasattr(self.crowd, "draw_hitbox"):
            self.crowd.draw_hitbox(self.screen, cam)


    def draw(self):
        """Render active game screen based on state machine."""
        if self.state == MENU:
            unlocked = [self.unlocked(i) for i in range(len(self.level_files))]
            ui.draw_menu(self.screen, self.big_font, self.font, self.level_names, self.selected, self.scores,
                         unlocked, self.unlock_all)
        else:
            self.draw_world()
            if self.is_boss_fight and self.boss:
                self.boss.draw_hud(self.screen, self.font)
            else:
                progress = self.crowd.z / self.level.finish_z
                ui.draw_hud(self.screen, self.font, self.level, progress)
            if self.state in (WIN, LOSE):
                ui.draw_end(self.screen, self.big_font, self.font, self.state == WIN, self.crowd.count,
                            *self.result)
        pygame.display.flip()

    def run(self):
        """Execute the primary game loop with delta-time clamping."""
        while True:
            # Clamp dt to max 0.05 (20 FPS) to prevent collision tunneling during lag spikes
            self.dt = min(self.clock.tick(C.FPS) / 1000, 0.05)
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    # Command line options to switch level directories for testing
    if "--random" in sys.argv:
        from level import set_level_dir
        set_level_dir(Path(__file__).parent / "random_levels")
    elif "--levels" in sys.argv:
        idx = sys.argv.index("--levels")
        if idx + 1 < len(sys.argv):
            from level import set_level_dir
            set_level_dir(Path(__file__).parent / sys.argv[idx + 1])
    Game().run()
