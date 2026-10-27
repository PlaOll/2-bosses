"""Theme and Environmental Rendering System: Plains, Desert, and Jungle environments.

Handles custom color palettes, sky gradients, brick road textures, pixel clouds,
procedural shrub/tuft generation, and boss battle arenas.
"""
import bisect
import random
import pygame
import config as C


class Theme:
    """Encapsulates color palettes and rendering routines for an environmental theme."""

    def __init__(
        self,
        name,
        sky_top,
        sky_bottom,
        ground_a,
        ground_b,
        road_base,
        road_mortar,
        road_bricks,
        road_edge,
        tuft_colors,
        arena_floor,
        arena_grid,
        arena_border,
        cloud_white=(245, 248, 255),
        cloud_shade=(214, 226, 245),
    ):
        """Initialize theme parameters.

        Args:
            name (str): Theme identifier (e.g. 'plains', 'desert', 'jungle').
            sky_top (tuple): RGB color at the top of the screen.
            sky_bottom (tuple): RGB color near the horizon.
            ground_a (tuple): Alternating ground grass/sand band color A.
            ground_b (tuple): Alternating ground grass/sand band color B.
            road_base (tuple): Base road color.
            road_mortar (tuple): Road brick mortar color.
            road_bricks (list[tuple]): List of RGB colors for randomized brick pattern.
            road_edge (tuple): Outer edge border stripe color.
            tuft_colors (tuple[tuple, tuple]): (dark_shade, light_shade) for foliage sprites.
            arena_floor (tuple): Boss arena floor fill color.
            arena_grid (tuple): Boss arena floor grid line color.
            arena_border (tuple): Boss arena outer perimeter glow color.
            cloud_white (tuple): Pixel cloud highlighted pixel color.
            cloud_shade (tuple): Pixel cloud bottom shadow pixel color.
        """
        self.name = name
        self.sky_top = sky_top
        self.sky_bottom = sky_bottom
        self.ground_a = ground_a
        self.ground_b = ground_b
        self.road_base = road_base
        self.road_mortar = road_mortar
        self.road_bricks = road_bricks
        self.road_edge = road_edge
        self.tuft_colors = tuft_colors
        self.arena_floor = arena_floor
        self.arena_grid = arena_grid
        self.arena_border = arena_border
        self.cloud_white = cloud_white
        self.cloud_shade = cloud_shade

    def make_road_rows(self, w=96, h=128):
        """Generate a procedural brick road texture and slice it into 1-pixel horizontal rows.

        Pre-slicing allows texture mapping in pseudo-3D by blitting single rows scaled to distance.

        Args:
            w (int): Pattern width in pixels.
            h (int): Pattern height in pixels.

        Returns:
            list[pygame.Surface]: List of 1-pixel high surface slices.
        """
        rng = random.Random(7)
        bw, bh = 16, 8
        tex = pygame.Surface((w, h))
        tex.fill(self.road_mortar)
        for row in range(h // bh):
            shift = (bw // 2) if row % 2 else 0
            for col in range(w // bw):
                color = rng.choice(self.road_bricks)
                light = tuple(min(255, c + 14) for c in color)
                x0 = col * bw + shift
                y0 = row * bh
                for dy in range(bh - 1):
                    for dx in range(bw - 1):
                        c = light if dy == 0 else color
                        tex.set_at(((x0 + dx) % w, y0 + dy), c)
        return [tex.subsurface((0, i, w, 1)).copy() for i in range(h)]

    def make_tuft_sprites(self):
        """Generate 3 randomized foliage/shrub sprite variations matching the theme palette.

        Returns:
            list[pygame.Surface]: List of 3 small sprite surfaces with alpha channels.
        """
        rng = random.Random(3)
        dark, light = self.tuft_colors
        sprites = []
        for _ in range(3):
            surf = pygame.Surface((9, 6), pygame.SRCALPHA)
            for bx in (1, 4, 7):
                hgt = rng.randint(2, 5)
                for y in range(hgt):
                    surf.set_at((bx, 5 - y), light if y == hgt - 1 else dark)
            sprites.append(surf)
        return sprites

    def make_clouds(self):
        """Generate retro blocky pixel cloud surfaces scaled for display.

        Returns:
            list[pygame.Surface]: List of scaled cloud surfaces.
        """
        shapes = [
            [(2, 3, 10, 3), (0, 4, 14, 3), (4, 1, 6, 3)],
            [(1, 2, 8, 3), (0, 3, 11, 2), (3, 0, 4, 3)],
        ]
        clouds = []
        for rects in shapes:
            surf = pygame.Surface((15, 8), pygame.SRCALPHA)
            for x, y, w, h in rects:
                pygame.draw.rect(surf, self.cloud_white, (x, y, w, h))
            pygame.draw.rect(surf, self.cloud_shade, (0, 6, 14, 1))
            clouds.append(pygame.transform.scale(surf, (15 * 8, 8 * 8)))
        return clouds

    def generate_tufts(self, finish_z, sprite_count):
        """Pre-generate roadside tuft coordinates along the track, sorted by Z.

        Args:
            finish_z (float): Track end distance in world units.
            sprite_count (int): Number of available sprite variants to pick from.

        Returns:
            tuple[list[tuple[int, float, int]], list[int]]:
                - tufts: List of (z, x, sprite_index)
                - tuft_zs: List of z coordinates corresponding to each tuft for fast bisect range queries.
        """
        rng = random.Random(11)
        tufts = []
        for z in range(0, int(finish_z) + 400, 40):
            for _ in range(2):
                side = rng.choice((-1, 1))
                x = side * rng.uniform(C.ROAD_HALF_W + 30, C.ROAD_HALF_W + 700)
                tufts.append((z, x, rng.randrange(sprite_count)))
        tuft_zs = [t[0] for t in tufts]
        return tufts, tuft_zs

    def draw_sky(self, screen, clouds):
        """Render multi-band gradient sky and animated drifting pixel clouds.

        Args:
            screen (pygame.Surface): Screen surface.
            clouds (list[pygame.Surface]): Pre-rendered cloud sprites.
        """
        bands = 8
        h = C.HORIZON_Y
        for i in range(bands):
            t = i / (bands - 1)
            color = tuple(int(self.sky_top[k] + (self.sky_bottom[k] - self.sky_top[k]) * t) for k in range(3))
            screen.fill(color, (0, i * h // bands, C.SCREEN_W, h // bands + 1))

        t = pygame.time.get_ticks() / 1000
        for cloud, y, speed, x0 in (
            (clouds[0], 50, 12, 80),
            (clouds[1], 110, 8, 300),
            (clouds[0], 170, 5, 520),
        ):
            x = (x0 + t * speed) % (C.SCREEN_W + 240) - 120
            screen.blit(cloud, (x, min(y, h - cloud.get_height())))

    def draw_background(self, screen, cam, level, is_boss_fight, tufts, tuft_zs, tuft_sprites, road_rows, clouds):
        """Render complete world background: sky, striped ground planes, textured road, and foliage.

        Args:
            screen (pygame.Surface): Display surface.
            cam (Camera): Active camera.
            level (Level): Active level.
            is_boss_fight (bool): Whether currently locked in boss arena fight.
            tufts (list): List of roadside tuft tuples (z, x, sprite_idx).
            tuft_zs (list): Sorted list of tuft Z values for binary search slicing.
            tuft_sprites (list): Foliage sprite images.
            road_rows (list): 1-pixel high textured road rows.
            clouds (list): Cloud sprite images.
        """
        near, far = cam.z + C.Z_NEAR, cam.z + C.Z_FAR

        # 1. Sky and clouds
        self.draw_sky(screen, clouds)

        # 2. Alternating ground terrain stripes
        ground_top = C.HORIZON_Y
        screen.fill(self.ground_a, (0, ground_top, C.SCREEN_W, C.SCREEN_H - ground_top))

        band_depth = 60
        first_band = int(near // band_depth)
        last_band = int(far // band_depth) + 1
        for b in range(first_band, last_band):
            if b % 2 == 1:
                z1 = max(near, b * band_depth)
                z2 = min(far, (b + 1) * band_depth)
                if z1 < z2:
                    _, y1, _ = cam.project(0, z1)
                    _, y2, _ = cam.project(0, z2)
                    y_top = max(ground_top, int(min(y1, y2)))
                    y_bot = min(C.SCREEN_H, int(max(y1, y2)))
                    if y_bot > y_top:
                        screen.fill(self.ground_b, (0, y_top, C.SCREEN_W, y_bot - y_top + 1))

        # 3. Base road polygon fill and textured surface (completely hidden during boss fight)
        if not is_boss_fight:
            has_boss = getattr(level, "boss", None) is not None
            road_end_z = (level.finish_z - 100) if has_boss else (level.finish_z + 400)
            road_far = min(far, road_end_z)
            if road_far > near:
                # Curb border width in world units (adjust to make side borders thicker/thinner)
                curb_world_w = 8.0
                curb_tile = 60.0  # Segment length along Z for alternating curb color blocks

                # Base polygon covers road + curbs to prevent seam gaps with grass
                p_near_l = cam.project(-C.ROAD_HALF_W - curb_world_w, near)[:2]
                p_near_r = cam.project(C.ROAD_HALF_W + curb_world_w, near)[:2]
                p_far_r = cam.project(C.ROAD_HALF_W + curb_world_w, road_far)[:2]
                p_far_l = cam.project(-C.ROAD_HALF_W - curb_world_w, road_far)[:2]
                pygame.draw.polygon(screen, self.road_base, [p_near_l, p_near_r, p_far_r, p_far_l])

                # Precalculate alternating curb colors (primary theme edge color and darker accent)
                curb_color_a = self.road_edge
                curb_color_b = tuple(max(0, c - 45) for c in self.road_edge)

                # Textured brick pattern on the road (seamless tiling) with perspective side borders
                step, tile = 4, 200
                n = len(road_rows)
                z_curr = near
                while z_curr < road_far:
                    z1 = min(z_curr + step, road_far)
                    xl, y0, s0 = cam.project(-C.ROAD_HALF_W, z_curr)
                    xr, _, _ = cam.project(C.ROAD_HALF_W, z_curr)
                    _, y1, _ = cam.project(0, z1)
                    w, h = int(xr - xl), int(abs(y0 - y1)) + 1
                    y_pos = int(min(y0, y1))

                    if w > 0 and h > 0:
                        # Render central brick texture slice
                        v = (z_curr % tile) / tile
                        row = road_rows[min(n - 1, int(v * n))]
                        screen.blit(pygame.transform.scale(row, (w, h)), (int(xl), y_pos))

                        # Render left and right side borders (curbs) with perspective scaling
                        curb_w = max(2, int(curb_world_w * s0))
                        curb_color = curb_color_a if (int(z_curr) // curb_tile) % 2 == 0 else curb_color_b
                        # Left border curb
                        pygame.draw.rect(screen, curb_color, (int(xl) - curb_w, y_pos, curb_w, h))
                        # Right border curb
                        pygame.draw.rect(screen, curb_color, (int(xr), y_pos, curb_w, h))

                    z_curr = z1

                # Dashed center dividing line along the road (x = 0)
                dash_step = 200
                dash_z = (int(near) // dash_step + 1) * dash_step
                while dash_z < road_far:
                    x1, y1, s1 = cam.project(0, dash_z)
                    x2, y2, _ = cam.project(0, min(road_far, dash_z + dash_step / 2))
                    pygame.draw.line(screen, self.road_edge, (x1, y1), (x2, y2), max(2, int(4 * s1)))
                    dash_z += dash_step

        # 4. Roadside tufts/bushes with perspective scaling
        i_start = bisect.bisect_left(tuft_zs, near)
        i_end = bisect.bisect_right(tuft_zs, far)
        for z, x, sprite_idx in reversed(tufts[i_start:i_end]):
            sx, sy, scale = cam.project(x, z)
            if scale > 0.05:
                spr = tuft_sprites[sprite_idx]
                w = max(1, int(spr.get_width() * scale * 2.2))
                h = max(1, int(spr.get_height() * scale * 2.2))
                screen.blit(pygame.transform.scale(spr, (w, h)), (int(sx - w // 2), int(sy - h)))

    def draw_arena(self, screen, cam, finish_z):
        """Render wide boss battle platform arena floor, grid lines, and perimeter borders.

        Args:
            screen (pygame.Surface): Display surface.
            cam (Camera): Active camera.
            finish_z (float): Track end distance where arena begins.
        """
        arena_w = 340
        arena_near = finish_z - 100
        arena_far = finish_z + 380

        p1 = cam.project(-arena_w, arena_near)[:2]
        p2 = cam.project(arena_w, arena_near)[:2]
        p3 = cam.project(arena_w, arena_far)[:2]
        p4 = cam.project(-arena_w, arena_far)[:2]

        # Arena floor polygon
        pygame.draw.polygon(screen, self.arena_floor, [p1, p2, p3, p4])

        # Floor grid lines
        for grid_x in (-240, -120, 0, 120, 240):
            g_start = cam.project(grid_x, arena_near)[:2]
            g_end = cam.project(grid_x, arena_far)[:2]
            pygame.draw.line(screen, self.arena_grid, g_start, g_end, 1)
        for grid_z in (finish_z + 60, finish_z + 180, finish_z + 300):
            g_left = cam.project(-arena_w, grid_z)[:2]
            g_right = cam.project(arena_w, grid_z)[:2]
            pygame.draw.line(screen, self.arena_grid, g_left, g_right, 1)

        # Glowing perimeter borders
        pygame.draw.line(screen, self.arena_border, p1, p4, 4)
        pygame.draw.line(screen, self.arena_border, p2, p3, 4)
        pygame.draw.line(screen, self.arena_border, p3, p4, 4)


# Predefined environment themes
THEMES = {
    "plains": Theme(
        name="plains",
        sky_top=(70, 140, 230),
        sky_bottom=(170, 215, 250),
        ground_a=C.GROUND_A,
        ground_b=C.GROUND_B,
        road_base=C.ROAD,
        road_mortar=(70, 62, 62),
        road_bricks=[(150, 98, 82), (160, 106, 88), (140, 90, 76), (168, 114, 94), (132, 88, 78)],
        road_edge=C.ROAD_EDGE,
        tuft_colors=((60, 120, 64), (130, 200, 105)),
        arena_floor=(65, 62, 75),
        arena_grid=(85, 80, 95),
        arena_border=(240, 180, 50),
    ),
    "desert": Theme(  # Scorpion Boss theme: warm dunes, sandstone road
        name="desert",
        sky_top=(230, 125, 60),
        sky_bottom=(255, 205, 140),
        ground_a=(215, 175, 105),
        ground_b=(195, 155, 90),
        road_base=(175, 135, 85),
        road_mortar=(115, 85, 50),
        road_bricks=[(205, 155, 95), (218, 170, 110), (190, 140, 85), (225, 180, 120), (180, 130, 75)],
        road_edge=(240, 210, 150),
        tuft_colors=((155, 115, 55), (215, 175, 90)),  # dry desert shrubs
        arena_floor=(115, 80, 55),
        arena_grid=(145, 105, 75),
        arena_border=(255, 150, 40),
        cloud_white=(255, 240, 220),
        cloud_shade=(230, 205, 180),
    ),
    "jungle": Theme(  # Plant Boss theme: misty rainforest, mossy stone road
        name="jungle",
        sky_top=(25, 80, 70),
        sky_bottom=(90, 165, 130),
        ground_a=(35, 75, 45),
        ground_b=(25, 60, 35),
        road_base=(55, 80, 65),
        road_mortar=(35, 50, 38),
        road_bricks=[(75, 100, 80), (88, 112, 90), (65, 88, 70), (98, 122, 95), (60, 80, 65)],
        road_edge=(110, 170, 130),
        tuft_colors=((20, 60, 30), (55, 150, 75)),  # lush tropical foliage
        arena_floor=(45, 68, 50),
        arena_grid=(65, 92, 70),
        arena_border=(100, 240, 110),
        cloud_white=(225, 245, 235),
        cloud_shade=(180, 210, 195),
    ),
}


def get_theme(name):
    """Retrieve Theme configuration by name, falling back to 'plains' if not found.

    Args:
        name (str | None): Theme identifier name.

    Returns:
        Theme: Corresponding Theme instance.
    """
    if not name:
        return THEMES["plains"]
    return THEMES.get(str(name).lower(), THEMES["plains"])
