import random
import sys

import pygame

from src.utils.settings import *
from src.core.game import GameSession


class Engine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Python Survivors - Pre-Alpha")
        self.clock = pygame.time.Clock()
        self.state = "MENU_PRINCIPAL"
        self.current_choices = []

    def run(self):
        while True:
            if self.state == "MENU_PRINCIPAL":
                self.menu_principal_loop()
            elif self.state == "MENU_SELECCION_SOLO":
                self.menu_seleccion_solo()
            elif self.state == "MENU_SELECCION_MULTIPLAYER":
                self.menu_seleccion_multiplayer()
            elif self.state == "PLAYING":
                self.game_loop()
            elif self.state == "GAME_OVER":
                self.game_over_loop()
            elif self.state == "LEVEL_UP":
                self.level_up_loop()

    def menu_principal_loop(self):
        self.screen.fill(DARK_GREY)

        # Generamos la fuente y los textos que se van a mostrar
        font = pygame.font.SysFont("Arial", 40 ,bold=True)
        title = font.render("SELECCIONA UN MODO", True, WHITE)

        # Creamos un rectangulo para centrar el texto
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))

        # Dibuja una superficie encima de "screen" (mostramos los textos)
        self.screen.blit(title, title_rect)

        # Definir las dimensiones y posición de los botones (Rectángulos)
        btn_width = 450
        btn_height = 70
        btn_solo = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width, btn_height)
        btn_multiplayer = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 60, btn_width, btn_height)

        # Obtener la posición actual del ratón
        mouse_pos = pygame.mouse.get_pos()

        # Dibujar boton solo
        # Si el raton toca el boton, usamos un azul mas claro, si no, el azul normal
        color_k = (80, 80, 255) if btn_solo.collidepoint(mouse_pos) else BLUE

        # Redondeamos las esquinas
        pygame.draw.rect(self.screen, color_k, btn_solo, border_radius=15)

        # Borde blanco
        pygame.draw.rect(self.screen, WHITE, btn_solo, 3, border_radius=15)

        txt_solo = font.render("Un Jugador", True, WHITE)

        self.screen.blit(txt_solo, (btn_solo.centerx - txt_solo.get_width() // 2,
                                      btn_solo.centery - txt_solo.get_height() // 2))

        # Dibujar boton multiplayer
        # Si el raton toca el boton, usamos un morado mas claro, si no el normal
        color_m = (180, 50, 255) if btn_multiplayer.collidepoint(mouse_pos) else (150, 0, 255)
        pygame.draw.rect(self.screen, color_m, btn_multiplayer, border_radius=15)
        pygame.draw.rect(self.screen, WHITE, btn_multiplayer, 3, border_radius=15)

        txt_multijugador = font.render("Multijugador", True, WHITE)
        self.screen.blit(txt_multijugador,
                         (btn_multiplayer.centerx - txt_multijugador.get_width() // 2, btn_multiplayer.centery - txt_multijugador.get_height() // 2))

        pygame.display.flip()

        # Gestionamos los eventos
        for event in pygame.event.get():
            # Si el usuario cierra el juego
            if event.type == pygame.QUIT:
                pygame.quit()
                # Se termina el programa
                sys.exit()

            # Si el usuario hace clic con el raton
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 1 significa "Clic Izquierdo"

                    # Comprobamos qué boton estaba tocando el raton al hacer clic
                    if btn_solo.collidepoint(mouse_pos):
                        self.state = "MENU_SELECCION_SOLO"

                    elif btn_multiplayer.collidepoint(mouse_pos):
                        self.state = "MENU_SELECCION_MULTIPLAYER"

    def menu_seleccion_solo(self):
        self.screen.fill(DARK_GREY)

        font = pygame.font.SysFont("Arial", 40, bold=True)
        title = font.render("SELECCIONA TU PERSONAJE", True, WHITE)

        # Creamos un rectangulo para centrar el texto
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))

        # Dibuja una superficie encima de "screen" (mostramos el texto)
        self.screen.blit(title, title_rect)

        # Definimos las dimensiones y posicion de los botones
        btn_width = 500
        btn_height = 70
        btn_knight = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width, btn_height)
        btn_mage = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 60, btn_width, btn_height)
        btn_my_uncle = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 + 160, btn_width, btn_height)

        # Obtenemos la posicion actual del raton
        mouse_pos = pygame.mouse.get_pos()

        # Dibujamos el boton del caballero
        # Si el raton toca el boton, usamos un azul mas claro, si no el azul normal
        color_k = (80, 80, 255) if btn_knight.collidepoint(mouse_pos) else BLUE

        # Borde redondeado
        pygame.draw.rect(self.screen, color_k, btn_knight, border_radius=15)

        # Borde blanco
        pygame.draw.rect(self.screen, WHITE, btn_knight, 3, border_radius=15)

        # Creamos el texto para el boton del caballero
        txt_knight = font.render("Caballero (Alta vida)", True, WHITE)

        # Lo representamos en la "screen"
        self.screen.blit(txt_knight, (btn_knight.centerx - txt_knight.get_width() // 2,
                                      btn_knight.centery - txt_knight.get_height() // 2))

        # Dibujamos el boton del mago
        # Si el raton toca el boton, usamos un morado mas claro, si no el normal
        color_m = (180, 50, 255) if btn_mage.collidepoint(mouse_pos) else (150, 0, 255)

        # Borde redondeado
        pygame.draw.rect(self.screen, color_m, btn_mage, border_radius=15)

        # Borde blanco
        pygame.draw.rect(self.screen, WHITE, btn_mage, 3, border_radius=15)

        # Creamos el texto para el boton del mago
        txt_mage = font.render("Mago (Más rápido)", True, WHITE)

        # Lo representamos en la "screen"
        self.screen.blit(txt_mage,
                         (btn_mage.centerx - txt_mage.get_width() // 2, btn_mage.centery - txt_mage.get_height() // 2))

        # Dibujamos el boton de mi tio
        # Si el raton toca el boton, usamos un morado mas claro, si no el normal
        color_unc = (LIGHT_YELLOW) if btn_my_uncle.collidepoint(mouse_pos) else YELLOW

        # Borde redondeado
        pygame.draw.rect(self.screen, color_unc, btn_my_uncle, border_radius=15)

        # Borde blanco
        pygame.draw.rect(self.screen, WHITE, btn_my_uncle, 3, border_radius=15)

        # Creamos el texto para el boton de mi tio
        txt_my_uncle = font.render("Mi Tio (El Mas Primitivo)", True, BLACK)

        # Lo representamos en la "screen"
        self.screen.blit(txt_my_uncle,
                         (btn_my_uncle.centerx - txt_my_uncle.get_width() // 2, btn_my_uncle.centery - txt_my_uncle.get_height() // 2))

        # Mostramos todos los cambios en el "display"
        pygame.display.flip()

        # Gestionamos los eventos
        for event in pygame.event.get():
            # Si el usuario cierra el juego
            if event.type == pygame.QUIT:
                pygame.quit()
                # Se termina el programa
                sys.exit()

            # Si se hace clic con el raton
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # 1 = click izquierdo

                    # Comprobamos que boton estaba tocando el raton al hacer clic
                    if btn_knight.collidepoint(mouse_pos):
                        # Le pasamos una sesion de juego con el caballero como personaje seleccionado
                        self.game = GameSession(character_name="caballero", multiplayer=False)
                        self.state = "PLAYING"

                    elif btn_mage.collidepoint(mouse_pos):
                        # Le pasamos una sesion de juego con el mago como personaje seleccionado
                        self.game = GameSession(character_name="mago", multiplayer=False)
                        self.state = "PLAYING"

                    elif btn_my_uncle.collidepoint(mouse_pos):
                        # Le pasamos una sesion de juego con el mago como personaje seleccionado
                        self.game = GameSession(character_name="my_uncle", multiplayer=False)
                        self.state = "PLAYING"

    def menu_seleccion_multiplayer(self):
        # Ponemos un color de fondo
        self.screen.fill(DARK_GREY)

        # Creamos la fuente y el texto
        font = pygame.font.SysFont("Arial", 40, bold=True)
        texto_provisional = font.render("ESTAMOS TRABAJANDO EN ELLO", True, WHITE)

        # Creamos un rectangulo para centrar el texto
        texto_rect = texto_provisional.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))

        # Dibuja una superficie encima de "screen" (mostramos los textos)
        self.screen.blit(texto_provisional, texto_rect)


        # Definimos las dimensiones y posicion de los botones
        btn_width = 450
        btn_height = 70
        btn_volver = pygame.Rect(WIDTH // 2 - btn_width // 2, HEIGHT // 2 - 40, btn_width + 30, btn_height)

        # Creamos el texto para el boton de vuelta al menu principal
        txt_volver = font.render("Volver al menu principal", True, WHITE)

        # Obtenemos la posicion actual del raton
        mouse_pos = pygame.mouse.get_pos()

        # Dibujamos el boton de vuelta
        # Si el raton toca el boton, usamos un morado mas claro, si no el normal
        color_m = (180, 50, 255) if btn_volver.collidepoint(mouse_pos) else (150, 0, 255)

        # Borde redondeado
        pygame.draw.rect(self.screen, color_m, btn_volver, border_radius=15)

        # Borde blanco
        pygame.draw.rect(self.screen, WHITE, btn_volver, 3, border_radius=15)

        # Lo representamos en la "screen"
        self.screen.blit(txt_volver,
                         (btn_volver.centerx - txt_volver.get_width() // 2, btn_volver.centery - txt_volver.get_height() // 2))

        # Mostramos todos los cambios en el "display"
        pygame.display.flip()

        # Gestionamos los eventos
        for event in pygame.event.get():
            # Si el usuario cierra el juego
            if event.type == pygame.QUIT:
                pygame.quit()
                # Se termina el programa
                sys.exit()

            # Si el usuario hace clic con el ratón...
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:

                    if btn_volver.collidepoint(mouse_pos):
                        self.state = "MENU_PRINCIPAL"

    def game_loop(self):
        # Si cerramos la ventana se termina la ejecucion
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        estado_juego = self.game.update()

        if estado_juego == "GAME_OVER":
            self.state = "GAME_OVER"
            return
        elif estado_juego == "LEVEL_UP":
            self.state = "LEVEL_UP"
            self.current_choices = random.sample(UPGRADES, min(3, len(UPGRADES)))

        # Dibujamos el nuevo estado con los movimientos en pantalla
        self.game.draw(self.screen)

        # Actualizamos el display
        pygame.display.flip()

        self.clock.tick(FPS)

    def game_over_loop(self):
        # Cambiamos el color del fondo y creamos las fuentes que vamos a usar en los textos
        self.screen.fill(DARK_GREY)

        font_titulo = pygame.font.SysFont("Arial", 50)
        font_texto = pygame.font.SysFont("Arial", 40)

        # Creamos los textos que vamos a mostrar
        title = font_titulo.render("GAME OVER", True, RED)
        txt_replay = font_texto.render("Pulse ESPACIO para volver a elegir personaje", True, RED)

        # Dibujamos sobre la "screen" los textos
        self.screen.blit(title, (WIDTH // 2 - 150, HEIGHT // 2 - 100))
        self.screen.blit(txt_replay, (WIDTH // 2 - 400, HEIGHT // 2))

        # Actualizamos el ontenido del display
        pygame.display.flip()

        # Comprobamos si se cumplen o no las siguientes condiciones:
        for event in pygame.event.get():
            # Si se cierra el juego se termina el proceso
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Si se presiona una tecla:
            if event.type == pygame.KEYDOWN:
                # Si la tecla es el espacio:
                if event.key == pygame.K_SPACE:
                    # Cambia el estado a MENU
                    self.state = "MENU_PRINCIPAL"

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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        btn_width = 450
        btn_height = 70
        spacing = 30
        start_y = 200

        for i, upgrade in enumerate(self.current_choices):
            btn_rect = pygame.Rect(WIDTH // 2 - btn_width // 2, start_y + i * (btn_height + spacing), btn_width, btn_height)

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
