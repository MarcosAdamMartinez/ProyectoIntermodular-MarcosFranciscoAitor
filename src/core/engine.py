import pygame
import sys
from src.utils.settings import *
from src.core.game import GameSession


class Engine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Python Survivors - DEMO")
        self.clock = pygame.time.Clock()
        self.state = "MENU"

    def run(self):
        while True:
            if self.state == "MENU":
                self.menu_loop()
            elif self.state == "PLAYING":
                self.game_loop()
            elif self.state == "GAME_OVER":
                self.game_over_loop()

    def menu_loop(self):
        self.screen.fill(DARK_GREY)

        # Generamos la fuente y los textos que se van a mostrar
        font = pygame.font.SysFont("Arial", 40 ,bold=True)

        title = font.render("SELECCIONA TU PERSONAJE", True, WHITE)
        txt_knight = font.render("1 - Caballero SKILL: Mucha vida - ARMA: Espada", True, BLUE)
        txt_mage = font.render("2 - Mago SKILL: Rápido - ARMA: Varita Mágica", True, GREEN)

        # Dibuja una superficie encima de "screen" (mostramos los textos)
        self.screen.blit(title, (WIDTH // 2 - 300, HEIGHT // 2 - 100))
        self.screen.blit(txt_knight, (WIDTH // 2 - 450, HEIGHT // 2 + 20))
        self.screen.blit(txt_mage, (WIDTH // 2 - 450, HEIGHT // 2 + 80))

        # Actualiza el display
        pygame.display.flip()

        # Comprobamos si las condiciones se han o no cumplido
        for event in pygame.event.get():
            # Si cerramos la ventana se termina la ejecucion
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Si presionamos una tecla:
            if event.type == pygame.KEYDOWN:
                # Si es "1" se escoge como personaje al caballero
                if event.key == pygame.K_1:
                    self.game = GameSession(character_name="caballero", multiplayer=False) # multiplayer por ahora no se toca porque la demo la hemos planteado sin mutijugador

                    # Cambiamos el estado a "PLAYING"
                    self.state = "PLAYING"

                # Si es "2" se escoge al mago
                if event.key == pygame.K_2:
                    self.game = GameSession(character_name="mago", multiplayer=False)

                    # Cambiamos el estado a "PLAYING"
                    self.state = "PLAYING"

    def game_loop(self):
        # Si cerramos la ventana se termina la ejecucion
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Obtenemos el estado del juego (True o False)
        juego_activo = self.game.update()

        # Si es False, pasamos al estado de GAME_OVER
        if not juego_activo:
            self.state = "GAME_OVER"
            return

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
                    self.state = "MENU"