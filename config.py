"""Global Game Configuration and Constants.

This file defines screen dimensions, physics constants, camera projection parameters,
colors, crowd boids behavior, and boss parameters. Modify these values to adjust gameplay feel.
"""

# ==============================================================================
# Screen & Display Settings
# ==============================================================================
SCREEN_W = 650               # Window width in pixels
SCREEN_H = 780             # Window height in pixels
FPS = 60                     # Target frame rate (frames per second)
TITLE = "Crowd Runner"       # Window title bar caption

# ==============================================================================
# World & Physics Coordinates (in World Units)
# Convention: X = Left/Right (0 = Road Center), Z = Forward Distance
# ==============================================================================
ROAD_HALF_W = 200            # Half of road width; road extends from x = -ROAD_HALF_W to +ROAD_HALF_W
CROWD_OFFSET = 200           # Distance the crowd stays ahead of the camera along the Z axis
CROWD_SIDE_SPEED = 350       # Minimum lateral movement speed via keyboard (world units / second)
CROWD_SIDE_RATIO = 1.6       # Lateral speed multiplier relative to forward speed (faster runs = faster dodging)
PERSON_SPACING = 10          # Visual and collision spacing between individual runners
MAX_DRAWN_PEOPLE = 60        # Cap on rendered runners to maintain high performance with large crowds
GATE_HEIGHT = 60             # Vertical height of arithmetic gates (world units)

# ==============================================================================
# Enemy Group Behavior & AI
# ==============================================================================
ENEMY_CHASE_DIST = 500.0     # Detection distance (Z); enemy charges towards player when closer than this
ENEMY_CHASE_SPEED_Z = 70.0   # Speed at which enemies run forward towards the player (units / sec)
ENEMY_CHASE_SPEED_X = 1      # Steering speed ratio of enemies homing in on the player's X position

# ==============================================================================
# Camera 3D Perspective (camera.py)
# ==============================================================================
CAMERA_MODE = "depth"        # Perspective projection mode ("depth")
CENTER_X = SCREEN_W // 2     # Screen horizontal center for vanishing point
HORIZON_Y = 200              # Screen Y position of the horizon / vanishing line
FOCAL = 300                  # Focal length (F) in projection formula: scale = F / (z - cam_z)
CAM_HEIGHT = 300             # Camera height above the ground plane
Z_NEAR = 50                  # Near clipping plane (objects closer than this are not rendered)
Z_FAR = 2000                 # Far clipping plane (objects farther than this are not rendered)

# ==============================================================================
# Color Palette (RGB Tuples)
# ==============================================================================
SKY = (120, 190, 255)            # Default sky color
GROUND = (90, 170, 90)           # Default ground grass color
ROAD = (200, 200, 210)           # Default road surface color
ROAD_EDGE = (150, 150, 160)      # Road border color
PLAYER_COLOR = (40, 110, 255)    # Player crowd UI and indicator color (Blue)
ENEMY_COLOR = (220, 50, 50)      # Enemy crowd UI and indicator color (Red)
GATE_GOOD = (60, 140, 255)       # Positive multiplier/addition gate color (Blue)
GATE_BAD = (230, 70, 70)         # Negative subtraction/division gate color (Red)
OBSTACLE_COLOR = (200, 60, 30)   # Road obstacle color
FINISH_COLOR = (255, 255, 255)      # Finish line stripe color
WHITE = (255, 255, 255)          # Standard white
BLACK = (0, 0, 0)                # Standard black

# ==============================================================================
# Crowd Flocking / Boids Physics Simulation
# ==============================================================================
CROWD_COHESION = 15.0         # Spring force pulling separated runners back toward cluster center
CROWD_SEPARATION = 100.0     # Repulsion force preventing runners from overlapping each other
CROWD_WANDER = 0.5           # Natural slight wandering movement jitter
REFORMATION_DELAY = 0.5      # Delay in seconds after taking damage before crowd pulls back together

# ==============================================================================
# Boss Mechanics (boss.py)
# ==============================================================================
POISON_DEATH_TIME = 1.5      # Standing inside a plant boss poison pool for this many seconds causes death

# Theme fallback colors
GROUND_A = (88, 160, 84)
GROUND_B = (80, 150, 78)
