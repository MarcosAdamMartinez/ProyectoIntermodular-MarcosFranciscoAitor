import pygame
import os
import random
import socket
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.entities.experience import Exp
from src.entities.bush import Bush
from src.utils.settings import WIDTH, HEIGHT, BLACK, load_sprite, BAR_GREEN, BAR_RED, WHITE, BORDER_GREEN


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

        #  FONDO PROCEDURAL
        self.tile_size = 256

        self.ground_surface = load_sprite("assets/sprites/grass.png", (self.tile_size, self.tile_size), (30, 100, 30),
                                          remove_bg=False)

        if not os.path.exists("assets/sprites/grass.png"):
            pygame.draw.rect(self.ground_surface, BORDER_GREEN, self.ground_surface.get_rect(), 4)

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - WIDTH // 2
        self.offset.y = player.rect.centery - HEIGHT // 2

        self.display_surface.fill(BLACK)

        start_x = int(self.offset.x // self.tile_size)
        start_y = int(self.offset.y // self.tile_size)

        tiles_in_x = (WIDTH // self.tile_size) + 2
        tiles_in_y = (HEIGHT // self.tile_size) + 2

        for col in range(start_x, start_x + tiles_in_x):
            for row in range(start_y, start_y + tiles_in_y):
                x = col * self.tile_size
                y = row * self.tile_size
                self.display_surface.blit(self.ground_surface, (x - self.offset.x, y - self.offset.y))

        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)


class GameSession:
    def __init__(self, character_name="caballero", multiplayer=False):
        self.multiplayer = multiplayer

        self.all_sprites = CameraGroup()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.exp = pygame.sprite.Group()

        self.local_player = Player(WIDTH // 2, HEIGHT // 2, character_name, self.all_sprites, self.projectiles)
        self.all_sprites.add(self.local_player)

        self.spawn_timer = 0
        self.spawn_rate = 60

        self.current_phase = 1
        self.boss_spawned = False

        self.score = 0
        self.survival_timer = 0
        self.generated_chunks = set()

        # --- CARGAR SONIDOS DE GAMEPLAY ---
        try:
            # Iniciar la música de fondo del juego
            pygame.mixer.music.load("assets/sounds/music_game.mp3")
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.01)

            # Sonido al recibir daño el jugador
            self.player_hurt_sound = pygame.mixer.Sound("assets/sounds/player/player_hurt.mp3")
            self.player_hurt_sound.set_volume(0.05)

        except:
            print("Faltan archivos de audio en assets/sounds/")
            self.player_hurt_sound = None

    def update(self, username, socket):
        if self.local_player.hp <= 0:
            subir_score = f"sbsc:{username}:{self.local_player.level}:{self.score}\n"
            socket.sendall(subir_score.encode())
            print("Intento de mansaje exitoso")
            return "GAME_OVER"

        if self.local_player.pending_level_ups > 0:
            self.local_player.pending_level_ups -= 1
            return "LEVEL_UP"

        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()
        self.exp.update()

        # Ahora los enemigos reciben la orden de caminar
        self.enemies.update()

        return "PLAYING"

    def update_singleplayer(self):
        # GENERACIÓN PROCEDURAL DE ARBUSTOS
        chunk_size = 512
        px, py = self.local_player.pos.x, self.local_player.pos.y
        cx, cy = int(px // chunk_size), int(py // chunk_size)

        for i in range(cx - 1, cx + 2):
            for j in range(cy - 1, cy + 2):
                if (i, j) not in self.generated_chunks:
                    self.generated_chunks.add((i, j))
                    if random.random() < 0.6:
                        for _ in range(random.randint(1, 4)):
                            bx = i * chunk_size + random.randint(0, chunk_size)
                            by = j * chunk_size + random.randint(0, chunk_size)
                            new_bush = Bush((bx, by))
                            self.all_sprites.add(new_bush)

        # SISTEMA DE PUNTOS
        self.survival_timer += 1
        if self.survival_timer >= 10:
            self.score += 1
            self.survival_timer = 0

        # SISTEMA DE FASES Y SPAWN DE ENEMIGOS
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:

            # Límite absoluto de 300 enemigos en pantalla para evitar crasheos de FPS
            if len(self.enemies) < 300:
                enemy_type = "zombie"
                if self.current_phase == 2:
                    enemy_type = random.choice(["zombie", "goblin", "goblin"])
                elif self.current_phase == 3:
                    enemy_type = random.choice(["goblin", "skeleton", "skeleton"])
                elif self.current_phase == 4:
                    enemy_type = random.choice(["skeleton", "skeleton", "goblin"])

                new_enemy = Enemy(target=self.local_player, enemy_type=enemy_type)
                self.enemies.add(new_enemy)
                self.all_sprites.add(new_enemy)

            self.spawn_timer = 0

            if self.current_phase == 1:
                if self.spawn_rate > 20:
                    self.spawn_rate -= 0.5
                else:
                    self.current_phase = 2
                    self.spawn_rate = 50

            elif self.current_phase == 2:
                if self.spawn_rate > 15:
                    self.spawn_rate -= 0.5
                else:
                    self.current_phase = 3
                    self.spawn_rate = 40

            elif self.current_phase == 3:
                if self.spawn_rate > 10:
                    self.spawn_rate -= 0.5
                else:
                    self.current_phase = 4

            elif self.current_phase == 4:
                if not self.boss_spawned:
                    boss = Enemy(target=self.local_player, enemy_type="boss")
                    self.enemies.add(boss)
                    self.all_sprites.add(boss)
                    self.boss_spawned = True

                if self.spawn_rate > 5:
                    self.spawn_rate -= 0.2

        # FÍSICAS RIGIDAS
        enemies_list = list(self.enemies)
        for i in range(len(enemies_list)):
            e1 = enemies_list[i]
            for j in range(i + 1, len(enemies_list)):
                e2 = enemies_list[j]

                # Solo calculamos distancias SI las cajas de colisión se están rozando
                if e1.rect.colliderect(e2.rect):
                    rad1 = 100 if e1.enemy_type == "boss" else 40
                    rad2 = 100 if e2.enemy_type == "boss" else 40
                    min_dist = (rad1 + rad2) / 2

                    dist = e1.pos.distance_to(e2.pos)
                    if dist < min_dist and dist > 0:
                        overlap = min_dist - dist
                        push = (e1.pos - e2.pos).normalize() * (overlap / 2)
                        e1.pos += push
                        e2.pos -= push
                        e1.rect.center = e1.pos
                        e2.rect.center = e2.pos

        # Jugador vs Zombi (Físicas de separación y daño)
        damage_taken = False
        for enemy in self.enemies:
            if self.local_player.rect.colliderect(enemy.rect):
                rad = 100 if enemy.enemy_type == "boss" else 45
                dist = self.local_player.pos.distance_to(enemy.pos)

                # Física de separación sólida
                if dist < rad and dist > 0:
                    overlap = rad - dist
                    push = (self.local_player.pos - enemy.pos).normalize() * (overlap / 2)
                    self.local_player.pos += push
                    enemy.pos -= push
                    self.local_player.rect.center = self.local_player.pos
                    enemy.rect.center = enemy.pos

                # Check de daño: El Boss tiene más alcance (105) para compensar su gran tamaño
                attack_rad = 105 if enemy.enemy_type == "boss" else 50
                if dist < attack_rad:
                    damage_taken = True

        # Aplicamos el daño una sola vez por fotograma si algún enemigo nos ha alcanzado
        if damage_taken:
            self.local_player.take_damage(1)
            # --- SONIDO AL RECIBIR DAÑO ---
            if self.player_hurt_sound:
                self.player_hurt_sound.play()

        # COLISIONES DE ARMAS Y LOOT DE EXPERIENCIA DINÁMICA
        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False,
                                          collided=pygame.sprite.collide_rect_ratio(0.5))

        for enemy, projs in hits.items():
            for proj in projs:
                if getattr(proj, 'is_boomerang', False) or getattr(proj, 'is_melee', False):
                    if enemy not in proj.hit_enemies:
                        if enemy.take_damage(proj.damage):

                            # CALCULAMOS LA EXPERIENCIA SEGUN EL TIPO
                            xp_amount = 10
                            if enemy.enemy_type == "goblin":
                                xp_amount = 30
                            elif enemy.enemy_type == "skeleton":
                                xp_amount = 75
                            elif enemy.enemy_type == "boss":
                                xp_amount = 200  # ¡10 gemas de 200 = 2000 XP!

                            drop_count = 10 if enemy.enemy_type == "boss" else 1
                            for _ in range(drop_count):
                                new_exp = Exp(
                                    enemy.pos + pygame.math.Vector2(random.randint(-20, 20), random.randint(-20, 20)),
                                    xp_amount)
                                self.exp.add(new_exp)
                                self.all_sprites.add(new_exp)
                            self.score += 500 if enemy.enemy_type == "boss" else 50
                        proj.hit_enemies.append(enemy)
                else:
                    if enemy.take_damage(proj.damage):

                        # --- CALCULAMOS LA EXPERIENCIA SEGUN EL TIPO ---
                        xp_amount = 10
                        if enemy.enemy_type == "goblin":
                            xp_amount = 30
                        elif enemy.enemy_type == "skeleton":
                            xp_amount = 75
                        elif enemy.enemy_type == "boss":
                            xp_amount = 200

                        drop_count = 10 if enemy.enemy_type == "boss" else 1
                        for _ in range(drop_count):
                            new_exp = Exp(
                                enemy.pos + pygame.math.Vector2(random.randint(-20, 20), random.randint(-20, 20)),
                                xp_amount)
                            self.exp.add(new_exp)
                            self.all_sprites.add(new_exp)
                        self.score += 500 if enemy.enemy_type == "boss" else 50
                    proj.kill()

        # Iman de experiencia
        for exp in self.exp:
            if self.local_player.pos.distance_to(exp.pos) < self.local_player.magnet_radius:
                exp.target = self.local_player

        collected = pygame.sprite.spritecollide(self.local_player, self.exp, True,
                                                collided=pygame.sprite.collide_rect_ratio(0.5))
        for gem in collected:
            self.local_player.gain_xp(gem.xp_value)


    def draw(self, screen):
        self.all_sprites.custom_draw(self.local_player)
        self.draw_ui(screen)

    def draw_ui(self, screen):
        bar_width = 200
        bar_height = 20
        x = 20
        y = 20

        current_hp = max(0, self.local_player.hp)
        hp_ratio = current_hp / self.local_player.max_hp
        fill_width = bar_width * hp_ratio

        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        fill_rect = pygame.Rect(x, y, fill_width, bar_height)

        pygame.draw.rect(screen, BAR_RED, bg_rect)
        pygame.draw.rect(screen, BAR_GREEN, fill_rect)
        pygame.draw.rect(screen, WHITE, bg_rect, 2)

        xp_y = y + bar_height + 5
        xp_ratio = self.local_player.xp / self.local_player.xp_to_next_level
        xp_fill_width = bar_width * xp_ratio

        xp_bg_rect = pygame.Rect(x, xp_y, bar_width, bar_height)
        xp_fill_rect = pygame.Rect(x, xp_y, xp_fill_width, bar_height)

        pygame.draw.rect(screen, (0, 0, 100), xp_bg_rect)
        pygame.draw.rect(screen, (50, 150, 255), xp_fill_rect)
        pygame.draw.rect(screen, (255, 255, 255), xp_bg_rect, 2)

        font = pygame.font.SysFont("Arial", 20, bold=True)
        lvl_text = font.render(f"Nivel: {self.local_player.level}", True, (255, 255, 255))
        screen.blit(lvl_text, (x + bar_width + 15, y + 10))

        font_score = pygame.font.SysFont("Arial", 20, bold=True)
        txt_score = font_score.render(f"Score: {self.score}", True, WHITE)
        score_rect = txt_score.get_rect(topright=(WIDTH - 20, 20))
        screen.blit(txt_score, score_rect)