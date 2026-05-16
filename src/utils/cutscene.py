# Importamos lo necesario para las cinemáticas: os para rutas, math para efectos y pygame
import os
import math
import pygame
from src.utils.settings import WHITE, BTN_BG, BTN_HOVER, BTN_BORDER, BTN_SHADOW

# Textos de cada cinemática organizados por carpeta; se pueden editar aquí fácilmente
STORY_TEXTS = {
    "inicio": [
        "En los tiempos del Antiguo Pacto, la tierra de Eldrath\n"
        "fue bendecida por los dioses con paz eterna...",

        "Pero la codicia de los hombres despertó a las Sombras,\n"
        "criaturas sin nombre que corroen la realidad.",

        "Solo un héroe, el último elegido,\n"
        "puede cerrar las Puertas del Abismo y salvar cuanto existe.",
    ],

    "mundo_1": [
        "El Valle Verdealma.\n"
        "Antaño hogar de druidas y bestias nobles,\n"
        "ahora invadido por criaturas corrompidas.",
    ],

    "mundo_2": [
        "El Yermo de Skjorn te aguarda.\n"
        "Un viento que congela el alma sopla sin cesar\n"
        "desde las cumbres donde mora el Yeti.",
    ],

    "mundo_3": [
        "Las Fauces de Infernia.\n"
        "La tierra misma sangra lava y los cielos\n"
        "arden en un eterno crepúsculo escarlata.",

        "El Minotauro aguarda en el corazón del abismo.\n"
        "Derrotarlo es la única forma de sellar\n"
        "la última puerta y devolver la luz al mundo.",
    ],

    "final": [
        "La última puerta se cierra.\n"
        "El rugido del Minotauro se apaga para siempre\n"
        "y la oscuridad retrocede.",

        "La tierra de Eldrath respira de nuevo.\n"
        "Los supervivientes alzarán monumentos\n"
        "en honor al héroe que nunca buscarán.",
    ],
}


def load_slide_images(folder_key: str) -> list:
    # Cargamos todas las imágenes de la carpeta del episodio ordenadas alfabéticamente
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


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
    # Dividimos el texto en líneas respetando los saltos \n y el ancho máximo del recuadro
    lines_out = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                # La palabra no cabe en la línea actual; guardamos la línea y empezamos una nueva
                if current:
                    lines_out.append(current)
                current = word
        lines_out.append(current)
    return lines_out


