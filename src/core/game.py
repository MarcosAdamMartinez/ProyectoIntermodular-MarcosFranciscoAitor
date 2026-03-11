import pygame
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.utils.settings import WIDTH, HEIGHT, BLACK

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        # Calcular el desplazamiento para centrar al jugador
        self.offset.x = player.rect.centerx - WIDTH // 2
        self.offset.y = player.rect.centery - HEIGHT // 2

        self.display_surface.fill(BLACK)

        # Dibujar sprites aplicando el offset, ordenados por Y para dar efecto de profundidad
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
        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()

    def update_singleplayer(self):
        self.spawn_timer += 1
        if self.spawn_timer >= 60:  # 1 enemigo por segundo a 60 FPS
            new_enemy = Enemy(target=self.local_player)
            self.enemies.add(new_enemy)
            self.all_sprites.add(new_enemy)
            self.spawn_timer = 0

        self.enemies.update()

        # Daño al jugador
        if pygame.sprite.spritecollide(self.local_player, self.enemies, False):
            self.local_player.take_damage(1)

        # Daño a enemigos
        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False)
        for enemy, projs in hits.items():
            for proj in projs:
                enemy.take_damage(proj.damage)
                proj.kill()

    def draw(self, screen):
        self.all_sprites.custom_draw(self.local_player)