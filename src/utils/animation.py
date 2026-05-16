# Importamos pygame y os para leer las carpetas de frames del disco
import pygame
import os


# Controlador de animaciones basado en carpetas de imágenes numeradas (1.png, 2.png, ...)
class AnimationController:
    def __init__(self, base_path: str, size: tuple, fallback_image: pygame.Surface,
                 fps: int = 8):
        self.size = size
        # Si no hay animación usamos esta imagen estática como fallback
        self.fallback = fallback_image
        self.anim_fps = fps
        # Convertimos FPS de animación a duración en ticks de juego (asumimos 60 FPS)
        self.frame_duration = max(1, 60 // fps)

        # Diccionario que mapea nombre de estado a lista de frames (Surfaces)
        self.animations: dict[str, list[pygame.Surface]] = {}
        self.load_animations(base_path)

        # Estado inicial y contadores de frame
        self.state = "idle"
        self.frame_index = 0
        self.tick = 0

        # Variables para la animación de hurt (solo se reproduce una vez)
        self.hurt_timer = 0
        self.prev_state = "idle"

    def load_animations(self, base_path: str):
        # Si no existe la carpeta base no cargamos nada y usamos el fallback
        if not os.path.isdir(base_path):
            return

        # Recorremos cada subcarpeta (cada estado de animación)
        for state_dir in os.listdir(base_path):
            full_dir = os.path.join(base_path, state_dir)
            if not os.path.isdir(full_dir):
                continue

            frames = self.load_frames(full_dir)
            if frames:
                self.animations[state_dir] = frames

        # Si existe walk_right pero no walk_left, lo generamos volteando horizontalmente
        if "walk_right" in self.animations and "walk_left" not in self.animations:
            self.animations["walk_left"] = [
                pygame.transform.flip(f, True, False)
                for f in self.animations["walk_right"]
            ]

        # Si el artista usó "walk" en vez de "walk_right/walk_left" lo mapeamos a ambos
        if "walk" in self.animations:
            if "walk_right" not in self.animations:
                self.animations["walk_right"] = self.animations["walk"]
            if "walk_left" not in self.animations:
                self.animations["walk_left"] = [
                    pygame.transform.flip(f, True, False)
                    for f in self.animations["walk"]
                ]

    def load_frames(self, folder: str) -> list[pygame.Surface]:
        # Cargamos los frames numerados desde 1.png en adelante hasta que no exista el siguiente
        frames = []
        i = 1
        while True:
            path = os.path.join(folder, f"{i}.png")
            if not os.path.exists(path):
                break

            try:
                img = pygame.image.load(path).convert_alpha()

                # Escalamos manteniendo la proporción original dentro del tamaño objetivo
                orig_w, orig_h = img.get_size()
                target_w, target_h = self.size
                ratio = min(target_w / orig_w, target_h / orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)

                # Forzamos a que el escalado final se ajuste estrictamente al tamaño de la caja objetivo
                img = pygame.transform.smoothscale(img, (new_w, new_h))

                # Centramos el frame escalado en un surface del tamaño objetivo
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

    def has_animation(self, state: str) -> bool:
        # Comprobamos si existe al menos un frame para el estado pedido
        return state in self.animations and len(self.animations[state]) > 0

    def set_state(self, state: str):
        # Cambiamos de estado y reiniciamos los contadores; hurt tiene prioridad y no se interrumpe
        if state == self.state:
            return
        if self.state == "hurt" and self.hurt_timer > 0:
            return
        if self.has_animation(state):
            self.state = state
            self.frame_index = 0
            self.tick = 0

    def trigger_hurt(self):
        # Activamos la animación de daño; guarda el estado actual para restaurarlo después
        if not self.has_animation("hurt"):
            return
        self.prev_state = self.state
        self.state = "hurt"
        self.frame_index = 0
        self.tick = 0
        # El timer dura exactamente los frames de hurt multiplicados por su duración
        self.hurt_timer = len(self.animations["hurt"]) * self.frame_duration

    def update(self) -> pygame.Surface:
        # Llamamos esto una vez por tick; devuelve el frame que hay que dibujar ahora
        if not self.has_animation(self.state):
            # Si el fallback también es gigante, lo escalamos al tamaño correcto antes de devolverlo
            if self.fallback.get_size() != self.size:
                self.fallback = pygame.transform.smoothscale(self.fallback, self.size)
            return self.fallback

        frames = self.animations[self.state]

        self.tick += 1
        if self.tick >= self.frame_duration:
            self.tick = 0
            self.frame_index += 1

            if self.state == "hurt":
                # La animación de hurt solo se reproduce una vez y luego vuelve al estado anterior
                self.hurt_timer -= self.frame_duration
                if self.frame_index >= len(frames):
                    self.frame_index = 0
                    self.hurt_timer = 0
                    restore = self.prev_state if self.has_animation(self.prev_state) else "idle"
                    self.state = restore
            else:
                # El resto de animaciones hacen loop automáticamente
                self.frame_index %= len(frames)

        return frames[self.frame_index]