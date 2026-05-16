# Importamos pygame y módulos del sistema que vamos a necesitar
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
from src.entities.projectile import BurnZone, BananaFrag
from src.entities.chest import Chest
from src.utils.settings import WIDTH, HEIGHT, BLACK, load_sprite, BAR_GREEN, BAR_RED, WHITE, BORDER_GREEN, UPGRADES

# Color principal del suelo para cada mundo (1=bosque, 2=hielo, 3=infierno)
WORLD_TILE_COLORS = {
    1: (30, 100, 30),
    2: (20, 40, 100),
    3: (80, 20, 20),
}

# Color del borde del tile, ligeramente más oscuro que el principal
WORLD_TILE_BORDER_COLORS = {
    1: (20, 80, 20),
    2: (10, 20, 80),
    3: (60, 10, 10),
}

# Ruta al sprite de suelo que usaremos para cada mundo
WORLD_TILE_SPRITES = {
    1: "assets/sprites/grass.png",
    2: "assets/sprites/frost.png",
    3: "assets/sprites/hell.png",
}


# Esta clase maneja la cámara y dibuja los tiles de fondo + todos los sprites
class CameraGroup(pygame.sprite.Group):
    def __init__(self, world=1):
        super().__init__()
        # El offset nos dice cuánto hay que desplazar la cámara respecto al jugador
        self.offset = pygame.math.Vector2()
        self.world = world
        self.tile_size = 256

        # Cargamos el sprite del suelo; si no existe usamos el color de fallback
        sprite_path = WORLD_TILE_SPRITES.get(world, "assets/sprites/grass.png")
        fallback_color = WORLD_TILE_COLORS.get(world, (30, 100, 30))
        self.ground_surface = load_sprite(sprite_path, (self.tile_size, self.tile_size), fallback_color, remove_bg=False)

        # Si el sprite no existe en disco, dibujamos un borde encima del color sólido
        if not os.path.exists(sprite_path):
            border_color = WORLD_TILE_BORDER_COLORS.get(world, (20, 80, 20))
            pygame.draw.rect(self.ground_surface, border_color, self.ground_surface.get_rect(), 4)

    def custom_draw(self, player):
        display_surface = pygame.display.get_surface()
        W = display_surface.get_width()
        H = display_surface.get_height()

        # Calculamos el offset para centrar la cámara en el jugador
        self.offset.x = player.rect.centerx - W // 2
        self.offset.y = player.rect.centery - H // 2

        # Calculamos qué tiles son visibles y los dibujamos todos (sin fill negro)
        start_x = int(self.offset.x // self.tile_size)
        start_y = int(self.offset.y // self.tile_size)
        tiles_in_x = (W // self.tile_size) + 2
        tiles_in_y = (H // self.tile_size) + 2

        for col in range(start_x, start_x + tiles_in_x):
            for row in range(start_y, start_y + tiles_in_y):
                x = col * self.tile_size
                y = row * self.tile_size
                display_surface.blit(self.ground_surface, (x - self.offset.x, y - self.offset.y))

        # Descartamos sprites fuera de pantalla antes de ordenar para no perder tiempo
        off_x = self.offset.x
        off_y = self.offset.y
        vis_l = off_x - 64
        vis_t = off_y - 64
        vis_r = off_x + W + 64
        vis_b = off_y + H + 64

        # Recopilamos solo los sprites visibles y los ordenamos por su Y para el efecto de profundidad
        visible = []
        for spr in self.sprites():
            r = spr.rect
            if r.right >= vis_l and r.left <= vis_r and r.bottom >= vis_t and r.top <= vis_b:
                cy = getattr(spr, 'hit_rect', r).centery
                visible.append((cy, r.x - off_x, r.y - off_y, spr.image))

        # Ordenamos por Y y dibujamos de arriba a abajo (los de abajo tapan a los de arriba)
        visible.sort(key=lambda t: t[0])
        for _, bx, by, img in visible:
            display_surface.blit(img, (bx, by))


# Esta es la clase principal que gestiona toda la lógica de una partida
class GameSession:
    def __init__(self, character_name="caballero", multiplayer=False, world=1, carry_player=None):
        self.multiplayer = multiplayer
        self.world = world

        # Creamos todos los grupos de sprites que vamos a necesitar
        self.all_sprites = CameraGroup(world=world)
        self.enemies    = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.exp        = pygame.sprite.Group()
        self.portals    = pygame.sprite.Group()
        self.rocks      = pygame.sprite.Group()
        self.bushes     = pygame.sprite.Group()
        self.burn_zones   = pygame.sprite.Group()
        self.banana_frags = pygame.sprite.Group()
        self.chests       = pygame.sprite.Group()
        self.pedestals  = pygame.sprite.Group()

        # Guardamos aquí el pedestal y cofre más cercano al jugador para saber si puede interactuar
        self.near_pedestal   = None
        self.near_chest      = None

        # Si venimos de otro mundo, reutilizamos el jugador anterior con sus stats
        if carry_player is not None:
            self.local_player = carry_player
            self.local_player.pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
            self.local_player.rect.center = self.local_player.pos
            self.local_player.sprite_group = self.all_sprites
            self.local_player.proj_group   = self.projectiles
            for weapon in self.local_player.weapons:
                weapon.owner = self.local_player
        else:
            # Si es partida nueva creamos el jugador desde cero
            self.local_player = Player(WIDTH // 2, HEIGHT // 2, character_name, self.all_sprites, self.projectiles)

        self.all_sprites.add(self.local_player)

        # Variables de control del spawn de enemigos y fases del juego
        self.spawn_timer   = 0
        self.spawn_rate    = 60
        self.current_phase = 1
        self.boss_spawned  = False
        self.boss_defeated = False
        self.final_slides_pending = False

        # Variables de puntuación y tiempo de partida
        self.score          = 0
        self.survival_timer = 0
        self.world_timer    = 0
        self.generated_chunks = set()
        self.volume_factor   = 1.0
        self.obstacles_cache  = []
        self.pedestal_spawned = False
        # Cuando matamos al minotauro activamos esto para congelar spawns y bloquear el pedestal
        self.endgame_active = False
        self.ui_fonts         = {}
        self.notifications    = []

        # Usamos deque para que el pop desde el frente sea O(1) en vez de O(n)
        from collections import deque as deque
        self.respawn_queue: deque = deque()
        # Máximo de enemigos que instanciamos por frame desde la cola de respawn
        self.RESPAWNS_PER_FRAME = 2

        # Grid espacial para colisiones jugador-obstáculos, cada celda mide 256 px
        self.obs_cell = 256
        self.obs_grid: dict = {}

        # Intentamos cargar el sonido de daño del jugador en varios formatos
        self.player_hurt_sound = None
        import os as os
        for ext in ("ogg", "wav", "mp3"):
            hurt_path = f"assets/sounds/player/player_hurt.{ext}"
            if os.path.exists(hurt_path):
                try:
                    self.player_hurt_sound = pygame.mixer.Sound(hurt_path)
                    self.player_hurt_sound.set_volume(0.05)
                except Exception as e:
                    print(f"[hurt sfx] Error: {e}")
                break

        # Pre-generamos los chunks del entorno para que los objetos ya existan al empezar
        self.pre_generate_chunks(radius=3)

    def add_to_obs_grid(self, hit_rect):
        # Insertamos el hit_rect de un obstáculo en la celda correcta del grid espacial
        cell = self.obs_cell
        cx_ = int(hit_rect.centerx // cell)
        cy_ = int(hit_rect.centery // cell)
        self.obs_grid.setdefault((cx_, cy_), []).append(hit_rect)

    def generate_chunk(self, i, j, chunk_size=512):
        # Generamos arbustos y rocas en el chunk (i, j) y los añadimos al grid
        chunk_cx = i * chunk_size + chunk_size // 2
        chunk_cy = j * chunk_size + chunk_size // 2
        player_x = self.local_player.pos.x
        player_y = self.local_player.pos.y

        # En mundos avanzados no generamos objetos demasiado cerca del jugador para evitar pop-in
        MIN_DIST_SQ = {1: 0, 2: 900**2, 3: 900**2}.get(self.world, 0)
        dist_sq = (chunk_cx - player_x) ** 2 + (chunk_cy - player_y) ** 2
        if dist_sq < MIN_DIST_SQ:
            return

        # Con 60% de probabilidad spawneamos entre 1 y 4 arbustos en este chunk
        if random.random() < 0.6:
            for _ in range(random.randint(1, 4)):
                bx = i * chunk_size + random.randint(0, chunk_size)
                by = j * chunk_size + random.randint(0, chunk_size)
                new_bush = Bush((bx, by), world=self.world)
                self.all_sprites.add(new_bush)
                self.bushes.add(new_bush)
                hit = getattr(new_bush, 'hit_rect', new_bush.rect)
                self.add_to_obs_grid(hit)

        # Con 20% de probabilidad spawneamos entre 1 y 2 rocas en este chunk
        if random.random() < 0.20:
            for _ in range(random.randint(1, 2)):
                rx = i * chunk_size + random.randint(0, chunk_size)
                ry = j * chunk_size + random.randint(0, chunk_size)
                new_rock = Rock((rx, ry), world=self.world)
                self.rocks.add(new_rock)
                self.all_sprites.add(new_rock)
                hit = getattr(new_rock, 'hit_rect', new_rock.rect)
                self.add_to_obs_grid(hit)

    def pre_generate_chunks(self, radius=3):
        # Generamos los chunks cercanos al inicio para que el jugador no vea cosas aparecer de la nada
        chunk_size = 512
        cx0 = int(self.local_player.pos.x // chunk_size)
        cy0 = int(self.local_player.pos.y // chunk_size)
        for i in range(cx0 - radius, cx0 + radius + 1):
            for j in range(cy0 - radius, cy0 + radius + 1):
                if (i, j) not in self.generated_chunks:
                    self.generated_chunks.add((i, j))
                    self.generate_chunk(i, j, chunk_size)
        self.obstacles_cache = list(self.rocks) + list(self.bushes) + list(self.pedestals)

    def spawn_pedestal_guaranteed(self):
        # Spawneamos el altar de invocación a una distancia aleatoria del jugador
        PEDESTAL_MIN_DIST = 5000
        PEDESTAL_MAX_DIST = 8000

        angle    = random.uniform(0, 360)
        distance = random.randint(PEDESTAL_MIN_DIST, PEDESTAL_MAX_DIST)
        offset   = pygame.math.Vector2(distance, 0).rotate(angle)
        spawn_pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2) + offset

        new_pedestal = Pedestal((int(spawn_pos.x), int(spawn_pos.y)), world=self.world)
        new_pedestal.apply_volume_scale(self.volume_factor)
        self.pedestals.add(new_pedestal)
        self.all_sprites.add(new_pedestal)
        self.pedestal_spawned = True
        self.obstacles_cache  = list(self.rocks) + list(self.bushes) + list(self.pedestals)
        self.add_to_obs_grid(new_pedestal.hit_rect)
        # Mostramos una notificación para que el jugador sepa que apareció el altar
        self.notifications.append({
            "text":      f"¡Ha aparecido el Altar de Invocación! Búscalo siguendo la flecha",
            "color":     {1: (226, 120, 78), 2: (163, 248, 151), 3: (94, 99, 255)}.get(self.world, (255, 220, 80)),
            "timer":     0,
            "max_timer": 360,
        })
        print(f"[Pedestal] Spawneado en {spawn_pos} (distancia {distance:.0f} px, ángulo {angle:.0f}°)")

    def apply_volume_scale(self, factor):
        # Aplicamos el factor de volumen a todos los sonidos de la sesión
        self.volume_factor = factor
        if self.player_hurt_sound:
            self.player_hurt_sound.set_volume(0.05 * factor)
        self.local_player.apply_volume_scale(factor)
        for enemy in self.enemies:
            enemy.apply_volume_scale(factor)
        for portal in self.portals:
            portal.apply_volume_scale(factor)
        for pedestal in self.pedestals:
            pedestal.apply_volume_scale(factor)

    def update(self, username, socket):
        # Si el jugador está muerto devolvemos GAME_OVER para que el engine lo gestione
        if self.local_player.hp <= 0:
            return "GAME_OVER"

        # Si el jugador tiene subidas de nivel pendientes las procesamos de una en una
        if self.local_player.pending_level_ups > 0:
            self.local_player.pending_level_ups -= 1
            return "LEVEL_UP"
        self.local_player.update(self.enemies)
        self.update_singleplayer()
        self.projectiles.update()
        self.exp.update()

        # Calculamos el rect de cámara para saber qué enemigos están en pantalla
        W = pygame.display.get_surface().get_width()
        H = pygame.display.get_surface().get_height()
        cam_x = self.local_player.rect.centerx - W // 2
        cam_y = self.local_player.rect.centery - H // 2

        # Los sprites dentro de este rect actualizan su animación normalmente
        screen_rect = pygame.Rect(cam_x - 200, cam_y - 200, W + 400, H + 400)

        # Los enemigos fuera de este rect más grande se despawnean para ahorrar CPU
        DESPAWN_MARGIN = 640
        despawn_rect = pygame.Rect(cam_x - DESPAWN_MARGIN, cam_y - DESPAWN_MARGIN,
                                   W + DESPAWN_MARGIN * 2, H + DESPAWN_MARGIN * 2)

        # Calculamos el rango en el que reaparecerán los enemigos despawneados
        RESPAWN_MIN = max(W, H) // 2 + 350
        RESPAWN_MAX = RESPAWN_MIN + 300

        enemies_to_respawn = []
        for enemy in list(self.enemies):
            enemy.on_screen = screen_rect.colliderect(enemy.rect)
            # Solo despawneamos enemigos normales, los bosses nunca desaparecen
            if not enemy.is_boss_type() and not despawn_rect.colliderect(enemy.rect):
                enemy.kill()
                enemies_to_respawn.append(enemy.enemy_type)

        # Metemos los tipos a respawnear en la cola para procesarlos poco a poco
        self.respawn_queue.extend(enemies_to_respawn)

        # Procesamos la cola de respawn poco a poco para no lagear el frame
        hp_mult  = 1.0 + (self.score // 1000) * 0.05
        dmg_mult = 1.0 + (self.score // 1000) * 0.05
        for _ in range(min(self.RESPAWNS_PER_FRAME, len(self.respawn_queue))):
            etype = self.respawn_queue.popleft()
            angle = random.uniform(0, 360)
            dist  = random.randint(RESPAWN_MIN, RESPAWN_MAX)
            offset_vec = pygame.math.Vector2(dist, 0).rotate(angle)
            new_pos = self.local_player.pos + offset_vec
            new_enemy = Enemy(target=self.local_player, enemy_type=etype)
            # Escalamos HP y daño según la puntuación acumulada
            new_enemy.hp             = max(1, int(new_enemy.hp             * hp_mult))
            new_enemy.max_hp         = max(1, int(new_enemy.max_hp         * hp_mult))
            new_enemy.contact_damage = max(1, int(new_enemy.contact_damage * dmg_mult))
            new_enemy.pos  = pygame.math.Vector2(new_pos)
            new_enemy.rect.center = new_pos
            new_enemy.apply_volume_scale(self.volume_factor)
            self.enemies.add(new_enemy)
            self.all_sprites.add(new_enemy)

        # Actualizamos el resto de grupos de sprites
        self.enemies.update()
        self.portals.update()
        self.pedestals.update()
        self.burn_zones.update()
        self.banana_frags.update()

        # Aplicamos daño de quemadura a los enemigos dentro de cada zona de fuego
        for bz in list(self.burn_zones):
            if bz.tick == 0:
                for enemy in list(self.enemies):
                    if enemy in bz.hit_enemies:
                        continue
                    dx = enemy.pos.x - bz.pos.x
                    dy = enemy.pos.y - bz.pos.y
                    if dx*dx + dy*dy <= bz.radius ** 2:
                        if enemy.take_damage(bz.burn_damage):
                            self.on_enemy_killed(enemy)
                        bz.hit_enemies.append(enemy)

        # Comprobamos colisiones entre enemigos y fragmentos de banana
        frag_hits = pygame.sprite.groupcollide(
            self.enemies, self.banana_frags, False, False,
            collided=pygame.sprite.collide_rect_ratio(0.5))
        for enemy, frags in frag_hits.items():
            for frag in frags:
                if enemy not in frag.hit_enemies:
                    killed = enemy.take_damage(frag.damage)
                    frag.hit_enemies.append(enemy)
                    if killed:
                        self.on_enemy_killed(enemy)
                        break

        self.chests.update()

        # Buscamos si el jugador está cerca de algún pedestal para mostrar el prompt
        self.near_pedestal = None
        for ped in self.pedestals:
            if ped.active and ped.player_in_summon_zone(self.local_player):
                self.near_pedestal = ped
                break

        # Buscamos el cofre más cercano al jugador para permitir abrirlo
        self.near_chest = None
        for chest in self.chests:
            if chest.player_nearby(self.local_player):
                self.near_chest = chest
                break

        # Si el jugador toca un portal, pasamos al siguiente mundo
        if self.portals:
            hit_portal = pygame.sprite.spritecollideany(
                self.local_player, self.portals,
                collided=pygame.sprite.collide_rect_ratio(0.6)
            )
            if hit_portal:
                return "NEXT_WORLD"

        # Si hay una cinemática de final de juego pendiente, la lanzamos
        if getattr(self, 'endgame_cutscene_pending', False):
            self.endgame_cutscene_pending = False
            return "ENDGAME_CUTSCENE"
        return "PLAYING"

    def update_singleplayer(self):

        # Generamos nuevos chunks según la posición del jugador (mundo infinito)
        chunk_size = 512
        px, py = self.local_player.pos.x, self.local_player.pos.y
        cx, cy = int(px // chunk_size), int(py // chunk_size)

        new_chunk_added = False
        for i in range(cx - 1, cx + 2):
            for j in range(cy - 1, cy + 2):
                if (i, j) not in self.generated_chunks:
                    self.generated_chunks.add((i, j))
                    new_chunk_added = True
                    self.generate_chunk(i, j, chunk_size)

        # Solo recalculamos el cache de obstáculos si añadimos un chunk nuevo
        if new_chunk_added:
            self.obstacles_cache = list(self.rocks) + list(self.bushes) + list(self.pedestals)

        # Sumamos puntos por sobrevivir; cada 10 frames equivale a 1 punto de supervivencia
        self.world_timer    += 1
        self.survival_timer += 1
        if self.survival_timer >= 10:
            self.score += 1
            self.survival_timer = 0

        # En pantallas pequeñas bajamos el cap de enemigos para no matar la CPU
        DEFAULT_WIDTH = 1720
        screen_w = pygame.display.get_surface().get_width()
        if screen_w < DEFAULT_WIDTH:
            HARD_CAP = {1: 150, 2: 150, 3: 150}.get(self.world, 150)
        else:
            HARD_CAP = {1: 200, 2: 200, 3: 200}.get(self.world, 200)

        # Cada vez que el timer llega al spawn_rate, spawneamos un nuevo enemigo
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:

            if len(self.enemies) < HARD_CAP:
                enemy_type = self.get_spawn_type()
                new_enemy = Enemy(target=self.local_player, enemy_type=enemy_type)
                # Los enemigos se vuelven más duros conforme sube la puntuación
                hp_mult  = 1.0 + (self.score // 1000) * 0.05
                dmg_mult = 1.0 + (self.score // 1000) * 0.05
                new_enemy.hp             = max(1, int(new_enemy.hp             * hp_mult))
                new_enemy.max_hp         = max(1, int(new_enemy.max_hp         * hp_mult))
                new_enemy.contact_damage = max(1, int(new_enemy.contact_damage * dmg_mult))
                new_enemy.apply_volume_scale(self.volume_factor)
                self.enemies.add(new_enemy)
                self.all_sprites.add(new_enemy)

            self.spawn_timer = 0

            # Progresión de fases: cada fase reduce spawn_rate hasta llegar al umbral
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

                # En fase 3 es cuando aparece el pedestal por primera vez
                if not self.pedestal_spawned:
                    self.spawn_pedestal_guaranteed()

            elif self.current_phase == 4:
                # Fase final: el spawn_rate sigue bajando hasta llegar a 1
                if self.spawn_rate > 1:
                    if self.spawn_rate > {1: 6, 2: 4, 3: 2}.get(self.world, 6):
                        self.spawn_rate -= 0.05
                    else:
                        self.spawn_rate = max(1, self.spawn_rate - 0.03)

                # Si el endgame está activo no volvemos a spawnear el pedestal
                if not self.pedestal_spawned and not self.endgame_active:
                    self.spawn_pedestal_guaranteed()

        # Separación entre enemigos usando un spatial hash para no hacer O(n²)
        CELL = 120
        grid: dict[tuple, list] = {}
        enemies_list = list(self.enemies)
        for e in enemies_list:
            cx_ = int(e.pos.x // CELL)
            cy_ = int(e.pos.y // CELL)
            grid.setdefault((cx_, cy_), []).append(e)

        for (cx_, cy_), cell_enemies in grid.items():
            # Revisamos la celda propia y las 8 vecinas para encontrar candidatos cercanos
            candidates = []
            for dx_ in (-1, 0, 1):
                for dy_ in (-1, 0, 1):
                    candidates.extend(grid.get((cx_ + dx_, cy_ + dy_), []))

            for i, e1 in enumerate(cell_enemies):
                for e2 in candidates:
                    if e2 is e1:
                        continue
                    # Usamos id para evitar procesar el mismo par dos veces
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

        # Cuántos frames de invencibilidad tiene el jugador tras recibir daño por contacto
        CONTACT_IFRAMES = 20

        # Inicializamos el contador de iframes si aún no existe en la sesión
        if not hasattr(self, 'contact_iframes'):
            self.contact_iframes = 0

        # Decrementamos el contador cada frame hasta que expire la invencibilidad
        if self.contact_iframes > 0:
            self.contact_iframes -= 1

        # Calculamos el máximo daño de contacto de todos los enemigos cercanos
        max_contact_damage = 0
        player_pos = self.local_player.pos
        for enemy in enemies_list:
            diff = player_pos - enemy.pos
            dist_sq = diff.x * diff.x + diff.y * diff.y
            attack_rad = 105 if enemy.is_boss_type() else 50
            if dist_sq >= attack_rad * attack_rad * 4:
                continue
            dist = dist_sq ** 0.5
            rad  = 100 if enemy.is_boss_type() else 45
            # Separamos físicamente al jugador del enemigo si se solapan
            if dist < rad and dist > 0:
                overlap = rad - dist
                push = diff / dist * (overlap / 2)
                self.local_player.pos += push
                enemy.pos -= push
                self.local_player.rect.center = self.local_player.pos
                enemy.rect.center = enemy.pos
                player_pos = self.local_player.pos
            if dist < attack_rad:
                max_contact_damage = max(max_contact_damage, enemy.contact_damage)

        # Solo hacemos daño si el jugador no está en frames de invencibilidad
        if max_contact_damage > 0 and self.contact_iframes == 0:
            self.local_player.take_damage(max_contact_damage)
            if self.player_hurt_sound:
                self.player_hurt_sound.play()
            self.contact_iframes = CONTACT_IFRAMES

        # Colisión del jugador con rocas y arbustos usando el spatial grid de obstáculos
        player_hitbox = self.local_player.rect.inflate(
            -self.local_player.rect.width  * 0.6,
            -self.local_player.rect.height * 0.6)
        px_c, py_c = int(self.local_player.pos.x // self.obs_cell), int(self.local_player.pos.y // self.obs_cell)
        nearby_obstacles = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                nearby_obstacles.extend(self.obs_grid.get((px_c + di, py_c + dj), []))
        for hit_rect in nearby_obstacles:
            if not player_hitbox.colliderect(hit_rect):
                continue
            dx = player_hitbox.centerx - hit_rect.centerx
            dy = player_hitbox.centery - hit_rect.centery
            overlap_x = (player_hitbox.width  / 2 + hit_rect.width  / 2) - abs(dx)
            overlap_y = (player_hitbox.height / 2 + hit_rect.height / 2) - abs(dy)
            # Empujamos al jugador por el eje con menos solapamiento
            if overlap_x > 0 and overlap_y > 0:
                if overlap_x < overlap_y:
                    self.local_player.pos.x += overlap_x if dx > 0 else -overlap_x
                else:
                    self.local_player.pos.y += overlap_y if dy > 0 else -overlap_y
                self.local_player.rect.center = self.local_player.pos
                player_hitbox = self.local_player.rect.inflate(
                    -self.local_player.rect.width  * 0.6,
                    -self.local_player.rect.height * 0.6)

        # Comprobamos qué proyectiles han golpeado enemigos
        hits = pygame.sprite.groupcollide(self.enemies, self.projectiles, False, False,
                                          collided=pygame.sprite.collide_rect_ratio(0.5))
        for enemy, projs in hits.items():
            for proj in projs:
                # Los boomerangs y armas cuerpo a cuerpo pueden golpear varios enemigos
                if getattr(proj, 'is_boomerang', False) or getattr(proj, 'is_melee', False):
                    if enemy not in proj.hit_enemies:
                        if enemy.take_damage(proj.damage):
                            self.on_enemy_killed(enemy)
                        proj.hit_enemies.append(enemy)

                        # Si el boomerang golpea por primera vez, genera fragmentos de banana
                        if getattr(proj, 'is_boomerang', False) and not proj.fragmented:
                            proj.fragmented = True
                            n_frags = proj.stats.get("frags", 2)
                            spread  = 60
                            for k in range(n_frags):
                                if n_frags > 1:
                                    angle_off = -spread / 2 + spread * k / (n_frags - 1)
                                else:
                                    angle_off = 0
                                frag_dir = proj.direction.rotate(angle_off)
                                frag = BananaFrag(proj.pos, frag_dir,
                                                  proj.damage // 2 or 1, proj.stats)
                                self.banana_frags.add(frag)
                                self.all_sprites.add(frag)
                else:
                    # Los proyectiles normales se destruyen al golpear
                    killed = enemy.take_damage(proj.damage)
                    if killed:
                        self.on_enemy_killed(enemy)
                    # Si el proyectil tiene quemadura, creamos una zona de fuego
                    if proj.stats.get("burn"):
                        bz = BurnZone(
                            proj.pos,
                            burn_damage=proj.stats.get("burn_damage", 3),
                            burn_radius=proj.stats.get("burn_radius", 35),
                        )
                        self.burn_zones.add(bz)
                        self.all_sprites.add(bz)
                    proj.kill()

        # El imán de experiencia atrae las gemas que estén dentro del radio del jugador
        magnet_sq = self.local_player.magnet_radius * self.local_player.magnet_radius
        plx = self.local_player.pos.x
        ply = self.local_player.pos.y
        for exp in self.exp:
            dx = exp.pos.x - plx
            dy = exp.pos.y - ply
            if dx * dx + dy * dy < magnet_sq:
                exp.target = self.local_player

        # Recogemos todas las gemas de XP que toca el jugador
        collected = pygame.sprite.spritecollide(self.local_player, self.exp, True,
                                                collided=pygame.sprite.collide_rect_ratio(0.5))
        for gem in collected:
            self.local_player.gain_xp(gem.xp_value)

    def get_spawn_type(self):
        # Devolvemos el tipo de enemigo que toca spawnear según el mundo y la fase actual
        if self.world == 1:
            if self.current_phase == 1:
                return random.choice(["slime", "slime"])
            elif self.current_phase == 2:
                return random.choice(["goblin", "slime", "goblin"])
            elif self.current_phase == 3:
                return random.choice(["zombie", "goblin", "slime", "zombie"])
            else:
                return random.choice(["goblin", "zombie", "slime"])

        elif self.world == 2:
            if self.current_phase == 1:
                return "zombie"
            elif self.current_phase == 2:
                return random.choice(["zombie", "golem", "golem"])
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
                # En fase 4 del mundo 3 los demonios se vuelven más frecuentes con el tiempo
                demon_weight = min(8, 1 + self.world_timer // 1800)
                pool = ["demon"] * demon_weight + ["bat"] * 2 + ["skeleton"]
                return random.choice(pool)

        return "zombie"

    def get_boss_type(self):
        # Cada mundo tiene su propio boss final
        return {1: "giga_zombie", 2: "yeti", 3: "minotaur"}.get(self.world, "giga_zombie")

    def on_enemy_killed(self, enemy):
        # Gestionamos la muerte de un enemigo: XP, drops, puntuación y eventos especiales
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
        # Los bosses sueltan 10 gemas en vez de una
        drop_count = 10 if enemy.is_boss_type() else 1

        for _ in range(drop_count):
            new_exp = Exp(
                enemy.pos + pygame.math.Vector2(random.randint(-20, 20), random.randint(-20, 20)),
                xp_amount)
            self.exp.add(new_exp)
            self.all_sprites.add(new_exp)

        self.score += 500 if enemy.is_boss_type() else 50

        # 5% de probabilidad de que el enemigo deje caer un cofre con mejora
        if random.random() < 0.05 and UPGRADES:
            upgrade = random.choice(UPGRADES)
            chest = Chest(enemy.pos, upgrade)
            self.chests.add(chest)
            self.all_sprites.add(chest)

        # Si matamos al boss activamos el portal o la cinemática final según el mundo
        if enemy.is_boss_type() and not self.boss_defeated:
            self.boss_defeated = True
            if enemy.enemy_type == "minotaur":
                # El minotauro es el jefe final: activamos la cinemática y congelamos spawns
                self.endgame_cutscene_pending = True
                self.endgame_active = True
            else:
                self.spawn_portal(enemy.pos)

    def open_chest(self):
        # Si el jugador está cerca de un cofre, lo abre y devuelve la mejora que contiene
        if self.near_chest is not None:
            upgrade = self.near_chest.upgrade
            self.near_chest.opened = True
            self.near_chest.kill()
            self.near_chest = None
            return upgrade
        return None

    def spawn_portal(self, pos):
        # Creamos un portal hacia el siguiente mundo (solo en mundos 1 y 2)
        if self.world >= 3:
            return
        portal = Portal(pos)
        self.portals.add(portal)
        self.all_sprites.add(portal)

    def try_summon_boss(self):
        # Intentamos invocar al boss cuando el jugador pulsa E en el pedestal
        if self.near_pedestal is None:
            return
        if self.boss_spawned or self.boss_defeated:
            return
        if self.near_pedestal.summon_boss():
            boss_type = self.get_boss_type()
            boss = Enemy(target=self.local_player, enemy_type=boss_type)
            boss.apply_volume_scale(self.volume_factor)
            self.enemies.add(boss)
            self.all_sprites.add(boss)
            self.boss_spawned = True
            self.near_pedestal = None

    def draw(self, screen):
        # Dibujamos el mundo y la UI en pantalla
        self.all_sprites.custom_draw(self.local_player)
        for enemy in self.enemies:
            if enemy.is_boss_type():
                enemy.draw_boss_ui(screen, self.all_sprites.offset)
        # Si hay un cofre cerca mostramos el prompt de interacción
        if self.near_chest is not None:
            self.near_chest.draw_prompt(screen, self.all_sprites.offset)
        self.draw_ui(screen)

    def get_font(self, size, bold=True):
        # Cacheamos las fuentes para no llamar a SysFont cada frame, que es muy lento
        key = (size, bold)
        if key not in self.ui_fonts:
            self.ui_fonts[key] = pygame.font.SysFont("Arial", size, bold=bold)
        return self.ui_fonts[key]

    def draw_ui(self, screen):
        W = screen.get_width()
        H = screen.get_height()
        bar_width  = 200
        bar_height = 20
        x, y = 20, 20

        # Dibujamos la barra de vida del jugador
        current_hp  = max(0, self.local_player.hp)
        hp_ratio    = current_hp / self.local_player.max_hp
        fill_width  = bar_width * hp_ratio

        pygame.draw.rect(screen, BAR_RED,   pygame.Rect(x, y, bar_width, bar_height))
        pygame.draw.rect(screen, BAR_GREEN, pygame.Rect(x, y, fill_width, bar_height))
        pygame.draw.rect(screen, WHITE,     pygame.Rect(x, y, bar_width, bar_height), 2)

        # Dibujamos la barra de experiencia justo debajo de la de vida
        xp_y       = y + bar_height + 5
        xp_ratio   = self.local_player.xp / self.local_player.xp_to_next_level
        xp_fill_w  = bar_width * xp_ratio

        pygame.draw.rect(screen, (0, 0, 100),    pygame.Rect(x, xp_y, bar_width, bar_height))
        pygame.draw.rect(screen, (50, 150, 255), pygame.Rect(x, xp_y, xp_fill_w, bar_height))
        pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(x, xp_y, bar_width, bar_height), 2)

        # Mostramos el nivel actual del jugador
        font = self.get_font(20)
        lvl_text = font.render(f"Nivel: {self.local_player.level}", True, (255, 255, 255))
        screen.blit(lvl_text, (x + bar_width + 15, y + 10))

        # Nombre del mundo centrado arriba con sombra para que se lea bien
        world_names  = {1: "El Valle Verdealma", 2: "El Yermo de Skjorn", 3: "El Ultimo Bastion: Infernia"}
        world_colors = {1: (100, 200, 100), 2: (100, 150, 255), 3: (255, 100, 100)}
        world_name   = world_names.get(self.world, f"Mundo {self.world}")
        world_color  = world_colors.get(self.world, WHITE)

        font_world  = self.get_font(26)
        world_text  = font_world.render(world_name, True, world_color)
        shadow_text = font_world.render(world_name, True, (0, 0, 0))
        world_rect  = world_text.get_rect(midtop=(W // 2, 10))
        screen.blit(shadow_text, (world_rect.x + 2, world_rect.y + 2))
        screen.blit(world_text,  world_rect)

        # Puntuación en la esquina superior derecha
        font_score = self.get_font(20)
        txt_score  = font_score.render(f"Score: {self.score}", True, WHITE)
        screen.blit(txt_score, txt_score.get_rect(topright=(W - 20, 20)))

        # Aviso parpadeante de portal cuando el boss ha sido derrotado
        if self.portals and self.boss_defeated:
            font_portal = self.get_font(22)
            alpha = int(abs(pygame.time.get_ticks() % 1200 - 600) / 600 * 255)
            msg = font_portal.render("¡Portal activo! Entra para continuar al siguiente mundo", True, (200, 150, 255))
            msg.set_alpha(alpha)
            screen.blit(msg, msg.get_rect(center=(W // 2, H - 40)))

        # Aviso parpadeante cuando el jugador está cerca del pedestal y puede invocar al boss
        if self.near_pedestal is not None and not self.boss_spawned and not self.boss_defeated:
            boss_name = PEDESTAL_BOSS_NAMES.get(self.world, "Boss")
            font_ped  = self.get_font(24)
            alpha     = int(abs(pygame.time.get_ticks() % 1000 - 500) / 500 * 255)
            world_prompt_colors = {1: (120, 255, 120), 2: (120, 180, 255), 3: (255, 120, 60)}
            prompt_color = world_prompt_colors.get(self.world, (255, 255, 255))
            msg_ped = font_ped.render(f"Presiona E para invocar a {boss_name}", True, prompt_color)
            shadow  = font_ped.render(f"Presiona E para invocar a {boss_name}", True, (0, 0, 0))
            msg_ped.set_alpha(alpha); shadow.set_alpha(alpha)
            cx, cy = W // 2, H - 80
            screen.blit(shadow,  shadow.get_rect(center=(cx + 2, cy + 2)))
            screen.blit(msg_ped, msg_ped.get_rect(center=(cx,     cy)))

        # Flecha en el borde de pantalla apuntando al pedestal si está fuera de vista
        if not self.boss_spawned and not self.boss_defeated:
            for ped in self.pedestals:
                if not ped.active:
                    continue
                import math as math
                offset = self.all_sprites.offset
                screen_cx = W // 2
                screen_cy = H // 2

                # Calculamos la posición del pedestal en coordenadas de pantalla
                ped_sx = ped.rect.centerx - offset.x
                ped_sy = ped.rect.centery - offset.y

                # Si ya está en pantalla no hace falta dibujar la flecha
                if 0 <= ped_sx <= W and 0 <= ped_sy <= H:
                    break

                dx = ped_sx - screen_cx
                dy = ped_sy - screen_cy
                dist   = max(1, math.hypot(dx, dy))
                nx, ny = dx / dist, dy / dist

                # Calculamos el punto del borde de la pantalla más cercano al pedestal
                margin = 70
                scale  = min(
                    (screen_cx - margin) / max(abs(nx), 0.001),
                    (screen_cy - margin) / max(abs(ny), 0.001),
                )
                ax = int(screen_cx + nx * scale)
                ay = int(screen_cy + ny * scale)

                # Dibujamos un triángulo apuntando hacia el pedestal
                angle = math.atan2(ny, nx)
                arrow_len = 24
                arrow_w   = 12

                tip   = (ax + int(math.cos(angle) * arrow_len),
                         ay + int(math.sin(angle) * arrow_len))
                left  = (ax + int(math.cos(angle + math.pi * 0.75) * arrow_w),
                         ay + int(math.sin(angle + math.pi * 0.75) * arrow_w))
                right = (ax + int(math.cos(angle - math.pi * 0.75) * arrow_w),
                         ay + int(math.sin(angle - math.pi * 0.75) * arrow_w))

                world_arrow_colors = {1: (236, 108, 56), 2: (141, 225, 124), 3: (92, 123, 207)}
                arrow_color = world_arrow_colors.get(self.world, (255, 220, 50))

                pygame.draw.polygon(screen, arrow_color,     [tip, left, right])
                pygame.draw.polygon(screen, (255, 255, 255), [tip, left, right], 2)
                break

        # Sistema de notificaciones flotantes con fade in/out y slide desde arriba
        import math as math
        font_notif = self.get_font(22)
        active_notifs = []
        for notif in self.notifications:
            notif["timer"] += 1
            t   = notif["timer"]
            mt  = notif["max_timer"]
            if t >= mt:
                continue
            active_notifs.append(notif)

            # Calculamos el alpha: sube en los primeros 30 frames y baja en los últimos 60
            if t < 30:
                alpha = int(255 * t / 30)
            elif t > mt - 60:
                alpha = int(255 * (mt - t) / 60)
            else:
                alpha = 255

            # La notificación entra deslizándose desde arriba
            slide_y = int(max(0, (30 - t) / 30 * 40))

            surf   = font_notif.render(notif["text"], True, notif["color"])
            shadow = font_notif.render(notif["text"], True, (0, 0, 0))
            surf.set_alpha(alpha); shadow.set_alpha(alpha)

            # Fondo semitransparente para que el texto sea legible sobre cualquier escenario
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

        # Actualizamos la lista de notificaciones con las que aún están activas
        self.notifications = active_notifs