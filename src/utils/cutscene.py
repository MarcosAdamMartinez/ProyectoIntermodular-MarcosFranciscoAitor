"""
cutscene.py — Sistema de cinemáticas para Punternows Salvation

Maneja:
  - Splash de logo (3 s con fade-in/fade-out)
  - Secuencias de imágenes con texto translúcido (historia, intro de mundo, final)
  - Navegación con botones ◄ ► ; al llegar al final ejecuta un callback

Rutas de imágenes (la carpeta determina el número de slides):
    assets/historia/inicio/     → pantalla de título / historia global
    assets/historia/mundo_1/    → intro al empezar mundo 1
    assets/historia/mundo_2/    → intro al entrar en mundo 2
    assets/historia/mundo_3/    → intro al entrar en mundo 3
    assets/historia/final/      → tras derrotar al boss final

Textos (editar aquí fácilmente):
    STORY_TEXTS  → dict  {carpeta: [texto_slide_0, texto_slide_1, ...]}
    Si hay más imágenes que textos, los slides sobrantes aparecen sin texto.
    Si hay más textos que imágenes, los textos sobrantes se ignoran.
"""

import os
import math
import pygame
from src.utils.settings import WHITE, BTN_BG, BTN_HOVER, BTN_BORDER, BTN_SHADOW

# ─────────────────────────────────────────────────────────────────────────────
#  TEXTOS DE LAS CINEMÁTICAS  (modifica libremente)
# ─────────────────────────────────────────────────────────────────────────────

