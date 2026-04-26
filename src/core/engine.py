import random
import sys
import socket
import json
import math

from src.utils.settings import *
from src.core.game import GameSession

# Resoluciones disponibles (etiqueta, ancho, alto)
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


class Engine:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.music_state    = "NONE"
        self.state          = "MENU_PRINCIPAL"
        self.current_choices = []

        # Variables de inicio de sesión
        self.username_text  = ""
        self.password_text  = ""
        self.active_input   = None
        self.login_error_msg = ""

        # Scoreboard
        self.scoreboard_data = []
        self.last_basc_time  = 0

        # Menú anterior para volver desde settings
        self.menu_anterior = "MENU_PRINCIPAL"

        # ── VARIABLES DE AJUSTES ────────────────────────────────────────────
        self.fullscreen       = False
        self.show_fps         = False
        self.volume           = 1.0
        self.dragging_volume  = False
        self.res_index        = 7          # índice en RESOLUTIONS (1720x920 por defecto)

        try:
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

        # Resolución activa
        self.W, self.H = RESOLUTIONS[self.res_index][1], RESOLUTIONS[self.res_index][2]

        self.screen = self._make_window()
        pygame.display.set_caption("Punternows Salvation: The Last Chance")
        self.clock = pygame.time.Clock()

        pygame.key.set_repeat(500, 50)

        self._load_assets()

        self.network_socket = None
        self.host = "108.130.127.24"

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS DE RESOLUCIÓN / VENTANA
    # ─────────────────────────────────────────────────────────────────────────

    def _make_window(self):
        if self.fullscreen:
            return pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN | pygame.SCALED)
        return pygame.display.set_mode((self.W, self.H))

    def _load_assets(self):
        """Carga / recarga assets que dependen del tamaño de ventana."""
        self.main_menu_bg      = load_sprite("assets/sprites/backgrounds/main_menu_bg.png",
                                              (self.W, self.H), DARK_GREY, remove_bg=False)
        self.game_over_menu_bg = load_sprite("assets/sprites/backgrounds/game_over_bg.png",
                                              (self.W, self.H), DARK_GREY, remove_bg=False)
        self.settings_icon     = load_sprite("assets/sprites/icons/settings.png", (80, 60), DARK_GREY)

    def _apply_resolution(self):
        """Cambia la resolución de pantalla y recarga assets dependientes."""
        self.W, self.H = RESOLUTIONS[self.res_index][1], RESOLUTIONS[self.res_index][2]
        self.screen = self._make_window()
        self._load_assets()
        self._save_settings()

    # Escala proporcional respecto a 1720×920 (resolución base)
    def _sx(self, x): return int(x * self.W / 1720)
    def _sy(self, y): return int(y * self.H / 920)
    def _sf(self, size): return max(10, int(size * min(self.W / 1720, self.H / 920)))

    # ─────────────────────────────────────────────────────────────────────────
    # UTILIDADES DE DIBUJO
    # ─────────────────────────────────────────────────────────────────────────

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

    def draw_fps(self):
        font_fps = pygame.font.SysFont("Arial", self._sf(18), bold=True)
        fps_txt  = font_fps.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        self.screen.blit(fps_txt, fps_txt.get_rect(topright=(self.W - 20, self._sy(50))))

    def _draw_settings_icon(self):
        """Dibuja el icono de ajustes en la esquina superior derecha. Devuelve su Rect."""
        icon_size = self._sx(80)
        margin    = self._sx(20)
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

    # ─────────────────────────────────────────────────────────────────────────
    # VOLUMEN
    # ─────────────────────────────────────────────────────────────────────────

    def _vol(self, base):
        if self.volume <= 0: return 0.0
        factor = math.log10(1 + 9 * self.volume) / math.log10(10)
        return base * factor

    def apply_volume(self):
        if self.state == "PLAYING":
            pygame.mixer.music.set_volume(self._vol(0.01))
        else:
            pygame.mixer.music.set_volume(self._vol(0.04))
        if hasattr(self, "game"):
            factor = math.log10(1 + 9 * self.volume) / math.log10(10) if self.volume > 0 else 0.0
            self.game.apply_volume_scale(factor)

    def update_music(self):
        if self.state in ["MENU_PRINCIPAL", "MENU_LOGIN", "MENU_REGISTER", "GAME_OVER",
                          "MENU_SELECCION_MODO", "MENU_SELECCION_SOLO"] and self.music_state != "MENU":
            try:
                pygame.mixer.music.load("assets/sounds/music_menu.mp3")
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(self._vol(0.04))
                self.music_state = "MENU"
            except:
                print("No se encontro assets/sounds/music_menu.mp3")

    # ─────────────────────────────────────────────────────────────────────────
    # GUARDADO
    # ─────────────────────────────────────────────────────────────────────────

    def _save_settings(self):
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

    # ─────────────────────────────────────────────────────────────────────────
    # BUCLE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self.update_music()
            if   self.state == "MENU_PRINCIPAL":          self.menu_principal_loop()
            elif self.state == "MENU_LOGIN":              self.menu_login_loop()
            elif self.state == "MENU_REGISTER":           self.menu_register_loop()
            elif self.state == "MENU_SELECCION_MODO":     self.menu_seleccion_modo_loop()
            elif self.state == "MENU_SELECCION_SOLO":     self.menu_seleccion_solo()
            elif self.state == "MENU_SELECCION_MULTIPLAYER": self.menu_seleccion_multiplayer()
            elif self.state == "MENU_SELECCION_SCORE":    self.menu_score_loop()
            elif self.state == "MENU_SETTINGS":           self.menu_settings_loop()
            elif self.state == "PAUSE_MENU":              self.pause_menu_loop()
            elif self.state == "PLAYING":                 self.game_loop()
            elif self.state == "GAME_OVER":               self.game_over_loop()
            elif self.state == "LEVEL_UP":                self.level_up_loop()

    # ─────────────────────────────────────────────────────────────────────────
    # MENÚ PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def menu_principal_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font     = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        title    = font.render("Punternows Salvation: The Last Chance", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(100))))

        bw, bh   = self._sx(450), self._sy(70)
        btn_play = pygame.Rect(W // 2 - bw // 2, H // 2 - self._sy(20),  bw, bh)
        btn_esc  = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(70),  bw, bh)

        self.draw_modern_button(btn_play, "Jugar",              font)
        self.draw_modern_button(btn_esc,  "Salir al Escritorio", font)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(mouse_pos):
                    self.state = "MENU_LOGIN"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                elif btn_esc.collidepoint(mouse_pos):
                    self._quit()

    # ─────────────────────────────────────────────────────────────────────────
    # SETTINGS
    # ─────────────────────────────────────────────────────────────────────────

    def menu_settings_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font       = pygame.font.SysFont("Arial", self._sf(38), bold=True)
        font_small = pygame.font.SysFont("Arial", self._sf(24), bold=True)
        font_label = pygame.font.SysFont("Arial", self._sf(20), bold=True)

        # ── Título ───────────────────────────────────────────────────────────
        title = font.render("AJUSTES", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(230))))

        # ── Panel de fondo ───────────────────────────────────────────────────
        panel_w, panel_h = self._sx(600), self._sy(520)
        panel = pygame.Rect(W // 2 - panel_w // 2, H // 2 - self._sy(190), panel_w, panel_h)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 25, 200))
        self.screen.blit(panel_surf, panel.topleft)
        pygame.draw.rect(self.screen, BTN_BORDER, panel, 2, border_radius=16)

        bw = self._sx(480)
        bh = self._sy(58)
        cx = W // 2

        # ── Pantalla completa ────────────────────────────────────────────────
        row1_y = H // 2 - self._sy(155)
        txt_fs  = "Pantalla Completa:  SÍ" if self.fullscreen else "Pantalla Completa:  NO"
        btn_fs  = pygame.Rect(cx - bw // 2, row1_y, bw, bh)
        self.draw_modern_button(btn_fs, txt_fs, font_small)

        # ── Mostrar FPS ──────────────────────────────────────────────────────
        row2_y = row1_y + bh + self._sy(18)
        txt_fps = "Mostrar FPS:  SÍ" if self.show_fps else "Mostrar FPS:  NO"
        btn_fps = pygame.Rect(cx - bw // 2, row2_y, bw, bh)
        self.draw_modern_button(btn_fps, txt_fps, font_small)

        # ── Resolución ───────────────────────────────────────────────────────
        row3_y = row2_y + bh + self._sy(18)
        res_label = font_label.render("RESOLUCIÓN", True, (180, 180, 180))
        self.screen.blit(res_label, res_label.get_rect(center=(cx, row3_y - self._sy(0))))

        arrow_w  = self._sx(48)
        mid_w    = self._sx(280)
        row3_h   = self._sy(52)

        btn_res_prev = pygame.Rect(cx - mid_w // 2 - arrow_w - self._sx(8), row3_y + self._sy(10), arrow_w, row3_h)
        btn_res_next = pygame.Rect(cx + mid_w // 2 + self._sx(8),           row3_y + self._sy(10), arrow_w, row3_h)
        btn_res_lbl  = pygame.Rect(cx - mid_w // 2,                          row3_y + self._sy(10), mid_w,   row3_h)

        mouse_pos = pygame.mouse.get_pos()

        # Fondo del label de resolución actual
        lbl_color = BTN_HOVER if btn_res_lbl.collidepoint(mouse_pos) else BTN_BG
        pygame.draw.rect(self.screen, (15, 15, 18), btn_res_lbl.move(0, 3), border_radius=10)  # sombra
        pygame.draw.rect(self.screen, lbl_color,    btn_res_lbl, border_radius=10)
        pygame.draw.rect(self.screen, BTN_BORDER,   btn_res_lbl, 2, border_radius=10)

        res_txt = font_small.render(RESOLUTIONS[self.res_index][0], True, WHITE)
        self.screen.blit(res_txt, res_txt.get_rect(center=btn_res_lbl.center))

        # Botones < y >
        for btn, symbol in [(btn_res_prev, "◄"), (btn_res_next, "►")]:
            bc = BTN_HOVER if btn.collidepoint(mouse_pos) else BTN_BG
            pygame.draw.rect(self.screen, (15, 15, 18), btn.move(0, 3), border_radius=10)
            pygame.draw.rect(self.screen, bc,           btn, border_radius=10)
            pygame.draw.rect(self.screen, BTN_BORDER,   btn, 2, border_radius=10)
            sym = font_small.render(symbol, True, WHITE)
            self.screen.blit(sym, sym.get_rect(center=btn.center))

        # ── Volumen ──────────────────────────────────────────────────────────
        row4_y   = row3_y + row3_h + self._sy(42)
        slider_w = self._sx(480)
        slider_h = self._sy(10)
        slider_x = cx - slider_w // 2
        slider_y = row4_y + self._sy(30)

        vol_lbl = font_small.render(f"Volumen:  {int(self.volume * 100)}%", True, WHITE)
        self.screen.blit(vol_lbl, vol_lbl.get_rect(center=(cx, row4_y + self._sy(8))))

        rail = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
        pygame.draw.rect(self.screen, (90, 90, 90), rail, border_radius=5)
        fill_w = int(slider_w * self.volume)
        pygame.draw.rect(self.screen, (210, 210, 210),
                         pygame.Rect(slider_x, slider_y, max(fill_w, 0), slider_h), border_radius=5)

        hx = slider_x + fill_w
        hy = slider_y + slider_h // 2
        hr = self._sx(13)
        hovered = abs(mouse_pos[0] - hx) < hr + 6 and abs(mouse_pos[1] - hy) < hr + 6
        pygame.draw.circle(self.screen, (60, 60, 60), (hx, hy + 2), hr)
        h_color = (255, 255, 255) if (hovered or self.dragging_volume) else (200, 200, 200)
        pygame.draw.circle(self.screen, h_color, (hx, hy), hr)

        # ── Botón Volver ─────────────────────────────────────────────────────
        btn_volver = pygame.Rect(cx - bw // 2, H // 2 + self._sy(220), bw, bh)
        self.draw_modern_button(btn_volver, "Volver", font_small)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Slider
                if (slider_x - hr <= mouse_pos[0] <= slider_x + slider_w + hr and
                        slider_y - hr * 2 <= mouse_pos[1] <= slider_y + slider_h + hr * 2):
                    self.dragging_volume = True
                    self.volume = max(0.0, min(1.0, (mouse_pos[0] - slider_x) / slider_w))
                    self.apply_volume()

                elif btn_fs.collidepoint(mouse_pos):
                    self.fullscreen = not self.fullscreen
                    self._apply_resolution()

                elif btn_fps.collidepoint(mouse_pos):
                    self.show_fps = not self.show_fps
                    self._save_settings()

                elif btn_res_prev.collidepoint(mouse_pos):
                    self.res_index = (self.res_index - 1) % len(RESOLUTIONS)
                    self._apply_resolution()

                elif btn_res_next.collidepoint(mouse_pos):
                    self.res_index = (self.res_index + 1) % len(RESOLUTIONS)
                    self._apply_resolution()

                elif btn_volver.collidepoint(mouse_pos):
                    self.state = self.menu_anterior

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_volume:
                    self.dragging_volume = False
                    self._save_settings()

            if event.type == pygame.MOUSEMOTION:
                if self.dragging_volume:
                    self.volume = max(0.0, min(1.0, (mouse_pos[0] - slider_x) / slider_w))
                    self.apply_volume()

    # ─────────────────────────────────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────────────────────────────────

    def menu_login_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        font_input = pygame.font.SysFont("Arial", self._sf(28))
        font_small = pygame.font.SysFont("Arial", self._sf(20), bold=True)

        title = font_title.render("INICIO DE SESION", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(150))))

        iw, ih = self._sx(400), self._sy(50)
        bw, bh = self._sx(450), self._sy(60)

        user_rect = pygame.Rect(W // 2 - iw // 2, H // 2 - self._sy(70),  iw, ih)
        pass_rect = pygame.Rect(W // 2 - iw // 2, H // 2 + self._sy(10),  iw, ih)
        btn_log   = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(120), bw, bh)
        btn_volver= pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(200), bw, bh)

        color_active   = (50, 150, 255)
        color_inactive = (95, 99, 104)
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

        self.draw_modern_button(btn_log,    "INICIAR SESION", font_title)
        self.draw_modern_button(btn_volver, "VOLVER ATRAS",   font_title)

        txt_no_acc = font_small.render("¿No tienes cuenta?", True, WHITE)
        self.screen.blit(txt_no_acc, (self._sx(30), H - self._sy(110)))
        btn_go_register = pygame.Rect(self._sx(30), H - self._sy(80), self._sx(220), self._sy(40))
        self.draw_modern_button(btn_go_register, "Ir a Registro", font_small)

        if self.login_error_msg:
            font_error = pygame.font.SysFont("Arial", self._sf(30), bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 50, 50))
            mx, my = 10, 5
            bg = pygame.Surface((txt_err.get_width() + mx * 2, txt_err.get_height() + my * 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            px = W // 2 - bg.get_width() // 2
            py = H // 2 + self._sy(65)
            self.screen.blit(bg, (px, py))
            self.screen.blit(txt_err, (W // 2 - txt_err.get_width() // 2, H // 2 + self._sy(70)))

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_LOGIN"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):   self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos): self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                else: self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    self._try_login()
                elif btn_volver.collidepoint(mouse_pos):
                    self._clear_login(); self.state = "MENU_PRINCIPAL"
                elif btn_go_register.collidepoint(mouse_pos):
                    self._clear_login(); self.state = "MENU_REGISTER"

            if event.type == pygame.KEYDOWN:
                self._handle_text_input(event)

    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRO
    # ─────────────────────────────────────────────────────────────────────────

    def menu_register_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        font_input = pygame.font.SysFont("Arial", self._sf(28))
        font_small = pygame.font.SysFont("Arial", self._sf(20), bold=True)

        title = font_title.render("REGISTRO DE NUEVO USUARIO", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(150))))

        iw, ih = self._sx(400), self._sy(50)
        bw, bh = self._sx(450), self._sy(60)

        user_rect = pygame.Rect(W // 2 - iw // 2, H // 2 - self._sy(70),  iw, ih)
        pass_rect = pygame.Rect(W // 2 - iw // 2, H // 2 + self._sy(10),  iw, ih)
        btn_log   = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(120), bw, bh)
        btn_volver= pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(200), bw, bh)

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
        self.screen.blit(txt_have_acc, (self._sx(30), H - self._sy(110)))
        btn_go_login = pygame.Rect(self._sx(30), H - self._sy(80), self._sx(220), self._sy(40))
        self.draw_modern_button(btn_go_login, "Ir a Login", font_small)

        if self.login_error_msg:
            font_error = pygame.font.SysFont("Arial", self._sf(30), bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 50, 50))
            mx, my = 10, 5
            bg = pygame.Surface((txt_err.get_width() + mx * 2, txt_err.get_height() + my * 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            self.screen.blit(bg, (W // 2 - bg.get_width() // 2, H // 2 + self._sy(65)))
            self.screen.blit(txt_err, (W // 2 - txt_err.get_width() // 2, H // 2 + self._sy(70)))

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):   self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos): self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                else: self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    self._try_register()
                elif btn_volver.collidepoint(mouse_pos):
                    self._clear_login(); self.state = "MENU_PRINCIPAL"
                elif btn_go_login.collidepoint(mouse_pos):
                    self._clear_login(); self.state = "MENU_LOGIN"

            if event.type == pygame.KEYDOWN:
                self._handle_text_input(event)

    # ─────────────────────────────────────────────────────────────────────────
    # SELECCIÓN DE MODO
    # ─────────────────────────────────────────────────────────────────────────

    def menu_seleccion_modo_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))

        font = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        title = font.render("SELECCIONA UN MODO", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(100))))

        bw, bh = self._sx(470), self._sy(70)
        btn_solo       = pygame.Rect(W // 2 - bw // 2, H // 2 - self._sy(40),  bw, bh)
        btn_multi      = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(60),  bw, bh)
        btn_score      = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(160), bw, bh)
        btn_menu_princ = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(260), bw, bh)

        self.draw_modern_button(btn_solo,       "Un Jugador",              font)
        self.draw_modern_button(btn_multi,      "Multijugador",            font)
        self.draw_modern_button(btn_score,      "Tabla de Clasificacion",  font)
        self.draw_modern_button(btn_menu_princ, "Volver al menu principal", font)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_MODO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_solo.collidepoint(mouse_pos):       self.state = "MENU_SELECCION_SOLO"
                elif btn_multi.collidepoint(mouse_pos):      self.state = "MENU_SELECCION_MULTIPLAYER"
                elif btn_score.collidepoint(mouse_pos):
                    self.last_basc_time = 0; self.state = "MENU_SELECCION_SCORE"
                elif btn_settings.collidepoint(mouse_pos):   self.state = "MENU_SETTINGS"
                elif btn_menu_princ.collidepoint(mouse_pos):
                    self.state = "MENU_PRINCIPAL"
                    if self.network_socket: self.network_socket.close()

    # ─────────────────────────────────────────────────────────────────────────
    # SELECCIÓN DE PERSONAJE
    # ─────────────────────────────────────────────────────────────────────────

    def menu_seleccion_solo(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        title = font.render("SELECCIONA TU PERSONAJE", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(150))))

        bw, bh = self._sx(500), self._sy(65)
        btn_knight   = pygame.Rect(W // 2 - bw // 2, H // 2 - self._sy(80),  bw, bh)
        btn_mage     = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(10),  bw, bh)
        btn_my_uncle = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(100), bw, bh)
        btn_volver   = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(200), bw, bh)

        self.draw_modern_button(btn_knight,   "Caballero (Alta vida)",     font)
        self.draw_modern_button(btn_mage,     "Mago (Mas rapido)",         font)
        self.draw_modern_button(btn_my_uncle, "Mi Tio (Lanza Platanos)",   font)
        self.draw_modern_button(btn_volver,   "Volver Atras",              font)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SOLO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                char = None
                if   btn_knight.collidepoint(mouse_pos):   char = "caballero"
                elif btn_mage.collidepoint(mouse_pos):     char = "mago"
                elif btn_my_uncle.collidepoint(mouse_pos): char = "my_uncle"
                elif btn_volver.collidepoint(mouse_pos):   self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"
                if char:
                    self.character_name = char
                    self.game = GameSession(character_name=char, multiplayer=False, world=1)
                    self.apply_volume()
                    self.state = "PLAYING"

    # ─────────────────────────────────────────────────────────────────────────
    # MULTIJUGADOR (en desarrollo)
    # ─────────────────────────────────────────────────────────────────────────

    def menu_seleccion_multiplayer(self):
        W, H = self.W, self.H
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        txt  = font.render("ESTAMOS TRABAJANDO EN ELLO", True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=(W // 2, H // 2 - self._sy(100))))

        bw, bh  = self._sx(450), self._sy(70)
        btn_vol = pygame.Rect(W // 2 - bw // 2, H // 2 - self._sy(40), bw, bh)
        self.draw_modern_button(btn_vol, "Volver al menu", font)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_MULTIPLAYER"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_vol.collidepoint(mouse_pos):      self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"

    # ─────────────────────────────────────────────────────────────────────────
    # SCOREBOARD
    # ─────────────────────────────────────────────────────────────────────────

    def get_scoreboard(self):
        if self.network_socket:
            try:
                self.network_socket.sendall("basc:u:s\n".encode())
                self.last_basc_time = pygame.time.get_ticks()
            except Exception as e:
                print(f"Error pidiendo scores: {e}")

    def menu_score_loop(self):
        W, H = self.W, self.H
        ahora = pygame.time.get_ticks()
        if ahora - self.last_basc_time > 15000:
            self.get_scoreboard()

        if self.network_socket:
            try:
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
            finally:
                self.network_socket.setblocking(True)

        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font       = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        font_small = pygame.font.SysFont("Arial", self._sf(30))

        title = font.render("TABLA DE CLASIFICACION", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, self._sy(100))))

        panel_w, panel_h = self._sx(700), self._sy(450)
        panel = pygame.Rect(W // 2 - panel_w // 2, self._sy(180), panel_w, panel_h)
        pygame.draw.rect(self.screen, (32, 33, 36), panel, border_radius=15)
        pygame.draw.rect(self.screen, (95, 99, 104), panel, width=2, border_radius=15)

        start_y = self._sy(220)
        if not self.scoreboard_data:
            ph = font_small.render("Cargando datos...", True, (200, 200, 200))
            self.screen.blit(ph, ph.get_rect(center=(W // 2, self._sy(400))))
        else:
            row_h = self._sy(40)
            for i, (user, score) in enumerate(self.scoreboard_data):
                color_rank = (255, 215, 0) if i == 0 else (200, 200, 200)
                t_rank  = font_small.render(f"#{i+1}", True, color_rank)
                t_user  = font_small.render(user,       True, WHITE)
                t_score = font_small.render(f"{score} pts", True, LIGHT_YELLOW)
                self.screen.blit(t_rank,  (W // 2 - self._sx(280), start_y + i * row_h))
                self.screen.blit(t_user,  (W // 2 - self._sx(150), start_y + i * row_h))
                self.screen.blit(t_score, (W // 2 + self._sx(150), start_y + i * row_h))

        bw, bh = self._sx(450), self._sy(70)
        btn_volver = pygame.Rect(W // 2 - bw // 2, H - self._sy(120), bw, bh)
        self.draw_modern_button(btn_volver, "Volver al menu", font)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SCORE"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_volver.collidepoint(mouse_pos):   self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos): self.state = "MENU_SETTINGS"

    # ─────────────────────────────────────────────────────────────────────────
    # GAMEPLAY
    # ─────────────────────────────────────────────────────────────────────────

    def game_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "PAUSE_MENU"
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_k:
                self.game.current_phase = 4

        estado_juego = self.game.update(self.username_text, self.network_socket)

        if estado_juego == "GAME_OVER":
            self.state = "GAME_OVER"
            return
        elif estado_juego == "LEVEL_UP":
            self.state = "LEVEL_UP"
            self.current_choices = random.sample(UPGRADES, min(3, len(UPGRADES)))
        elif estado_juego == "NEXT_WORLD":
            next_world = self.game.world + 1
            if next_world <= 3:
                player          = self.game.local_player
                accumulated     = self.game.score
                self.game       = GameSession(character_name=getattr(self, "character_name", "caballero"),
                                              multiplayer=False, world=next_world, carry_player=player)
                self.game.score = accumulated
                self.apply_volume()
            return

        self.game.draw(self.screen)
        if self.show_fps:
            self.draw_fps()
        pygame.display.flip()
        self.clock.tick(FPS)

    # ─────────────────────────────────────────────────────────────────────────
    # PAUSA
    # ─────────────────────────────────────────────────────────────────────────

    def pause_menu_loop(self):
        W, H = self.W, self.H
        self.game.draw(self.screen)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", self._sf(50), bold=True)
        font_btn   = pygame.font.SysFont("Arial", self._sf(40), bold=True)

        title = font_title.render("PAUSA", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, H // 2 - self._sy(150))))

        bw, bh = self._sx(450), self._sy(70)
        btn_reanudar  = pygame.Rect(W // 2 - bw // 2, H // 2 - self._sy(40), bw, bh)
        btn_abandonar = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(60), bw, bh)

        self.draw_modern_button(btn_reanudar,  "Reanudar",          font_btn)
        self.draw_modern_button(btn_abandonar, "Abandonar partida", font_btn)

        btn_settings = self._draw_settings_icon()
        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()
        self.menu_anterior = "PAUSE_MENU"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "PLAYING"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if   btn_reanudar.collidepoint(mouse_pos):   self.state = "PLAYING"
                elif btn_abandonar.collidepoint(mouse_pos):  self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):   self.state = "MENU_SETTINGS"

    # ─────────────────────────────────────────────────────────────────────────
    # GAME OVER
    # ─────────────────────────────────────────────────────────────────────────

    def game_over_loop(self):
        W, H = self.W, self.H
        self.screen.blit(self.game_over_menu_bg, (0, 0))

        font   = pygame.font.SysFont("Arial", self._sf(40), bold=True)
        bw, bh = self._sx(450), self._sy(70)
        btn    = pygame.Rect(W // 2 - bw // 2, H // 2 + self._sy(200), bw, bh)
        self.draw_modern_button(btn, "Volver al menu", font, BAR_RED)

        mouse_pos = pygame.mouse.get_pos()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "MENU_SELECCION_MODO"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"

    # ─────────────────────────────────────────────────────────────────────────
    # SUBIDA DE NIVEL
    # ─────────────────────────────────────────────────────────────────────────

    def level_up_loop(self):
        W, H = self.W, self.H
        self.game.draw(self.screen)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", self._sf(20), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self._sf(15))

        title = font_title.render("SUBIDA DE NIVEL!", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(W // 2, self._sy(100))))

        mouse_pos = pygame.mouse.get_pos()
        clicked   = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        bw      = self._sx(450)
        bh      = self._sy(70)
        spacing = self._sy(30)
        start_y = self._sy(200)

        for i, upgrade in enumerate(self.current_choices):
            btn_rect = pygame.Rect(W // 2 - bw // 2, start_y + i * (bh + spacing), bw, bh)
            color = (100, 100, 100) if btn_rect.collidepoint(mouse_pos) else (70, 70, 70)

            if btn_rect.collidepoint(mouse_pos) and clicked:
                self.game.local_player.apply_upgrade(upgrade)
                self.state = "PLAYING"
                return

            pygame.draw.rect(self.screen, color,         btn_rect, border_radius=10)
            pygame.draw.rect(self.screen, (155, 215, 0), btn_rect, 2, border_radius=10)

            name_txt = font_title.render(upgrade["name"], True, (255, 255, 255))
            desc_txt = font_desc.render(upgrade["desc"],  True, (200, 200, 200))
            self.screen.blit(name_txt, (btn_rect.x + 20, btn_rect.y + 15))
            self.screen.blit(desc_txt, (btn_rect.x + 20, btn_rect.y + name_txt.get_height() + 15))

        pygame.display.flip()

    # ─────────────────────────────────────────────────────────────────────────
    # UTILIDADES INTERNAS
    # ─────────────────────────────────────────────────────────────────────────

    def _quit(self):
        if self.network_socket:
            self.network_socket.close()
        pygame.quit()
        sys.exit()

    def _clear_login(self):
        self.username_text  = ""
        self.password_text  = ""
        self.active_input   = None
        self.login_error_msg = ""

    def _handle_text_input(self, event):
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

    def _try_login(self):
        port = 6667
        try:
            self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.network_socket.connect((self.host, port))
            self.network_socket.sendall(f"l:{self.username_text}:{self.password_text}\n".encode())
            resp = self.network_socket.recv(1024).decode().strip()
            if   resp == "ENTRAR":     self.state = "MENU_SELECCION_MODO"
            elif resp == "INCORRECTO": self.login_error_msg = "Contraseña incorrecta"; self.network_socket.close()
            elif resp == "INSUFICIENTE": self.login_error_msg = "Faltan datos por completar"; self.network_socket.close()
            elif resp == "INEXISTENTE":  self.login_error_msg = "No existe el usuario"; self.network_socket.close()
        except:
            self.login_error_msg = "Error al conectar con el servidor"
            if self.network_socket: self.network_socket.close()

    def _try_register(self):
        port = 6667
        try:
            self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.network_socket.connect((self.host, port))
            self.network_socket.sendall(f"r:{self.username_text}:{self.password_text}\n".encode())
            resp = self.network_socket.recv(1024).decode().strip()
            if   resp == "ENTRAR":         self.state = "MENU_SELECCION_MODO"
            elif resp == "EXISTENTE":      self.login_error_msg = "El usuario ya existe"; self.network_socket.close()
            elif resp == "INSUFICIENTE":   self.login_error_msg = "Faltan datos por completar"; self.network_socket.close()
            elif resp == "ERROR_SERVIDOR": self.login_error_msg = "Error al registrar el usuario"; self.network_socket.close()
        except:
            self.login_error_msg = "Error al conectar con el servidor"
            if self.network_socket: self.network_socket.close()