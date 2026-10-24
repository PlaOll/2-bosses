"""Camera System: Converts 3D world coordinates (x, z) to 2D screen coordinates (sx, sy, scale).

Key Concept:
All gameplay logic (collision, movement, physics) operates purely in world units.
Only the Camera knows how to project world coordinates onto the screen surface.
"""
import config as C


class Camera:
    """Handles perspective projection and smooth camera tracking along the track."""

    def __init__(self, mode="depth"):
        """Initialize camera state.

        Args:
            mode (str): Projection mode, currently 'depth' for pseudo-3D perspective.
        """
        self.mode = mode
        self.z = 0.0          # Current camera forward position in world coordinates
        self.follow_x = 0.0   # Current camera X target being smoothly followed (lerp)

    def visible(self, z):
        """Check if an object at distance z falls within camera clipping range.

        Args:
            z (float): World Z position to test.

        Returns:
            bool: True if the Z position is between Z_NEAR and Z_FAR from the camera.
        """
        rel = z - self.z
        return C.Z_NEAR <= rel <= C.Z_FAR

    def follow(self, crowd_x, dt, speed=5.0):
        """Smoothly lerp camera horizontal position toward the crowd center.

        Args:
            crowd_x (float): Current target X position of the crowd.
            dt (float): Delta time in seconds since the previous frame.
            speed (float): Tracking responsiveness multiplier (higher = faster camera snap).
        """
        self.follow_x += (crowd_x - self.follow_x) * min(1.0, speed * dt)

    def project(self, x, z):
        """Project a 3D ground point (x, z) to 2D screen coordinates (sx, sy) and scaling factor.

        Formula:
            rel = z - camera.z
            scale = FOCAL / rel
            sx = CENTER_X + (x - follow_x) * scale
            sy = HORIZON_Y + CAM_HEIGHT * scale

        Args:
            x (float): World X coordinate (left < 0 < right).
            z (float): World Z coordinate (forward distance).

        Returns:
            tuple[float, float, float]: (screen_x, screen_y, scale factor).
        """
        rel = z - self.z  # Distance ahead of camera
        if rel <= 0:
            scale = 0.0
        else:
            scale = min(C.FOCAL / rel, C.FOCAL / C.Z_NEAR)

        # Offset by follow_x so world shifts relative to camera center
        sx = C.CENTER_X + (x - self.follow_x) * scale
        sy = C.HORIZON_Y + C.CAM_HEIGHT * scale
        return sx, sy, scale

    def unproject_x(self, sx, z):
        """Convert a 2D screen X position back into a world X coordinate at a given distance z.

        Useful for mouse controls or click targeting.

        Args:
            sx (float): Screen X pixel coordinate.
            z (float): Target world Z depth plane.

        Returns:
            float: World X coordinate corresponding to screen position sx at depth z.
        """
        _, _, scale = self.project(0, z)
        if scale <= 1e-4:
            return self.follow_x
        return (sx - C.CENTER_X) / scale + self.follow_x
