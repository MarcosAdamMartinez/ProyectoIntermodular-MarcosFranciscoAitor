import pygame
import random
from src.utils.settings import load_sprite


class Rock(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Elegimos aleatoriamente uno de los 3 sprites de roca
        rock_variant = random.randint(1, 3)

        # Tamaño aleatorio para variedad visual (un poco más grandes que los arbustos)
        size = random.randint(65, 115)
        w = size
        h = int(size * 0.75)  # Las rocas suelen ser más anchas que altas

        # Color de fallback distinto por variante si no existe el sprite
        fallback_colors = {
            1: (120, 110, 100),  # Gris cálido
            2: (90,  90,  95),   # Gris azulado
            3: (100, 85,  75),   # Gris marrón
        }

        self.image = load_sprite(
            f"assets/sprites/objects/rock{rock_variant}.png",
            (w, h),
            fallback_colors[rock_variant]
        )

        # --- COLISIÓN AJUSTADA A LA IMAGEN ---
        # hit_rect es un rectángulo reducido (60% ancho, 55% alto) centrado
        # en la parte inferior de la imagen, donde está la "base" visual de la roca.
        # Esto evita la barrera invisible en los bordes superiores y laterales.
        hx = int(w * 0.60)
        hy = int(h * 0.55)
        self.hit_rect = pygame.Rect(0, 0, hx, hy)
        self.hit_rect.center = (int(pos[0]), int(pos[1]) + h // 6)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)