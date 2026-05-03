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
from src.entities.pedestal import Pedestal, PEDESTAL_SPAWN_RADIUS_TILES, PEDESTAL_BOSS_NAMES
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
        self.pedestals  = pygame.sprite.Group()

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
        self._near_pedestal   = None
        self._pedestal_spawned = False
        self._obstacles_cache  = []
        self._ui_fonts         = {}
        self._notifications    = []
        # Cola de respawns diferidos: lista de tipos de enemigo pendientes de crear
        self._respawn_queue: list = []
        # Cuántos enemigos instanciar como máximo por frame desde la cola
        self._RESPAWNS_PER_FRAME = 2
        # Spatial grid para colisión jugador-obstáculos (cell = 256 px)
        self._obs_cell = 256
        self._obs_grid: dict = {}   # (cx,cy) -> [hit_rect, ...]

        try:
            pygame.mixer.music.load("assets/sounds/music_game.mp3")
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.01)
            self.player_hurt_sound = pygame.mixer.Sound("assets/sounds/player/player_hurt.mp3")
            self.player_hurt_sound.set_volume(0.05)
        except:
            print("Faltan archivos de audio en assets/sounds/")
            self.player_hurt_sound = None

        # Pre-generar chunks en radio 3 para que arbustos y rocas ya existan
        # al empezar sin que popeen en pantalla (se hace una sola vez aquí)
        self._pre_generate_chunks(radius=3)

    # ─────────────────────────────────────────────────────────────────────────
    def _add_to_obs_grid(self, hit_rect):
        """Inserta un hit_rect en el spatial grid de obstáculos."""
        cell = self._obs_cell
        cx_ = int(hit_rect.centerx // cell)
        cy_ = int(hit_rect.centery // cell)
        self._obs_grid.setdefault((cx_, cy_), []).append(hit_rect)

    def _generate_chunk(self, i, j, chunk_size=512):
        """Genera el contenido de un chunk y lo añade a los grupos y al grid."""
        # En mundos 2 y 3 exigimos que los objetos estén al menos 1 tile (512 px)
        # fuera de la cámara para evitar pop-in visible.
        # Calculamos la posición central del chunk y la del jugador para filtrar.
        chunk_cx = i * chunk_size + chunk_size // 2
        chunk_cy = j * chunk_size + chunk_size // 2
        player_x = self.local_player.pos.x
        player_y = self.local_player.pos.y

        # Distancia mínima desde el jugador para generar objetos (mundos 2 y 3)
        MIN_DIST_SQ = {1: 0, 2: 900**2, 3: 900**2}.get(self.world, 0)
        dist_sq = (chunk_cx - player_x) ** 2 + (chunk_cy - player_y) ** 2
        if dist_sq < MIN_DIST_SQ:
            return   # chunk demasiado cerca — no generar vegetación/rocas aún

        if random.random() < 0.6:
            for _ in range(random.randint(1, 4)):
                bx = i * chunk_size + random.randint(0, chunk_size)
                by = j * chunk_size + random.randint(0, chunk_size)
                new_bush = Bush((bx, by), world=self.world)
                self.all_sprites.add(new_bush)
                self.bushes.add(new_bush)
                hit = getattr(new_bush, 'hit_rect', new_bush.rect)
                self._add_to_obs_grid(hit)

        if random.random() < 0.20:
            for _ in range(random.randint(1, 2)):
                rx = i * chunk_size + random.randint(0, chunk_size)
                ry = j * chunk_size + random.randint(0, chunk_size)
                new_rock = Rock((rx, ry), world=self.world)
                self.rocks.add(new_rock)
                self.all_sprites.add(new_rock)
                hit = getattr(new_rock, 'hit_rect', new_rock.rect)
                self._add_to_obs_grid(hit)

    def _pre_generate_chunks(self, radius=3):
        """Pre-genera chunks en un radio dado al iniciar la sesión (off-screen buffer)."""
        chunk_size = 512
        # Centro del mapa = posición inicial del jugador en chunks
        cx0 = int(self.local_player.pos.x // chunk_size)
        cy0 = int(self.local_player.pos.y // chunk_size)
        for i in range(cx0 - radius, cx0 + radius + 1):
            for j in range(cy0 - radius, cy0 + radius + 1):
                if (i, j) not in self.generated_chunks:
                    self.generated_chunks.add((i, j))
                    self._generate_chunk(i, j, chunk_size)
        self._obstacles_cache = list(self.rocks) + list(self.bushes) + list(self.pedestals)

    # ─────────────────────────────────────────────────────────────────────────
    def _spawn_pedestal_guaranteed(self):
        """Spawnea el pedestal en una posición aleatoria entre 1500 y 3000 px
        del jugador inicial, en una dirección aleatoria.
        Ajusta PEDESTAL_MIN_DIST y PEDESTAL_MAX_DIST para cambiar el rango."""
        PEDESTAL_MIN_DIST = 5000   # ← mínimo en píxeles (~10 tiles de 512 px)
        PEDESTAL_MAX_DIST = 8000   # ← máximo en píxeles (~16 tiles)

        angle    = random.uniform(0, 360)
        distance = random.randint(PEDESTAL_MIN_DIST, PEDESTAL_MAX_DIST)
        offset   = pygame.math.Vector2(distance, 0).rotate(angle)
        spawn_pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2) + offset

        new_pedestal = Pedestal((int(spawn_pos.x), int(spawn_pos.y)), world=self.world)
        new_pedestal.apply_volume_scale(self._volume_factor)
        self.pedestals.add(new_pedestal)
        self.all_sprites.add(new_pedestal)
        self._pedestal_spawned = True
        self._obstacles_cache  = list(self.rocks) + list(self.bushes) + list(self.pedestals)
        self._add_to_obs_grid(new_pedestal.hit_rect)
        boss_name = PEDESTAL_BOSS_NAMES.get(self.world, "Boss")
        self._notifications.append({
            "text":      f"¡Ha aparecido el Altar de Invocación! Búscalo para despertar a {boss_name}",
            "color":     {1: (120, 255, 120), 2: (120, 180, 255), 3: (255, 120, 60)}.get(self.world, (255, 220, 80)),
            "timer":     0,
            "max_timer": 360,   # 6 segundos a 60 fps
        })
        print(f"[Pedestal] Spawneado en {spawn_pos} (distancia {distance:.0f} px, ángulo {angle:.0f}°)")

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
        for pedestal in self.pedestals:
            pedestal.apply_volume_scale(factor)

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

        # Marcar enemigos en/fuera de pantalla y despawnear los muy lejanos
        W = pygame.display.get_surface().get_width()
        H = pygame.display.get_surface().get_height()
        cam_x = self.local_player.rect.centerx - W // 2
        cam_y = self.local_player.rect.centery - H // 2

        # Rect de visibilidad para animaciones (cámara + 200 px de margen)
        screen_rect = pygame.Rect(cam_x - 200, cam_y - 200, W + 400, H + 400)

        # Rect de despawn: cámara + ~2.5 tiles (≈640 px) de margen en cada lado
        DESPAWN_MARGIN = 640
        despawn_rect = pygame.Rect(cam_x - DESPAWN_MARGIN, cam_y - DESPAWN_MARGIN,
                                   W + DESPAWN_MARGIN * 2, H + DESPAWN_MARGIN * 2)

        # Radio mínimo y máximo para el respawn justo fuera de cámara
        RESPAWN_MIN = max(W, H) // 2 + 350   # justo fuera del borde de pantalla
        RESPAWN_MAX = RESPAWN_MIN + 300        # hasta ~300 px más lejos

        enemies_to_respawn = []
        for enemy in list(self.enemies):
            enemy._on_screen = screen_rect.colliderect(enemy.rect)
            # Solo despawnear enemigos normales (los bosses nunca desaparecen)
            if not enemy.is_boss_type() and not despawn_rect.colliderect(enemy.rect):
                enemy.kill()
                enemies_to_respawn.append(enemy.enemy_type)

        # Meter en la cola — no instanciar aquí para no lagear el frame
        self._respawn_queue.extend(enemies_to_respawn)

        # Procesar como máximo N respawns por frame para repartir la carga
        import random as _rnd
        for _ in range(min(self._RESPAWNS_PER_FRAME, len(self._respawn_queue))):
            etype = self._respawn_queue.pop(0)
            angle = _rnd.uniform(0, 360)
            dist  = _rnd.randint(RESPAWN_MIN, RESPAWN_MAX)
            offset_vec = pygame.math.Vector2(dist, 0).rotate(angle)
            new_pos = self.local_player.pos + offset_vec
            new_enemy = Enemy(target=self.local_player, enemy_type=etype)
            new_enemy.pos  = pygame.math.Vector2(new_pos)
            new_enemy.rect.center = new_pos
            new_enemy.apply_volume_scale(self._volume_factor)
            self.enemies.add(new_enemy)
            self.all_sprites.add(new_enemy)

        self.enemies.update()
        self.portals.update()
        self.pedestals.update()

        # Detectar pedestal más cercano en zona de interacción
        self._near_pedestal = None
        for ped in self.pedestals:
            if ped.active and ped.player_in_summon_zone(self.local_player):
                self._near_pedestal = ped
                break

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

        new_chunk_added = False
        for i in range(cx - 1, cx + 2):
            for j in range(cy - 1, cy + 2):
                if (i, j) not in self.generated_chunks:
                    self.generated_chunks.add((i, j))
                    new_chunk_added = True
                    self._generate_chunk(i, j, chunk_size)

        if new_chunk_added:
            self._obstacles_cache = list(self.rocks) + list(self.bushes) + list(self.pedestals)

        # ── SISTEMA DE PUNTOS ────────────────────────────────────────────────
        self.world_timer    += 1
        self.survival_timer += 1
        if self.survival_timer >= 10:
            self.score += 1
            self.survival_timer = 0

        # ── SISTEMA DE FASES Y SPAWN ─────────────────────────────────────────
        # Maximo numero de enemigos
        HARD_CAP = {1: 200, 2: 200, 3: 200}.get(self.world, 80)

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:

            if len(self.enemies) < HARD_CAP:
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

                if not self._pedestal_spawned:
                    self._spawn_pedestal_guaranteed()

            elif self.current_phase == 4:
                # El boss ya no se invoca automáticamente — solo desde el pedestal.
                # Fase 4: el spawn baja gradualmente sin límite hasta 1
                if self.spawn_rate > 1:
                    if self.spawn_rate > {1: 6, 2: 4, 3: 2}.get(self.world, 6):
                        self.spawn_rate -= 0.05
                    else:
                        self.spawn_rate = max(1, self.spawn_rate - 0.03)

                if not self._pedestal_spawned:
                    self._spawn_pedestal_guaranteed()

        # ── FÍSICAS RÍGIDAS ENTRE ENEMIGOS (spatial hash) ─────────────────────
        # En lugar de O(n²) comparamos solo enemigos en la misma celda/vecinas
        CELL = 120   # tamaño de celda del grid; ~radio de separación máximo
        grid: dict[tuple, list] = {}
        enemies_list = list(self.enemies)
        for e in enemies_list:
            cx_ = int(e.pos.x // CELL)
            cy_ = int(e.pos.y // CELL)
            grid.setdefault((cx_, cy_), []).append(e)

        for (cx_, cy_), cell_enemies in grid.items():
            # Reunir candidatos: celda propia + 8 vecinas
            candidates = []
            for dx_ in (-1, 0, 1):
                for dy_ in (-1, 0, 1):
                    candidates.extend(grid.get((cx_ + dx_, cy_ + dy_), []))

            for i, e1 in enumerate(cell_enemies):
                for e2 in candidates:
                    if e2 is e1:
                        continue
                    # Evitar procesar el par dos veces usando id
                    if id(e2) <= id(e1):
                        continue
                    rad1 = 100 if e1.is_boss_type() else 40
                    rad2 = 100 if e2.is_boss_type() else 40
                    min_dist = (rad1 + rad2) / 2
                    diff = e1.pos - e2.pos
                    dist_sq = diff.x * diff.x + diff.y * diff.y
                    min_sq  = min_dist * min_dist
                    if 0 < dist_sq < min_sq:
                        dist   = dist_sq ** 0.5
                        overlap = min_dist - dist
                        push   = diff / dist * (overlap / 2)
                        e1.pos += push
                        e2.pos -= push
                        e1.rect.center = e1.pos
                        e2.rect.center = e2.pos

        # ── JUGADOR VS ENEMIGOS ───────────────────────────────────────────────
        damage_taken = False
        player_pos = self.local_player.pos
        for enemy in enemies_list:
            diff = player_pos - enemy.pos
            dist_sq = diff.x * diff.x + diff.y * diff.y
            attack_rad = 105 if enemy.is_boss_type() else 50
            if dist_sq >= attack_rad * attack_rad * 4:   # culling rápido
                continue
            dist = dist_sq ** 0.5
            rad  = 100 if enemy.is_boss_type() else 45
            if dist < rad and dist > 0:
                overlap = rad - dist
                push = diff / dist * (overlap / 2)
                self.local_player.pos += push
                enemy.pos -= push
                self.local_player.rect.center = self.local_player.pos
                enemy.rect.center = enemy.pos
                player_pos = self.local_player.pos   # actualizar ref
            if dist < attack_rad:
                damage_taken = True

        if damage_taken:
            self.local_player.take_damage(1)
            if self.player_hurt_sound:
                self.player_hurt_sound.play()

        # ── COLISIÓN JUGADOR VS ROCAS Y ÁRBOLES ──────────────────────────────
        # Solo el jugador colisiona con obstáculos (los enemigos los atraviesan,
        # igual que en Vampire Survivors — eliminar ese bucle fue la mayor ganancia).
        player_hitbox = self.local_player.rect.inflate(
            -self.local_player.rect.width  * 0.6,
            -self.local_player.rect.height * 0.6)
        px_c, py_c = int(self.local_player.pos.x // self._obs_cell), int(self.local_player.pos.y // self._obs_cell)
        nearby_obstacles = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                nearby_obstacles.extend(self._obs_grid.get((px_c + di, py_c + dj), []))
        for hit_rect in nearby_obstacles:
            if not player_hitbox.colliderect(hit_rect):
                continue
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
                player_hitbox = self.local_player.rect.inflate(
                    -self.local_player.rect.width  * 0.6,
                    -self.local_player.rect.height * 0.6)

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
            "zombie":      30,
            "slime":        8,
            "goblin":      10,
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
    def try_summon_boss(self):
        """Llama esto cuando el jugador pulsa E. Invoca al boss si procede."""
        if self._near_pedestal is None:
            return
        if self.boss_spawned or self.boss_defeated:
            return
        if self._near_pedestal.summon_boss():
            boss_type = self._get_boss_type()
            boss = Enemy(target=self.local_player, enemy_type=boss_type)
            boss.apply_volume_scale(self._volume_factor)
            self.enemies.add(boss)
            self.all_sprites.add(boss)
            self.boss_spawned = True
            self._near_pedestal = None

    # ─────────────────────────────────────────────────────────────────────────
    def draw(self, screen):
        self.all_sprites.custom_draw(self.local_player)
        for enemy in self.enemies:
            if enemy.is_boss_type():
                enemy.draw_boss_ui(screen, self.all_sprites.offset)
        self.draw_ui(screen)

    def _get_font(self, size, bold=True):
        """Devuelve una fuente cacheada — SysFont es muy caro si se llama cada frame."""
        key = (size, bold)
        if key not in self._ui_fonts:
            self._ui_fonts[key] = pygame.font.SysFont("Arial", size, bold=bold)
        return self._ui_fonts[key]

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
        font = self._get_font(20)
        lvl_text = font.render(f"Nivel: {self.local_player.level}", True, (255, 255, 255))
        screen.blit(lvl_text, (x + bar_width + 15, y + 10))

        # Mundo — centrado en la parte superior con sombra
        world_names  = {1: "Mundo 1", 2: "Mundo 2", 3: "Mundo Final"}
        world_colors = {1: (100, 200, 100), 2: (100, 150, 255), 3: (255, 100, 100)}
        world_name   = world_names.get(self.world, f"Mundo {self.world}")
        world_color  = world_colors.get(self.world, WHITE)

        font_world  = self._get_font(26)
        world_text  = font_world.render(world_name, True, world_color)
        shadow_text = font_world.render(world_name, True, (0, 0, 0))
        world_rect  = world_text.get_rect(midtop=(W // 2, 10))
        screen.blit(shadow_text, (world_rect.x + 2, world_rect.y + 2))
        screen.blit(world_text,  world_rect)

        # Score
        font_score = self._get_font(20)
        txt_score  = font_score.render(f"Score: {self.score}", True, WHITE)
        screen.blit(txt_score, txt_score.get_rect(topright=(W - 20, 20)))

        # Aviso de portal activo
        if self.portals and self.boss_defeated:
            font_portal = self._get_font(22)
            alpha = int(abs(pygame.time.get_ticks() % 1200 - 600) / 600 * 255)
            msg = font_portal.render("¡Portal activo! Entra para continuar al siguiente mundo", True, (200, 150, 255))
            msg.set_alpha(alpha)
            screen.blit(msg, msg.get_rect(center=(W // 2, H - 40)))

        # Aviso de pedestal cercano
        if self._near_pedestal is not None and not self.boss_spawned and not self.boss_defeated:
            boss_name = PEDESTAL_BOSS_NAMES.get(self.world, "Boss")
            font_ped  = self._get_font(24)
            alpha     = int(abs(pygame.time.get_ticks() % 1000 - 500) / 500 * 255)
            world_prompt_colors = {1: (120, 255, 120), 2: (120, 180, 255), 3: (255, 120, 60)}
            prompt_color = world_prompt_colors.get(self.world, (255, 255, 255))
            msg_ped = font_ped.render(f"Presiona E para invocar a {boss_name}", True, prompt_color)
            shadow  = font_ped.render(f"Presiona E para invocar a {boss_name}", True, (0, 0, 0))
            msg_ped.set_alpha(alpha); shadow.set_alpha(alpha)
            cx, cy = W // 2, H - 80
            screen.blit(shadow,  shadow.get_rect(center=(cx + 2, cy + 2)))
            screen.blit(msg_ped, msg_ped.get_rect(center=(cx,     cy)))

        # Flecha hacia el pedestal (cuando no está en pantalla y el boss no ha sido invocado)
        if not self.boss_spawned and not self.boss_defeated:
            for ped in self.pedestals:
                if not ped.active:
                    continue
                import math as _math
                offset = self.all_sprites.offset
                screen_cx = W // 2
                screen_cy = H // 2

                # Posición del pedestal en pantalla
                ped_sx = ped.rect.centerx - offset.x
                ped_sy = ped.rect.centery - offset.y

                # Solo dibujar la flecha si está FUERA de pantalla
                if 0 <= ped_sx <= W and 0 <= ped_sy <= H:
                    break   # está en pantalla, no hace falta flecha

                dx = ped_sx - screen_cx
                dy = ped_sy - screen_cy
                dist   = max(1, _math.hypot(dx, dy))
                nx, ny = dx / dist, dy / dist

                # Clampeamos el punto de la flecha al borde interior de la pantalla
                margin = 70
                scale  = min(
                    (screen_cx - margin) / max(abs(nx), 0.001),
                    (screen_cy - margin) / max(abs(ny), 0.001),
                )
                ax = int(screen_cx + nx * scale)
                ay = int(screen_cy + ny * scale)

                angle = _math.atan2(ny, nx)
                arrow_len = 24
                arrow_w   = 12

                tip   = (ax + int(_math.cos(angle) * arrow_len),
                         ay + int(_math.sin(angle) * arrow_len))
                left  = (ax + int(_math.cos(angle + _math.pi * 0.75) * arrow_w),
                         ay + int(_math.sin(angle + _math.pi * 0.75) * arrow_w))
                right = (ax + int(_math.cos(angle - _math.pi * 0.75) * arrow_w),
                         ay + int(_math.sin(angle - _math.pi * 0.75) * arrow_w))

                world_arrow_colors = {1: (80, 220, 80), 2: (80, 160, 255), 3: (255, 100, 30)}
                arrow_color = world_arrow_colors.get(self.world, (255, 220, 50))

                pygame.draw.polygon(screen, arrow_color,     [tip, left, right])
                pygame.draw.polygon(screen, (255, 255, 255), [tip, left, right], 2)
                break   # solo hay un pedestal por sesión

        # ── NOTIFICACIONES FLOTANTES ──────────────────────────────────────────
        import math as _math
        font_notif = self._get_font(22)
        active_notifs = []
        for notif in self._notifications:
            notif["timer"] += 1
            t   = notif["timer"]
            mt  = notif["max_timer"]
            if t >= mt:
                continue
            active_notifs.append(notif)

            # Fade in (primeros 30 frames) y fade out (últimos 60 frames)
            if t < 30:
                alpha = int(255 * t / 30)
            elif t > mt - 60:
                alpha = int(255 * (mt - t) / 60)
            else:
                alpha = 255

            # Slide in desde arriba
            slide_y = int(max(0, (30 - t) / 30 * 40))

            surf   = font_notif.render(notif["text"], True, notif["color"])
            shadow = font_notif.render(notif["text"], True, (0, 0, 0))
            surf.set_alpha(alpha); shadow.set_alpha(alpha)

            # Fondo semitransparente
            pad = 14
            bg = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, min(alpha, 160)))
            bx = W // 2 - bg.get_width() // 2
            by = H // 5 - bg.get_height() // 2 - slide_y
            screen.blit(bg, (bx, by))

            tx = W // 2 - surf.get_width() // 2
            ty = by + pad // 2
            screen.blit(shadow, (tx + 2, ty + 2))
            screen.blit(surf,   (tx, ty))

        self._notifications = active_notifs