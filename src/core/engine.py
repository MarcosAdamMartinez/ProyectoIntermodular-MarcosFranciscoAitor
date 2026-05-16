# importamos todo lo que necesitamos: random para sorteos, socket para red, json para configs
import random
import sys
import socket
import json
import math

# importamos nuestras clases propias: settings globales, sesión de juego y cinemáticas
from src.utils.settings import *
from src.core.game import GameSession
from src.utils.cutscene import LogoSplash, StorySequence

# lista de resoluciones disponibles con su etiqueta, ancho y alto
RESOLUTIONS = [
    ("640 x 360",   640,   360),
    ("800 x 450",   800,   450),
    ("960 x 540",   960,   540),
    ("1024 x 576",  1024,  576),
    ("1280 x 720",  1280,  720),
    ("1366 x 768",  1366,  768),
    ("1600 x 900",  1600,  900),
    ("1720 x 920",  1720,  920),
    ("1920 x 1080", 1920, 1080),
    ("2560 x 1440", 2560, 1440),
]


# clase principal que controla todo: menús, estados, red y renderizado
class Engine:
    def __init__(self):
        # iniciamos pygame y el sistema de audio
        pygame.init()
        pygame.mixer.init()

        # estado actual de la música, del juego, lista de mejoras y mejora pendiente del cofre
        self.music_state    = "NONE"
        self.state          = "MENU_PRINCIPAL"
        self.current_choices     = []
        self.pending_chest_upgrade = None

        # variables del formulario de login: texto, campo activo y mensaje de error
        self.username_text  = ""
        self.password_text  = ""
        self.active_input   = None
        self.login_error_msg = ""

        # datos del ranking y timestamp de la última petición al servidor
        self.scoreboard_data = []
        self.last_basc_time  = 0

        # guardamos de qué menú venimos para poder volver desde settings
        self.menu_anterior = "MENU_PRINCIPAL"

        # ajustes de pantalla y audio con sus valores por defecto
        self.fullscreen       = False
        self.show_fps         = False
        self.volume           = 1.0
        self.dragging_volume  = False
        self.res_index        = 7

        try:
            # cargamos la configuración guardada del archivo settings.json
            with open("settings.json", "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.fullscreen = bool(datos.get("fullscreen", False))
            self.show_fps   = bool(datos.get("fps", False))
            self.volume     = max(0.0, min(1.0, float(datos.get("volume", 1.0))))
            saved_res = datos.get("resolution", None)
            if saved_res:
                for i, (lbl, w, h) in enumerate(RESOLUTIONS):
                    if (w, h) == tuple(saved_res):
                        self.res_index = i
                        break
        except:
            print("Error loading settings")

        # ancho y alto de la resolución seleccionada
        self.W, self.H = RESOLUTIONS[self.res_index][1], RESOLUTIONS[self.res_index][2]

        # creamos la ventana, le ponemos título y el reloj para controlar los FPS
        self.screen = self.make_window()
        pygame.display.set_caption("Punternows Salvation: The Last Chance")
        self.clock = pygame.time.Clock()

        # activamos repetición de teclas: 500ms delay inicial, 50ms entre repeticiones
        pygame.key.set_repeat(500, 50)

        # cargamos todos los sprites y recursos gráficos del juego
        self.load_assets()

        # cinemática activa y estado al que ir cuando termine
        self.cutscene      = None
        self.cutscene_next = None

        # socket de red e IP del servidor del juego
        self.network_socket = None
        self.host = "52.215.64.91"

        # modo sin conexión y mejor puntuación guardada en local
        self.offline_mode    = False
        self.offline_max_score = 0


    # crea la ventana en modo fullscreen o ventana normal según la config
    def make_window(self):
        if self.fullscreen:
            try:
                # probamos fullscreen con escala, sin escala, y si falla volvemos a ventana normal
                return pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN | pygame.SCALED)
            except pygame.error:
                try:
                    return pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
                except pygame.error:
                    print("Advertencia: no se pudo crear ventana fullscreen, usando modo ventana.")
                    self.fullscreen = False
        return pygame.display.set_mode((self.W, self.H))

    # carga los sprites que dependen del tamaño de ventana, se llama también al cambiar resolución
    def load_assets(self):
        self.main_menu_bg      = load_sprite("assets/sprites/backgrounds/main_menu_bg.png",
                                              (self.W, self.H), DARK_GREY, remove_bg=False)
        self.game_over_menu_bg = load_sprite("assets/sprites/backgrounds/game_over_bg.png",
                                              (self.W, self.H), DARK_GREY, remove_bg=False)
        self.settings_icon     = load_sprite("assets/sprites/icons/settings.png", (80, 60), DARK_GREY)
        self.controles_bg      = load_sprite("assets/sprites/backgrounds/controles_bg.png",
                                              (self.W, self.H), (20, 20, 30), remove_bg=False)

    # cambia la resolución, recrea la ventana y recarga los assets que dependen del tamaño
    def apply_resolution(self):
        self.W, self.H = RESOLUTIONS[self.res_index][1], RESOLUTIONS[self.res_index][2]
        self.screen = self.make_window()
        self.load_assets()
        self.save_settings()

    # helpers para escalar coordenadas y fuentes respecto a la resolución base 1720x920
    def sx(self, x): return int(x * self.W / 1720)
    def sy(self, y): return int(y * self.H / 920)
    def sf(self, size): return max(10, int(size * min(self.W / 1720, self.H / 920)))


    # dibuja botón con sombra y borde; si se pasa color lo usa fijo, si no cambia con hover
    def draw_modern_button(self, rect, text, font, *color):
        mouse_pos = pygame.mouse.get_pos()
        if color:
            sombra = rect.copy(); sombra.y += 4
            pygame.draw.rect(self.screen, BTN_SHADOW, sombra, border_radius=12)
            pygame.draw.rect(self.screen, color[0],   rect,   border_radius=12)
            pygame.draw.rect(self.screen, BTN_BORDER, rect, width=2, border_radius=12)
            txt_surf = font.render(text, True, DEATH_TEXT)
        else:
            color_actual = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_BG
            sombra = rect.copy(); sombra.y += 4
            pygame.draw.rect(self.screen, BTN_SHADOW,    sombra, border_radius=12)
            pygame.draw.rect(self.screen, color_actual,  rect,   border_radius=12)
            pygame.draw.rect(self.screen, BTN_BORDER,    rect, width=2, border_radius=12)
            txt_surf = font.render(text, True, WHITE)
        self.screen.blit(txt_surf,
                         (rect.centerx - txt_surf.get_width()  // 2,
                          rect.centery - txt_surf.get_height() // 2))

    # dibuja el contador de FPS en la esquina superior derecha
    def draw_fps(self):
        font_fps = pygame.font.SysFont("Arial", self.sf(18), bold=True)
        fps_txt  = font_fps.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        self.screen.blit(fps_txt, fps_txt.get_rect(topright=(self.W - 20, self.sy(50))))

    # dibuja el icono de ajustes y devuelve su Rect para detectar clics
    def draw_settings_icon(self):
        icon_size = self.sx(80)
        margin    = self.sx(20)
        sx = self.W - icon_size - margin
        sy = margin
        btn = pygame.Rect(sx, sy, icon_size, icon_size)
        mouse_pos = pygame.mouse.get_pos()
        if btn.collidepoint(mouse_pos):
            hover = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover, (60, 64, 67, 180), hover.get_rect(), border_radius=10)
            self.screen.blit(hover, (sx, sy))
        scaled_icon = pygame.transform.scale(self.settings_icon, (icon_size, int(icon_size * 0.75)))
        self.screen.blit(scaled_icon, (sx, sy))
        return btn

    # dibuja el botón '?' en la esquina inferior derecha y devuelve su Rect
    def draw_help_icon(self):
        size   = self.sx(56)
        margin = self.sx(20)
        sx = self.W - size - margin
        sy = self.H - size - margin
        btn = pygame.Rect(sx, sy, size, size)
        mouse_pos = pygame.mouse.get_pos()
        color = (80, 90, 110) if not btn.collidepoint(mouse_pos) else (110, 130, 160)
        pygame.draw.rect(self.screen, (15, 15, 18), btn.move(0, 3), border_radius=12)
        pygame.draw.rect(self.screen, color,        btn,            border_radius=12)
        pygame.draw.rect(self.screen, BTN_BORDER,   btn, 2,         border_radius=12)
        font_q = pygame.font.SysFont("Arial", self.sf(28), bold=True)
        q_surf = font_q.render("?", True, WHITE)
        self.screen.blit(q_surf, q_surf.get_rect(center=btn.center))
        return btn


    # aplica escala logarítmica al volumen para que suene más natural al mover el slider
    def vol(self, base):
        if self.volume <= 0: return 0.0
        factor = math.log10(1 + 9 * self.volume) / math.log10(10)
        return base * factor

    # actualiza el volumen de la música y los sonidos del juego según el estado actual
    def apply_volume(self):
        if self.state == "PLAYING":
            pygame.mixer.music.set_volume(self.vol(0.01))
        else:
            pygame.mixer.music.set_volume(self.vol(0.04))
        if hasattr(self, "game"):
            factor = math.log10(1 + 9 * self.volume) / math.log10(10) if self.volume > 0 else 0.0
            self.game.apply_volume_scale(factor)

    # gestiona qué música debe sonar según el estado, evitando recargas innecesarias
    def update_music(self):
        MENU_STATES = {"MENU_PRINCIPAL", "MENU_LOGIN", "MENU_REGISTER",
                       "MENU_SELECCION_MODO", "MENU_SELECCION_SOLO"}
        if self.state in MENU_STATES:
            if self.music_state != "MENU":
                try:
                    pygame.mixer.music.load("assets/sounds/music_menu.mp3")
                    pygame.mixer.music.play(-1)
                    pygame.mixer.music.set_volume(self.vol(0.04))
                    self.music_state = "MENU"
                except:
                    print("No se encontro assets/sounds/music_menu.mp3")
            return

        if self.state in ("PLAYING", "PAUSED", "LEVEL_UP", "CUTSCENE", "STORY"):
            world = getattr(self.game, "world", 1) if self.game else 1
            desired = f"WORLD_{world}"
            if self.music_state != desired:
                track = f"assets/sounds/music_world_{world}.mp3"
                try:
                    pygame.mixer.music.load(track)
                    pygame.mixer.music.play(-1)
                    pygame.mixer.music.set_volume(self.vol(0.04))
                    self.music_state = desired
                except:
                    print(f"No se encontro {track}")


    # guarda la configuración en settings.json, leyendo antes para no perder otros campos
    def save_settings(self):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                datos = json.load(f)
        except:
            datos = {}
        datos["fullscreen"]  = self.fullscreen
        datos["fps"]         = self.show_fps
        datos["volume"]      = round(self.volume, 3)
        datos["resolution"]  = [self.W, self.H]
        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(datos, indent=4))
        except:
            pass


    # lee offline.json con los datos sin conexión, devuelve {} si no existe
    def load_offline(self):
        try:
            with open("offline.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    # escribe en offline.json el usuario, contraseña y mejor puntuación local
    def save_offline(self, username, password, max_score):
        try:
            with open("offline.json", "w", encoding="utf-8") as f:
                json.dump({"username": username, "password": password,
                           "max_score": max_score}, f, indent=4)
        except:
            pass

    # sube los datos de offline.json al servidor cuando hay conexión disponible
    def sync_offline_to_server(self):
        datos = self.load_offline()
        if not datos:
            return

        user      = datos.get("username", "")
        password  = datos.get("password", "")
        score     = datos.get("max_score", 0)

        if not user or not password:
            return

        port = 6667
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self.host, port))
            # comando especial para sincronizar datos offline con el servidor
            sock.sendall(f"offline_sync:{user}:{password}:{score}\n".encode())
            resp = sock.recv(1024).decode().strip()
            sock.close()
            if resp in ("SYNC_OK", "SYNC_REGISTERED"):
                import os
                try:
                    os.remove("offline.json")
                except:
                    pass
        except:
            pass

    # guarda las credenciales en offline.json y activa el modo sin conexión
    def play_offline(self):
        user     = self.username_text.strip()
        password = self.password_text.strip()
        if not user:
            self.login_error_msg = "Introduce un nombre de usuario"
            return

        datos = self.load_offline()
        # recuperamos la puntuación previa si ya había un offline.json para este usuario
        prev_score = datos.get("max_score", 0) if datos.get("username") == user else 0

        self.save_offline(user, password, prev_score)
        self.offline_max_score = prev_score
        self.offline_mode      = True
        self.state             = "MENU_SELECCION_MODO"


    # bucle principal: llama al método correcto según el estado del juego en cada frame
    def run(self):
        self.start_logo_splash()

        while True:
            self.update_music()
            if   self.state == "LOGO_SPLASH":             self.cutscene_loop()
            elif self.state == "STORY_SEQUENCE":          self.cutscene_loop()
            elif self.state == "MENU_PRINCIPAL":          self.menu_principal_loop()
            elif self.state == "MENU_LOGIN":              self.menu_login_loop()
            elif self.state == "MENU_REGISTER":           self.menu_register_loop()
            elif self.state == "MENU_SELECCION_MODO":     self.menu_seleccion_modo_loop()
            elif self.state == "MENU_SELECCION_SOLO":     self.menu_seleccion_solo()
            elif self.state == "MENU_SELECCION_SCORE":    self.menu_score_loop()
            elif self.state == "MENU_SETTINGS":           self.menu_settings_loop()
            elif self.state == "MENU_CONTROLES":          self.menu_controles_loop()
            elif self.state == "PAUSE_MENU":              self.pause_menu_loop()
            elif self.state == "PLAYING":                 self.game_loop()
            elif self.state == "GAME_OVER":               self.game_over_loop()
            elif self.state == "LEVEL_UP":                self.level_up_loop()
            elif self.state == "CHEST_REWARD":            self.chest_reward_loop()


    # inicia el splash de logo; al terminar lanza automáticamente la historia de inicio
    def start_logo_splash(self):
        def on_logo_done():
            self.start_story("inicio", "MENU_PRINCIPAL")

        self.cutscene = LogoSplash(self.screen, on_done=on_logo_done)
        self.cutscene_next = None
        self.state = "LOGO_SPLASH"

    # carga una secuencia de slides; si no hay imágenes ni textos salta directo al siguiente estado
    def start_story(self, folder_key: str, next_state: str):
        import os
        base = os.path.join("assets", "historia", folder_key)
        texts = []
        from src.utils.cutscene import STORY_TEXTS
        texts = STORY_TEXTS.get(folder_key, [])
        # comprobamos si hay imágenes en la carpeta de la historia correspondiente
        has_images = os.path.isdir(base) and any(
            f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
            for f in os.listdir(base)
        ) if os.path.isdir(base) else False

        if not has_images and not texts:
            self.state = next_state
            return

        def on_done():
            self.state = next_state

        self.cutscene = StorySequence(
            self.screen, folder_key, on_done=on_done,
            sx=self.sx, sy=self.sy, sf=self.sf
        )
        self.cutscene_next = next_state
        self.state = "STORY_SEQUENCE"

    # loop genérico para cualquier cinemática activa, gestiona eventos y frames
    def cutscene_loop(self):
        if self.cutscene is None:
            self.state = self.cutscene_next or "MENU_PRINCIPAL"
            return

        # guardamos referencia a la cinemática por si el callback carga una nueva
        current_cutscene = self.cutscene

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if current_cutscene.handle_event(event):
                if self.cutscene is current_cutscene:
                    self.cutscene = None
                return

        done = current_cutscene.update_and_draw()
        if done:
            if self.cutscene is current_cutscene:
                self.cutscene = None

        self.clock.tick(FPS)


    # dibuja y gestiona el menú principal con botones de jugar y salir
    def menu_principal_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font     = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        title    = font.render("Punternows Salvation: The Last Chance", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(130))))

        bw, bh   = self.sx(450), self.sy(65)
        gap      = self.sy(22)
        start_y  = H // 2 - self.sy(20)
        btn_play = pygame.Rect(W // 2 - bw // 2, start_y,          bw, bh)
        btn_esc  = pygame.Rect(W // 2 - bw // 2, start_y + bh + gap, bw, bh)

        self.draw_modern_button(btn_play, "Jugar",              font)
        self.draw_modern_button(btn_esc,  "Salir al Escritorio", font)

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(mouse_pos):
                    self.state = "MENU_LOGIN"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):
                    self.state = "MENU_CONTROLES"
                elif btn_esc.collidepoint(mouse_pos):
                    self.quit()


    # muestra la pantalla de controles y espera a que el jugador vuelva atrás
    def menu_controles_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.controles_bg, (0, 0))

        font_btn = pygame.font.SysFont("Arial", self.sf(28), bold=True)
        bw, bh   = self.sx(340), self.sy(62)
        btn_volver = pygame.Rect(W // 2 - bw // 2, H - self.sy(100), bw, bh)
        self.draw_modern_button(btn_volver, "Volver", font_btn)

        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = self.menu_anterior
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_volver.collidepoint(mouse_pos):
                    self.state = self.menu_anterior


    # menú de ajustes: pantalla completa, FPS, resolución y slider de volumen
    def menu_settings_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font       = pygame.font.SysFont("Arial", self.sf(38), bold=True)
        font_small = pygame.font.SysFont("Arial", self.sf(24), bold=True)
        font_label = pygame.font.SysFont("Arial", self.sf(20), bold=True)

        title = font.render("AJUSTES", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(230))))

        panel_w, panel_h = self.sx(600), self.sy(520)
        panel = pygame.Rect(W // 2 - panel_w // 2, H // 2 - self.sy(190), panel_w, panel_h)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 25, 200))
        self.screen.blit(panel_surf, panel.topleft)
        pygame.draw.rect(self.screen, BTN_BORDER, panel, 2, border_radius=16)

        bw = self.sx(480)
        bh = self.sy(58)
        cx = W // 2

        row1_y = H // 2 - self.sy(155)
        # botón para alternar pantalla completa
        txt_fs  = "Pantalla Completa:  SÍ" if self.fullscreen else "Pantalla Completa:  NO"
        btn_fs  = pygame.Rect(cx - bw // 2, row1_y, bw, bh)
        self.draw_modern_button(btn_fs, txt_fs, font_small)

        row2_y = row1_y + bh + self.sy(18)
        # botón para mostrar u ocultar el contador de FPS
        txt_fps = "Mostrar FPS:  SÍ" if self.show_fps else "Mostrar FPS:  NO"
        btn_fps = pygame.Rect(cx - bw // 2, row2_y, bw, bh)
        self.draw_modern_button(btn_fps, txt_fps, font_small)

        row3_y = row2_y + bh + self.sy(18)
        # selector de resolución con botones de flecha izquierda y derecha
        res_label = font_label.render("RESOLUCIÓN", True, (180, 180, 180))
        self.screen.blit(res_label, res_label.get_rect(center=(cx, row3_y - self.sy(0))))

        arrow_w  = self.sx(48)
        mid_w    = self.sx(280)
        row3_h   = self.sy(52)

        btn_res_prev = pygame.Rect(cx - mid_w // 2 - arrow_w - self.sx(8), row3_y + self.sy(10), arrow_w, row3_h)
        btn_res_next = pygame.Rect(cx + mid_w // 2 + self.sx(8),           row3_y + self.sy(10), arrow_w, row3_h)
        btn_res_lbl  = pygame.Rect(cx - mid_w // 2,                          row3_y + self.sy(10), mid_w,   row3_h)

        mouse_pos = pygame.mouse.get_pos()

        lbl_color = BTN_HOVER if btn_res_lbl.collidepoint(mouse_pos) else BTN_BG
        pygame.draw.rect(self.screen, (15, 15, 18), btn_res_lbl.move(0, 3), border_radius=10)
        pygame.draw.rect(self.screen, lbl_color,    btn_res_lbl, border_radius=10)
        pygame.draw.rect(self.screen, BTN_BORDER,   btn_res_lbl, 2, border_radius=10)

        res_txt = font_small.render(RESOLUTIONS[self.res_index][0], True, WHITE)
        self.screen.blit(res_txt, res_txt.get_rect(center=btn_res_lbl.center))

        for btn, symbol in [(btn_res_prev, "◄"), (btn_res_next, "►")]:
            bc = BTN_HOVER if btn.collidepoint(mouse_pos) else BTN_BG
            pygame.draw.rect(self.screen, (15, 15, 18), btn.move(0, 3), border_radius=10)
            pygame.draw.rect(self.screen, bc,           btn, border_radius=10)
            pygame.draw.rect(self.screen, BTN_BORDER,   btn, 2, border_radius=10)
            sym = font_small.render(symbol, True, WHITE)
            self.screen.blit(sym, sym.get_rect(center=btn.center))

        row4_y   = row3_y + row3_h + self.sy(42)
        slider_w = self.sx(480)
        slider_h = self.sy(10)
        slider_x = cx - slider_w // 2
        slider_y = row4_y + self.sy(30)

        # slider de volumen con el valor en porcentaje
        vol_lbl = font_small.render(f"Volumen:  {int(self.volume * 100)}%", True, WHITE)
        self.screen.blit(vol_lbl, vol_lbl.get_rect(center=(cx, row4_y + self.sy(8))))

        rail = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(self.screen, (90, 90, 90), rail, border_radius=5)
        fill_w = int(slider_w * self.volume)
        pygame.draw.rect(self.screen, (210, 210, 210),
                         pygame.Rect(slider_x, slider_y, max(fill_w, 0), slider_h), border_radius=5)

        hx = slider_x + fill_w
        hy = slider_y + slider_h // 2
        hr = self.sx(13)
        # calculamos si el ratón está encima del thumb del slider
        hovered = abs(mouse_pos[0] - hx) < hr + 6 and abs(mouse_pos[1] - hy) < hr + 6
        pygame.draw.circle(self.screen, (60, 60, 60), (hx, hy + 2), hr)
        h_color = (255, 255, 255) if (hovered or self.dragging_volume) else (200, 200, 200)
        pygame.draw.circle(self.screen, h_color, (hx, hy), hr)

        btn_volver = pygame.Rect(cx - bw // 2, H // 2 + self.sy(220), bw, bh)
        self.draw_modern_button(btn_volver, "Volver", font_small)

        btn_help  = self.draw_help_icon()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (slider_x - hr <= mouse_pos[0] <= slider_x + slider_w + hr and
                        slider_y - hr * 2 <= mouse_pos[1] <= slider_y + slider_h + hr * 2):
                    self.dragging_volume = True
                    self.volume = max(0.0, min(1.0, (mouse_pos[0] - slider_x) / slider_w))
                    self.apply_volume()

                elif btn_fs.collidepoint(mouse_pos):
                    self.fullscreen = not self.fullscreen
                    self.apply_resolution()

                elif btn_fps.collidepoint(mouse_pos):
                    self.show_fps = not self.show_fps
                    self.save_settings()

                elif btn_res_prev.collidepoint(mouse_pos):
                    self.res_index = (self.res_index - 1) % len(RESOLUTIONS)
                    self.apply_resolution()

                elif btn_res_next.collidepoint(mouse_pos):
                    self.res_index = (self.res_index + 1) % len(RESOLUTIONS)
                    self.apply_resolution()

                elif btn_help.collidepoint(mouse_pos):
                    self.state = "MENU_CONTROLES"

                elif btn_volver.collidepoint(mouse_pos):
                    self.state = self.menu_anterior

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_volume:
                    self.dragging_volume = False
                    self.save_settings()

            if event.type == pygame.MOUSEMOTION:
                if self.dragging_volume:
                    self.volume = max(0.0, min(1.0, (mouse_pos[0] - slider_x) / slider_w))
                    self.apply_volume()


    # dibuja y gestiona el formulario de inicio de sesión
    def menu_login_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        font_input = pygame.font.SysFont("Arial", self.sf(28))
        font_small = pygame.font.SysFont("Arial", self.sf(20), bold=True)

        title = font_title.render("INICIO DE SESION", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(190))))

        iw, ih = self.sx(460), self.sy(52)
        bw, bh = self.sx(460), self.sy(58)
        gap    = self.sy(18)
        cx     = W // 2

        user_rect   = pygame.Rect(cx - iw // 2, H // 2 - self.sy(95), iw, ih)
        pass_rect   = pygame.Rect(cx - iw // 2, user_rect.bottom + gap, iw, ih)
        err_gap     = self.sy(44)
        btn_log     = pygame.Rect(cx - bw // 2, pass_rect.bottom + self.sy(28) + err_gap, bw, bh)
        btn_offline = pygame.Rect(cx - bw // 2, btn_log.bottom    + gap,                   bw, bh)
        btn_volver  = pygame.Rect(cx - bw // 2, btn_offline.bottom + gap,                  bw, bh)

        # el campo activo se resalta en azul, el inactivo en gris
        color_active   = (50, 150, 255)
        color_inactive = (95, 99, 104)
        color_user = color_active if self.active_input == "username" else color_inactive
        color_pass = color_active if self.active_input == "password" else color_inactive

        pygame.draw.rect(self.screen, (32, 33, 36), user_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_user,   user_rect, width=2, border_radius=8)
        pygame.draw.rect(self.screen, (32, 33, 36), pass_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_pass,   pass_rect, width=2, border_radius=8)

        # mostramos el texto del campo o el placeholder si está vacío
        txt_user = font_input.render(self.username_text or "Nombre de usuario",
                                     True, WHITE if self.username_text else (150, 150, 150))
        txt_pass = font_input.render("*" * len(self.password_text) if self.password_text else "Contraseña",
                                     True, WHITE if self.password_text else (150, 150, 150))
        self.screen.blit(txt_user, (user_rect.x + 15, user_rect.y + 10))
        self.screen.blit(txt_pass, (pass_rect.x + 15, pass_rect.y + 10))

        self.draw_modern_button(btn_log,     "INICIAR SESION",      font_title)
        self.draw_modern_button(btn_offline, "JUGAR SIN CONEXION",  font_title, (40, 100, 40))
        self.draw_modern_button(btn_volver,  "VOLVER ATRAS",        font_title)

        txt_no_acc = font_small.render("¿No tienes cuenta?", True, WHITE)
        self.screen.blit(txt_no_acc, (self.sx(30), H - self.sy(110)))
        btn_go_register = pygame.Rect(self.sx(30), H - self.sy(80), self.sx(220), self.sy(40))
        self.draw_modern_button(btn_go_register, "Ir a Registro", font_small)

        if self.login_error_msg:
            font_error = pygame.font.SysFont("Arial", self.sf(22), bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 80, 80))
            mx, my = 12, 6
            bg = pygame.Surface((txt_err.get_width() + mx * 2, txt_err.get_height() + my * 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            err_y = pass_rect.bottom + self.sy(8)
            self.screen.blit(bg, (cx - bg.get_width() // 2, err_y))
            self.screen.blit(txt_err, (cx - txt_err.get_width() // 2, err_y + my))

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_LOGIN"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):   self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos): self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):     self.state = "MENU_CONTROLES"
                else: self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    self.try_login()
                elif btn_offline.collidepoint(mouse_pos):
                    self.play_offline()
                elif btn_volver.collidepoint(mouse_pos):
                    self.clear_login(); self.state = "MENU_PRINCIPAL"
                elif btn_go_register.collidepoint(mouse_pos):
                    self.clear_login(); self.state = "MENU_REGISTER"

            if event.type == pygame.KEYDOWN:
                self.handle_text_input(event)


    # dibuja y gestiona el formulario de registro de nuevos usuarios
    def menu_register_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        font_input = pygame.font.SysFont("Arial", self.sf(28))
        font_small = pygame.font.SysFont("Arial", self.sf(20), bold=True)

        title = font_title.render("REGISTRO DE NUEVO USUARIO", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(190))))

        iw, ih = self.sx(420), self.sy(52)
        bw, bh = self.sx(420), self.sy(58)
        gap    = self.sy(18)
        cx     = W // 2

        user_rect = pygame.Rect(cx - iw // 2, H // 2 - self.sy(95), iw, ih)
        pass_rect = pygame.Rect(cx - iw // 2, user_rect.bottom + gap, iw, ih)
        err_gap   = self.sy(44)
        btn_log   = pygame.Rect(cx - bw // 2, pass_rect.bottom + self.sy(28) + err_gap, bw, bh)
        btn_volver= pygame.Rect(cx - bw // 2, btn_log.bottom   + gap,                    bw, bh)

        color_active = (50, 150, 255); color_inactive = (95, 99, 104)
        color_user = color_active if self.active_input == "username" else color_inactive
        color_pass = color_active if self.active_input == "password" else color_inactive

        pygame.draw.rect(self.screen, (32, 33, 36), user_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_user,   user_rect, width=2, border_radius=8)
        pygame.draw.rect(self.screen, (32, 33, 36), pass_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_pass,   pass_rect, width=2, border_radius=8)

        txt_user = font_input.render(self.username_text or "Nombre de usuario",
                                     True, WHITE if self.username_text else (150, 150, 150))
        txt_pass = font_input.render("*" * len(self.password_text) if self.password_text else "Contraseña",
                                     True, WHITE if self.password_text else (150, 150, 150))
        self.screen.blit(txt_user, (user_rect.x + 15, user_rect.y + 10))
        self.screen.blit(txt_pass, (pass_rect.x + 15, pass_rect.y + 10))

        self.draw_modern_button(btn_log,    "REGISTRARSE",  font_title)
        self.draw_modern_button(btn_volver, "VOLVER ATRAS", font_title)

        txt_have_acc = font_small.render("¿Ya tienes cuenta?", True, WHITE)
        self.screen.blit(txt_have_acc, (self.sx(30), H - self.sy(110)))
        btn_go_login = pygame.Rect(self.sx(30), H - self.sy(80), self.sx(220), self.sy(40))
        self.draw_modern_button(btn_go_login, "Ir a Login", font_small)

        if self.login_error_msg:
            font_error = pygame.font.SysFont("Arial", self.sf(22), bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 80, 80))
            mx, my = 12, 6
            bg = pygame.Surface((txt_err.get_width() + mx * 2, txt_err.get_height() + my * 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            err_y = pass_rect.bottom + self.sy(8)
            self.screen.blit(bg, (W // 2 - bg.get_width() // 2, err_y))
            self.screen.blit(txt_err, (W // 2 - txt_err.get_width() // 2, err_y + my))

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):   self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos): self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):     self.state = "MENU_CONTROLES"
                else: self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    self.try_register()
                elif btn_volver.collidepoint(mouse_pos):
                    self.clear_login(); self.state = "MENU_PRINCIPAL"
                elif btn_go_login.collidepoint(mouse_pos):
                    self.clear_login(); self.state = "MENU_LOGIN"

            if event.type == pygame.KEYDOWN:
                self.handle_text_input(event)


    # muestra las opciones: jugar, ver ranking o volver al menú principal
    def menu_seleccion_modo_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        title = font.render("SELECCIONA UN MODO", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(150))))

        bw, bh = self.sx(470), self.sy(65)
        gap    = self.sy(22)
        start_y = H // 2 - self.sy(55)
        btn_solo       = pygame.Rect(W // 2 - bw // 2, start_y,                   bw, bh)
        btn_score      = pygame.Rect(W // 2 - bw // 2, start_y + (bh + gap),      bw, bh)
        btn_menu_princ = pygame.Rect(W // 2 - bw // 2, start_y + (bh + gap) * 2,  bw, bh)

        self.draw_modern_button(btn_solo,       "Jugar",              font)
        self.draw_modern_button(btn_score,      "Tabla de Clasificacion",  font)
        self.draw_modern_button(btn_menu_princ, "Volver al menu principal", font)

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_MODO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_solo.collidepoint(mouse_pos):       self.state = "MENU_SELECCION_SOLO"
                elif btn_score.collidepoint(mouse_pos):
                    self.last_basc_time = 0; self.state = "MENU_SELECCION_SCORE"
                elif btn_settings.collidepoint(mouse_pos):   self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):       self.state = "MENU_CONTROLES"
                elif btn_menu_princ.collidepoint(mouse_pos):
                    self.state = "MENU_PRINCIPAL"
                    if not self.offline_mode:
                        self.sync_offline_to_server()
                    if self.network_socket:
                        self.network_socket.close()
                    self.offline_mode = False


    # pantalla de selección de personaje con tarjetas interactivas
    def menu_seleccion_solo(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        mouse_pos = pygame.mouse.get_pos()

        font_title = pygame.font.SysFont("Arial", self.sf(42), bold=True)
        font_name  = pygame.font.SysFont("Arial", self.sf(22), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self.sf(16))
        font_stat  = pygame.font.SysFont("Arial", self.sf(14))
        font_back  = pygame.font.SysFont("Arial", self.sf(22), bold=True)

        title = font_title.render("SELECCIONA TU PERSONAJE", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, self.sy(70))))

        # datos de cada personaje: nombre, descripción, stats, icono y colores
        characters = [
            {
                "key":   "caballero",
                "name":  "Caballero",
                "desc":  "Guerrero resistente con\nalto aguante en combate",
                "stats": ["Vida: 240", "Vel: 4", "Espada"],
                "icon":  "assets/sprites/icons/knight_icon.png",
                "color": (60, 100, 200),
                "accent": (100, 160, 255),
            },
            {
                "key":   "mago",
                "name":  "Mago",
                "desc":  "Veloz lanzador de hechizos\ncon gran movilidad",
                "stats": ["Vida: 120", "Vel: 6", "Varita"],
                "icon":  "assets/sprites/icons/mage_icon.png",
                "color": (100, 30, 180),
                "accent": (180, 80, 255),
            },
            {
                "key":   "primal_man",
                "name":  "Hombre Primal",
                "desc":  "Personaje misterioso que\nlanza plátanos como armas",
                "stats": ["Vida: 160", "Vel: 5", "Banana"],
                "icon":  "assets/sprites/icons/primal_man_icon.png",
                "color": (120, 90, 30),
                "accent": (220, 180, 60),
            },
        ]

        # calculamos el layout para distribuir las tarjetas de forma uniforme
        n        = len(characters)
        margin_x = self.sx(60)
        gap      = self.sx(30)
        card_w   = (W - margin_x * 2 - gap * (n - 1)) // n
        card_h   = self.sy(440)
        cards_y  = self.sy(130)

        # generamos los Rect de cada tarjeta según el layout calculado
        card_rects = []
        for i in range(n):
            cx = margin_x + i * (card_w + gap)
            card_rects.append(pygame.Rect(cx, cards_y, card_w, card_h))

        # dibujamos cada tarjeta con sombra, fondo, icono, nombre, stats y hover
        char_keys = []
        for i, (char, rect) in enumerate(zip(characters, card_rects)):
            hovered = rect.collidepoint(mouse_pos)
            char_keys.append(char["key"])

            # sombra desplazada hacia abajo para dar sensación de profundidad
            shadow = rect.move(0, 6)
            pygame.draw.rect(self.screen, (10, 10, 15), shadow, border_radius=18)

            # aumentamos la opacidad de la tarjeta al pasar el ratón por encima
            bg_alpha = 230 if hovered else 190
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            r, g, b = char["color"]
            card_surf.fill((max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), bg_alpha))
            self.screen.blit(card_surf, rect.topleft)

            # el borde usa el color del personaje al hacer hover
            border_color = char["accent"] if hovered else (80, 80, 90)
            border_w = 3 if hovered else 2
            pygame.draw.rect(self.screen, border_color, rect, border_w, border_radius=18)

            icon_size = int(min(card_w * 0.55, card_h * 0.38))
            icon_rect = pygame.Rect(rect.centerx - icon_size // 2,
                                    rect.y + self.sy(18), icon_size, icon_size)

            import os
            # cargamos el icono del personaje o dibujamos un placeholder si no existe
            if os.path.exists(char["icon"]):
                try:
                    icon_img = pygame.image.load(char["icon"]).convert_alpha()
                    bg_col   = icon_img.get_at((0, 0))
                    icon_img.set_colorkey(bg_col)
                    icon_img = pygame.transform.scale(icon_img, (icon_size, icon_size))
                    self.screen.blit(icon_img, icon_rect.topleft)
                except:
                    pygame.draw.rect(self.screen, char["accent"], icon_rect, border_radius=12)
            else:
                pygame.draw.rect(self.screen, char["color"], icon_rect, border_radius=12)
                pygame.draw.rect(self.screen, char["accent"], icon_rect, 2, border_radius=12)
                ini  = font_title.render(char["name"][0], True, WHITE)
                self.screen.blit(ini, ini.get_rect(center=icon_rect.center))

            text_y = icon_rect.bottom + self.sy(14)
            name_surf = font_name.render(char["name"], True, WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, y=text_y))
            text_y += name_surf.get_height() + self.sy(8)

            sep_x1 = rect.x + self.sx(20)
            sep_x2 = rect.right - self.sx(20)
            pygame.draw.line(self.screen, char["accent"], (sep_x1, text_y), (sep_x2, text_y), 1)
            text_y += self.sy(8)

            for line in char["desc"].split("\n"):
                d_surf = font_desc.render(line, True, (200, 200, 220))
                self.screen.blit(d_surf, d_surf.get_rect(centerx=rect.centerx, y=text_y))
                text_y += d_surf.get_height() + self.sy(2)
            text_y += self.sy(10)

            for stat in char["stats"]:
                s_surf = font_stat.render(stat, True, char["accent"])
                self.screen.blit(s_surf, s_surf.get_rect(centerx=rect.centerx, y=text_y))
                text_y += s_surf.get_height() + self.sy(4)

            if hovered:
                # al hacer hover mostramos el texto 'Seleccionar' con fondo semitransparente
                sel_surf = font_stat.render("Seleccionar", True, WHITE)
                sel_y    = rect.bottom - sel_surf.get_height() - self.sy(14)
                sel_rect_bg = pygame.Rect(rect.x + self.sx(14), sel_y - self.sy(4),
                                          card_w - self.sx(28), sel_surf.get_height() + self.sy(8))
                hl = pygame.Surface((sel_rect_bg.w, sel_rect_bg.h), pygame.SRCALPHA)
                hl.fill((*char["accent"], 60))
                self.screen.blit(hl, sel_rect_bg.topleft)
                self.screen.blit(sel_surf, sel_surf.get_rect(centerx=rect.centerx, y=sel_y))

        bw_back  = self.sx(280)
        bh_back  = self.sy(50)
        btn_volver = pygame.Rect(W // 2 - bw_back // 2,
                                 cards_y + card_h + self.sy(22), bw_back, bh_back)
        self.draw_modern_button(btn_volver, "Volver Atrás", font_back)

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SOLO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                char = None
                for i, rect in enumerate(card_rects):
                    if rect.collidepoint(mouse_pos):
                        char = char_keys[i]
                        break
                if char:
                    self.character_name = char
                    # creamos la sesión de juego con el personaje seleccionado
                    self.game = GameSession(character_name=char, multiplayer=False, world=1)
                    self.apply_volume()
                    self.start_story("mundo_1", "PLAYING")
                elif btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):
                    self.state = "MENU_CONTROLES"


    # pide el ranking al servidor sin estar logueado; en offline deja la tabla vacía
    def fetch_scoreboard_guest(self):
        if self.offline_mode:
            self.last_basc_time = pygame.time.get_ticks()
            return
        try:
            tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tmp.settimeout(2)
            tmp.connect((self.host, 6667))
            tmp.sendall("basc_guest:\n".encode())
            data = tmp.recv(4096).decode().strip()
            tmp.close()
            # parseamos la respuesta: formato 'basc:usuario,puntos:usuario,puntos:...'
            if data.startswith("basc"):
                partes = data.split(":")
                if len(partes) > 1:
                    self.scoreboard_data = []
                    for p in partes[1:]:
                        if "," in p:
                            u, s = p.split(",")
                            self.scoreboard_data.append((u, s))
            self.last_basc_time = pygame.time.get_ticks()
        except Exception as e:
            print(f"Scoreboard sin conexión (modo invitado): {e}")
            self.last_basc_time = pygame.time.get_ticks()

    # solicita el ranking al servidor o como invitado si no hay socket activo
    def get_scoreboard(self):
        if self.offline_mode:
            self.last_basc_time = pygame.time.get_ticks()
            return
        if self.network_socket:
            try:
                self.network_socket.sendall("basc:u:s\n".encode())
                self.last_basc_time = pygame.time.get_ticks()
            except Exception:
                try: self.network_socket.close()
                except: pass
                self.network_socket = None
                self.fetch_scoreboard_guest()
        else:
            self.fetch_scoreboard_guest()

    # busca la puntuación y posición del jugador actual en el ranking descargado
    def get_my_score_and_rank(self):
        username = self.username_text.strip()

        if self.offline_mode:
            datos = self.load_offline()
            my_score = datos.get("max_score", 0)
        else:
            my_score = None
            for i, (u, s) in enumerate(self.scoreboard_data):
                if u == username:
                    my_score = int(s)
                    break

        my_rank = None
        for i, (u, s) in enumerate(self.scoreboard_data):
            if u == username:
                my_rank = i + 1
                break

        return my_score, my_rank

    # muestra la tabla de clasificación, actualizándola cada 15 segundos
    def menu_score_loop(self):
        W, H = self.W, self.H
        ahora = pygame.time.get_ticks()
        if ahora - self.last_basc_time > 15000:
            self.get_scoreboard()

        if self.network_socket:
            try:
                # modo no-bloqueante para recibir datos sin congelar la UI
                self.network_socket.setblocking(False)
                data = self.network_socket.recv(4096).decode().strip()
                if data.startswith("basc"):
                    partes = data.split(":")
                    if len(partes) > 1:
                        self.scoreboard_data = []
                        for p in partes[1:]:
                            if "," in p:
                                u, s = p.split(",")
                                self.scoreboard_data.append((u, s))
            except (BlockingIOError, socket.error):
                pass
            except Exception:
                try: self.network_socket.close()
                except: pass
                self.network_socket = None
            finally:
                if self.network_socket:
                    self.network_socket.setblocking(True)

        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font       = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        font_small = pygame.font.SysFont("Arial", self.sf(28))
        font_info  = pygame.font.SysFont("Arial", self.sf(22), bold=True)

        title = font.render("TABLA DE CLASIFICACION", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, self.sy(90))))

        panel_w, panel_h = self.sx(700), self.sy(420)
        panel_y = self.sy(160)
        panel = pygame.Rect(W // 2 - panel_w // 2, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (32, 33, 36), panel, border_radius=15)
        pygame.draw.rect(self.screen, (95, 99, 104), panel, width=2, border_radius=15)

        start_y = panel_y + self.sy(30)
        username = self.username_text.strip()

        if not self.scoreboard_data:
            if self.offline_mode:
                ph = font_small.render("Tabla no disponible en modo sin conexión", True, (180, 180, 180))
            else:
                ph = font_small.render("Cargando datos...", True, (200, 200, 200))
            self.screen.blit(ph, ph.get_rect(center=(W // 2, panel_y + panel_h // 2)))
        else:
            row_h = self.sy(38)
            for i, (user, score) in enumerate(self.scoreboard_data):
                is_me = (user == username)
                if i == 0:
                    # oro para el 1º, plata para el 2º, bronce para el 3º y gris para el resto
                    color_rank = (255, 215, 0)
                elif i == 1:
                    color_rank = (192, 192, 192)
                elif i == 2:
                    color_rank = (205, 127, 50)
                else:
                    color_rank = (180, 180, 180)

                if is_me:
                    # resaltamos en verde la fila del jugador actual
                    row_bg = pygame.Surface((panel_w - self.sx(20), row_h - 2), pygame.SRCALPHA)
                    row_bg.fill((60, 120, 60, 120))
                    self.screen.blit(row_bg, (W // 2 - (panel_w - self.sx(20)) // 2,
                                              start_y + i * row_h - 2))

                name_txt = f"► {user}" if is_me else user
                txt_color = (120, 255, 120) if is_me else WHITE

                t_rank  = font_small.render(f"#{i+1}", True, color_rank)
                t_user  = font_small.render(name_txt, True, txt_color)
                t_score = font_small.render(f"{score} pts", True, LIGHT_YELLOW)
                self.screen.blit(t_rank,  (W // 2 - self.sx(290), start_y + i * row_h))
                self.screen.blit(t_user,  (W // 2 - self.sx(160), start_y + i * row_h))
                self.screen.blit(t_score, (W // 2 + self.sx(100),  start_y + i * row_h))

        # franja personal debajo del ranking con puntuación y posición del jugador
        my_score, my_rank = self.get_my_score_and_rank()
        personal_y = panel_y + panel_h + self.sy(14)
        personal_w = panel_w
        personal_h = self.sy(52)
        personal_rect = pygame.Rect(W // 2 - personal_w // 2, personal_y,
                                    personal_w, personal_h)
        pygame.draw.rect(self.screen, (28, 60, 28), personal_rect, border_radius=10)
        pygame.draw.rect(self.screen, (60, 160, 60), personal_rect, 2, border_radius=10)

        if username:
            if my_score is not None:
                score_txt = f"{my_score} pts"
            else:
                score_txt = "Sin puntuación aún"

            if my_rank is not None:
                rank_txt = f"Tu posición: #{my_rank}"
            else:
                rank_txt = "No estás en el top 10"

            line = f"{username}  ·  {score_txt}  ·  {rank_txt}"
            surf_line = font_info.render(line, True, (180, 255, 180))
            self.screen.blit(surf_line, surf_line.get_rect(center=personal_rect.center))
        else:
            surf_guest = font_info.render("Inicia sesión para ver tu puntuación", True, (180, 180, 180))
            self.screen.blit(surf_guest, surf_guest.get_rect(center=personal_rect.center))

        bw, bh = self.sx(450), self.sy(65)
        btn_volver = pygame.Rect(W // 2 - bw // 2, H - self.sy(110), bw, bh)
        self.draw_modern_button(btn_volver, "Volver al menu", font)

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SCORE"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_volver.collidepoint(mouse_pos):   self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):     self.state = "MENU_CONTROLES"


    # loop de gameplay: procesa eventos, actualiza el juego y decide el siguiente estado
    def game_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "PAUSE_MENU"
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_k:
                # tecla K fuerza fase 4 con spawn rápido (para testing)
                self.game.current_phase = 4
                self.game.spawn_rate = 6
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                # tecla E: intentar invocar boss y abrir cofre si hay uno cerca
                self.game.try_summon_boss()
                upgrade = self.game.open_chest()
                if upgrade is not None:
                    self.pending_chest_upgrade = upgrade
                    self.state = "CHEST_REWARD"

        # actualizamos el juego y obtenemos el nuevo estado (GAME_OVER, LEVEL_UP, etc.)
        estado_juego = self.game.update(self.username_text, self.network_socket)

        if estado_juego == "GAME_OVER":
            # al morir guardamos puntuación y la enviamos al servidor o al JSON offline
            score_actual = self.game.score
            level_actual = self.game.local_player.level

            if not self.offline_mode and self.network_socket:
                try:
                    # enviamos la puntuación al servidor solo si estamos online y conectados
                    msg = f"sbsc:{self.username_text}:{level_actual}:{score_actual}\n"
                    self.network_socket.sendall(msg.encode())
                except Exception:
                    pass

            # en modo offline solo guardamos si superamos el récord local
            if self.offline_mode and score_actual > self.offline_max_score:
                self.offline_max_score = score_actual
                datos = self.load_offline()
                self.save_offline(
                    datos.get("username", self.username_text),
                    datos.get("password", self.password_text),
                    score_actual)

            self.state = "GAME_OVER"
            # paramos la música y buscamos el sonido de game over en cualquier formato
            pygame.mixer.music.stop()
            self.music_state = "GAME_OVER"
            import os as os
            for ext in ("ogg", "wav", "mp3"):
                go_path = f"assets/sounds/game_over.{ext}"
                if os.path.exists(go_path):
                    try:
                        pygame.mixer.music.load(go_path)
                        pygame.mixer.music.play(0)
                        pygame.mixer.music.set_volume(self.vol(0.6))
                        print(f"[game_over sfx] Reproduciendo {go_path}")
                    except Exception as e:
                        print(f"[game_over sfx] Error: {e}")
                    break
            else:
                print("[game_over sfx] No se encontro game_over.ogg/.wav/.mp3")
            return
        # al subir de nivel generamos las opciones de mejora para el jugador
        elif estado_juego == "LEVEL_UP":
            self.state = "LEVEL_UP"
            player = self.game.local_player
            char   = getattr(self, "character_name", "caballero")

            # armas que ya tiene el jugador y las que aún puede desbloquear
            owned_names     = {w.name for w in player.weapons}
            all_unlockable  = [w for w in WEAPONS if w not in owned_names]
            unowned_weapons = all_unlockable

            # 5% de probabilidad de ofrecer un arma nueva si quedan por desbloquear
            if unowned_weapons and random.random() < 0.05:
                weapon_choice = random.choice(unowned_weapons)
                weapon_option = {
                    "id": f"weapon_{weapon_choice}",
                    "name": f"Arma: {weapon_choice.capitalize()}",
                    "desc": "¡Nuevo tipo de ataque!",
                    "type": "new_weapon", "value": weapon_choice
                }
                weapon_pool = [upg for wname, upgrades in WEAPON_UPGRADES.items()
                               if wname in owned_names for upg in upgrades]
                rest_pool   = list(UPGRADES) + weapon_pool
                rest = random.sample(rest_pool, min(2, len(rest_pool)))
                self.current_choices = [weapon_option] + rest
            else:
                weapon_pool = [upg for wname, upgrades in WEAPON_UPGRADES.items()
                               if wname in owned_names for upg in upgrades]
                combined    = list(UPGRADES) + weapon_pool
                self.current_choices = random.sample(combined, min(3, len(combined)))
        # al completar un mundo creamos nueva sesión con el mismo jugador en el mundo siguiente
        elif estado_juego == "NEXT_WORLD":
            next_world = self.game.world + 1
            if next_world <= 3:
                player          = self.game.local_player
                accumulated     = self.game.score
                self.game       = GameSession(character_name=getattr(self, "character_name", "caballero"),
                                              multiplayer=False, world=next_world, carry_player=player)
                # mantenemos la puntuación acumulada al pasar al siguiente mundo
                self.game.score = accumulated
                self.apply_volume()
                folder = f"mundo_{next_world}"
                self.start_story(folder, "PLAYING")
            else:
                pass
            return
        # si se derrota al minotauro lanzamos la cinemática final
        elif estado_juego == "ENDGAME_CUTSCENE":
            self.start_story("final", "PLAYING")
            return

        self.game.draw(self.screen)
        if self.show_fps:
            self.draw_fps()
        pygame.display.flip()
        self.clock.tick(FPS)


    # menú de pausa con el juego congelado de fondo y opciones de reanudar o abandonar
    def pause_menu_loop(self):
        W, H = self.W, self.H
        self.game.draw(self.screen)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", self.sf(50), bold=True)
        font_btn   = pygame.font.SysFont("Arial", self.sf(40), bold=True)

        title = font_title.render("PAUSA", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self.sy(150))))

        bw, bh = self.sx(450), self.sy(70)
        btn_reanudar  = pygame.Rect(W // 2 - bw // 2, H // 2 - self.sy(40), bw, bh)
        btn_abandonar = pygame.Rect(W // 2 - bw // 2, H // 2 + self.sy(60), bw, bh)

        self.draw_modern_button(btn_reanudar,  "Reanudar",          font_btn)
        self.draw_modern_button(btn_abandonar, "Abandonar partida", font_btn)

        btn_settings = self.draw_settings_icon()
        btn_help     = self.draw_help_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "PAUSE_MENU"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "PLAYING"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_reanudar.collidepoint(mouse_pos):   self.state = "PLAYING"
                elif btn_abandonar.collidepoint(mouse_pos):  self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):   self.state = "MENU_SETTINGS"
                elif btn_help.collidepoint(mouse_pos):       self.state = "MENU_CONTROLES"


    # pantalla de game over con fondo especial y botón para volver al menú
    def game_over_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.game_over_menu_bg, (0, 0))

        font   = pygame.font.SysFont("Arial", self.sf(40), bold=True)
        bw, bh = self.sx(450), self.sy(70)
        btn    = pygame.Rect(W // 2 - bw // 2, H // 2 + self.sy(200), bw, bh)
        self.draw_modern_button(btn, "Volver al menu", font, BAR_RED)

        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "MENU_SELECCION_MODO"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"


    # pantalla de subida de nivel con las tarjetas de mejora para elegir
    def level_up_loop(self):
        W, H = self.W, self.H
        self.game.draw(self.screen)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        mouse_pos = pygame.mouse.get_pos()
        clicked   = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        font_title = pygame.font.SysFont("Arial", self.sf(44), bold=True)
        font_sub   = pygame.font.SysFont("Arial", self.sf(20))
        font_name  = pygame.font.SysFont("Arial", self.sf(20), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self.sf(15))

        # animación de pulso para el título dorado de '¡SUBIDA DE NIVEL!'
        pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
        gold  = (int(200 + 55 * pulse), int(180 + 35 * pulse), 0)
        title = font_title.render("¡SUBIDA DE NIVEL!", True, gold)
        sub   = font_sub.render("Elige una mejora", True, (180, 180, 180))
        self.screen.blit(title, title.get_rect(center=(W // 2, self.sy(80))))
        self.screen.blit(sub,   sub.get_rect(center=(W // 2, self.sy(130))))

        # diccionario que mapea tipos de mejora con su icono, emoji y color
        UPGRADE_ICONS = {
            "max_hp":     ("assets/sprites/icons/hp_up.png",     "",  (200,  40,  40)),
            "speed":      ("assets/sprites/icons/speed_up.png",  "",  ( 60, 160, 255)),
            "magnet":     ("assets/sprites/icons/magnet_up.png", "",  (120,  80, 220)),
            "hp":         ("assets/sprites/icons/heal_up.png",   "",  ( 50, 200, 100)),
            "new_weapon": ("",                                    "⚔", (220, 180,  40)),
            "w_damage":   ("",  "", (255, 120,  30)),
            "w_cooldown": ("",  "", (255, 200,   0)),
            "w_burn_dmg": ("",  "", (255,  80,   0)),
            "w_burn_rad": ("",  "", (255, 140,  20)),
            "w_frags":    ("",  "", (255, 220,   0)),
        }

        # rutas de los iconos de cada arma del juego
        WEAPON_ICON_PATHS = {
            "espada": "assets/sprites/icons/sword_icon.png",
            "varita": "assets/sprites/icons/wand_icon.png",
            "banana": "assets/sprites/icons/banana_icon.png",
        }

        # calculamos el layout de tarjetas de mejora para que quepan bien en pantalla
        n        = len(self.current_choices)
        margin_x = self.sx(80)
        gap      = self.sx(28)
        card_w   = (W - margin_x * 2 - gap * (n - 1)) // max(n, 1)
        card_h   = self.sy(280)
        cards_y  = H // 2 - card_h // 2 + self.sy(20)

        import os
        for i, upgrade in enumerate(self.current_choices):
            cx   = margin_x + i * (card_w + gap)
            rect = pygame.Rect(cx, cards_y, card_w, card_h)
            hov  = rect.collidepoint(mouse_pos)

            icon_path, icon_emoji, accent = UPGRADE_ICONS.get(
                upgrade["type"], ("", "", (180, 180, 50)))

            # sombra de la tarjeta de mejora
            pygame.draw.rect(self.screen, (8, 8, 12), rect.move(0, 7), border_radius=18)

            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            r, g, b = accent
            bg_alpha = 210 if hov else 175
            pygame.draw.rect(card_surf, (max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), bg_alpha),
                             pygame.Rect(0, 0, card_w, card_h), border_radius=18)
            self.screen.blit(card_surf, rect.topleft)

            # borde más grueso y del color del acento al hacer hover
            border_col = accent if hov else (70, 70, 80)
            border_w   = 3 if hov else 2
            pygame.draw.rect(self.screen, border_col, rect, border_w, border_radius=18)

            if hov:
                # brillo en la parte superior de la tarjeta al hacer hover
                glow_h = self.sy(4)
                glow = pygame.Surface((card_w - border_w * 2, glow_h), pygame.SRCALPHA)
                glow.fill((*accent, 160))
                self.screen.blit(glow, (rect.x + border_w, rect.y + border_w))

            icon_size = int(min(card_w * 0.38, card_h * 0.30))
            icon_y    = rect.y + self.sy(22)
            icon_rect = pygame.Rect(rect.centerx - icon_size // 2, icon_y, icon_size, icon_size)

            # si la mejora es de arma usamos el icono del arma en vez del genérico
            weapon_name = upgrade.get("weapon")
            if weapon_name:
                icon_path = WEAPON_ICON_PATHS.get(weapon_name, "")

            icon_loaded = False
            if icon_path and os.path.exists(icon_path):
                try:
                    ic = pygame.image.load(icon_path).convert_alpha()
                    ic = pygame.transform.scale(ic, (icon_size, icon_size))
                    self.screen.blit(ic, icon_rect.topleft)
                    icon_loaded = True
                except:
                    pass

            if not icon_loaded:
                pygame.draw.circle(self.screen, accent,
                                   icon_rect.center, icon_size // 2)
                pygame.draw.circle(self.screen, (255, 255, 255),
                                   icon_rect.center, icon_size // 2, 2)
                # si no hay icono dibujamos un círculo con emoji como fallback
                ico_font = pygame.font.SysFont("Segoe UI Emoji", int(icon_size * 0.52))
                ico_surf = ico_font.render(icon_emoji, True, WHITE)
                self.screen.blit(ico_surf, ico_surf.get_rect(center=icon_rect.center))

            text_y = icon_rect.bottom + self.sy(12)
            name_surf = font_name.render(upgrade["name"], True, WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, y=text_y))
            text_y += name_surf.get_height() + self.sy(6)

            pygame.draw.line(self.screen, accent,
                             (rect.x + self.sx(18), text_y),
                             (rect.right - self.sx(18), text_y), 1)
            text_y += self.sy(8)

            desc_surf = font_desc.render(upgrade["desc"], True, (210, 210, 230))
            self.screen.blit(desc_surf, desc_surf.get_rect(centerx=rect.centerx, y=text_y))

            # zona inferior: badge del arma y texto 'Elegir' siempre en la misma posición
            pick_font  = pygame.font.SysFont("Arial", self.sf(14), bold=True)
            badge_font = pygame.font.SysFont("Arial", self.sf(13), bold=True)

            pick_surf = pick_font.render("Elegir", True, WHITE)
            pick_y    = rect.bottom - pick_surf.get_height() - self.sy(10)

            if upgrade.get("weapon"):
                badge_surf = badge_font.render(upgrade["weapon"].upper(), True, accent)
                badge_y    = pick_y - badge_surf.get_height() - self.sy(6)
                self.screen.blit(badge_surf, badge_surf.get_rect(centerx=rect.centerx, y=badge_y))

            if hov:
                hl = pygame.Surface((card_w - self.sx(28),
                                     pick_surf.get_height() + self.sy(8)), pygame.SRCALPHA)
                hl.fill((*accent, 70))
                self.screen.blit(hl, (rect.x + self.sx(14), pick_y - self.sy(4)))
                self.screen.blit(pick_surf, pick_surf.get_rect(centerx=rect.centerx, y=pick_y))

            # si se hizo clic encima aplicamos la mejora y volvemos al juego
            if hov and clicked:
                self.game.local_player.apply_upgrade(upgrade)
                if upgrade.get("type") == "new_weapon": self.apply_volume()
                self.state = "PLAYING"
                pygame.display.flip()
                return

        pygame.display.flip()


    # muestra la recompensa de abrir un cofre con tarjeta centrada y botón de aceptar
    def chest_reward_loop(self):
        W, H = self.W, self.H
        upgrade = self.pending_chest_upgrade
        if upgrade is None:
            self.state = "PLAYING"
            return

        self.game.draw(self.screen)
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        # dibujamos el juego congelado de fondo con overlay oscuro semitransparente
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", self.sf(38), bold=True)
        font_name  = pygame.font.SysFont("Arial", self.sf(30), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self.sf(22))
        font_btn   = pygame.font.SysFont("Arial", self.sf(28), bold=True)

        title_surf = font_title.render("¡Cofre encontrado!", True, (255, 215, 0))
        self.screen.blit(title_surf, title_surf.get_rect(center=(W // 2, H // 2 - self.sy(210))))

        UPGRADE_ICONS = {
            "max_hp":  ("assets/sprites/icons/hp_up.png",     (200,  40,  40)),
            "speed":   ("assets/sprites/icons/speed_up.png",  ( 60, 160, 255)),
            "magnet":  ("assets/sprites/icons/magnet_up.png", (120,  80, 220)),
            "hp":      ("assets/sprites/icons/heal_up.png",   ( 50, 200, 100)),
        }
        icon_path, accent = UPGRADE_ICONS.get(upgrade.get("type", ""), ("", (180, 180, 50)))

        card_w = self.sx(360)
        card_h = self.sy(310)
        card_x = W // 2 - card_w // 2
        card_y = H // 2 - card_h // 2 - self.sy(30)
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

        pygame.draw.rect(self.screen, (8, 8, 12), card_rect.move(0, 7), border_radius=18)

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        r, g, b = accent
        card_surf.fill((max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 210))
        self.screen.blit(card_surf, card_rect.topleft)
        pygame.draw.rect(self.screen, accent, card_rect, 3, border_radius=18)

        icon_size = self.sx(90)
        icon_rect = pygame.Rect(W // 2 - icon_size // 2,
                                card_y + self.sy(25), icon_size, icon_size)
        icon_loaded = False
        if icon_path and os.path.exists(icon_path):
            try:
                ic = pygame.image.load(icon_path).convert_alpha()
                ic = pygame.transform.scale(ic, (icon_size, icon_size))
                self.screen.blit(ic, icon_rect.topleft)
                icon_loaded = True
            except Exception:
                pass
        if not icon_loaded:
            pygame.draw.circle(self.screen, accent, icon_rect.center, icon_size // 2)
            pygame.draw.circle(self.screen, (255, 255, 255), icon_rect.center, icon_size // 2, 2)

        name_surf = font_name.render(upgrade.get("name", "Mejora"), True, (255, 255, 255))
        desc_surf = font_desc.render(upgrade.get("desc", ""),       True, (210, 210, 230))
        self.screen.blit(name_surf, name_surf.get_rect(center=(W // 2, card_y + self.sy(145))))
        self.screen.blit(desc_surf, desc_surf.get_rect(center=(W // 2, card_y + self.sy(190))))

        bw, bh = self.sx(300), self.sy(62)
        btn = pygame.Rect(W // 2 - bw // 2, card_y + card_h + self.sy(20), bw, bh)
        self.draw_modern_button(btn, "Aceptar", font_btn, accent)

        mouse_pos = pygame.mouse.get_pos()
        clicked   = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                clicked = True

        # aceptamos la mejora tanto con clic en el botón como pulsando E
        if clicked and btn.collidepoint(mouse_pos) or (clicked and pygame.key.get_pressed()[pygame.K_e]):
            self.game.local_player.apply_upgrade(upgrade)
            if upgrade.get("type") == "new_weapon": self.apply_volume()
            self.pending_chest_upgrade = None
            self.state = "PLAYING"

        pygame.display.flip()


    # cierra el socket, para pygame limpiamente y termina el proceso
    def quit(self):
        if self.network_socket:
            self.network_socket.close()
        pygame.quit()
        sys.exit()

    # resetea todos los campos del formulario de login/registro
    def clear_login(self):
        self.username_text  = ""
        self.password_text  = ""
        self.active_input   = None
        self.login_error_msg = ""

    # gestiona escritura en campos de texto: backspace, tab y caracteres imprimibles
    def handle_text_input(self, event):
        if self.active_input == "username":
            if   event.key == pygame.K_BACKSPACE: self.username_text = self.username_text[:-1]
            elif event.key == pygame.K_TAB:       self.active_input = "password"
            elif len(self.username_text) < 15 and event.unicode.isprintable():
                self.username_text += event.unicode
        elif self.active_input == "password":
            if   event.key == pygame.K_BACKSPACE: self.password_text = self.password_text[:-1]
            elif event.key == pygame.K_RETURN:    pass
            elif len(self.password_text) < 15 and event.unicode.isprintable():
                self.password_text += event.unicode

    # intenta hacer login en el servidor; si falla prueba con datos offline como fallback
    def try_login(self):
        port = 6667

        # abre el socket y manda las credenciales, lanza excepción si hay error de red
        def open_socket_and_login():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                sock.connect((self.host, port))
                sock.sendall(f"l:{self.username_text}:{self.password_text}\n".encode())
                resp = sock.recv(1024).decode().strip()
                return sock, resp
            except Exception:
                try: sock.close()
                except: pass
                raise

        self.network_socket = None

        try:
            sock, resp = open_socket_and_login()

            # login correcto: guardamos el socket y sincronizamos datos offline si los hay
            if resp == "ENTRAR":
                self.network_socket = sock
                self.offline_mode = False
                self.sync_offline_to_server()
                self.state = "MENU_SELECCION_MODO"
                return

            try: sock.close()
            except: pass

            # contraseña incorrecta: probamos si tenemos datos offline para sincronizar
            if resp == "INCORRECTO":
                datos_off = self.load_offline()
                if datos_off.get("username") == self.username_text:
                    self.sync_offline_to_server()
                    try:
                        sock2, resp2 = open_socket_and_login()
                        if resp2 == "ENTRAR":
                            self.network_socket = sock2
                            self.offline_mode = False
                            self.state = "MENU_SELECCION_MODO"
                        else:
                            try: sock2.close()
                            except: pass
                            self.login_error_msg = "Contraseña incorrecta"
                    except Exception:
                        self.login_error_msg = "Sin conexión con el servidor"
                else:
                    self.login_error_msg = "Contraseña incorrecta"
            elif resp == "INSUFICIENTE":
                self.login_error_msg = "Faltan datos por completar"
            elif resp == "INEXISTENTE":
                self.login_error_msg = "No existe el usuario"
            else:
                self.login_error_msg = "Error desconocido del servidor"

        except OSError:
            self.login_error_msg = "No se puede conectar al servidor"
            self.network_socket = None
        except Exception:
            self.login_error_msg = "Error al conectar con el servidor"
            self.network_socket = None

    # intenta registrar un nuevo usuario y loguea directamente si tiene éxito
    def try_register(self):
        port = 6667
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self.host, port))
            # mandamos el comando de registro con usuario y contraseña
            sock.sendall(f"r:{self.username_text}:{self.password_text}\n".encode())
            resp = sock.recv(1024).decode().strip()
            if resp == "ENTRAR":
                self.network_socket = sock
                self.offline_mode = False
                self.sync_offline_to_server()
                self.state = "MENU_SELECCION_MODO"
            else:
                try: sock.close()
                except: pass
                self.network_socket = None
                if   resp == "EXISTENTE":      self.login_error_msg = "El usuario ya existe"
                elif resp == "INSUFICIENTE":   self.login_error_msg = "Faltan datos por completar"
                elif resp == "ERROR_SERVIDOR": self.login_error_msg = "Error al registrar el usuario"
                else:                          self.login_error_msg = "Respuesta inesperada del servidor"
        except OSError:
            try: sock.close() if sock else None
            except: pass
            self.network_socket = None
            self.login_error_msg = "No se puede conectar al servidor"
        except Exception:
            try: sock.close() if sock else None
            except: pass
            self.network_socket = None
            self.login_error_msg = "Error al conectar con el servidor"