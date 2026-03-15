import pygame
import os
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.entities.experience import Exp
from src.utils.settings import WIDTH, HEIGHT, BLACK, load_sprite, BAR_GREEN, BAR_RED, WHITE, BORDER_GREEN


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

        #  FONDO PROCEDURAL
        self.tile_size = 256  # Tamaño de cada baldosa del suelo

        # Intentamos cargar la textura de suelo
        # Si no existe usamos el metodo load_sprite que nos devolvera un cuadrado de color verde oscuro
        self.ground_surface = load_sprite("assets/sprites/grass.png", (self.tile_size, self.tile_size), (30, 100, 30), remove_bg=False)

        # Si estamos usando el color de respaldo, le dibujamos un borde
        # para que se note la cuadricula al mover la camara
        if not os.path.exists("assets/sprites/grass.png"):
            pygame.draw.rect(self.ground_surface, BORDER_GREEN, self.ground_surface.get_rect(), 4)

    def custom_draw(self, player):
        # Calculamos el desplazamiento de la camara para centrar al jugador
        self.offset.x = player.rect.centerx - WIDTH // 2
        self.offset.y = player.rect.centery - HEIGHT // 2

        # Rellenamos la superficie del display
        self.display_surface.fill(BLACK)

        # DIBUJAMOS EL FONDO PROCEDURAL INFINITO
        # Averiguamos en que coordenadas de baldosa esta la esquina superior izquierda de la camara
        start_x = int(self.offset.x // self.tile_size)
        start_y = int(self.offset.y // self.tile_size)

        # Calculamos cuantas baldosas caben en la pantalla y le sumamos 2 para cubrir los bordes al desplazarse
        tiles_in_x = (WIDTH // self.tile_size) + 2
        tiles_in_y = (HEIGHT // self.tile_size) + 2

        for col in range(start_x, start_x + tiles_in_x):
            for row in range(start_y, start_y + tiles_in_y):
                # Posicion de la baldosa en el mundo real
                x = col * self.tile_size
                y = row * self.tile_size

                # Le restamos el offset de la cámara para saber donde dibujarla en la pantalla
                self.display_surface.blit(self.ground_surface, (x - self.offset.x, y - self.offset.y))

        # Dibujamos todos los sprites (jugador, enemigos, proyectiles) aplicando el offset
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)


class GameSession:
    def __init__(self, character_name="caballero", multiplayer=False):
        # Variable para el multijugador
        self.multiplayer = multiplayer

        # Variable encargada de almacenar todos los sprites
        self.all_sprites = CameraGroup()
        # Variable encargada de almacenar todos los enemigos
        self.enemies = pygame.sprite.Group()
        # Variable encargada de almacenar todos los proyectiles
        self.projectiles = pygame.sprite.Group()
        # Variable encargada de almacenar toda la experiencia en el suelo
        self.exp = pygame.sprite.Group()

        # Jugador Local
        self.local_player = Player(WIDTH // 2, HEIGHT // 2, character_name, self.all_sprites, self.projectiles)
        self.all_sprites.add(self.local_player)

        # Variables para el spawn de los enemigos
        self.spawn_timer = 0
        self.spawn_rate = 60

    def update(self):
        # Comprobar si el jugador esta muerto
        if self.local_player.hp <= 0:
            # Si lo esta devuelve "GAME_OVER"
            return "GAME_OVER"

        if self.local_player.pending_level_ups > 0:
            self.local_player.pending_level_ups -= 1
            return "LEVEL_UP"

        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()
        self.exp.update()

        return "PLAYING"


    def update_singleplayer(self):
        # Sumamos 1 por cada tick para llegar al spawn_rate
        self.spawn_timer += 1

        # Si el spawn_timer es igual l spawn_rate spawnea un enemigo
        if self.spawn_timer >= self.spawn_rate:

            # Crea el enemigo
            new_enemy = Enemy(target=self.local_player)
            self.enemies.add(new_enemy)
            (self.all_sprites.add(new_enemy))

            # Resetea el spawn_timer
            self.spawn_timer = 0

            # Disminuye el spawn_rate progresivamente para mas dificultad
            if self.spawn_rate > 20:
                self.spawn_rate -= 0.5

        self.enemies.update()

        # Colisiones Enemigo -> Jugador
        # Añadimos collided = pygame.sprite.collide_rect_ratio(0.5) para reducir la hitbox de ambos a la mitad centrada
        if pygame.sprite.spritecollide(self.local_player, self.enemies, False, collided=pygame.sprite.collide_rect_ratio(0.4)):
            self.local_player.take_damage(1)

        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False, collided=pygame.sprite.collide_rect_ratio(0.4))

        for enemy, projs in hits.items():
            for proj in projs:
                # Si el enemigo muere al recibir el dano creamos una gema en su posicion
                if enemy.take_damage(proj.damage):
                    new_exp = Exp(enemy.pos)
                    self.exp.add(new_exp)
                    self.all_sprites.add(new_exp)
                proj.kill()

        # Comprobamos la distancia de todas las gemas para activar el iman del jugador
        for exp in self.exp:
            if self.local_player.pos.distance_to(exp.pos) < self.local_player.magnet_radius:
                exp.target = self.local_player

        # Verificamos si el jugador ha tocado fisicamente alguna gema para absorberla
        collected = pygame.sprite.spritecollide(self.local_player, self.exp, True, collided=pygame.sprite.collide_rect_ratio(0.5))
        for gem in collected:
            self.local_player.gain_xp(gem.xp_value)

    def draw(self, screen):
        # La cámara dibuja el mapa y los sprites desplazados
        self.all_sprites.custom_draw(self.local_player)

        # Dibuja la Interfaz de Usuario - Barra de vida
        self.draw_ui(screen)

    def draw_ui(self, screen):
        # BARRA DE VIDA
        bar_width = 200
        bar_height = 20

        x = 20
        y = 20

        # Prevenir que la vida baje de 0 para el cálculo matemático
        current_hp = max(0, self.local_player.hp)

        # Calcular qué porcentaje de la barra debe estar lleno
        hp_ratio = current_hp / self.local_player.max_hp
        fill_width = bar_width * hp_ratio

        # Crear los rectángulos
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        fill_rect = pygame.Rect(x, y, fill_width, bar_height)

        # Dibujar en la pantalla (Fondo rojo oscuro, relleno verde, borde blanco)
        pygame.draw.rect(screen, BAR_RED, bg_rect)  # Fondo Rojo
        pygame.draw.rect(screen, BAR_GREEN, fill_rect)  # Relleno Verde
        pygame.draw.rect(screen, WHITE, bg_rect, 2)  # Borde

        # BARRA DE EXPERIENCIA
        xp_y = y + bar_height + 5  # La colocamos un poco mas abajo que la de vida

        # Calculamos el porcentaje de nivel completado
        xp_ratio = self.local_player.xp / self.local_player.xp_to_next_level
        xp_fill_width = bar_width * xp_ratio

        xp_bg_rect = pygame.Rect(x, xp_y, bar_width, bar_height)
        xp_fill_rect = pygame.Rect(x, xp_y, xp_fill_width, bar_height)

        # Dibujamos fondo oscuro relleno azul y borde blanco
        pygame.draw.rect(screen, (0, 0, 100), xp_bg_rect)
        pygame.draw.rect(screen, (50, 150, 255), xp_fill_rect)
        pygame.draw.rect(screen, (255, 255, 255), xp_bg_rect, 2)

        # Dibujamos el texto del nivel actual al lado de las barras
        font = pygame.font.SysFont("Arial", 20, bold=True)
        lvl_text = font.render(f"Nivel: {self.local_player.level}", True, (255, 255, 255))
        screen.blit(lvl_text, (x + bar_width + 15, y + 10))