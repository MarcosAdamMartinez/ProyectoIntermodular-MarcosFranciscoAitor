# importamos pygame y nuestros helpers de sprites y colores
import pygame
from src.utils.settings import load_sprite, WHITE, LIGHT_YELLOW


# cofre que aparece al matar enemigos y da una mejora al jugador al abrirlo
class Chest(pygame.sprite.Sprite):
    # distancia máxima en píxeles a la que el jugador puede interactuar con el cofre
    INTERACT_RADIUS = 120

    # inicializamos el cofre en su posición con la mejora que va a dar
    def __init__(self, pos, upgrade):
        super().__init__()
        self.pos     = pygame.math.Vector2(pos)
        # guardamos la mejora que dará el cofre al abrirse
        self.upgrade = upgrade
        # flag para saber si el cofre ya fue abierto y evitar aplicar la mejora dos veces
        self.opened  = False

        size = (52, 46)
        self.image = load_sprite("assets/sprites/objects/chest.png", size, (180, 120, 40))
        self.rect  = self.image.get_rect(center=(int(pos[0]), int(pos[1])))

        # fuente inicializada de forma lazy la primera vez que se dibuja el prompt
        self.font = None

    # comprueba si el jugador está lo suficientemente cerca para poder interactuar
    def player_nearby(self, player):
        # usamos distancia al cuadrado para evitar la raíz cuadrada y ir más rápido
        dx = player.pos.x - self.pos.x
        dy = player.pos.y - self.pos.y
        return dx * dx + dy * dy <= self.INTERACT_RADIUS ** 2

    # aplica la mejora al jugador, marca el cofre como abierto y lo elimina del juego
    def open(self, player):
        # si ya estaba abierto no hacemos nada, evitamos doble aplicación
        if self.opened:
            return
        self.opened = True
        player.apply_upgrade(self.upgrade)
        self.kill()

    # dibuja el texto 'E - Abrir' encima del cofre con sombra y fondo semitransparente
    def draw_prompt(self, screen, camera_offset):
        if self.opened:
            return
        # inicializamos la fuente aquí para no crearla si nunca se muestra el prompt
        if self.font is None:
            self.font = pygame.font.SysFont("Arial", 18, bold=True)

        # convertimos la posición del cofre a coordenadas de pantalla restando el offset de cámara
        sx = self.rect.centerx - camera_offset.x
        sy = self.rect.top     - camera_offset.y - 28

        txt    = self.font.render("E  -  Abrir", True, LIGHT_YELLOW)
        shadow = self.font.render("E  -  Abrir", True, (0, 0, 0))

        # fondo semitransparente detrás del texto para que se lea bien sobre cualquier fondo
        pad = 8
        bg  = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        screen.blit(bg,     (sx - txt.get_width() // 2 - pad, sy - pad // 2))
        screen.blit(shadow, (sx - txt.get_width() // 2 + 1,   sy + 1))
        screen.blit(txt,    (sx - txt.get_width() // 2,        sy))