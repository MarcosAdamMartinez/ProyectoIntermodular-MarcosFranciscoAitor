import pygame
from src.utils.settings import load_sprite, WHITE, LIGHT_YELLOW


class Chest(pygame.sprite.Sprite):
    """
    Cofre que dropea al matar un enemigo (1% de probabilidad).
    Al acercarse muestra "E - Abrir"; al pulsar E da una mejora global al jugador.
    """
    INTERACT_RADIUS = 120   # px — distancia máxima para interactuar

    def __init__(self, pos, upgrade):
        super().__init__()
        self.pos     = pygame.math.Vector2(pos)
        self.upgrade = upgrade          # dict de UPGRADES que dará al abrir
        self.opened  = False

        size = (52, 46)
        self.image = load_sprite("assets/sprites/objects/chest.png", size, (180, 120, 40))
        self.rect  = self.image.get_rect(center=(int(pos[0]), int(pos[1])))

        self._font = None   # se inicializa lazy la primera vez que se dibuja

    def player_nearby(self, player):
        dx = player.pos.x - self.pos.x
        dy = player.pos.y - self.pos.y
        return dx * dx + dy * dy <= self.INTERACT_RADIUS ** 2

    def open(self, player):
        """Aplica la mejora al jugador y marca el cofre como abierto."""
        if self.opened:
            return
        self.opened = True
        player.apply_upgrade(self.upgrade)
        self.kill()

    def draw_prompt(self, screen, camera_offset):
        """Dibuja el mensaje 'E - Abrir' encima del cofre si no está abierto."""
        if self.opened:
            return
        if self._font is None:
            self._font = pygame.font.SysFont("Arial", 18, bold=True)

        sx = self.rect.centerx - camera_offset.x
        sy = self.rect.top     - camera_offset.y - 28

        txt    = self._font.render("E  -  Abrir", True, LIGHT_YELLOW)
        shadow = self._font.render("E  -  Abrir", True, (0, 0, 0))

        # Fondo semitransparente
        pad = 8
        bg  = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        screen.blit(bg,     (sx - txt.get_width() // 2 - pad, sy - pad // 2))
        screen.blit(shadow, (sx - txt.get_width() // 2 + 1,   sy + 1))
        screen.blit(txt,    (sx - txt.get_width() // 2,        sy))