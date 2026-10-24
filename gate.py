"""Arithmetic Gates: Modify crowd counts upon player contact.

Gates are generated from JSON level files with operators:
'+' (addition), '-' (subtraction), 'x' (multiplication), '/' (division).
"""
import pygame
import config as C

# Mapping from JSON operator symbol to displayed unicode symbol
SYMBOLS = {"+": "+", "-": "-", "x": "×", "/": "÷"}


class Gate:
    """Represents a single lane of an arithmetic gate covering a section of the road."""

    def __init__(self, x_min, x_max, op, value):
        """Initialize gate parameters.

        Args:
            x_min (float): Left boundary of the gate in world units.
            x_max (float): Right boundary of the gate in world units.
            op (str): Mathematical operator ('+', '-', 'x', '/').
            value (int): Operand value.
        """
        if op not in SYMBOLS:
            raise ValueError(f"unknown gate op: {op!r}")
        if op == "/" and value == 0:
            raise ValueError("gate cannot divide by 0")
        self.x_min, self.x_max = x_min, x_max
        self.op, self.value = op, value

    def apply(self, count):
        """Calculate the new crowd count after passing through this gate.

        Pure mathematical function without mutating internal state.

        Args:
            count (int): Current crowd count before passing the gate.

        Returns:
            int: Resulting crowd count (floored integer, non-negative).
        """
        if self.op == "+":
            return count + self.value
        if self.op == "-":
            return max(0, count - self.value)   # Count cannot be negative
        if self.op == "x":
            return count * self.value
        return count // self.value              # Floor division keeps crowd integer

    def is_good(self):
        """Check whether passing this gate increases or maintains the crowd.

        Returns:
            bool: True for '+' and 'x', False for '-' and '/'.
        """
        return self.op in ("+", "x")

    def label(self):
        """Get formatted display label text (e.g. '×2', '+25', '÷3').

        Returns:
            str: Human-readable operator and value string.
        """
        return f"{SYMBOLS[self.op]}{self.value}"

    def contains(self, x):
        """Check if an X position falls within the lane of this gate.

        Args:
            x (float): World X coordinate to test.

        Returns:
            bool: True if x_min <= x < x_max.
        """
        return self.x_min <= x < self.x_max


class GatePair:
    """A pair of left and right gates positioned side-by-side at the same Z coordinate.

    The player chooses which half of the road to run through.
    """

    def __init__(self, z, left, right):
        """Initialize gate pair.

        Args:
            z (float): World Z position along the track.
            left (tuple): Tuple of (op, value) for the left lane (from -ROAD_HALF_W to 0).
            right (tuple): Tuple of (op, value) for the right lane (from 0 to +ROAD_HALF_W).
        """
        self.z = z
        self.left = Gate(-C.ROAD_HALF_W, 0, *left)
        self.right = Gate(0, C.ROAD_HALF_W, *right)
        self.used = False  # Set to True once the crowd has crossed this gate pair

    def update(self, dt):
        """Update gate animation per frame.

        Args:
            dt (float): Delta time in seconds.
        """
        pass

    def on_reach(self, crowd):
        """Apply gate arithmetic when the crowd crosses the gate pair's Z coordinate.

        Chooses left or right gate based on current crowd.x position.

        Args:
            crowd (Crowd): The player's crowd instance.
        """
        gate = self.left if self.left.contains(crowd.x) else self.right
        crowd.count = gate.apply(crowd.count)
        self.used = True

    def draw(self, screen, camera, font):
        """Render both gate lanes in 3D perspective with transparent tinted surfaces.

        Args:
            screen (pygame.Surface): Screen surface to render onto.
            camera (Camera): Active camera for projection.
            font (pygame.font.Font): Font used for rendering operation labels.
        """
        if self.used or not camera.visible(self.z):
            return
        for gate in (self.left, self.right):
            x1, y, scale = camera.project(gate.x_min, self.z)
            x2, _, _ = camera.project(gate.x_max, self.z)
            h = C.GATE_HEIGHT * scale
            rect = pygame.Rect(x1 + 2, y - h, x2 - x1 - 4, h)
            color = C.GATE_GOOD if gate.is_good() else C.GATE_BAD

            # Semi-transparent colored background
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill((*color, 150))
            screen.blit(surf, rect.topleft)

            # Operator label with perspective scale
            text = font.render(gate.label(), True, C.WHITE)
            size = max(1, int(text.get_width() * min(scale, 1.5))), max(1, int(text.get_height() * min(scale, 1.5)))
            text = pygame.transform.smoothscale(text, size)
            screen.blit(text, text.get_rect(center=rect.center))
