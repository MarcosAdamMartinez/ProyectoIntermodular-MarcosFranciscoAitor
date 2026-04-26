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
        self.host = "34.253.221.107"

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
        overlay = pygame.Surface((W, H), pygame.SRCALPHA); overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        mouse_pos = pygame.mouse.get_pos()

        font_title = pygame.font.SysFont("Arial", self._sf(42), bold=True)
        font_name  = pygame.font.SysFont("Arial", self._sf(22), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self._sf(16))
        font_stat  = pygame.font.SysFont("Arial", self._sf(14))
        font_back  = pygame.font.SysFont("Arial", self._sf(22), bold=True)

        title = font_title.render("SELECCIONA TU PERSONAJE", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(W // 2, self._sy(70))))

        # ── Datos de personajes ───────────────────────────────────────────────
        characters = [
            {
                "key":   "caballero",
                "name":  "Caballero",
                "desc":  "Guerrero resistente con\nalto aguante en combate",
                "stats": ["Vida: 150", "Vel: 4", "Espada"],
                "icon":  "assets/sprites/icons/knight_icon.png",
                "color": (60, 100, 200),
                "accent": (100, 160, 255),
            },
            {
                "key":   "mago",
                "name":  "Mago",
                "desc":  "Veloz lanzador de hechizos\ncon gran movilidad",
                "stats": ["Vida: 80", "Vel: 6", "Varita"],
                "icon":  "assets/sprites/icons/mage_icon.png",
                "color": (100, 30, 180),
                "accent": (180, 80, 255),
            },
            {
                "key":   "my_uncle",
                "name":  "Mi Tío",
                "desc":  "Personaje misterioso que\nlanza plátanos como armas",
                "stats": ["Vida: 100", "Vel: 5", "Banana"],
                "icon":  "assets/sprites/icons/my_uncle_icon.png",
                "color": (120, 90, 30),
                "accent": (220, 180, 60),
            },
        ]

        # ── Layout de tarjetas ────────────────────────────────────────────────
        n        = len(characters)
        margin_x = self._sx(60)
        gap      = self._sx(30)
        card_w   = (W - margin_x * 2 - gap * (n - 1)) // n
        card_h   = self._sy(440)
        cards_y  = self._sy(130)

        card_rects = []
        for i in range(n):
            cx = margin_x + i * (card_w + gap)
            card_rects.append(pygame.Rect(cx, cards_y, card_w, card_h))

        # ── Dibuja cada tarjeta ───────────────────────────────────────────────
        char_keys = []
        for i, (char, rect) in enumerate(zip(characters, card_rects)):
            hovered = rect.collidepoint(mouse_pos)
            char_keys.append(char["key"])

            # Sombra
            shadow = rect.move(0, 6)
            pygame.draw.rect(self.screen, (10, 10, 15), shadow, border_radius=18)

            # Fondo de tarjeta
            bg_alpha = 230 if hovered else 190
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            r, g, b = char["color"]
            card_surf.fill((max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), bg_alpha))
            self.screen.blit(card_surf, rect.topleft)

            # Borde — más brillante si hover
            border_color = char["accent"] if hovered else (80, 80, 90)
            border_w = 3 if hovered else 2
            pygame.draw.rect(self.screen, border_color, rect, border_w, border_radius=18)

            # Icono / sprite del personaje
            icon_size = int(min(card_w * 0.55, card_h * 0.38))
            icon_rect = pygame.Rect(rect.centerx - icon_size // 2,
                                    rect.y + self._sy(18), icon_size, icon_size)

            import os
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
                # Placeholder con inicial
                pygame.draw.rect(self.screen, char["color"], icon_rect, border_radius=12)
                pygame.draw.rect(self.screen, char["accent"], icon_rect, 2, border_radius=12)
                ini  = font_title.render(char["name"][0], True, WHITE)
                self.screen.blit(ini, ini.get_rect(center=icon_rect.center))

            # Nombre
            text_y = icon_rect.bottom + self._sy(14)
            name_surf = font_name.render(char["name"], True, WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, y=text_y))
            text_y += name_surf.get_height() + self._sy(8)

            # Separador
            sep_x1 = rect.x + self._sx(20)
            sep_x2 = rect.right - self._sx(20)
            pygame.draw.line(self.screen, char["accent"], (sep_x1, text_y), (sep_x2, text_y), 1)
            text_y += self._sy(8)

            # Descripción (multilínea manual)
            for line in char["desc"].split("\n"):
                d_surf = font_desc.render(line, True, (200, 200, 220))
                self.screen.blit(d_surf, d_surf.get_rect(centerx=rect.centerx, y=text_y))
                text_y += d_surf.get_height() + self._sy(2)
            text_y += self._sy(10)

            # Stats
            for stat in char["stats"]:
                s_surf = font_stat.render(stat, True, char["accent"])
                self.screen.blit(s_surf, s_surf.get_rect(centerx=rect.centerx, y=text_y))
                text_y += s_surf.get_height() + self._sy(4)

            # Texto "Seleccionar" al pasar el ratón
            if hovered:
                sel_surf = font_stat.render("Seleccionar", True, WHITE)
                sel_y    = rect.bottom - sel_surf.get_height() - self._sy(14)
                sel_rect_bg = pygame.Rect(rect.x + self._sx(14), sel_y - self._sy(4),
                                          card_w - self._sx(28), sel_surf.get_height() + self._sy(8))
                hl = pygame.Surface((sel_rect_bg.w, sel_rect_bg.h), pygame.SRCALPHA)
                hl.fill((*char["accent"], 60))
                self.screen.blit(hl, sel_rect_bg.topleft)
                self.screen.blit(sel_surf, sel_surf.get_rect(centerx=rect.centerx, y=sel_y))

        # ── Botón volver ──────────────────────────────────────────────────────
        bw_back  = self._sx(280)
        bh_back  = self._sy(50)
        btn_volver = pygame.Rect(W // 2 - bw_back // 2,
                                 cards_y + card_h + self._sy(22), bw_back, bh_back)
        self.draw_modern_button(btn_volver, "Volver Atrás", font_back)

        btn_settings = self._draw_settings_icon()
        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SOLO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                char = None
                for i, rect in enumerate(card_rects):
                    if rect.collidepoint(mouse_pos):
                        char = char_keys[i]
                        break
                if char:
                    self.character_name = char
                    self.game = GameSession(character_name=char, multiplayer=False, world=1)
                    self.apply_volume()
                    self.state = "PLAYING"
                elif btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"

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
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        mouse_pos = pygame.mouse.get_pos()
        clicked   = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        font_title = pygame.font.SysFont("Arial", self._sf(44), bold=True)
        font_sub   = pygame.font.SysFont("Arial", self._sf(20))
        font_name  = pygame.font.SysFont("Arial", self._sf(20), bold=True)
        font_desc  = pygame.font.SysFont("Arial", self._sf(15))

        # Título animado con pulso dorado
        pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
        gold  = (int(200 + 55 * pulse), int(180 + 35 * pulse), 0)
        title = font_title.render("¡SUBIDA DE NIVEL!", True, gold)
        sub   = font_sub.render("Elige una mejora", True, (180, 180, 180))
        self.screen.blit(title, title.get_rect(center=(W // 2, self._sy(80))))
        self.screen.blit(sub,   sub.get_rect(center=(W // 2, self._sy(130))))

        # ── Iconos de mejora por tipo ─────────────────────────────────────────
        UPGRADE_ICONS = {
            "max_hp":  ("assets/sprites/icons/hp_up.png",     "❤",  (200,  40,  40)),
            "speed":   ("assets/sprites/icons/speed_up.png",  "⚡", ( 60, 160, 255)),
            "damage":  ("assets/sprites/icons/dmg_up.png",    "⚔",  (255, 120,  30)),
            "cooldown":("assets/sprites/icons/cd_down.png",   "🔥", (255, 200,   0)),
            "magnet":  ("assets/sprites/icons/magnet_up.png", "", (120,  80, 220)),
            "hp":      ("assets/sprites/icons/heal_up.png",   "", ( 50, 200, 100)),
        }

        # ── Layout de tarjetas ────────────────────────────────────────────────
        n        = len(self.current_choices)
        margin_x = self._sx(80)
        gap      = self._sx(28)
        card_w   = (W - margin_x * 2 - gap * (n - 1)) // max(n, 1)
        card_h   = self._sy(280)
        cards_y  = H // 2 - card_h // 2 + self._sy(20)

        import os
        for i, upgrade in enumerate(self.current_choices):
            cx   = margin_x + i * (card_w + gap)
            rect = pygame.Rect(cx, cards_y, card_w, card_h)
            hov  = rect.collidepoint(mouse_pos)

            icon_path, icon_emoji, accent = UPGRADE_ICONS.get(
                upgrade["type"], ("", "★", (180, 180, 50)))

            # Sombra
            pygame.draw.rect(self.screen, (8, 8, 12), rect.move(0, 7), border_radius=18)

            # Fondo de tarjeta con gradiente simulado
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            r, g, b = accent
            card_surf.fill((max(r - 60, 0), max(g - 60, 0), max(b - 60, 0), 210 if hov else 175))
            self.screen.blit(card_surf, rect.topleft)

            border_col = accent if hov else (70, 70, 80)
            border_w   = 3 if hov else 2
            pygame.draw.rect(self.screen, border_col, rect, border_w, border_radius=18)

            # Brillo superior al hacer hover
            if hov:
                glow = pygame.Surface((card_w, self._sy(4)), pygame.SRCALPHA)
                glow.fill((*accent, 160))
                self.screen.blit(glow, (rect.x, rect.y + border_w))

            # Icono de mejora
            icon_size = int(min(card_w * 0.38, card_h * 0.30))
            icon_y    = rect.y + self._sy(22)
            icon_rect = pygame.Rect(rect.centerx - icon_size // 2, icon_y, icon_size, icon_size)

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
                # Círculo de fondo + emoji/símbolo
                pygame.draw.circle(self.screen, accent,
                                   icon_rect.center, icon_size // 2)
                pygame.draw.circle(self.screen, (255, 255, 255),
                                   icon_rect.center, icon_size // 2, 2)
                ico_font = pygame.font.SysFont("Segoe UI Emoji", int(icon_size * 0.52))
                ico_surf = ico_font.render(icon_emoji, True, WHITE)
                self.screen.blit(ico_surf, ico_surf.get_rect(center=icon_rect.center))

            # Nombre de la mejora
            text_y = icon_rect.bottom + self._sy(12)
            name_surf = font_name.render(upgrade["name"], True, WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(centerx=rect.centerx, y=text_y))
            text_y += name_surf.get_height() + self._sy(6)

            # Separador
            pygame.draw.line(self.screen, accent,
                             (rect.x + self._sx(18), text_y),
                             (rect.right - self._sx(18), text_y), 1)
            text_y += self._sy(8)

            # Descripción
            desc_surf = font_desc.render(upgrade["desc"], True, (210, 210, 230))
            self.screen.blit(desc_surf, desc_surf.get_rect(centerx=rect.centerx, y=text_y))

            # Label hover al fondo
            if hov:
                pick_font = pygame.font.SysFont("Arial", self._sf(14), bold=True)
                pick_surf = pick_font.render("Elegir", True, WHITE)
                pick_y    = rect.bottom - pick_surf.get_height() - self._sy(12)
                hl        = pygame.Surface((card_w - self._sx(28),
                                            pick_surf.get_height() + self._sy(8)), pygame.SRCALPHA)
                hl.fill((*accent, 70))
                self.screen.blit(hl, (rect.x + self._sx(14), pick_y - self._sy(4)))
                self.screen.blit(pick_surf, pick_surf.get_rect(centerx=rect.centerx, y=pick_y))

            if hov and clicked:
                self.game.local_player.apply_upgrade(upgrade)
                self.state = "PLAYING"
                pygame.display.flip()
                return

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