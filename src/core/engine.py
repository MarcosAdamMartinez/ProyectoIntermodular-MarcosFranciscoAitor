import pygame
import sys
from src.utils.settings import *
from src.core.game import GameSession


class Engine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Python Survivors")
        self.clock = pygame.time.Clock()
        self.state = "MENU"

    def run(self):
        while True:
            if self.state == "MENU":
                self.menu_loop()
            elif self.state == "PLAYING":
                self.game_loop()

    def menu_loop(self):
        self.screen.fill(BLACK)
        font = pygame.font.SysFont("Arial", 40)
        title = font.render("Selecciona tu Personaje", True, WHITE)
        txt_knight = font.render("1. Caballero (Alta vida, Espada)", True, BLUE)
        txt_mage = font.render("2. Mago (Rápido, Varita Mágica)", True, (150, 0, 255))

        self.screen.blit(title, (WIDTH // 2 - 200, HEIGHT // 2 - 100))
        self.screen.blit(txt_knight, (WIDTH // 2 - 200, HEIGHT // 2))
        self.screen.blit(txt_mage, (WIDTH // 2 - 200, HEIGHT // 2 + 50))

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

        self.game.update()
        self.game.draw(self.screen)

        pygame.display.flip()
        self.clock.tick(FPS)