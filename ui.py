"""UI and Screen Overlay Systems: Menu screen, in-game HUD progress bar, and Win/Lose end screens."""
import math
import pygame
import config as C

# UI Layout and Palette constants
MENU_TOP = 190                # Screen Y pixel coordinate of the first level row in the menu
MENU_ROW_H = 44               # Vertical pixel height of each level item button
STAR_ON = (255, 205, 40)      # Bright gold color for earned stars
STAR_OFF = (90, 100, 130)     # Dim grey-blue color for unearned stars


def draw_text_center(screen, font, text, y, color=C.WHITE):
    """Render a text surface horizontally centered on the screen at a given Y coordinate.

    Args:
        screen (pygame.Surface): Target drawing surface.
        font (pygame.font.Font): Font used for text.
        text (str): String content to render.
        y (int): Vertical center Y pixel position.
        color (tuple): RGB color tuple.
    """
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, y)))


def menu_row_rect(i):
    """Calculate the interactive bounding rectangle for level row index i.

    Args:
        i (int): Level row index in the menu list.

    Returns:
        pygame.Rect: Bounding rectangle used for rendering and mouse click detection.
    """
    return pygame.Rect(30, MENU_TOP + i * MENU_ROW_H, C.SCREEN_W - 60, MENU_ROW_H - 6)


def get_clicked_menu_level(pos, level_files, scores, unlock_all=False):
    """Detect which playable level was clicked on the menu screen.

    Args:
        pos (tuple[int, int]): (x, y) mouse click coordinates.
        level_files (list[str]): List of all level filenames.
        scores (dict): Dictionary of loaded high scores.
        unlock_all (bool): Debug unlock flag override.

    Returns:
        int | None: Selected level index, or None if click hit no valid unlocked row.
    """
    from scores import is_level_unlocked
    for i in range(len(level_files)):
        if menu_row_rect(i).collidepoint(pos) and is_level_unlocked(level_files, i, scores, unlock_all):
            return i
    return None


def draw_star(screen, center, r, filled):
    """Draw a 5-pointed geometric star polygon.

    Args:
        screen (pygame.Surface): Target surface.
        center (tuple[int, int]): (cx, cy) pixel coordinates of star center.
        r (float): Outer radius of the star points.
        filled (bool): True for bright earned star; False for dimmed unearned star.
    """
    cx, cy = center
    pts = []
    for k in range(10):
        rad = r if k % 2 == 0 else r * 0.45
        a = math.radians(-90 + k * 36)
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    pygame.draw.polygon(screen, STAR_ON if filled else STAR_OFF, pts)


def draw_stars(screen, center, n, r=10, total=3):
    """Draw a horizontal row of star icons (e.g. 3 stars total).

    Args:
        screen (pygame.Surface): Target surface.
        center (tuple[int, int]): Midpoint of the star row.
        n (int): Number of filled stars (0 to total).
        r (int): Outer radius per star.
        total (int): Total number of stars to display (default 3).
    """
    cx, cy = center
    gap = r * 2.4
    for k in range(total):
        draw_star(screen, (cx + (k - (total - 1) / 2) * gap, cy), r, k < n)


def draw_lock(screen, center, color):
    """Draw a small padlock icon for locked level buttons.

    Args:
        screen (pygame.Surface): Target surface.
        center (tuple[int, int]): Midpoint of padlock icon.
        color (tuple): RGB color for lock icon.
    """
    cx, cy = center
    pygame.draw.rect(screen, color, (cx - 6, cy - 12, 12, 12), 3, border_radius=6)
    pygame.draw.rect(screen, color, (cx - 9, cy - 4, 18, 14), border_radius=3)


