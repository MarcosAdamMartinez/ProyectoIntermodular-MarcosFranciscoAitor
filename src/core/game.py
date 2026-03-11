import pygame
import os
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.utils.settings import WIDTH, HEIGHT, BLACK, load_sprite


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

        #  FONDO PROCEDURAL
        self.tile_size = 256  # Tamaño de cada baldosa de suelo

        # Intentamos cargar una textura para el suelo (ej: grass.png)
        # Si no existe, load_sprite nos devolverá un cuadrado de color verde oscuro
        self.ground_surface = load_sprite("assets/sprites/grass.png", (self.tile_size, self.tile_size), (30, 100, 30), remove_bg=False)

        # Si estamos usando el color de respaldo (sin imagen), le dibujamos un borde
        # para que se note la cuadrícula al mover la cámara.
        if not os.path.exists("assets/sprites/grass.png"):
            pygame.draw.rect(self.ground_surface, (20, 80, 20), self.ground_surface.get_rect(), 4)

    def custom_draw(self, player):
        # 1. Calcular el desplazamiento de la cámara para centrar al jugador
        self.offset.x = player.rect.centerx - WIDTH // 2
        self.offset.y = player.rect.centery - HEIGHT // 2

        self.display_surface.fill(BLACK)

        # 2. --- DIBUJAR FONDO PROCEDURAL INFINITO ---
        # Averiguamos en qué "coordenadas de baldosa" está la esquina superior izquierda de la cámara
        start_x = int(self.offset.x // self.tile_size)
        start_y = int(self.offset.y // self.tile_size)

        # Calculamos cuántas baldosas caben en la pantalla (+2 para cubrir los bordes al moverse)
        tiles_in_x = (WIDTH // self.tile_size) + 2
        tiles_in_y = (HEIGHT // self.tile_size) + 2

        for col in range(start_x, start_x + tiles_in_x):
            for row in range(start_y, start_y + tiles_in_y):
                # Posición de la baldosa en el mundo real
                x = col * self.tile_size
                y = row * self.tile_size

                # Le restamos el offset de la cámara para saber dónde dibujarla en la pantalla
                self.display_surface.blit(self.ground_surface, (x - self.offset.x, y - self.offset.y))

        # 3. Dibujar todos los sprites (jugador, enemigos, proyectiles) aplicando el offset
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)


class GameSession:
    def __init__(self, character_name="caballero", multiplayer=False):
        self.multiplayer = multiplayer
        self.all_sprites = CameraGroup()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()

        # Jugador Local
        self.local_player = Player(WIDTH // 2, HEIGHT // 2, character_name, self.all_sprites, self.projectiles)
        self.all_sprites.add(self.local_player)

        self.spawn_timer = 0

    def update(self):
        if self.local_player.hp <= 0:
            return False
        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()

        return True

    def update_singleplayer(self):
        self.spawn_timer += 1
        if self.spawn_timer >= 60:  # 1 enemigo por segundo
            new_enemy = Enemy(target=self.local_player)
            self.enemies.add(new_enemy)
            self.all_sprites.add(new_enemy)
            self.spawn_timer = 0

        self.enemies.update()

        # Colisiones Enemigo -> Jugador
        if pygame.sprite.spritecollide(self.local_player, self.enemies, False):
            self.local_player.take_damage(1)

        # Colisiones Proyectil -> Enemigo
        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False)
        for enemy, projs in hits.items():
            for proj in projs:
                enemy.take_damage(proj.damage)
                proj.kill()

    def draw(self, screen):
        self.all_sprites.custom_draw(self.local_player)