# Muestra el logo del juego durante 3 segundos con fade-in y fade-out y llama on_done() al terminar
class LogoSplash:
    TOTAL_MS   = 3000
    FADEIN_MS  = 600
    FADEOUT_MS = 600

    def __init__(self, screen: pygame.Surface, on_done):
        self.screen  = screen
        self.on_done = on_done
        # Guardamos el momento de inicio para calcular el tiempo transcurrido
        self.start   = pygame.time.get_ticks()

        W, H = screen.get_size()
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            try:
                raw = pygame.image.load(logo_path).convert_alpha()
                # Escalamos el logo para que ocupe como máximo el 60% de la pantalla
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

        self.font = pygame.font.SysFont("Arial", max(28, int(H * 0.05)), bold=True)

    def update_and_draw(self) -> bool:
        # Dibujamos un frame del splash; devolvemos True cuando ha terminado
        now     = pygame.time.get_ticks()
        elapsed = now - self.start

        if elapsed >= self.TOTAL_MS:
            self.on_done()
            return True

        # Calculamos el alpha: sube en el fade-in, se mantiene y baja en el fade-out
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
            # Si no hay logo mostramos el título del juego en texto
            surf = self.font.render("PUNTERNOWS SALVATION", True, WHITE)
            surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(W // 2, H // 2)))

        pygame.display.flip()
        return False

    def handle_event(self, event):
        # Permitimos saltar el splash con ESPACIO, ENTER o clic del ratón
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            if event.type == pygame.KEYDOWN and event.key not in (
                    pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                return
            self.on_done()


# Secuencia de slides (imagen + texto) con botones de navegación ◄ y ►
class StorySequence:
    # Estilo visual del recuadro de texto sobre la imagen
    TEXT_ALPHA      = 140
    TEXT_PAD_X      = 40
    TEXT_PAD_Y      = 22
    TEXT_MAX_WIDTH  = 0.70

    def __init__(self, screen: pygame.Surface, folder_key: str, on_done,
                 sx=None, sy=None, sf=None):
        self.screen     = screen
        self.folder_key = folder_key
        self.on_done    = on_done
        # Funciones de escala opcionales para resoluciones dinámicas
        self.sx = sx or (lambda x: x)
        self.sy = sy or (lambda y: y)
        self.sf = sf or (lambda s: s)

        self.images = load_slide_images(folder_key)
        self.texts  = STORY_TEXTS.get(folder_key, [])
        self.index  = 0

        # Si no hay imágenes generamos slides vacíos con solo texto sobre fondo negro
        n = max(len(self.images), len(self.texts), 1)
        self.total = n

        self.build_fonts()
        self.build_buttons()

    def build_fonts(self):
        # Creamos las fuentes escaladas a la resolución actual de pantalla
        W, H = self.screen.get_size()
        self.font_text = pygame.font.SysFont(
            "Arial", max(16, int(H * 0.028)), bold=False)
        self.font_counter = pygame.font.SysFont(
            "Arial", max(13, int(H * 0.020)), bold=True)
        self.font_hint = pygame.font.SysFont(
            "Arial", max(12, int(H * 0.018)), bold=False)

    def build_buttons(self):
        # Calculamos la posición y tamaño de los botones ◄ y ► según la pantalla
        W, H = self.screen.get_size()
        bw = max(60, int(W * 0.06))
        bh = max(50, int(H * 0.08))
        margin = max(20, int(W * 0.025))
        cy = H - bh - margin

        self.btn_prev = pygame.Rect(margin,        cy, bw, bh)
        self.btn_next = pygame.Rect(W - bw - margin, cy, bw, bh)

    def draw_background(self):
        # Dibujamos la imagen del slide actual escalada a pantalla completa, o fondo negro
        W, H = self.screen.get_size()
        if self.index < len(self.images):
            img = self.images[self.index]
            scaled = pygame.transform.smoothscale(img, (W, H))
            self.screen.blit(scaled, (0, 0))
        else:
            self.screen.fill((10, 10, 15))

    def draw_text_box(self):
        # Dibujamos el recuadro de texto translúcido con el texto del slide actual
        if self.index >= len(self.texts):
            return
        text = self.texts[self.index]
        if not text.strip():
            return

        W, H = self.screen.get_size()
        max_w = int(W * self.TEXT_MAX_WIDTH)
        lines = wrap_text(text, self.font_text, max_w - self.TEXT_PAD_X * 2)

        line_h   = self.font_text.get_linesize()
        box_w    = max_w
        box_h    = len(lines) * line_h + self.TEXT_PAD_Y * 2
        box_x    = (W - box_w) // 2
        # Posicionamos el recuadro cerca de la parte inferior de la pantalla
        box_y    = int(H * 0.91) - box_h // 2

        # Fondo negro semitransparente para que el texto contraste con la imagen
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, self.TEXT_ALPHA))
        self.screen.blit(bg, (box_x, box_y))

        # Borde sutil alrededor del recuadro
        pygame.draw.rect(self.screen, (80, 80, 90, 180),
                         pygame.Rect(box_x, box_y, box_w, box_h), 1, border_radius=6)

        # Dibujamos las líneas de texto una por una
        text_x = box_x + self.TEXT_PAD_X
        text_y = box_y + self.TEXT_PAD_Y
        for line in lines:
            surf = self.font_text.render(line, True, (230, 230, 230))
            self.screen.blit(surf, (text_x, text_y))
            text_y += line_h

    def draw_counter(self):
        # Mostramos el número de slide actual y el total en la parte inferior central
        W, H = self.screen.get_size()
        txt = f"{self.index + 1} / {self.total}"
        surf = self.font_counter.render(txt, True, (200, 200, 200))
        self.screen.blit(surf, surf.get_rect(center=(W // 2, H - self.sy(25))))

    def draw_nav_button(self, rect, label, enabled=True):
        # Dibujamos un botón de navegación con efecto hover y sombra
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

        font = self.font_counter
        sym  = font.render(label, True, text_color)
        self.screen.blit(sym, sym.get_rect(center=rect.center))

    def draw_skip_hint(self):
        # Mostramos un aviso pequeño en la esquina superior derecha para saltar la historia
        W, H = self.screen.get_size()
        hint = "Presiona ENTER para saltar la historia"
        surf = self.font_hint.render(hint, True, (200, 200, 200))
        pad_x, pad_y = 10, 6
        margin = max(12, int(W * 0.012))
        box_w = surf.get_width() + pad_x * 2
        box_h = surf.get_height() + pad_y * 2
        box_x = W - box_w - margin
        box_y = margin
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (box_x, box_y))
        self.screen.blit(surf, (box_x + pad_x, box_y + pad_y))

    def draw_next_label(self):
        # En el último slide mostramos un símbolo doble para indicar que es el final
        W, H = self.screen.get_size()
        is_last = (self.index >= self.total - 1)
        label = "►►" if is_last else "►"
        return label

    def update_and_draw(self) -> bool:
        # Dibujamos un frame completo de la secuencia; devolvemos True si ha terminado
        self.draw_background()
        self.draw_text_box()
        self.draw_counter()
        self.draw_skip_hint()

        has_prev = self.index > 0
        self.draw_nav_button(self.btn_prev, "◄", enabled=has_prev)
        self.draw_nav_button(self.btn_next, self.draw_next_label(), enabled=True)

        pygame.display.flip()
        return False

    def handle_event(self, event) -> bool:
        # Procesamos los clics en los botones y la tecla ENTER para saltar todo de golpe
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.on_done()
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        mouse_pos = pygame.mouse.get_pos()

        if self.btn_prev.collidepoint(mouse_pos) and self.index > 0:
            self.index -= 1
            return False

        if self.btn_next.collidepoint(mouse_pos):
            if self.index >= self.total - 1:
                # Último slide: llamamos a on_done para continuar al juego
                self.on_done()
                return True
            else:
                self.index += 1
                return False

        return False

    def resize(self):
        # Reconstruimos fuentes y botones si cambia la resolución en caliente
        self.build_fonts()
        self.build_buttons()