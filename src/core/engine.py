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
        font = pygame.font.SysFont("Arial", 40 ,bold=True)
        title = font.render("SELECCIONA TU PERSONAJE", True, WHITE)
        txt_knight = font.render("1 - Caballero SKILL: Mucha vida - ARMA: Espada", True, BLUE)
        txt_mage = font.render("2 - Mago SKILL: Rápido - ARMA: Varita Mágica", True, GREEN)

        self.screen.blit(title, (WIDTH // 2 - 300, HEIGHT // 2 - 100))
        self.screen.blit(txt_knight, (WIDTH // 2 - 450, HEIGHT // 2 + 20))
        self.screen.blit(txt_mage, (WIDTH // 2 - 450, HEIGHT // 2 + 80))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.game = GameSession(character_name="caballero", multiplayer=False)
                    self.state = "PLAYING"
                if event.key == pygame.K_2:
                    self.game = GameSession(character_name="mago", multiplayer=False)
                    self.state = "PLAYING"

    def game_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        juego_activo = self.game.update()

        if not juego_activo:
            self.state = "GAME_OVER"
            return

        self.game.draw(self.screen)

        pygame.display.flip()
        self.clock.tick(FPS)

    def game_over_loop(self):
        self.screen.fill(GREY)
        font_titulo = pygame.font.SysFont("Arial", 50)
        font_texto = pygame.font.SysFont("Arial", 40)

        title = font_titulo.render("GAME OVER", True, RED)
        txt_replay = font_texto.render("Pulse ESPACIO para volver a elegir personaje", True, RED)

        self.screen.blit(title, (WIDTH // 2 - 150, HEIGHT // 2 - 100))
        self.screen.blit(txt_replay, (WIDTH // 2 - 400, HEIGHT // 2))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.state = "MENU"