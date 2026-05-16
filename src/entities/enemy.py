# Importamos lo necesario para el enemigo: pygame, math para la flecha, random para variedad
import pygame
import math
import random
from src.utils.settings import *
from src.utils.animation import AnimationController


# Clase que representa a cualquier enemigo del juego, incluyendo bosses
class Enemy(pygame.sprite.Sprite):
    def __init__(self, target, enemy_type="zombie"):
        super().__init__()

        self.enemy_type = enemy_type

        # Asignamos tamaño, color de fallback, velocidad y HP según el tipo de enemigo
        if enemy_type == "zombie":
            size = (70, 60);   color = RED;              self.speed = random.uniform(1.5, 2.5);  self.hp = 100
        elif enemy_type == "slime":
            size = (80, 70);   color = (0, 200, 100);   self.speed = random.uniform(1.2, 2.0);  self.hp = 30
        elif enemy_type == "goblin":
            size = (70, 60);   color = (0, 150, 0);     self.speed = random.uniform(2.0, 3.0);  self.hp = 90
        elif enemy_type == "skeleton":
            size = (70, 60);   color = (200, 200, 200); self.speed = random.uniform(2.5, 3.5);  self.hp = 120
        elif enemy_type == "golem":
            size = (90, 90);   color = (100, 80, 60);   self.speed = random.uniform(1.0, 1.8);  self.hp = 280
        elif enemy_type == "bat":
            size = (80, 80);   color = (80, 0, 80);     self.speed = random.uniform(3.0, 4.5);  self.hp = 70
        elif enemy_type == "demon":
            size = (110, 110); color = (180, 20, 20);   self.speed = random.uniform(2.5, 3.5);  self.hp = 300
        elif enemy_type == "giga_zombie":
            size = (170, 170); color = (180, 30, 0);    self.speed = random.uniform(2.5, 3.5);  self.hp = 10000
        elif enemy_type == "yeti":
            size = (170, 170); color = (200, 230, 255); self.speed = random.uniform(3.0, 4.8);  self.hp = 20000
        elif enemy_type == "minotaur":
            size = (200, 200); color = (120, 40, 10);   self.speed = random.uniform(3.0, 4.0);  self.hp = 30000
        else:
            size = (200, 200); color = (150, 0, 0);     self.speed = random.uniform(1.0, 1.5);  self.hp = 500

        # El daño por contacto viene de settings para que sea fácil de ajustar
        self.contact_damage = ENEMY_CONTACT_DAMAGE.get(enemy_type, 1)

        # Imagen estática de fallback por si no hay sprites de animación
        fallback = load_sprite(f"assets/sprites/enemies/{enemy_type}.png", size, color)

        # Inicializamos el controlador de animación con la carpeta del enemigo
        anim_base = f"assets/sprites/enemies/{enemy_type}"
        self.anim = AnimationController(anim_base, size, fallback, fps=8)

        self.image = self.anim.update()

        # Los bosses spawnean un poco más lejos para dar tiempo de reacción al jugador
        boss_types = {"giga_zombie", "yeti", "minotaur", "boss"}
        if enemy_type in boss_types:
            spawn_radius = random.randint(1100, 1400)
        else:
            # 1000 px mínimo garantiza que aparece fuera de cámara en cualquier resolución
            spawn_radius = random.randint(1000, 1300)
        angle = random.uniform(0, 360)
        offset = pygame.math.Vector2(spawn_radius, 0).rotate(angle)
        spawn_pos = target.pos + offset

        self.rect = self.image.get_rect(center=(spawn_pos.x, spawn_pos.y))
        self.pos  = pygame.math.Vector2(spawn_pos)

        self.max_hp = self.hp
        self.target = target
        # Game.py actualiza on_screen cada frame para saber si animamos este enemigo
        self.on_screen = True

        # Cacheamos las fuentes para no crear objetos SysFont en cada draw
        self.font_small = pygame.font.SysFont("Arial", 15, bold=True)
        self.font_boss  = pygame.font.SysFont("Arial", 16, bold=True)

        # Cargamos el sonido de daño; si no existe dejamos None sin crashear
        self.base_hurt_vol = 0.04
        try:
            self.hurt_sound = pygame.mixer.Sound(f"assets/sounds/enemies/{enemy_type}hurt.mp3")
            self.hurt_sound.set_volume(self.base_hurt_vol)
        except:
            self.hurt_sound = None

    def apply_volume_scale(self, factor):
        # Ajustamos el volumen del sonido de daño según el factor global
        if self.hurt_sound:
            self.hurt_sound.set_volume(self.base_hurt_vol * factor)

    def update(self):
        # Calculamos la dirección hacia el jugador y movemos al enemigo
        dx = self.target.pos.x - self.pos.x
        dy = self.target.pos.y - self.pos.y
        dist_sq = dx * dx + dy * dy

        moving = dist_sq > 1.0
        if moving:
            # Normalizamos y escalamos en un solo paso para evitar sqrt doble
            inv = self.speed / (dist_sq ** 0.5)
            self.pos.x += dx * inv
            self.pos.y += dy * inv
            self.rect.centerx = int(self.pos.x)
            self.rect.centery  = int(self.pos.y)

        # Solo actualizamos la animación si el enemigo está en pantalla para ahorrar CPU
        if self.on_screen:
            if moving:
                self.anim.set_state("walk_right" if dx >= 0 else "walk_left")
            else:
                self.anim.set_state("idle")
            new_img = self.anim.update()
            # Solo reasignamos image si el frame cambió, evitando get_rect innecesario
            if new_img is not self.image:
                self.image = new_img
                self.rect  = self.image.get_rect(center=self.rect.center)

    def take_damage(self, amount):
        # Reproducimos el sonido de daño, disparamos la animación de hurt y restamos HP
        if self.hurt_sound:
            self.hurt_sound.play()

        self.anim.trigger_hurt()

        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def is_boss_type(self):
        # Devuelve True si este enemigo es un boss (lógica separada en muchos sitios)
        return self.enemy_type in {"giga_zombie", "yeti", "minotaur", "boss"}

    def is_on_screen(self, camera_offset):
        # Comprobamos si el sprite está dentro de los bordes de pantalla con un margen de 16 px
        sx = self.rect.centerx - camera_offset.x
        sy = self.rect.centery - camera_offset.y
        hw = self.rect.width  // 2 + 16
        hh = self.rect.height // 2 + 16
        surf = pygame.display.get_surface()
        W, H = surf.get_width(), surf.get_height()
        return -hw < sx < W + hw and -hh < sy < H + hh

    def draw_boss_ui(self, screen, camera_offset):
        # Dibujamos la barra de vida y el nombre del boss, o una flecha si está fuera de pantalla
        W = screen.get_width()
        H = screen.get_height()

        # Calculamos si el boss está visible en pantalla
        sx = self.rect.centerx - camera_offset.x
        sy = self.rect.centery - camera_offset.y
        hw = self.rect.width  // 2 + 16
        hh = self.rect.height // 2 + 16
        on_screen = -hw < sx < W + hw and -hh < sy < H + hh

        if not on_screen:
            # Si el boss no se ve, dibujamos una flecha en el borde apuntando hacia él
            screen_cx = W // 2
            screen_cy = H // 2

            bx = self.rect.centerx - camera_offset.x
            by = self.rect.centery - camera_offset.y

            dx = bx - screen_cx
            dy = by - screen_cy
            dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)
            nx, ny = dx / dist, dy / dist

            # Clampeamos la flecha al borde interior de la pantalla
            margin = 60
            scale = min(
                (screen_cx - margin) / max(abs(nx), 0.001),
                (screen_cy - margin) / max(abs(ny), 0.001),
            )
            ax = int(screen_cx + nx * scale)
            ay = int(screen_cy + ny * scale)

            # Dibujamos el triángulo de la flecha
            angle = math.atan2(ny, nx)
            arrow_len = 22
            arrow_w = 11
            tip   = (ax + int(math.cos(angle) * arrow_len),
                     ay + int(math.sin(angle) * arrow_len))
            left  = (ax + int(math.cos(angle + math.pi * 0.75) * arrow_w),
                     ay + int(math.sin(angle + math.pi * 0.75) * arrow_w))
            right = (ax + int(math.cos(angle - math.pi * 0.75) * arrow_w),
                     ay + int(math.sin(angle - math.pi * 0.75) * arrow_w))

            pygame.draw.polygon(screen, (220, 20, 20), [tip, left, right])
            pygame.draw.polygon(screen, (255, 255, 255), [tip, left, right], 2)

            # Mostramos también el HP actual junto a la flecha
            font_small = self.font_small
            hp_txt = font_small.render(f"{self.hp}/{self.max_hp}", True, (255, 200, 200))
            screen.blit(hp_txt, (ax - hp_txt.get_width() // 2, ay - hp_txt.get_height() // 2 - 18))

        elif on_screen:
            # Si el boss está en pantalla dibujamos la barra de HP encima de él
            screen_pos = pygame.math.Vector2(self.rect.centerx - camera_offset.x,
                                             self.rect.top      - camera_offset.y - 14)
            bar_w = self.rect.width
            bar_h = 10
            bx = int(screen_pos.x - bar_w // 2)
            by = int(screen_pos.y)

            ratio   = max(0.0, self.hp / self.max_hp)
            fill_w  = int(bar_w * ratio)

            pygame.draw.rect(screen, (100, 0, 0),    (bx, by, bar_w, bar_h), border_radius=4)
            # El color de la barra va de verde a rojo según el HP restante
            if ratio > 0.5:
                bar_color = (255, int(255 * (1 - ratio) * 2), 0)
            else:
                bar_color = (255, int(255 * ratio * 2), 0)
            pygame.draw.rect(screen, bar_color,       (bx, by, fill_w, bar_h), border_radius=4)
            pygame.draw.rect(screen, (255, 255, 255), (bx, by, bar_w,  bar_h), 2, border_radius=4)

            # Dibujamos el nombre del boss encima de la barra con sombra
            font_boss = self.font_boss
            boss_names = {
                "giga_zombie": "Giga Zombie",
                "yeti":        "Yeti",
                "minotaur":    "Minotauro",
                "boss":        "Boss",
            }
            name       = boss_names.get(self.enemy_type, self.enemy_type.capitalize())
            name_surf  = font_boss.render(name, True, (255, 80, 80))
            shadow_surf = font_boss.render(name, True, (0, 0, 0))
            nx_pos = int(screen_pos.x - name_surf.get_width() // 2)
            ny_pos = by - name_surf.get_height() - 2
            screen.blit(shadow_surf, (nx_pos + 1, ny_pos + 1))
            screen.blit(name_surf,   (nx_pos,     ny_pos))