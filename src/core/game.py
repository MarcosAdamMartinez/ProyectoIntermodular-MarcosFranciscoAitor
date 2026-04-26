import pygame
import os
import random
import socket
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.entities.experience import Exp
from src.entities.bush import Bush
from src.entities.rock import Rock
from src.entities.portal import Portal
from src.utils.settings import WIDTH, HEIGHT, BLACK, load_sprite, BAR_GREEN, BAR_RED, WHITE, BORDER_GREEN

# Colores de fondo por mundo
WORLD_TILE_COLORS = {
    1: (30, 100, 30),
    2: (20, 40, 100),
    3: (80, 20, 20),
}

WORLD_TILE_BORDER_COLORS = {
    1: (20, 80, 20),
    2: (10, 20, 80),
    3: (60, 10, 10),
}

WORLD_TILE_SPRITES = {
    1: "assets/sprites/grass.png",
    2: "assets/sprites/frost.png",
    3: "assets/sprites/hell.png",
}


class CameraGroup(pygame.sprite.Group):
    def __init__(self, world=1):
        super().__init__()
        self.offset = pygame.math.Vector2()
        self.world = world
        self.tile_size = 256

        sprite_path = WORLD_TILE_SPRITES.get(world, "assets/sprites/grass.png")
        fallback_color = WORLD_TILE_COLORS.get(world, (30, 100, 30))
        self.ground_surface = load_sprite(sprite_path, (self.tile_size, self.tile_size), fallback_color, remove_bg=False)

        if not os.path.exists(sprite_path):
            border_color = WORLD_TILE_BORDER_COLORS.get(world, (20, 80, 20))
            pygame.draw.rect(self.ground_surface, border_color, self.ground_surface.get_rect(), 4)

    def custom_draw(self, player):
        display_surface = pygame.display.get_surface()
        W = display_surface.get_width()
        H = display_surface.get_height()

        self.offset.x = player.rect.centerx - W // 2
        self.offset.y = player.rect.centery - H // 2

        display_surface.fill(BLACK)

        start_x = int(self.offset.x // self.tile_size)
        start_y = int(self.offset.y // self.tile_size)
        tiles_in_x = (W // self.tile_size) + 2
        tiles_in_y = (H // self.tile_size) + 2

        for col in range(start_x, start_x + tiles_in_x):
            for row in range(start_y, start_y + tiles_in_y):
                x = col * self.tile_size
                y = row * self.tile_size
                display_surface.blit(self.ground_surface, (x - self.offset.x, y - self.offset.y))

        for sprite in sorted(self.sprites(), key=lambda sprite: getattr(sprite, 'hit_rect', sprite.rect).centery):
            offset_pos = sprite.rect.topleft - self.offset
            display_surface.blit(sprite.image, offset_pos)


class GameSession:
    def __init__(self, character_name="caballero", multiplayer=False, world=1, carry_player=None):
        self.multiplayer = multiplayer
        self.world = world

        self.all_sprites = CameraGroup(world=world)
        self.enemies    = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.exp        = pygame.sprite.Group()
        self.portals    = pygame.sprite.Group()
        self.rocks      = pygame.sprite.Group()
        self.bushes     = pygame.sprite.Group()

        if carry_player is not None:
            self.local_player = carry_player
            self.local_player.pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
            self.local_player.rect.center = self.local_player.pos
            self.local_player.sprite_group = self.all_sprites
            self.local_player.proj_group   = self.projectiles
            for weapon in self.local_player.weapons:
                weapon.owner = self.local_player
        else:
            self.local_player = Player(WIDTH // 2, HEIGHT // 2, character_name, self.all_sprites, self.projectiles)

        self.all_sprites.add(self.local_player)

        self.spawn_timer   = 0
        self.spawn_rate    = 60
        self.current_phase = 1
        self.boss_spawned  = False
        self.boss_defeated = False

        self.score          = 0
        self.survival_timer = 0
        self.world_timer    = 0
        self.generated_chunks = set()
        self._volume_factor   = 1.0

        try:
            pygame.mixer.music.load("assets/sounds/music_game.mp3")
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.01)
            self.player_hurt_sound = pygame.mixer.Sound("assets/sounds/player/player_hurt.mp3")
            self.player_hurt_sound.set_volume(0.05)
        except:
            print("Faltan archivos de audio en assets/sounds/")
            self.player_hurt_sound = None

    # ─────────────────────────────────────────────────────────────────────────
    def apply_volume_scale(self, factor):
        self._volume_factor = factor
        if self.player_hurt_sound:
            self.player_hurt_sound.set_volume(0.05 * factor)
        self.local_player.apply_volume_scale(factor)
        for enemy in self.enemies:
            enemy.apply_volume_scale(factor)
        for portal in self.portals:
            portal.apply_volume_scale(factor)

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, username, socket):
        if self.local_player.hp <= 0:
            try:
                subir_score = f"sbsc:{username}:{self.local_player.level}:{self.score}\n"
                socket.sendall(subir_score.encode())
            except:
                pass
            return "GAME_OVER"

        if self.local_player.pending_level_ups > 0:
            self.local_player.pending_level_ups -= 1
            return "LEVEL_UP"

        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()
        self.exp.update()
        self.enemies.update()
        self.portals.update()

        if self.portals:
            hit_portal = pygame.sprite.spritecollideany(
                self.local_player, self.portals,
                collided=pygame.sprite.collide_rect_ratio(0.6)
            )
            if hit_portal:
                return "NEXT_WORLD"

        return "PLAYING"

    # ─────────────────────────────────────────────────────────────────────────
    def update_singleplayer(self):

        # ── GENERACIÓN PROCEDURAL DE ARBUSTOS Y ROCAS ────────────────────────
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
                            new_bush = Bush((bx, by), world=self.world)
                            self.all_sprites.add(new_bush)
                            self.bushes.add(new_bush)

                    if random.random() < 0.20:
                        for _ in range(random.randint(1, 2)):
                            rx = i * chunk_size + random.randint(0, chunk_size)
                            ry = j * chunk_size + random.randint(0, chunk_size)
                            new_rock = Rock((rx, ry), world=self.world)
                            self.rocks.add(new_rock)
                            self.all_sprites.add(new_rock)

        # ── SISTEMA DE PUNTOS ────────────────────────────────────────────────
        self.world_timer    += 1
        self.survival_timer += 1
        if self.survival_timer >= 10:
            self.score += 1
            self.survival_timer = 0

        # ── SISTEMA DE FASES Y SPAWN ─────────────────────────────────────────
        # Límite de enemigos por mundo para no explotar el PC
        # En fase 4 no hay límite: la presión es intencionalmente letal
        enemy_cap = {1: 80, 2: 120, 3: 160}.get(self.world, 80)

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:

            if self.current_phase < 4 and len(self.enemies) < enemy_cap or self.current_phase == 4:
                enemy_type = self._get_spawn_type()
                new_enemy = Enemy(target=self.local_player, enemy_type=enemy_type)
                new_enemy.apply_volume_scale(self._volume_factor)
                self.enemies.add(new_enemy)
                self.all_sprites.add(new_enemy)

            self.spawn_timer = 0

            # Progresión de fases — thresholds más altos en mundos avanzados
            if self.current_phase == 1:
                threshold = {1: 30, 2: 35, 3: 40}.get(self.world, 30)
                if self.spawn_rate > threshold:
                    self.spawn_rate -= 0.3
                else:
                    self.current_phase = 2
                    self.spawn_rate = {1: 55, 2: 60, 3: 65}.get(self.world, 55)

            elif self.current_phase == 2:
                threshold = {1: 20, 2: 25, 3: 30}.get(self.world, 20)
                if self.spawn_rate > threshold:
                    self.spawn_rate -= 0.25
                else:
                    self.current_phase = 3
                    self.spawn_rate = {1: 45, 2: 50, 3: 55}.get(self.world, 45)

            elif self.current_phase == 3:
                threshold = {1: 12, 2: 15, 3: 18}.get(self.world, 12)
                if self.spawn_rate > threshold:
                    self.spawn_rate -= 0.2
                else:
                    self.current_phase = 4

            elif self.current_phase == 4:
                if not self.boss_spawned:
                    boss_type = self._get_boss_type()
                    boss = Enemy(target=self.local_player, enemy_type=boss_type)
                    boss.apply_volume_scale(self._volume_factor)
                    self.enemies.add(boss)
                    self.all_sprites.add(boss)
                    self.boss_spawned = True

                # Fase 4: el spawn baja gradualmente sin límite hasta 1
                # Primero baja rápido hasta el umbral de fase, luego muy
                # despacio hacia 1 (un enemigo por tick = presión letal).
                # El enemy_cap se ignora en fase 4 para que la presión sea real.
                if self.spawn_rate > 1:
                    if self.spawn_rate > {1: 6, 2: 4, 3: 2}.get(self.world, 6):
                        # Tramo inicial: misma velocidad que antes
                        self.spawn_rate -= 0.05
                    else:
                        # Tramo infinito: baja muy despacio (≈3 min para llegar a 1)
                        self.spawn_rate = max(1, self.spawn_rate - 0.03)

        # ── FÍSICAS RÍGIDAS ENTRE ENEMIGOS ───────────────────────────────────
        enemies_list = list(self.enemies)
        for i in range(len(enemies_list)):
            e1 = enemies_list[i]
            for j in range(i + 1, len(enemies_list)):
                e2 = enemies_list[j]
                if e1.rect.colliderect(e2.rect):
                    rad1 = 100 if e1.is_boss_type() else 40
                    rad2 = 100 if e2.is_boss_type() else 40
                    min_dist = (rad1 + rad2) / 2
                    dist = e1.pos.distance_to(e2.pos)
                    if dist < min_dist and dist > 0:
                        overlap = min_dist - dist
                        push = (e1.pos - e2.pos).normalize() * (overlap / 2)
                        e1.pos += push
                        e2.pos -= push
                        e1.rect.center = e1.pos
                        e2.rect.center = e2.pos

        # ── JUGADOR VS ENEMIGOS ───────────────────────────────────────────────
        damage_taken = False
        for enemy in self.enemies:
            if self.local_player.rect.colliderect(enemy.rect):
                rad  = 100 if enemy.is_boss_type() else 45
                dist = self.local_player.pos.distance_to(enemy.pos)

                if dist < rad and dist > 0:
                    overlap = rad - dist
                    push = (self.local_player.pos - enemy.pos).normalize() * (overlap / 2)
                    self.local_player.pos += push
                    enemy.pos -= push
                    self.local_player.rect.center = self.local_player.pos
                    enemy.rect.center = enemy.pos

                attack_rad = 105 if enemy.is_boss_type() else 50
                if dist < attack_rad:
                    damage_taken = True

        if damage_taken:
            self.local_player.take_damage(1)
            if self.player_hurt_sound:
                self.player_hurt_sound.play()

        # ── COLISIÓN JUGADOR VS ROCAS Y ÁRBOLES ──────────────────────────────
        for obstacle in list(self.rocks) + list(self.bushes):
            hit_rect = getattr(obstacle, 'hit_rect', obstacle.rect)

            player_hitbox = self.local_player.rect.inflate(
                -self.local_player.rect.width  * 0.6,
                -self.local_player.rect.height * 0.6)

            if player_hitbox.colliderect(hit_rect):
                dx = player_hitbox.centerx - hit_rect.centerx
                dy = player_hitbox.centery - hit_rect.centery
                overlap_x = (player_hitbox.width  / 2 + hit_rect.width  / 2) - abs(dx)
                overlap_y = (player_hitbox.height / 2 + hit_rect.height / 2) - abs(dy)

                if overlap_x > 0 and overlap_y > 0:
                    if overlap_x < overlap_y:
                        self.local_player.pos.x += overlap_x if dx > 0 else -overlap_x
                    else:
                        self.local_player.pos.y += overlap_y if dy > 0 else -overlap_y
                    self.local_player.rect.center = self.local_player.pos

        # ── COLISIÓN ENEMIGOS VS ROCAS Y ÁRBOLES ─────────────────────────────
        for enemy in self.enemies:
            for obstacle in list(self.rocks) + list(self.bushes):
                hit_rect = getattr(obstacle, 'hit_rect', obstacle.rect)

                enemy_hitbox = enemy.rect.inflate(
                    -enemy.rect.width  * 0.3,
                    -enemy.rect.height * 0.3)

                if enemy_hitbox.colliderect(hit_rect):
                    dx = enemy_hitbox.centerx - hit_rect.centerx
                    dy = enemy_hitbox.centery - hit_rect.centery
                    overlap_x = (enemy_hitbox.width  / 2 + hit_rect.width  / 2) - abs(dx)
                    overlap_y = (enemy_hitbox.height / 2 + hit_rect.height / 2) - abs(dy)

                    if overlap_x > 0 and overlap_y > 0:
                        if overlap_x < overlap_y:
                            enemy.pos.x += overlap_x if dx > 0 else -overlap_x
                        else:
                            enemy.pos.y += overlap_y if dy > 0 else -overlap_y
                        enemy.rect.center = enemy.pos

        # ── COLISIONES DE ARMAS Y LOOT DE EXPERIENCIA ────────────────────────
        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False,
                                          collided=pygame.sprite.collide_rect_ratio(0.5))
        for enemy, projs in hits.items():
            for proj in projs:
                if getattr(proj, 'is_boomerang', False) or getattr(proj, 'is_melee', False):
                    if enemy not in proj.hit_enemies:
                        if enemy.take_damage(proj.damage):
                            self.on_enemy_killed(enemy)
                        proj.hit_enemies.append(enemy)
                else:
                    if enemy.take_damage(proj.damage):
                        self.on_enemy_killed(enemy)
                    proj.kill()

        # ── IMÁN DE EXPERIENCIA ───────────────────────────────────────────────
        for exp in self.exp:
            if self.local_player.pos.distance_to(exp.pos) < self.local_player.magnet_radius:
                exp.target = self.local_player

        collected = pygame.sprite.spritecollide(self.local_player, self.exp, True,
                                                collided=pygame.sprite.collide_rect_ratio(0.5))
        for gem in collected:
            self.local_player.gain_xp(gem.xp_value)

    # ─────────────────────────────────────────────────────────────────────────
    def _get_spawn_type(self):
        if self.world == 1:
            if self.current_phase == 1:
                return random.choice(["zombie", "slime"])
            elif self.current_phase == 2:
                return random.choice(["zombie", "slime", "goblin"])
            elif self.current_phase == 3:
                return random.choice(["goblin", "goblin", "slime", "zombie"])
            else:
                return random.choice(["goblin", "zombie", "slime"])

        elif self.world == 2:
            if self.current_phase == 1:
                return "zombie"
            elif self.current_phase == 2:
                return random.choice(["zombie", "golem"])
            elif self.current_phase == 3:
                return random.choice(["golem", "skeleton", "skeleton"])
            else:
                return random.choice(["skeleton", "golem", "zombie"])

        elif self.world == 3:
            if self.current_phase == 1:
                return "skeleton"
            elif self.current_phase == 2:
                return random.choice(["skeleton", "bat"])
            elif self.current_phase == 3:
                return random.choice(["bat", "demon", "skeleton"])
            else:
                # Proporción de demonios crece cada 30 s
                demon_weight = min(8, 1 + self.world_timer // 1800)
                pool = ["demon"] * demon_weight + ["bat"] * 2 + ["skeleton"]
                return random.choice(pool)

        return "zombie"

    def _get_boss_type(self):
        return {1: "giga_zombie", 2: "yeti", 3: "minotaur"}.get(self.world, "giga_zombie")

    # ─────────────────────────────────────────────────────────────────────────
    def on_enemy_killed(self, enemy):
        xp_table = {
            "zombie":      10,
            "slime":        8,
            "goblin":      30,
            "golem":       60,
            "skeleton":    75,
            "bat":         20,
            "demon":      100,
            "giga_zombie": 200,
            "yeti":        300,
            "minotaur":    500,
            "boss":        200,
        }
        xp_amount  = xp_table.get(enemy.enemy_type, 10)
        drop_count = 10 if enemy.is_boss_type() else 1

        for _ in range(drop_count):
            new_exp = Exp(
                enemy.pos + pygame.math.Vector2(random.randint(-20, 20), random.randint(-20, 20)),
                xp_amount)
            self.exp.add(new_exp)
            self.all_sprites.add(new_exp)

        self.score += 500 if enemy.is_boss_type() else 50

        if enemy.is_boss_type() and not self.boss_defeated:
            self.boss_defeated = True
            self._spawn_portal(enemy.pos)

    def _spawn_portal(self, pos):
        if self.world >= 3:
            return
        portal = Portal(pos)
        self.portals.add(portal)
        self.all_sprites.add(portal)

    # ─────────────────────────────────────────────────────────────────────────
    def draw(self, screen):
        self.all_sprites.custom_draw(self.local_player)
        for enemy in self.enemies:
            if enemy.is_boss_type():
                enemy.draw_boss_ui(screen, self.all_sprites.offset)
        self.draw_ui(screen)

    def draw_ui(self, screen):
        W = screen.get_width()
        H = screen.get_height()
        bar_width  = 200
        bar_height = 20
        x, y = 20, 20

        # Barra de vida
        current_hp  = max(0, self.local_player.hp)
        hp_ratio    = current_hp / self.local_player.max_hp
        fill_width  = bar_width * hp_ratio

        pygame.draw.rect(screen, BAR_RED,   pygame.Rect(x, y, bar_width, bar_height))
        pygame.draw.rect(screen, BAR_GREEN, pygame.Rect(x, y, fill_width, bar_height))
        pygame.draw.rect(screen, WHITE,     pygame.Rect(x, y, bar_width, bar_height), 2)

        # Barra de experiencia
        xp_y       = y + bar_height + 5
        xp_ratio   = self.local_player.xp / self.local_player.xp_to_next_level
        xp_fill_w  = bar_width * xp_ratio

        pygame.draw.rect(screen, (0, 0, 100),    pygame.Rect(x, xp_y, bar_width, bar_height))
        pygame.draw.rect(screen, (50, 150, 255), pygame.Rect(x, xp_y, xp_fill_w, bar_height))
        pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(x, xp_y, bar_width, bar_height), 2)

        # Nivel
        font = pygame.font.SysFont("Arial", 20, bold=True)
        lvl_text = font.render(f"Nivel: {self.local_player.level}", True, (255, 255, 255))
        screen.blit(lvl_text, (x + bar_width + 15, y + 10))

        # Mundo — centrado en la parte superior con sombra
        world_names  = {1: "Mundo 1", 2: "Mundo 2", 3: "Mundo Final"}
        world_colors = {1: (100, 200, 100), 2: (100, 150, 255), 3: (255, 100, 100)}
        world_name   = world_names.get(self.world, f"Mundo {self.world}")
        world_color  = world_colors.get(self.world, WHITE)

        font_world  = pygame.font.SysFont("Arial", 26, bold=True)
        world_text  = font_world.render(world_name, True, world_color)
        shadow_text = font_world.render(world_name, True, (0, 0, 0))
        world_rect  = world_text.get_rect(midtop=(W // 2, 10))
        screen.blit(shadow_text, (world_rect.x + 2, world_rect.y + 2))
        screen.blit(world_text,  world_rect)

        # Score
        font_score = pygame.font.SysFont("Arial", 20, bold=True)
        txt_score  = font_score.render(f"Score: {self.score}", True, WHITE)
        screen.blit(txt_score, txt_score.get_rect(topright=(W - 20, 20)))

        # Aviso de portal activo
        if self.portals and self.boss_defeated:
            font_portal = pygame.font.SysFont("Arial", 22, bold=True)
            alpha = int(abs(pygame.time.get_ticks() % 1200 - 600) / 600 * 255)
            msg = font_portal.render("¡Portal activo! Entra para continuar al siguiente mundo", True, (200, 150, 255))
            msg.set_alpha(alpha)
            screen.blit(msg, msg.get_rect(center=(W // 2, H - 40)))