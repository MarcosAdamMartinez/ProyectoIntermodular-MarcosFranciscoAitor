import random
import sys
import socket
import json
from asyncio.windows_events import NULL

from src.utils.settings import *
from src.core.game import GameSession


class Engine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Punternows Salvation: The Last Chance")
        self.clock = pygame.time.Clock()

        # Estado inicial del motor
        self.state = "MENU_PRINCIPAL"
        self.current_choices = []

        self.main_menu_bg = load_sprite("assets/sprites/backgrounds/main_menu_bg.png", (WIDTH, HEIGHT), DARK_GREY,
                                        remove_bg=False)
        self.game_over_menu_bg = load_sprite("assets/sprites/backgrounds/game_over_bg.png", (WIDTH, HEIGHT), DARK_GREY,
                                             remove_bg=False)

        # Variables para el sistema de inicio de sesion
        self.username_text = ""
        self.password_text = ""
        self.active_input = None
        self.login_error_msg = ""

        # Variable para saber en que menu volver del settings
        self.menu_anterior = "MENU_PRINCIPAL"

        # Icono de ajustes
        self.settings_icon = load_sprite("assets/sprites/icons/settings.png", (80, 60), DARK_GREY)

        # --- VARIABLES DE AJUSTES ---
        self.fullscreen = False
        self.show_fps = False
        try:
            with open("settings.json", "r", encoding='utf-8') as f:
                datos = json.load(f)
                if datos["fullscreen"]:
                    self.fullscreen = True
                if datos["fps"]:
                    self.show_fps = True
        except:
            print("Error loading settings")

        if self.fullscreen:
            # Esto escala el juego a tu monitor manteniendo las proporciones
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        else:
            # Volvemos al modo ventana normal
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

        pygame.key.set_repeat(500, 50)

        self.network_socket = None
        self.username = ""

    def draw_modern_button(self, rect, text, font, *color):
        mouse_pos = pygame.mouse.get_pos()

        BTN_BG = (32, 33, 36)
        BTN_HOVER = (60, 64, 67)
        BTN_BORDER = (95, 99, 104)
        BTN_SHADOW = (15, 15, 18)

        if color:
            sombra = rect.copy()
            sombra.y += 4
            pygame.draw.rect(self.screen, BTN_SHADOW, sombra, border_radius=12)
            pygame.draw.rect(self.screen, color[0], rect, border_radius=12)
            pygame.draw.rect(self.screen, BTN_BORDER, rect, width=2, border_radius=12)
            txt_surf = font.render(text, True, DEATH_TEXT if 'DEATH_TEXT' in globals() else WHITE)
        else:
            color_actual = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_BG
            sombra = rect.copy()
            sombra.y += 4
            pygame.draw.rect(self.screen, BTN_SHADOW, sombra, border_radius=12)
            pygame.draw.rect(self.screen, color_actual, rect, border_radius=12)
            pygame.draw.rect(self.screen, BTN_BORDER, rect, width=2, border_radius=12)
            txt_surf = font.render(text, True, WHITE)

        self.screen.blit(txt_surf,
                         (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))

    def draw_fps(self):
        # Dibuja el contador de FPS en la esquina superior izquierda
        font_fps = pygame.font.SysFont("Arial", 18, bold=True)
        fps_txt = font_fps.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        fps_rect = fps_txt.get_rect(topright=(WIDTH - 20, 50))

        self.screen.blit(fps_txt, fps_rect)

    def run(self):
        while True:
            if self.state == "MENU_PRINCIPAL":
                self.menu_principal_loop()
            elif self.state == "MENU_LOGIN":
                self.menu_login_loop()
            elif self.state == "MENU_REGISTER":
                self.menu_register_loop()
            elif self.state == "MENU_SELECCION_MODO":
                self.menu_seleccion_modo_loop()
            elif self.state == "MENU_SELECCION_SOLO":
                self.menu_seleccion_solo()
            elif self.state == "MENU_SELECCION_MULTIPLAYER":
                self.menu_seleccion_multiplayer()
            elif self.state == "MENU_SELECCION_SCORE":
                self.menu_score_loop()
            elif self.state == "MENU_SETTINGS":
                self.menu_settings_loop()
            elif self.state == "PAUSE_MENU":  # <--- NUEVO ESTADO DE PAUSA
                self.pause_menu_loop()
            elif self.state == "PLAYING":
                self.game_loop()
            elif self.state == "GAME_OVER":
                self.game_over_loop()
            elif self.state == "LEVEL_UP":
                self.level_up_loop()

    def menu_principal_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        title = font.render("Punternows Salvation: The Last Chance", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        self.screen.blit(title, title_rect)

        btn_width = 450
        btn_height = 70
        btn_play = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 20, btn_width, btn_height)
        btn_esc = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 70, btn_width, btn_height)

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin

        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.draw_modern_button(btn_play, "Jugar", font)
        self.draw_modern_button(btn_esc, "Salir al Escritorio", font)
        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()

        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(mouse_pos):
                    self.state = "MENU_LOGIN"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                elif btn_esc.collidepoint(mouse_pos):
                    if self.network_socket:
                        self.network_socket.close()
                    pygame.quit()
                    sys.exit()

    def menu_settings_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        title = font.render("AJUSTES", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title, title_rect)

        btn_width = 450
        btn_height = 70

        btn_fs = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 50, btn_width, btn_height)
        btn_fps = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 40, btn_width, btn_height)
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 180, btn_width, btn_height)

        txt_fs = "Pantalla Completa: SI" if self.fullscreen else "Pantalla Completa: NO"
        txt_fps = "Mostrar FPS: SI" if self.show_fps else "Mostrar FPS: NO"

        self.draw_modern_button(btn_fs, txt_fs, font)
        self.draw_modern_button(btn_fps, txt_fps, font)
        self.draw_modern_button(btn_volver, "Volver", font)

        pygame.display.flip()

        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_fs.collidepoint(mouse_pos):
                    self.fullscreen = not self.fullscreen
                    try:
                        with open("settings.json", "r", encoding='utf-8') as f:
                            datos = json.load(f)
                            datos["fullscreen"] = self.fullscreen
                        with open("settings.json", "w", encoding='utf-8') as f:
                            f.write(json.dumps(datos, indent=4))
                    except:
                        pass

                    if self.fullscreen:
                        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
                    else:
                        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

                elif btn_fps.collidepoint(mouse_pos):
                    self.show_fps = not self.show_fps
                    try:
                        with open("settings.json", "r", encoding='utf-8') as f:
                            datos = json.load(f)
                            datos["fps"] = self.show_fps
                        with open("settings.json", "w", encoding='utf-8') as f:
                            f.write(json.dumps(datos, indent=4))
                    except:
                        pass

                elif btn_volver.collidepoint(mouse_pos):
                    self.state = self.menu_anterior

    def menu_login_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", 40, bold=True)
        font_input = pygame.font.SysFont("Arial", 28)
        font_small = pygame.font.SysFont("Arial", 20, bold=True)

        title = font_title.render("INICIO DE SESION", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title, title_rect)

        input_width = 400
        input_height = 50
        btn_width = 450
        btn_height = 60

        user_rect = pygame.Rect(WIDTH // 2 - input_width // 2, HEIGHT // 2 - 70, input_width, input_height)
        pass_rect = pygame.Rect(WIDTH // 2 - input_width // 2, HEIGHT // 2 + 10, input_width, input_height)

        btn_log = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 120, btn_width, btn_height)
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 200, btn_width, btn_height)

        color_active = (50, 150, 255)
        color_inactive = (95, 99, 104)

        color_user = color_active if self.active_input == "username" else color_inactive
        color_pass = color_active if self.active_input == "password" else color_inactive

        pygame.draw.rect(self.screen, (32, 33, 36), user_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_user, user_rect, width=2, border_radius=8)

        pygame.draw.rect(self.screen, (32, 33, 36), pass_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_pass, pass_rect, width=2, border_radius=8)

        if self.username_text == "":
            txt_user = font_input.render("Nombre de usuario", True, (150, 150, 150))
        else:
            txt_user = font_input.render(self.username_text, True, WHITE)
        self.screen.blit(txt_user, (user_rect.x + 15, user_rect.y + 10))

        if self.password_text == "":
            txt_pass = font_input.render("Contraseña", True, (150, 150, 150))
        else:
            txt_pass = font_input.render("*" * len(self.password_text), True, WHITE)
        self.screen.blit(txt_pass, (pass_rect.x + 15, pass_rect.y + 10))

        self.draw_modern_button(btn_log, "ENTRAR", font_title)
        self.draw_modern_button(btn_volver, "VOLVER ATRAS", font_title)

        txt_need_reg = font_small.render("¿Necesitas registrarte?", True, WHITE)
        self.screen.blit(txt_need_reg, (30, HEIGHT - 110))
        btn_go_register = pygame.Rect(30, HEIGHT - 80, 220, 40)
        self.draw_modern_button(btn_go_register, "Ir a Registro", font_small)

        if self.login_error_msg != "":
            font_error = pygame.font.SysFont("Arial", 30, bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 50, 50))

            margen_x = 10
            margen_y = 5
            ancho_caja = txt_err.get_width() + (margen_x * 2)
            alto_caja = txt_err.get_height() + (margen_y * 2)

            caja_fondo = pygame.Surface((ancho_caja, alto_caja), pygame.SRCALPHA)
            caja_fondo.fill((0, 0, 0, 150))

            pos_x = WIDTH // 2 - ancho_caja // 2
            pos_y = HEIGHT // 2 + 65

            self.screen.blit(caja_fondo, (pos_x, pos_y))
            self.screen.blit(txt_err, (WIDTH // 2 - txt_err.get_width() // 2, HEIGHT // 2 + 70))

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_LOGIN"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):
                    self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos):
                    self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                else:
                    self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    self.username = self.username_text

                    host = "127.0.0.1"
                    post = 6667
                    try:
                        self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.network_socket.connect((host, post))

                        mensaje = f"l:{self.username_text}:{self.password_text}\n"
                        self.network_socket.sendall(mensaje.encode())

                        respuesta = self.network_socket.recv(1024).decode().strip()

                        if respuesta == "ENTRAR":
                            self.state = "MENU_SELECCION_MODO"
                        elif respuesta == "INCORRECTO":
                            self.login_error_msg = "Contraseña incorrecta"
                            self.network_socket.close()
                        elif respuesta == "INSUFICIENTE":
                            self.login_error_msg = "Faltan datos por completar"
                            self.network_socket.close()
                        elif respuesta == "INEXISTENTE":
                            self.login_error_msg = "No existe el usuario, compruebelo de nuevo o registrese"
                            self.network_socket.close()
                    except Exception as e:
                        self.login_error_msg = "Error al conectar con el servidor"
                        if self.network_socket:
                            self.network_socket.close()

                elif btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_PRINCIPAL"
                    self.username_text = ""
                    self.password_text = ""
                    self.active_input = None
                    self.login_error_msg = ""

                elif btn_go_register.collidepoint(mouse_pos):
                    self.state = "MENU_REGISTER"
                    self.username_text = ""
                    self.password_text = ""
                    self.active_input = None
                    self.login_error_msg = ""

            if event.type == pygame.KEYDOWN:
                if self.active_input == "username":
                    if event.key == pygame.K_BACKSPACE:
                        self.username_text = self.username_text[:-1]
                    elif event.key == pygame.K_TAB:
                        self.active_input = "password"
                    else:
                        if len(self.username_text) < 15 and event.unicode.isprintable():
                            self.username_text += event.unicode
                elif self.active_input == "password":
                    if event.key == pygame.K_BACKSPACE:
                        self.password_text = self.password_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        pass  # Login logica
                    else:
                        if len(self.password_text) < 15 and event.unicode.isprintable():
                            self.password_text += event.unicode

    def menu_register_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))

        font_title = pygame.font.SysFont("Arial", 40, bold=True)
        font_input = pygame.font.SysFont("Arial", 28)
        font_small = pygame.font.SysFont("Arial", 20, bold=True)

        title = font_title.render("REGISTRO DE NUEVO USUARIO", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title, title_rect)

        input_width = 400
        input_height = 50
        btn_width = 450
        btn_height = 60

        user_rect = pygame.Rect(WIDTH // 2 - input_width // 2, HEIGHT // 2 - 70, input_width, input_height)
        pass_rect = pygame.Rect(WIDTH // 2 - input_width // 2, HEIGHT // 2 + 10, input_width, input_height)

        btn_log = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 120, btn_width, btn_height)
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 200, btn_width, btn_height)

        color_active = (50, 150, 255)
        color_inactive = (95, 99, 104)

        color_user = color_active if self.active_input == "username" else color_inactive
        color_pass = color_active if self.active_input == "password" else color_inactive

        pygame.draw.rect(self.screen, (32, 33, 36), user_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_user, user_rect, width=2, border_radius=8)

        pygame.draw.rect(self.screen, (32, 33, 36), pass_rect, border_radius=8)
        pygame.draw.rect(self.screen, color_pass, pass_rect, width=2, border_radius=8)

        if self.username_text == "":
            txt_user = font_input.render("Nombre de usuario", True, (150, 150, 150))
        else:
            txt_user = font_input.render(self.username_text, True, WHITE)
        self.screen.blit(txt_user, (user_rect.x + 15, user_rect.y + 10))

        if self.password_text == "":
            txt_pass = font_input.render("Contraseña", True, (150, 150, 150))
        else:
            txt_pass = font_input.render("*" * len(self.password_text), True, WHITE)
        self.screen.blit(txt_pass, (pass_rect.x + 15, pass_rect.y + 10))

        self.draw_modern_button(btn_log, "REGISTRARSE", font_title)
        self.draw_modern_button(btn_volver, "VOLVER ATRAS", font_title)

        txt_have_acc = font_small.render("¿Ya tienes cuenta?", True, WHITE)
        self.screen.blit(txt_have_acc, (30, HEIGHT - 110))
        btn_go_login = pygame.Rect(30, HEIGHT - 80, 220, 40)
        self.draw_modern_button(btn_go_login, "Ir a Login", font_small)

        if self.login_error_msg != "":
            font_error = pygame.font.SysFont("Arial", 30, bold=True)
            txt_err = font_error.render(self.login_error_msg, True, (255, 50, 50))

            margen_x = 10
            margen_y = 5
            ancho_caja = txt_err.get_width() + (margen_x * 2)
            alto_caja = txt_err.get_height() + (margen_y * 2)

            caja_fondo = pygame.Surface((ancho_caja, alto_caja), pygame.SRCALPHA)
            caja_fondo.fill((0, 0, 0, 150))

            pos_x = WIDTH // 2 - ancho_caja // 2
            pos_y = HEIGHT // 2 + 65

            self.screen.blit(caja_fondo, (pos_x, pos_y))
            self.screen.blit(txt_err, (WIDTH // 2 - txt_err.get_width() // 2, HEIGHT // 2 + 70))

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_PRINCIPAL"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if user_rect.collidepoint(mouse_pos):
                    self.active_input = "username"
                elif pass_rect.collidepoint(mouse_pos):
                    self.active_input = "password"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                else:
                    self.active_input = None

                if btn_log.collidepoint(mouse_pos):
                    host = "127.0.0.1"
                    post = 6667
                    try:
                        self.network_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.network_socket.connect((host, post))

                        mensaje = f"r:{self.username_text}:{self.password_text}\n"
                        self.network_socket.sendall(mensaje.encode())

                        respuesta = self.network_socket.recv(1024).decode().strip()

                        if respuesta == "ENTRAR":
                            self.state = "MENU_SELECCION_MODO"
                        elif respuesta == "EXISTENTE":
                            self.login_error_msg = "El usuario ya existe"
                            self.network_socket.close()
                        elif respuesta == "INSUFICIENTE":
                            self.login_error_msg = "Faltan datos por completar"
                            self.network_socket.close()
                        elif respuesta == "ERROR_SERVIDOR":
                            self.login_error_msg = "Error al registrar el nuevo usuario"
                            self.network_socket.close()

                    except Exception as e:
                        self.login_error_msg = "Error al conectar con el servidor"
                        if self.network_socket:
                            self.network_socket.close()

                elif btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_PRINCIPAL"
                    self.username_text = ""
                    self.password_text = ""
                    self.active_input = None
                    self.login_error_msg = ""

                elif btn_go_login.collidepoint(mouse_pos):
                    self.state = "MENU_LOGIN"
                    self.username_text = ""
                    self.password_text = ""
                    self.active_input = None
                    self.login_error_msg = ""

            if event.type == pygame.KEYDOWN:
                if self.active_input == "username":
                    if event.key == pygame.K_BACKSPACE:
                        self.username_text = self.username_text[:-1]
                    elif event.key == pygame.K_TAB:
                        self.active_input = "password"
                    else:
                        if len(self.username_text) < 15 and event.unicode.isprintable():
                            self.username_text += event.unicode
                elif self.active_input == "password":
                    if event.key == pygame.K_BACKSPACE:
                        self.password_text = self.password_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        pass
                    else:
                        if len(self.password_text) < 15 and event.unicode.isprintable():
                            self.password_text += event.unicode

    def menu_seleccion_modo_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        title = font.render("SELECCIONA UN MODO", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        self.screen.blit(title, title_rect)

        btn_width = 470
        btn_height = 70
        btn_solo = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width, btn_height)
        btn_multiplayer = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 60, btn_width, btn_height)
        btn_score = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 160, btn_width, btn_height)
        btn_menu_principal = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 260, btn_width, btn_height)

        self.draw_modern_button(btn_solo, "Un Jugador", font)
        self.draw_modern_button(btn_multiplayer, "Multijugador", font)
        self.draw_modern_button(btn_score, "Tabla de Clasificacion", font)
        self.draw_modern_button(btn_menu_principal, "Volver al menu principal", font)

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_MODO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_solo.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_SOLO"
                elif btn_multiplayer.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MULTIPLAYER"
                elif btn_score.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_SCORE"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"
                elif btn_menu_principal.collidepoint(mouse_pos):
                    self.state = "MENU_PRINCIPAL"
                    if self.network_socket:
                        self.network_socket.close()

    def menu_seleccion_solo(self):
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        title = font.render("SELECCIONA TU PERSONAJE", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title, title_rect)

        btn_width = 500
        btn_height = 65
        btn_knight = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 80, btn_width, btn_height)
        btn_mage = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 10, btn_width, btn_height)
        btn_my_uncle = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 100, btn_width, btn_height)
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 200, btn_width, btn_height)

        self.draw_modern_button(btn_knight, "Caballero (Alta vida)", font)
        self.draw_modern_button(btn_mage, "Mago (Mas rapido)", font)
        self.draw_modern_button(btn_my_uncle, "Mi Tio (Lanza Platanos)", font)
        self.draw_modern_button(btn_volver, "Volver Atras", font)

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SOLO"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_knight.collidepoint(mouse_pos):
                    self.game = GameSession(character_name="caballero", multiplayer=False)
                    self.state = "PLAYING"
                elif btn_mage.collidepoint(mouse_pos):
                    self.game = GameSession(character_name="mago", multiplayer=False)
                    self.state = "PLAYING"
                elif btn_my_uncle.collidepoint(mouse_pos):
                    self.game = GameSession(character_name="my_uncle", multiplayer=False)
                    self.state = "PLAYING"
                elif btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"

    def menu_seleccion_multiplayer(self):
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        texto_provisional = font.render("ESTAMOS TRABAJANDO EN ELLO", True, WHITE)
        texto_rect = texto_provisional.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        self.screen.blit(texto_provisional, texto_rect)

        btn_width = 450
        btn_height = 70
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width, btn_height)

        self.draw_modern_button(btn_volver, "Volver al menu", font)

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_MULTIPLAYER"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"

    def menu_score_loop(self):
        self.screen.blit(self.main_menu_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)
        font_small = pygame.font.SysFont("Arial", 25)

        title = font.render("TABLA DE CLASIFICACION", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        panel_rect = pygame.Rect(WIDTH // 2 - 350, 180, 700, 350)
        pygame.draw.rect(self.screen, (32, 33, 36, 220), panel_rect, border_radius=15)
        pygame.draw.rect(self.screen, (95, 99, 104), panel_rect, width=2, border_radius=15)

        txt_placeholder = font_small.render("Conectando con base de datos PostgreSQL...", True, (200, 200, 200))
        self.screen.blit(txt_placeholder, txt_placeholder.get_rect(center=(WIDTH // 2, 350)))

        btn_width = 450
        btn_height = 70
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT - 120, btn_width, btn_height)

        self.draw_modern_button(btn_volver, "Volver al menu", font)

        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin
        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()
        self.menu_anterior = "MENU_SELECCION_SCORE"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_volver.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"

    def game_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "PAUSE_MENU"
                    return

        estado_juego = self.game.update(self.username ,self.network_socket)

        if estado_juego == "GAME_OVER":
            self.state = "GAME_OVER"
            return
        elif estado_juego == "LEVEL_UP":
            self.state = "LEVEL_UP"
            self.current_choices = random.sample(UPGRADES, min(3, len(UPGRADES)))

        self.game.draw(self.screen)

        if self.show_fps:
            self.draw_fps()

        pygame.display.flip()
        self.clock.tick(FPS)

    def pause_menu_loop(self):
        # Dibujamos el juego de fondo para que parezca congelado
        self.game.draw(self.screen)

        # Aplicamos una capa semitransparente
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", 50, bold=True)
        font_btn = pygame.font.SysFont("Arial", 40, bold=True)

        title = font_title.render("PAUSA", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        self.screen.blit(title, title_rect)

        btn_width = 450
        btn_height = 70
        btn_reanudar = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width, btn_height)
        btn_abandonar = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 60, btn_width, btn_height)

        self.draw_modern_button(btn_reanudar, "Reanudar", font_btn)
        self.draw_modern_button(btn_abandonar, "Abandonar partida", font_btn)

        # Boton de ajustes
        icon_size = 80
        margin = 20
        settings_x = WIDTH - icon_size - margin
        settings_y = margin + 50

        btn_settings = pygame.Rect(settings_x, settings_y, icon_size, icon_size)

        mouse_pos = pygame.mouse.get_pos()

        if btn_settings.collidepoint(mouse_pos):
            hover_surface = pygame.Surface((icon_size, icon_size - 20), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (60, 64, 67, 180), hover_surface.get_rect(), border_radius=10)
            self.screen.blit(hover_surface, (settings_x, settings_y))

        self.screen.blit(self.settings_icon, (settings_x, settings_y))

        pygame.display.flip()

        self.menu_anterior = "PAUSE_MENU"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()

            # Volver a jugar si pulsa ESC
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "PLAYING"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_reanudar.collidepoint(mouse_pos):
                    self.state = "PLAYING"
                elif btn_abandonar.collidepoint(mouse_pos):
                    # Mandamos al usuario a la selección de modo
                    self.state = "MENU_SELECCION_MODO"
                elif btn_settings.collidepoint(mouse_pos):
                    self.state = "MENU_SETTINGS"

    def game_over_loop(self):
        self.screen.blit(self.game_over_menu_bg, (0, 0))

        font = pygame.font.SysFont("Arial", 40, bold=True)

        btn_width = 450
        btn_height = 70
        btn_volver_menu = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 200, btn_width, btn_height)

        self.draw_modern_button(btn_volver_menu, "Volver al menu", font,
                                BAR_RED if 'BAR_RED' in globals() else (255, 0, 0))

        pygame.display.flip()

        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.state = "MENU_SELECCION_MODO"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_volver_menu.collidepoint(mouse_pos):
                    self.state = "MENU_SELECCION_MODO"

    def level_up_loop(self):
        self.game.draw(self.screen)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_desc = pygame.font.SysFont("Arial", 15)

        title = font_title.render("SUBIDA DE NIVEL!", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 100)))

        mouse_pos = pygame.mouse.get_pos()
        clicked = False

        # Bucle de eventos único para recoger el clic
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.network_socket:
                    self.network_socket.close()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        btn_width = 450
        btn_height = 70
        spacing = 30
        start_y = 200

        for i, upgrade in enumerate(self.current_choices):
            btn_rect = pygame.Rect(WIDTH // 2 - btn_width // 2, start_y + i * (btn_height + spacing), btn_width,
                                   btn_height)

            color = (70, 70, 70)
            if btn_rect.collidepoint(mouse_pos):
                color = (100, 100, 100)

                if clicked:
                    self.game.local_player.apply_upgrade(upgrade)
                    self.state = "PLAYING"
                    return

            pygame.draw.rect(self.screen, color, btn_rect, border_radius=10)
            pygame.draw.rect(self.screen, (155, 215, 0), btn_rect, 2, border_radius=10)

            name_txt = font_title.render(upgrade["name"], True, (255, 255, 255))
            desc_txt = font_desc.render(upgrade["desc"], True, (200, 200, 200))

            self.screen.blit(name_txt, (btn_rect.x + 20, btn_rect.y + 15))
            self.screen.blit(desc_txt, (btn_rect.x + 20, btn_rect.y + name_txt.get_height() + 15))

        pygame.display.flip()