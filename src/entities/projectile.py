# Importamos lo necesario para los proyectiles: pygame, math para ángulos y random
import pygame
import math
import random
from src.utils.settings import load_sprite


# Clase general de proyectil: maneja proyectiles normales, boomerangs y armas cuerpo a cuerpo
class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats, owner):
        super().__init__()

        self.owner = owner
        self.stats = stats
        # Flags para saber qué tipo de proyectil es y aplicar la lógica correcta
        self.is_boomerang = stats.get("boomerang", False)
        self.is_melee = stats.get("melee", False)
        self.returning = False
        # Lista de enemigos ya golpeados para no aplicar daño dos veces en el mismo frame
        self.hit_enemies = []
        # El boomerang solo fragmenta una sola vez al primer impacto
        self.fragmented = False

        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.direction = direction

        # Guardamos la posición de origen para que el boomerang sepa a dónde volver
        self.origin_pos = pygame.math.Vector2(pos)

        # El tamaño del sprite varía según si es cuerpo a cuerpo, boomerang o proyectil normal
        if self.is_melee:
            w_size = (90, 90)
        elif self.is_boomerang:
            w_size = (50, 50)
        else:
            w_size = (70, 70)

        self.original_image = load_sprite(
            f"assets/sprites/weapons/{stats['type']}.png", w_size, stats["color"])

        if self.is_melee:
            # El arma cuerpo a cuerpo gira en arco alrededor del jugador
            self.original_image = load_sprite(
                f"assets/sprites/weapons/melee.png", w_size, stats["color"])
            self.base_angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.current_angle = self.base_angle + 45
            self.sweep_speed = -3
            self.distance = 45
            self.update_melee_pos()
        else:
            # Rotamos el sprite para que apunte en la dirección de disparo
            angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.image = pygame.transform.rotate(self.original_image, angle)
            self.rect = self.image.get_rect(center=pos)
            self.pos = pygame.math.Vector2(pos)
            self.lifetime = 30

    def update_melee_pos(self):
        # Calculamos la posición del arma girando alrededor del jugador y rotamos su imagen
        offset = pygame.math.Vector2(self.distance, 0).rotate(-self.current_angle)
        self.pos = self.owner.pos + offset
        self.image = pygame.transform.rotate(self.original_image, self.current_angle - 45)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        if self.is_melee:
            # El arma cuerpo a cuerpo barre un arco y se destruye al completarlo
            self.current_angle += self.sweep_speed
            self.update_melee_pos()
            if self.current_angle <= self.base_angle - 45:
                self.kill()

        elif self.is_boomerang:
            if not self.returning:
                # Fase de ida: avanzamos en la dirección de lanzamiento
                self.pos += self.direction * self.speed
                self.lifetime -= 1
                if self.lifetime <= 0:
                    self.returning = True
            else:
                # Fase de vuelta: nos dirigimos hacia la posición de origen del lanzador
                return_dir = self.origin_pos - self.pos
                if return_dir.length() < self.speed + 10:
                    self.kill()
                else:
                    return_dir = return_dir.normalize()
                    self.pos += return_dir * (self.speed + 2)
            self.rect.center = self.pos
        else:
            # Proyectil normal: avanza recto y se destruye al agotar su lifetime
            self.pos += self.direction * self.speed
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()
            self.rect.center = self.pos


# Fragmento de banana que sale al primer impacto del boomerang
class BananaFrag(pygame.sprite.Sprite):
    SPEED    = 9
    LIFETIME = 22

    def __init__(self, impact_pos, direction, damage, stats):
        super().__init__()
        self.damage      = damage
        self.stats       = stats
        self.hit_enemies = []
        # El fragmento vuelve al punto de impacto, no al lanzador
        self.impact_pos  = pygame.math.Vector2(impact_pos)
        self.pos         = pygame.math.Vector2(impact_pos)
        self.direction   = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)
        self.returning   = False
        self.lifetime    = self.LIFETIME

        # Cargamos el sprite del fragmento de banana rotado en la dirección correcta
        w_size = (32, 32)
        self.original_image = load_sprite("assets/sprites/weapons/banana.png", w_size, (255, 220, 0))
        angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
        self.image = pygame.transform.rotate(self.original_image, angle)
        self.rect  = self.image.get_rect(center=(int(impact_pos[0]), int(impact_pos[1])))

    def update(self):
        if not self.returning:
            # Fase de ida: sale disparado hacia adelante
            self.pos += self.direction * self.SPEED
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.returning = True
        else:
            # Fase de vuelta: regresa al punto de impacto y se destruye al llegar
            ret = self.impact_pos - self.pos
            if ret.length() < self.SPEED + 5:
                self.kill()
                return
            self.pos += ret.normalize() * (self.SPEED + 2)
        self.rect.center = self.pos


# Zona de fuego que deja la varita al impactar; daña a los enemigos que la pisen
class BurnZone(pygame.sprite.Sprite):
    DURATION  = 60
    TICK_RATE = 10

    COLOR_FILL   = (255, 120, 20)
    COLOR_BORDER = (255, 60,  0)
    FILL_ALPHA   = 90

    def __init__(self, pos, burn_damage=3, burn_radius=35):
        super().__init__()
        self.pos         = pygame.math.Vector2(pos)
        self.burn_damage = burn_damage
        self.radius      = burn_radius
        self.timer       = 0
        # tick cuenta los frames desde el último pulso de daño
        self.tick        = 0
        # Lista de enemigos golpeados en el pulso actual para no golpear dos veces
        self.hit_enemies = []

        # Dibujamos el círculo de fuego inicial
        d = self.radius * 2
        self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        self.redraw(255)
        self.rect = self.image.get_rect(center=(int(pos[0]), int(pos[1])))

    def redraw(self, alpha_scale):
        # Redibujamos el círculo con el alpha calculado para el efecto de desvanecimiento
        d = self.radius * 2
        if self.image.get_size() != (d, d):
            self.image = pygame.Surface((d, d), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        r = self.radius
        fill_alpha   = int(self.FILL_ALPHA * alpha_scale / 255)
        border_alpha = alpha_scale
        fill_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(fill_surf, (*self.COLOR_FILL, fill_alpha), (r, r), r)
        self.image.blit(fill_surf, (0, 0))
        pygame.draw.circle(self.image, (*self.COLOR_BORDER, border_alpha), (r, r), r, 3)

    def update(self):
        self.timer += 1
        self.tick  += 1

        # En el último tercio de vida la zona se va desvaneciendo gradualmente
        fade_start = self.DURATION * 2 // 3
        if self.timer > fade_start:
            remaining   = max(0, self.DURATION - self.timer)
            alpha_scale = int(255 * remaining / max(1, self.DURATION - fade_start))
            self.redraw(alpha_scale)

        # Cada TICK_RATE frames limpiamos la lista de golpeados para el siguiente pulso
        if self.tick >= self.TICK_RATE:
            self.tick = 0
            self.hit_enemies.clear()

        # Cuando se acaba la duración destruimos la zona de fuego
        if self.timer >= self.DURATION:
            self.kill()