STORY_TEXTS = {
    # ── Historia inicial (pantalla de título) ─────────────────────────────────
    "inicio": [
        "En los tiempos del Antiguo Pacto, la tierra de Eldrath\n"
        "fue bendecida por los dioses con paz eterna...",

        "Pero la codicia de los hombres despertó a las Sombras,\n"
        "criaturas sin nombre que corroen la realidad.",

        "Solo un héroe, el último elegido,\n"
        "puede cerrar las Puertas del Abismo y salvar cuanto existe.",
    ],

    # ── Introducción al Mundo 1 ───────────────────────────────────────────────
    "mundo_1": [
        "El Valle Verdealma.\n"
        "Antaño hogar de druidas y bestias nobles,\n"
        "ahora invadido por criaturas corrompidas.",

        "Las aldeas que quedaban han sido evacuadas.\n"
        "Solo el héroe se adentra en la espesura,\n"
        "buscando el altar que convoca al guardián caído.",
    ],

    # ── Introducción al Mundo 2 ───────────────────────────────────────────────
    "mundo_2": [
        "El Yermo de Skjorn te aguarda.\n"
        "Un viento que congela el alma sopla sin cesar\n"
        "desde las cumbres donde mora el Yeti.",

        "El frío no es tu mayor enemigo aquí.\n"
        "Los espíritus del hielo tienen memoria,\n"
        "y recuerdan a quienes los despiertan.",
    ],

    # ── Introducción al Mundo 3 ───────────────────────────────────────────────
    "mundo_3": [
        "Las Fauces de Infernia.\n"
        "La tierra misma sangra lava y los cielos\n"
        "arden en un eterno crepúsculo escarlata.",

        "El Minotauro aguarda en el corazón del abismo.\n"
        "Derrotarlo es la única forma de sellar\n"
        "la última puerta y devolver la luz al mundo.",
    ],

    # ── Cinemática final ──────────────────────────────────────────────────────
    "final": [
        "La última puerta se cierra.\n"
        "El rugido del Minotauro se apaga para siempre\n"
        "y la oscuridad retrocede.",

        "La tierra de Eldrath respira de nuevo.\n"
        "Los supervivientes alzarán monumentos\n"
        "en honor al héroe que nunca buscarán.",

        "Pero el héroe ya camina hacia el horizonte,\n"
        "sabiendo que la paz es frágil\n"
        "y el abismo, paciente.",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_slide_images(folder_key: str) -> list:
    """
    Carga todas las imágenes PNG/JPG de assets/historia/<folder_key>/
    ordenadas alfabéticamente.  Devuelve lista de pygame.Surface (o vacía).
    """
    base = os.path.join("assets", "historia", folder_key)
    if not os.path.isdir(base):
        return []

    exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
    files = sorted(
        f for f in os.listdir(base)
        if os.path.splitext(f)[1].lower() in exts
    )

    surfaces = []
    for fname in files:
        path = os.path.join(base, fname)
        try:
            img = pygame.image.load(path).convert()
            surfaces.append(img)
        except Exception as e:
            print(f"[cutscene] No se pudo cargar '{path}': {e}")
    return surfaces


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
    """
    Envuelve texto a múltiples líneas respetando '\n' y el ancho máximo.
    Devuelve lista de strings lista para renderizar.
    """
    lines_out = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines_out.append(current)
                current = word
        lines_out.append(current)
    return lines_out


# ─────────────────────────────────────────────────────────────────────────────
#  CLASE LOGO SPLASH
# ─────────────────────────────────────────────────────────────────────────────

class LogoSplash:
    """
    Muestra el logo en assets/logo.png (o fallback de texto) durante 3 segundos
    con fade-in y fade-out.  Llama a on_done() al terminar.
    """
    TOTAL_MS   = 3000
    FADEIN_MS  = 600
    FADEOUT_MS = 600

    def __init__(self, screen: pygame.Surface, on_done):
        self.screen  = screen
        self.on_done = on_done
        self.start   = pygame.time.get_ticks()

        W, H = screen.get_size()
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            try:
                raw = pygame.image.load(logo_path).convert_alpha()
                # Escalar para que quepa en 60 % de pantalla manteniendo ratio
                max_w = int(W * 0.6)
                max_h = int(H * 0.6)
                rw, rh = raw.get_size()
                scale  = min(max_w / rw, max_h / rh, 1.0)
                self.logo = pygame.transform.smoothscale(
                    raw, (int(rw * scale), int(rh * scale)))
            except:
                self.logo = None
        else:
            self.logo = None

        self._font = pygame.font.SysFont("Arial", max(28, int(H * 0.05)), bold=True)

    def update_and_draw(self) -> bool:
        """Dibuja un frame. Devuelve True si ha terminado."""
        now     = pygame.time.get_ticks()
        elapsed = now - self.start

        if elapsed >= self.TOTAL_MS:
            self.on_done()
            return True

        # Calcular alpha
        if elapsed < self.FADEIN_MS:
            alpha = int(255 * elapsed / self.FADEIN_MS)
        elif elapsed > self.TOTAL_MS - self.FADEOUT_MS:
            remaining = self.TOTAL_MS - elapsed
            alpha = int(255 * remaining / self.FADEOUT_MS)
        else:
            alpha = 255

        W, H = self.screen.get_size()
        self.screen.fill((0, 0, 0))

        if self.logo:
            logo_copy = self.logo.copy()
            logo_copy.set_alpha(alpha)
            rect = logo_copy.get_rect(center=(W // 2, H // 2))
            self.screen.blit(logo_copy, rect)
        else:
            surf = self._font.render("PUNTERNOWS SALVATION", True, WHITE)
            surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

        pygame.display.flip()
        return False

    def handle_event(self, event):
        """Permite saltar el splash con ESPACIO, ENTER o clic."""
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            if event.type == pygame.KEYDOWN and event.key not in (
                    pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                return
            self.on_done()


# ─────────────────────────────────────────────────────────────────────────────
#  CLASE SECUENCIA DE SLIDES
# ─────────────────────────────────────────────────────────────────────────────

class StorySequence:
    """
    Secuencia de N slides (imagen + texto translúcido).
    Navegación con botones ◄ / ►.
    Al pasar el último slide ejecuta on_done().

    Parámetros
    ----------
    screen      : superficie de dibujo
    folder_key  : clave de STORY_TEXTS y nombre de subcarpeta en assets/historia/
    on_done     : callable sin argumentos que se invoca al finalizar
    sx / sy / sf: funciones de escala del Engine (para resoluciones dinámicas)
    """

    # Estilo del cuadro de texto
    TEXT_ALPHA      = 140    # alpha del fondo negro del recuadro (0-255)
    TEXT_PAD_X      = 40     # padding horizontal interior del recuadro
    TEXT_PAD_Y      = 22     # padding vertical interior del recuadro
    TEXT_MAX_WIDTH  = 0.70   # fracción del ancho de pantalla para el recuadro

    def __init__(self, screen: pygame.Surface, folder_key: str, on_done,
                 sx=None, sy=None, sf=None):
        self.screen     = screen
        self.folder_key = folder_key
        self.on_done    = on_done
        self._sx = sx or (lambda x: x)
        self._sy = sy or (lambda y: y)
        self._sf = sf or (lambda s: s)

        self.images = _load_slide_images(folder_key)
        self.texts  = STORY_TEXTS.get(folder_key, [])
        self.index  = 0

        # Si no hay imágenes generamos slides vacíos (fondo negro) con solo texto
        n = max(len(self.images), len(self.texts), 1)
        self._total = n

        self._build_fonts()
        self._build_buttons()

    # ── setup ──────────────────────────────────────────────────────────────── #

    def _build_fonts(self):
        W, H = self.screen.get_size()
        self._font_text = pygame.font.SysFont(
            "Arial", max(16, int(H * 0.028)), bold=False)
        self._font_counter = pygame.font.SysFont(
            "Arial", max(13, int(H * 0.020)), bold=True)

    def _build_buttons(self):
        W, H = self.screen.get_size()
        bw = max(60, int(W * 0.06))
        bh = max(50, int(H * 0.08))
        margin = max(20, int(W * 0.025))
        cy = H - bh - margin

        self._btn_prev = pygame.Rect(margin,        cy, bw, bh)
        self._btn_next = pygame.Rect(W - bw - margin, cy, bw, bh)

    # ── rendering ─────────────────────────────────────────────────────────── #

    def _draw_background(self):
        W, H = self.screen.get_size()
        if self.index < len(self.images):
            img = self.images[self.index]
            scaled = pygame.transform.smoothscale(img, (W, H))
            self.screen.blit(scaled, (0, 0))
        else:
            self.screen.fill((10, 10, 15))

    def _draw_text_box(self):
        if self.index >= len(self.texts):
            return
        text = self.texts[self.index]
        if not text.strip():
            return

        W, H = self.screen.get_size()
        max_w = int(W * self.TEXT_MAX_WIDTH)
        lines = _wrap_text(text, self._font_text, max_w - self.TEXT_PAD_X * 2)

        line_h   = self._font_text.get_linesize()
        box_w    = max_w
        box_h    = len(lines) * line_h + self.TEXT_PAD_Y * 2
        box_x    = (W - box_w) // 2
        box_y    = int(H * 0.68) - box_h // 2   # posición vertical ~68 %

        # Fondo translúcido
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, self.TEXT_ALPHA))
        self.screen.blit(bg, (box_x, box_y))

        # Borde sutil
        pygame.draw.rect(self.screen, (80, 80, 90, 180),
                         pygame.Rect(box_x, box_y, box_w, box_h), 1, border_radius=6)

        # Texto
        text_x = box_x + self.TEXT_PAD_X
        text_y = box_y + self.TEXT_PAD_Y
        for line in lines:
            surf = self._font_text.render(line, True, (230, 230, 230))
            self.screen.blit(surf, (text_x, text_y))
            text_y += line_h

    def _draw_counter(self):
        W, H = self.screen.get_size()
        txt = f"{self.index + 1} / {self._total}"
        surf = self._font_counter.render(txt, True, (200, 200, 200))
        self.screen.blit(surf, surf.get_rect(center=(W // 2, H - self._sy(30))))

    def _draw_nav_button(self, rect, label, enabled=True):
        mouse_pos = pygame.mouse.get_pos()
        if not enabled:
            color = (40, 40, 45)
            text_color = (80, 80, 90)
        else:
            color = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_BG
            text_color = WHITE

        shadow = rect.move(0, 3)
        pygame.draw.rect(self.screen, BTN_SHADOW, shadow, border_radius=10)
        pygame.draw.rect(self.screen, color,      rect,   border_radius=10)
        pygame.draw.rect(self.screen, BTN_BORDER, rect, 2, border_radius=10)

        font = self._font_counter
        sym  = font.render(label, True, text_color)
        self.screen.blit(sym, sym.get_rect(center=rect.center))

    def _draw_next_label(self):
        """Cuando es el último slide el botón ► muestra una etiqueta especial."""
        W, H = self.screen.get_size()
        is_last = (self.index >= self._total - 1)
        label = "►►" if is_last else "►"
        return label

    # ── public interface ───────────────────────────────────────────────────── #

    def update_and_draw(self) -> bool:
        """Dibuja un frame. Devuelve True si la secuencia ha terminado."""
        self._draw_background()
        self._draw_text_box()
        self._draw_counter()

        has_prev = self.index > 0
        self._draw_nav_button(self._btn_prev, "◄", enabled=has_prev)
        self._draw_nav_button(self._btn_next, self._draw_next_label(), enabled=True)

        pygame.display.flip()
        return False

    def handle_event(self, event) -> bool:
        """
        Procesa eventos de navegación.
        Devuelve True si la secuencia debe terminar (y ha llamado a on_done).
        """
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        mouse_pos = pygame.mouse.get_pos()

        if self._btn_prev.collidepoint(mouse_pos) and self.index > 0:
            self.index -= 1
            return False

        if self._btn_next.collidepoint(mouse_pos):
            if self.index >= self._total - 1:
                self.on_done()
                return True
            else:
                self.index += 1
                return False

        return False

    def resize(self):
        """Llamar si cambia la resolución de pantalla."""
        self._build_fonts()
        self._build_buttons()