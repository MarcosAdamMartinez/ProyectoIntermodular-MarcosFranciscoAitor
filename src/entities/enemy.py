import pygame
import random
from src.utils.settings import *


# Definimos la clase del enemigo basandonos en los sprites de Pygame
class Enemy(pygame.sprite.Sprite):
    def __init__(self, target, enemy_type="zombie"):
        super().__init__()

        self.enemy_type = enemy_type

        # Asignamos estadisticas y sprites segun el tipo de enemigo
        if enemy_type == "zombie":
            size = (100, 90)
            color = RED
            self.speed = random.uniform(1.5, 2.5)
            self.hp = 20
        elif enemy_type == "slime":
            size = (80, 70)
            color = (0, 200, 100)  # Verde lima si no hay sprite
            self.speed = random.uniform(1.2, 2.0)
            self.hp = 12
        elif enemy_type == "goblin":
            size = (90, 80)
            color = (0, 150, 0)  # Verde si no hay sprite
            self.speed = random.uniform(2.0, 3.0)
            self.hp = 45
        elif enemy_type == "skeleton":
            size = (95, 95)
            color = (200, 200, 200)  # Gris claro si no hay sprite
            self.speed = random.uniform(2.5, 3.5)
            self.hp = 80
        elif enemy_type == "golem":
            size = (130, 130)
            color = (100, 80, 60)  # Marrón piedra si no hay sprite
            self.speed = random.uniform(1.0, 1.8)
            self.hp = 180
        elif enemy_type == "bat":
            size = (70, 60)
            color = (80, 0, 80)  # Morado oscuro si no hay sprite
            self.speed = random.uniform(3.0, 4.5)
            self.hp = 30
        elif enemy_type == "demon":
            size = (110, 110)
            color = (180, 20, 20)  # Rojo demonio si no hay sprite
            self.speed = random.uniform(2.5, 3.5)
            self.hp = 150
        elif enemy_type == "giga_zombie":
            size = (200, 200)
            color = (180, 30, 0)  # Rojo zombificado si no hay sprite
            self.speed = random.uniform(1.0, 1.5)
            self.hp = 500
        elif enemy_type == "yeti":
            size = (200, 200)
            color = (200, 230, 255)  # Blanco azulado si no hay sprite
            self.speed = random.uniform(1.2, 1.8)
            self.hp = 700
        elif enemy_type == "minotaur":
            size = (220, 220)
            color = (120, 40, 10)  # Marrón rojizo si no hay sprite
            self.speed = random.uniform(1.5, 2.2)
            self.hp = 1000
        elif enemy_type == "boss":
            # boss genérico de fallback — no debería usarse en la lógica nueva
            size = (200, 200)
            color = (150, 0, 0)
            self.speed = random.uniform(1.0, 1.5)
            self.hp = 500

        # Cargamos la imagen correspondiente (Ej: assets/sprites/goblin.png)
        self.image = load_sprite(f"assets/sprites/enemies/{enemy_type}.png", size, color)

        # Calculamos el punto de aparicion circular
        boss_types = {"giga_zombie", "yeti", "minotaur", "boss"}
        spawn_radius = 500 if enemy_type in boss_types else 400

        angle = random.uniform(0, 360)
        offset = pygame.math.Vector2(spawn_radius, 0).rotate(angle)
        spawn_pos = target.pos + offset

        self.rect = self.image.get_rect(center=(spawn_pos.x, spawn_pos.y))
        self.pos = pygame.math.Vector2(spawn_pos)

        self.max_hp = self.hp   # guardamos HP máximo para la barra del boss

        self.target = target

        # --- CARGAR SONIDO DE RECIBIR DAÑO (ÚNICO SONIDO DEL ENEMIGO) ---
        self._base_hurt_vol = 0.04
        try:
            self.hurt_sound = pygame.mixer.Sound(f"assets/sounds/enemies/{enemy_type}_hurt.mp3")
            self.hurt_sound.set_volume(self._base_hurt_vol)
        except:
            self.hurt_sound = None

    def apply_volume_scale(self, factor):
        if self.hurt_sound:
            self.hurt_sound.set_volume(self._base_hurt_vol * factor)

    def update(self):
        direction = (self.target.pos - self.pos)

        if direction.length() > 0:
            direction = direction.normalize()
            self.pos += direction * self.speed
            self.rect.center = self.pos

    def take_damage(self, amount):
        # --- REPRODUCIR SONIDO AL RECIBIR DAÑO ---
        if self.hurt_sound:
            self.hurt_sound.play()

        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def is_boss_type(self):
        return self.enemy_type in {"giga_zombie", "yeti", "minotaur", "boss"}

    def is_on_screen(self, camera_offset):
        """Devuelve True si el boss es visible en la cámara actual."""
        screen_pos = self.rect.topleft - camera_offset
        screen_rect = pygame.Rect(screen_pos, self.rect.size)
        display_rect = pygame.Rect(0, 0, pygame.display.get_surface().get_width(),
                                   pygame.display.get_surface().get_height())
        return display_rect.colliderect(screen_rect)

    def draw_boss_ui(self, screen, camera_offset):
        """Dibuja la healthbar y la flecha indicadora del boss."""
        from src.utils.settings import WIDTH, HEIGHT

        # ── FLECHA INDICADORA cuando el boss está fuera de pantalla ─────────
        if not self.is_on_screen(camera_offset):
            screen_cx = WIDTH // 2
            screen_cy = HEIGHT // 2

            # Posición en pantalla del boss
            bx = self.rect.centerx - camera_offset.x
            by = self.rect.centery - camera_offset.y

            # Dirección desde el centro de la pantalla al boss
            dx = bx - screen_cx
            dy = by - screen_cy
            dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)
            nx, ny = dx / dist, dy / dist

            # Margen interior para que la flecha quede dentro de la pantalla
            margin = 60
            # Escalamos para tocar el borde
            scale = min(
                (screen_cx - margin) / max(abs(nx), 0.001),
                (screen_cy - margin) / max(abs(ny), 0.001),
            )
            ax = int(screen_cx + nx * scale)
            ay = int(screen_cy + ny * scale)

            # Dibujamos una flecha triangular apuntando al boss
            import math
            angle = math.atan2(ny, nx)
            arrow_len = 22
            arrow_w = 11
            tip = (ax + int(math.cos(angle) * arrow_len),
                   ay + int(math.sin(angle) * arrow_len))
            left = (ax + int(math.cos(angle + math.pi * 0.75) * arrow_w),
                    ay + int(math.sin(angle + math.pi * 0.75) * arrow_w))
            right = (ax + int(math.cos(angle - math.pi * 0.75) * arrow_w),
                     ay + int(math.sin(angle - math.pi * 0.75) * arrow_w))

            pygame.draw.polygon(screen, (220, 20, 20), [tip, left, right])
            pygame.draw.polygon(screen, (255, 255, 255), [tip, left, right], 2)

            # Mini texto con HP restante junto a la flecha
            font_small = pygame.font.SysFont("Arial", 15, bold=True)
            hp_txt = font_small.render(f"{self.hp}/{self.max_hp}", True, (255, 200, 200))
            screen.blit(hp_txt, (ax - hp_txt.get_width() // 2, ay - hp_txt.get_height() // 2 - 18))

        # ── HEALTHBAR sobre el boss cuando está en pantalla ──────────────────
        else:
            screen_pos = pygame.math.Vector2(self.rect.centerx - camera_offset.x,
                                             self.rect.top    - camera_offset.y - 14)

            bar_w = self.rect.width
            bar_h = 10
            bx = int(screen_pos.x - bar_w // 2)
            by = int(screen_pos.y)

            ratio = max(0.0, self.hp / self.max_hp)
            fill_w = int(bar_w * ratio)

            # Fondo rojo oscuro
            pygame.draw.rect(screen, (100, 0, 0),   (bx, by, bar_w, bar_h), border_radius=4)
            # Relleno verde → amarillo → rojo según HP
            if ratio > 0.5:
                bar_color = (255, int(255 * (1 - ratio) * 2), 0)
            else:
                bar_color = (255, int(255 * ratio * 2), 0)
            pygame.draw.rect(screen, bar_color,      (bx, by, fill_w, bar_h), border_radius=4)
            # Borde blanco
            pygame.draw.rect(screen, (255, 255, 255), (bx, by, bar_w, bar_h), 2, border_radius=4)

            # Nombre del boss
            font_boss = pygame.font.SysFont("Arial", 16, bold=True)
            boss_names = {
                "giga_zombie": "Giga Zombie",
                "yeti":        "Yeti",
                "minotaur":    "Minotauro",
                "boss":        "Boss",
            }
            name = boss_names.get(self.enemy_type, self.enemy_type.capitalize())
            name_surf = font_boss.render(name, True, (255, 80, 80))
            shadow_surf = font_boss.render(name, True, (0, 0, 0))
            nx_pos = int(screen_pos.x - name_surf.get_width() // 2)
            ny_pos = by - name_surf.get_height() - 2
            screen.blit(shadow_surf, (nx_pos + 1, ny_pos + 1))
            screen.blit(name_surf,   (nx_pos,     ny_pos))