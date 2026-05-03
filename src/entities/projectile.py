import pygame
import math
from src.utils.settings import load_sprite

class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats, owner):
        super().__init__()

        self.owner = owner
        self.stats = stats
        self.is_boomerang = stats.get("boomerang", False)
        self.is_melee = stats.get("melee", False)
        self.returning = False
        self.hit_enemies = []

        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.direction = direction

        self.origin_pos = pygame.math.Vector2(pos)

        if self.is_melee:
            w_size = (90, 90)
        elif self.is_boomerang:
            w_size = (50, 50)
        else:
            w_size = (70, 70)

        self.original_image = load_sprite(f"assets/sprites/weapons/{stats['type']}.png", w_size, stats["color"])

        if self.is_melee:
            self.original_image = load_sprite(f"assets/sprites/weapons/melee.png", w_size, stats["color"])
            self.base_angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.current_angle = self.base_angle + 45
            self.sweep_speed = -3
            self.distance = 45
            self._update_melee_pos()
        else:
            angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.image = pygame.transform.rotate(self.original_image, angle)
            self.rect = self.image.get_rect(center=pos)
            self.pos = pygame.math.Vector2(pos)
            self.lifetime = 30

    def _update_melee_pos(self):
        offset = pygame.math.Vector2(self.distance, 0).rotate(-self.current_angle)
        self.pos = self.owner.pos + offset
        self.image = pygame.transform.rotate(self.original_image, self.current_angle - 45)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        if self.is_melee:
            self.current_angle += self.sweep_speed
            self._update_melee_pos()
            if self.current_angle <= self.base_angle - 45:
                self.kill()

        elif self.is_boomerang:
            if not self.returning:
                self.pos += self.direction * self.speed
                self.lifetime -= 1
                if self.lifetime <= 0:
                    self.returning = True
            else:
                return_dir = self.origin_pos - self.pos
                if return_dir.length() < self.speed + 10:
                    self.kill()
                else:
                    return_dir = return_dir.normalize()
                    self.pos += return_dir * (self.speed + 2)
            self.rect.center = self.pos
        else:
            self.pos += self.direction * self.speed
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()
            self.rect.center = self.pos

class BurnZone(pygame.sprite.Sprite):
    """
    Área de quemadura que deja la varita al impactar.
    Círculo naranja semitransparente con borde sólido.
    Dura ~60 frames (1 segundo a 60 fps) y aplica daño periódico.
    """
    RADIUS      = 35       # radio en píxeles — modifica aquí para ajustar el área
    DURATION    = 60       # frames de vida (60 = 1 segundo)
    TICK_RATE   = 10       # frames entre cada tick de daño
    BURN_DAMAGE = 3        # daño por tick

    # Colores
    COLOR_FILL   = (255, 120, 20)   # naranja interior
    COLOR_BORDER = (255, 60,  0)    # naranja oscuro borde
    FILL_ALPHA   = 90               # opacidad del relleno (0-255)

    def __init__(self, pos):
        super().__init__()
        self.pos      = pygame.math.Vector2(pos)
        self.timer    = 0
        self.tick     = 0
        self.hit_enemies = []       # enemigos ya dañados en este tick

        d = self.RADIUS * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(int(pos[0]), int(pos[1])))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        r   = self.RADIUS
        cx  = cy = r

        # Relleno semitransparente
        fill_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(fill_surf, (*self.COLOR_FILL, self.FILL_ALPHA), (r, r), r)
        self.image.blit(fill_surf, (0, 0))

        # Borde sólido
        pygame.draw.circle(self.image, (*self.COLOR_BORDER, 255), (cx, cy), r, 3)

    def update(self):
        self.timer += 1
        self.tick  += 1

        # Fade out en el último tercio de vida
        if self.timer > self.DURATION * 2 // 3:
            remaining = self.DURATION - self.timer
            alpha = max(0, int(255 * remaining / (self.DURATION // 3)))
            self.image.fill((0, 0, 0, 0))
            r = self.RADIUS
            fill_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fill_surf, (*self.COLOR_FILL, int(self.FILL_ALPHA * alpha / 255)), (r, r), r)
            self.image.blit(fill_surf, (0, 0))
            pygame.draw.circle(self.image, (*self.COLOR_BORDER, alpha), (r, r), r, 3)

        if self.tick >= self.TICK_RATE:
            self.tick = 0
            self.hit_enemies.clear()   # resetear para el siguiente tick

        if self.timer >= self.DURATION:
            self.kill()