# Importamos pygame, math para el efecto de pulso y os para comprobar rutas
import pygame
import math
import os
from src.utils.settings import load_sprite

# Sprite y color de fallback del altar según el mundo
PEDESTAL_SPRITES = {
    1: ("assets/sprites/objects/pedestal_w1.png", (120, 80,  40)),
    2: ("assets/sprites/objects/pedestal_w2.png", (60,  90, 160)),
    3: ("assets/sprites/objects/pedestal_w3.png", (140, 30,  10)),
}

# Nombre del boss que invoca cada mundo, para el mensaje de la UI
PEDESTAL_BOSS_NAMES = {
    1: "Giga Zombie",
    2: "Yeti",
    3: "Minotauro",
}

# Radio máximo desde el centro del mapa donde puede aparecer el altar (en tiles de 512 px)
PEDESTAL_SPAWN_RADIUS_TILES = 100


# El altar de invocación: objeto sólido con el que el jugador interactúa para invocar al boss
class Pedestal(pygame.sprite.Sprite):
    def __init__(self, pos, world=1):
        super().__init__()

        self.world  = world
        self.pos    = pygame.math.Vector2(pos)
        # active pasa a False cuando se invoca al boss para evitar una segunda invocación
        self.active = True
        # Timer para el efecto de brillo pulsante
        self.timer  = 0

        # Tamaño del sprite del altar
        self.base_w = 110
        self.base_h = 130

        # Cargamos el sprite del altar según el mundo, con color de fallback
        sprite_path, fallback_color = PEDESTAL_SPRITES.get(world, PEDESTAL_SPRITES[1])
        self.image = load_sprite(sprite_path, (self.base_w, self.base_h), fallback_color)

        self.rect = self.image.get_rect(center=pos)

        # hit_rect es la zona sólida que bloquea el paso (solo la base del altar)
        hx = int(self.base_w * 0.55)
        hy = int(self.base_h * 0.30)
        self.hit_rect = pygame.Rect(0, 0, hx, hy)
        self.hit_rect.midbottom = self.rect.midbottom

        # summon_rect es la zona más grande donde el jugador puede pulsar E para invocar
        sx = int(self.base_w * 1.6)
        sy = int(self.base_h * 1.4)
        self.summon_rect = pygame.Rect(0, 0, sx, sy)
        self.summon_rect.center = self.rect.center

        # Guardamos la imagen original para aplicar el efecto de brillo encima sin perderla
        self.base_image = self.image.copy()

        # Cargamos el sonido de invocación; si no existe seguimos sin error
        self.summon_vol = 0.08
        try:
            self.summon_sound = pygame.mixer.Sound("assets/sounds/boss_summon.mp3")
            self.summon_sound.set_volume(self.summon_vol)
        except Exception:
            self.summon_sound = None

    def apply_volume_scale(self, factor):
        # Ajustamos el volumen del sonido de invocación al factor global de la sesión
        if self.summon_sound:
            self.summon_sound.set_volume(self.summon_vol * factor)

    def player_in_summon_zone(self, player):
        # Comprobamos si el hitbox reducido del jugador está dentro de la zona de invocación
        player_hitbox = player.rect.inflate(
            -player.rect.width  * 0.4,
            -player.rect.height * 0.4,
        )
        return self.summon_rect.colliderect(player_hitbox)

    def summon_boss(self):
        # Intentamos invocar al boss: si ya fue invocado devolvemos False
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

        # Si existe el sprite real lo mostramos limpio; si no, aplicamos el efecto de brillo
        import os
        sprite_path = PEDESTAL_SPRITES.get(self.world, PEDESTAL_SPRITES[1])[0]
        if os.path.exists(sprite_path):
            self.image = self.base_image.copy()
        else:
            # Brillo pulsante con sin() para que sea suave y continuo
            pulse      = (math.sin(self.timer * 0.07) + 1) / 2
            glow_alpha = int(40 + pulse * 80)
            world_glow_colors = {
                1: (80,  200,  80,  glow_alpha),
                2: (100, 160,  255, glow_alpha),
                3: (255,  60,   0,  glow_alpha),
            }
            glow_color = world_glow_colors.get(self.world, (200, 200, 200, glow_alpha))
            self.image = self.base_image.copy()
            glow_surf  = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            glow_surf.fill(glow_color)
            # BLEND_RGBA_ADD suma el color del brillo sin borrar lo que hay debajo
            self.image.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)