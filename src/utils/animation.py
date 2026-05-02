import pygame
import os


class AnimationController:
    """
    Controlador de animaciones basado en carpetas de frames.

    Estructura de carpetas esperada:
        assets/sprites/players/<nombre>/<estado>/0.png, 1.png, ...
        assets/sprites/enemies/<tipo>/<estado>/0.png, 1.png, ...

    Estados soportados:
        - idle        → en reposo
        - walk_right  → moviéndose a la derecha (o cualquier dirección)
        - walk_left   → moviéndose a la izquierda (espejo de walk_right)
        - hurt        → recibiendo daño (se reproduce una vez)

    Si una carpeta de estado no existe, usa el frame estático de fallback.
    Si walk_left no existe pero walk_right sí, se voltea horizontalmente.
    """

    def __init__(self, base_path: str, size: tuple, fallback_image: pygame.Surface,
                 fps: int = 8):
        """
        base_path   : carpeta raíz del personaje/enemigo
                      ej. "assets/sprites/players/knight"
        size        : tamaño al que escalar cada frame
        fallback_image : Surface estática que se usa si no hay animación
        fps         : velocidad de la animación en frames de animación por segundo
                      (independiente del FPS del juego)
        """
        self.size = size
        self.fallback = fallback_image
        self.anim_fps = fps
        self.frame_duration = max(1, 60 // fps)   # en ticks de juego (asume 60 FPS)

        self.animations: dict[str, list[pygame.Surface]] = {}
        self._load_animations(base_path)

        self.state = "idle"
        self.frame_index = 0
        self.tick = 0

        # Para el estado hurt (se reproduce una sola vez)
        self.hurt_timer = 0
        self.prev_state = "idle"

    # ------------------------------------------------------------------ #
    #  Carga                                                               #
    # ------------------------------------------------------------------ #
    def _load_animations(self, base_path: str):
        """Carga todos los estados que encuentre en base_path."""
        if not os.path.isdir(base_path):
            return  # sin carpeta → solo fallback

        for state_dir in os.listdir(base_path):
            full_dir = os.path.join(base_path, state_dir)
            if not os.path.isdir(full_dir):
                continue

            frames = self._load_frames(full_dir)
            if frames:
                self.animations[state_dir] = frames

        # Si tenemos walk_right pero no walk_left, generamos walk_left volteando
        if "walk_right" in self.animations and "walk_left" not in self.animations:
            self.animations["walk_left"] = [
                pygame.transform.flip(f, True, False)
                for f in self.animations["walk_right"]
            ]

        # Si tenemos walk pero no walk_right/walk_left, los alias ambos
        if "walk" in self.animations:
            if "walk_right" not in self.animations:
                self.animations["walk_right"] = self.animations["walk"]
            if "walk_left" not in self.animations:
                self.animations["walk_left"] = [
                    pygame.transform.flip(f, True, False)
                    for f in self.animations["walk"]
                ]

    def _load_frames(self, folder: str) -> list[pygame.Surface]:
        frames = []
        i = 1
        while True:
            path = os.path.join(folder, f"{i}.png")
            if not os.path.exists(path):
                break

            try:
                img = pygame.image.load(path).convert_alpha()

                orig_w, orig_h = img.get_size()
                target_w, target_h = self.size
                ratio = min(target_w / orig_w, target_h / orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)

                img = pygame.transform.scale(img, (new_w, new_h))

                final = pygame.Surface(self.size, pygame.SRCALPHA)
                offset_x = (target_w - new_w) // 2
                offset_y = (target_h - new_h) // 2
                final.blit(img, (offset_x, offset_y))

                frames.append(final)
            except Exception as e:
                print(f"Error cargando frame {i}: {e}")
                break
            i += 1
        return frames

    # ------------------------------------------------------------------ #
    #  Control de estado                                                   #
    # ------------------------------------------------------------------ #
    def has_animation(self, state: str) -> bool:
        return state in self.animations and len(self.animations[state]) > 0

    def set_state(self, state: str):
        """Cambia de estado; reinicia el frame si el estado cambia."""
        if state == self.state:
            return
        # hurt tiene prioridad y se gestiona externamente con trigger_hurt()
        if self.state == "hurt" and self.hurt_timer > 0:
            return
        if self.has_animation(state):
            self.state = state
            self.frame_index = 0
            self.tick = 0

    def trigger_hurt(self):
        """Activa la animación de daño; se reproduce una vez."""
        if not self.has_animation("hurt"):
            return
        self.prev_state = self.state
        self.state = "hurt"
        self.frame_index = 0
        self.tick = 0
        self.hurt_timer = len(self.animations["hurt"]) * self.frame_duration

    # ------------------------------------------------------------------ #
    #  Actualización y obtención del frame actual                          #
    # ------------------------------------------------------------------ #
    def update(self) -> pygame.Surface:
        """
        Debe llamarse una vez por tick de juego.
        Devuelve el Surface que se debe mostrar.
        """
        if not self.has_animation(self.state):
            return self.fallback

        frames = self.animations[self.state]

        self.tick += 1
        if self.tick >= self.frame_duration:
            self.tick = 0
            self.frame_index += 1

            # ── Hurt: solo una pasada ──────────────────────────────────
            if self.state == "hurt":
                self.hurt_timer -= self.frame_duration
                if self.frame_index >= len(frames):
                    self.frame_index = 0
                    self.hurt_timer = 0
                    # Volver al estado anterior
                    restore = self.prev_state if self.has_animation(self.prev_state) else "idle"
                    self.state = restore
            else:
                self.frame_index %= len(frames)

        return frames[self.frame_index]