def draw_menu(screen, big, small, levels, selected, scores, unlocked, unlock_all=False):
    """Render the main level selection menu.

    Args:
        screen (pygame.Surface): Target window surface.
        big (pygame.font.Font): Large title font.
        small (pygame.font.Font): Smaller body / button font.
        levels (list[tuple[str, str]]): List of (filename, display_name).
        selected (int): Currently highlighted level index.
        scores (dict): Dictionary of recorded level high scores.
        unlocked (list[bool]): Boolean flag per level indicating whether it is unlocked.
        unlock_all (bool): Debug unlock state indicator.
    """
    screen.fill((30, 40, 70))
    draw_text_center(screen, big, C.TITLE, 90)
    draw_text_center(screen, small, "Choose a level", 150, (190, 200, 230))
    for i, (filename, name) in enumerate(levels):
        rect = menu_row_rect(i)
        if not unlocked[i]:
            pygame.draw.rect(screen, (38, 44, 62), rect, border_radius=8)
            label = small.render(name, True, (95, 105, 130))
            if label.get_width() > 250:
                label = pygame.transform.smoothscale(
                    label, (250, max(1, label.get_height() * 250 // label.get_width())))
            screen.blit(label, label.get_rect(midleft=(rect.x + 12, rect.centery)))
            draw_lock(screen, (rect.right - 25, rect.centery), (95, 105, 130))
            continue
        active = i == selected
        pygame.draw.rect(screen, (70, 95, 160) if active else (45, 58, 95), rect, border_radius=8)
        if active:
            pygame.draw.rect(screen, C.WHITE, rect, 2, border_radius=8)
        label = small.render(name, True, C.WHITE)
        if label.get_width() > 250:
            label = pygame.transform.smoothscale(
                label, (250, max(1, label.get_height() * 250 // label.get_width())))
        screen.blit(label, label.get_rect(midleft=(rect.x + 12, rect.centery)))
        best = scores.get(filename)
        draw_stars(screen, (rect.right - 95, rect.centery), best["stars"] if best else 0, r=8)
        if best:
            text = small.render(str(best["count"]), True, (190, 200, 230))
            screen.blit(text, text.get_rect(midright=(rect.right - 10, rect.centery)))

    hint_y = MENU_TOP + len(levels) * MENU_ROW_H + 20
    draw_text_center(screen, small, "Win a level to unlock the next one", hint_y, (190, 200, 230))
    draw_text_center(screen, small, "Up/Down + SPACE, or click a level", hint_y + 34, (190, 200, 230))
    if unlock_all:
        draw_text_center(screen, small, "U: unlock all (testing)  [ON]", hint_y + 68, STAR_ON)
    else:
        draw_text_center(screen, small, "U: unlock all (testing)", hint_y + 68, (120, 130, 160))


def draw_hud(screen, font, level, progress):
    """Render the in-game HUD showing level name and distance progress bar.

    Args:
        screen (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for level title.
        level (Level): Active level instance.
        progress (float): Completion ratio between 0.0 (start) and 1.0 (finish line).
    """
    screen.blit(font.render(level.name, True, C.BLACK), (12, 10))
    bar = pygame.Rect(12, 40, C.SCREEN_W - 24, 10)
    pygame.draw.rect(screen, C.WHITE, bar, border_radius=5)
    fill = bar.copy()
    fill.width = int(bar.width * max(0.0, min(1.0, progress)))
    pygame.draw.rect(screen, C.PLAYER_COLOR, fill, border_radius=5)


def draw_end(screen, big, small, won, count, star_count=0, best=None, new_record=False):
    """Render the endgame overlay screen (YOU WIN / GAME OVER) with star rating and high score.

    Args:
        screen (pygame.Surface): Target surface.
        big (pygame.font.Font): Large font for outcome title.
        small (pygame.font.Font): Body font for scores and restart prompts.
        won (bool): True if level was won; False if crowd died.
        count (int): Final crowd count.
        star_count (int): Number of stars earned (0 to 3).
        best (dict | None): Previous high score record dict {"count": int, "stars": int}.
        new_record (bool): True if this attempt set a new high score.
    """
    overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    draw_text_center(screen, big, "YOU WIN!" if won else "GAME OVER", 300)
    draw_stars(screen, (C.SCREEN_W // 2, 370), star_count, r=22)
    if won:
        draw_text_center(screen, small, f"People left: {count}", 430)
    if new_record:
        draw_text_center(screen, small, "NEW HIGH SCORE!", 470, STAR_ON)
    elif best:
        draw_text_center(screen, small, f"High score: {best['count']}", 470)
    draw_text_center(screen, small, "R: play again    M: level menu", 530)
