import pygame
import math
import os
from src.utils.settings import load_sprite

# Sprite y color de fallback por mundo
PEDESTAL_SPRITES = {
    1: ("assets/sprites/objects/pedestal_w1.png", (120, 80,  40)),   # Piedra marrón / bosque
    2: ("assets/sprites/objects/pedestal_w2.png", (60,  90, 160)),   # Hielo / ártico
    3: ("assets/sprites/objects/pedestal_w3.png", (140, 30,  10)),   # Obsidiana infernal
}

# Nombre del boss que invoca cada mundo (para el mensaje)
PEDESTAL_BOSS_NAMES = {
    1: "Giga Zombie",
    2: "Yeti",
    3: "Minotauro",
}

# Distancia máxima desde el origen del mapa donde puede aparecer el pedestal,
# medida en tiles de 512 px (el tamaño de chunk del juego).
# 100 tiles ≈ 51 200 px desde el centro del mapa.
PEDESTAL_SPAWN_RADIUS_TILES = 100   # ← modifica este valor para ajustar la distancia


class Pedestal(pygame.sprite.Sprite):
    """
    Altar de invocación.

    - Se dibuja en el mundo con su sprite correspondiente al mundo actual.
    - hit_rect    → colisión física sólida (bloquea el paso del jugador y enemigos).
    - summon_rect → área de interacción más grande (muestra mensaje E / invoca boss).
    - Cuando el jugador pulsa E dentro de summon_rect se invoca al boss del mundo.
    - Una vez invocado el boss, el altar queda desactivado (imagen oscurecida,
      sin mensaje y sin permitir una segunda invocación).
    """

    def __init__(self, pos, world=1):
        super().__init__()

        self.world  = world
        self.pos    = pygame.math.Vector2(pos)
        self.active = True          # False después de invocar al boss
        self.timer  = 0             # para el efecto de brillo / pulso

        # ── Tamaño y sprite ────────────────────────────────────────────────
        self.base_w = 110
        self.base_h = 130

        sprite_path, fallback_color = PEDESTAL_SPRITES.get(world, PEDESTAL_SPRITES[1])
        self.image = load_sprite(sprite_path, (self.base_w, self.base_h), fallback_color)

        self.rect = self.image.get_rect(center=pos)

        # ── hit_rect: colisión física (base del altar, zona sólida) ───────
        hx = int(self.base_w * 0.55)
        hy = int(self.base_h * 0.30)
        self.hit_rect = pygame.Rect(0, 0, hx, hy)
        self.hit_rect.midbottom = self.rect.midbottom

        # ── summon_rect: zona de interacción (bastante más grande) ────────
        sx = int(self.base_w * 1.6)
        sy = int(self.base_h * 1.4)
        self.summon_rect = pygame.Rect(0, 0, sx, sy)
        self.summon_rect.center = self.rect.center

        # ── Imagen base guardada para el efecto de brillo ─────────────────
        self._base_image = self.image.copy()

        # ── Sonido de invocación ───────────────────────────────────────────
        self._summon_vol = 0.08
        try:
            self.summon_sound = pygame.mixer.Sound("assets/sounds/boss_summon.mp3")
            self.summon_sound.set_volume(self._summon_vol)
        except Exception:
            self.summon_sound = None

    # ------------------------------------------------------------------ #

    def apply_volume_scale(self, factor):
        if self.summon_sound:
            self.summon_sound.set_volume(self._summon_vol * factor)

    def player_in_summon_zone(self, player):
        """Devuelve True si el hitbox reducido del jugador toca summon_rect."""
        player_hitbox = player.rect.inflate(
            -player.rect.width  * 0.4,
            -player.rect.height * 0.4,
        )
        return self.summon_rect.colliderect(player_hitbox)

    def summon_boss(self):
        if not self.active:
            return False
        self.active = False
        if self.summon_sound:
            self.summon_sound.play()
        return True

    def update(self):
        self.timer += 1
        if not self.active:
            return

        # Si el sprite real existe, mostrarlo limpio sin efectos encima.
        # Solo aplicar brillo pulsante si se usa el fallback de color sólido.
        import os
        sprite_path = PEDESTAL_SPRITES.get(self.world, PEDESTAL_SPRITES[1])[0]
        if os.path.exists(sprite_path):
            self.image = self._base_image.copy()
        else:
            pulse      = (math.sin(self.timer * 0.07) + 1) / 2
            glow_alpha = int(40 + pulse * 80)
            world_glow_colors = {
                1: (80,  200,  80,  glow_alpha),
                2: (100, 160,  255, glow_alpha),
                3: (255,  60,   0,  glow_alpha),
            }
            glow_color = world_glow_colors.get(self.world, (200, 200, 200, glow_alpha))
            self.image = self._base_image.copy()
            glow_surf  = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            glow_surf.fill(glow_color)
            self.image.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)