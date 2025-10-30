import pygame
import os
import sys
import threading
import pickle
import time
from network import NetworkManager


class Button:
    def __init__(
        self,
        image,
        pos,
        text_input,
        font,
        text_color,
        bg_color,
        hovering_color,
        size=(200, 60),
        scale_factor=1.1,
    ):
        self.image = image
        self.original_image = image
        self.x_pos = pos[0]
        self.y_pos = pos[1]
        self.font = font
        self.bg_color = bg_color
        self.text_color = text_color
        self.hovering_color = hovering_color
        self.text_input = text_input
        self.base_size = size
        self.scale_factor = scale_factor
        self.current_size = list(size)
        self.is_hovering = False

        if self.image is None:
            self.image = self.create_button_surface(self.base_size, self.bg_color)
            self.original_image = self.image

        self.text = self.font.render(self.text_input, False, self.text_color)

        if self.image is not None:
            self.image = pygame.transform.scale(self.original_image, self.current_size)
            self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        else:
            self.rect = pygame.Rect(0, 0, *self.current_size)
            self.rect.center = (self.x_pos, self.y_pos)

        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def create_button_surface(self, size, color):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, size[0], size[1])
        pygame.draw.rect(surface, color, rect, border_radius=12)
        pygame.draw.rect(surface, self.hovering_color, rect, 2, border_radius=12)
        return surface

    def update(self, screen):
        target_size = [
            int(self.base_size[0] * (self.scale_factor if self.is_hovering else 1)),
            int(self.base_size[1] * (self.scale_factor if self.is_hovering else 1)),
        ]

        for i in range(2):
            if abs(self.current_size[i] - target_size[i]) > 1:
                self.current_size[i] += (target_size[i] - self.current_size[i]) * 0.2
            else:
                self.current_size[i] = target_size[i]

        if self.image is not None:
            scaled_image = pygame.transform.scale(
                self.original_image, [int(x) for x in self.current_size]
            )
            scaled_rect = scaled_image.get_rect(center=(self.x_pos, self.y_pos))
            screen.blit(scaled_image, scaled_rect)
            self.rect = scaled_rect
        else:
            self.rect.size = (int(self.current_size[0]), int(self.current_size[1]))
            self.rect.center = (self.x_pos, self.y_pos)

        self.text_rect = self.text.get_rect(center=self.rect.center)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        return self.rect.collidepoint(position)

    def changeColor(self, position):
        if self.rect.collidepoint(position):
            if self.original_image is None:
                self.image = self.create_button_surface(
                    self.current_size, self.hovering_color
                )
        else:
            if self.original_image is None:
                self.image = self.create_button_surface(
                    self.current_size, self.bg_color
                )

    def check_hover(self, position):
        was_hovering = self.is_hovering
        self.is_hovering = self.rect.collidepoint(position)
        if was_hovering != self.is_hovering:
            self.changeColor(position)


class InputBox:
    def __init__(self, x, y, w, h, font, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color("#e35d59")
        self.color_active = pygame.Color("#F9AA33")
        self.color = self.color_inactive
        self.text = text
        self.font = font
        self.txt_surface = font.render(text, True, pygame.Color("#000000"))
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    print(self.text)
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = self.font.render(
                    self.text, True, pygame.Color("#000000")
                )

    def update(self):
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        pygame.draw.rect(screen, pygame.Color("#FFFFFF"), self.rect, border_radius=8)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=8)
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))


class UIManager:
    def __init__(self, screen_width, screen_height, network_manager):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.network_manager = network_manager
        self.SCREEN = pygame.display.set_mode(
            (self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption("Menu Principal")

        self.load_assets()
        self.current_screen = "main"
        self.clock = pygame.time.Clock()
        self.last_time = pygame.time.get_ticks()
        self.init_components()

        self.servers = []
        self.selectedServer = None
        self.isSeletedServer = False
        self.response = None
        self.is_hovered = None
        self.messages = []
        self.chatLock = threading.Lock()
        self.playGamePlayer = False

        self.wrong_password_until = 0
        self.fullserver_until = 0
        self.no_server_until = 0

        click_path = os.path.join("assets", "sonido", "click.wav")
        self.click_sound = pygame.mixer.Sound(click_path)

    def load_assets(self):
        assets_path = os.path.join(os.getcwd(), "assets")

        self.titulo_img_original = pygame.image.load(
            os.path.join(assets_path, "titulo.png")
        ).convert_alpha()
        self.fondo_img_original = pygame.image.load(
            os.path.join(assets_path, "fondo.png")
        ).convert()
        self.cuadro_img = pygame.image.load(
            os.path.join(assets_path, "cuadro.png")
        ).convert_alpha()

        self.animacion_fondo_img = pygame.image.load(
            os.path.join(assets_path, "animacion_fondo.png")
        ).convert_alpha()
        self.animacion_fondo_img = pygame.transform.scale(
            self.animacion_fondo_img, (1000, 800)
        )
        self.pos_izquierda = (40, 120)
        self.pos_derecha = (1230, 120)
        self.angulo_izquierda = 0
        self.angulo_derecha = 0

        try:
            self.pixel_font = pygame.font.Font(
                os.path.join("assets", "Play-Regular.ttf"),
                30,
            )
        except:
            print(
                "Advertencia: No se pudo cargar la fuente pixelada. Usando fuente por defecto."
            )
            self.pixel_font = pygame.font.SysFont("Arial", 30)

        self.credits_surface = self.pixel_font.render(
            "Proyecto realizado por el Equipo 1",
            True,
            "#ffffff",
        )

    def get_font(self, size):
        try:
            return pygame.font.Font(os.path.join("assets", "Play-Regular.ttf"), size)
        except:
            print(
                "Advertencia: No se pudo cargar la fuente personalizada. Usando fuente por defecto."
            )
            return pygame.font.SysFont("Arial", size)

    def init_components(self):
        self.titulo_img = pygame.transform.scale(
            self.titulo_img_original,
            (int(self.SCREEN_WIDTH * 0.5), int(self.SCREEN_HEIGHT * 0.35)),
        )
        self.fondo_img = pygame.transform.scale(
            self.fondo_img_original, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        )

        button_base_color = "#e35d59"
        text_color = "#FFFFFF"
        button_hover_color = "#F9AA33"

        self.JUGAR_BUTTON = Button(
            image=None,
            pos=(
                self.SCREEN_WIDTH // 2,
                int(self.SCREEN_HEIGHT * 0.55),
            ),
            text_input="JUGAR",
            font=self.get_font(35),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(300, 65),
        )

        self.REGLAS_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 - 180, int(self.SCREEN_HEIGHT * 0.75)),
            text_input="REGLAS",
            font=self.get_font(35),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(220, 65),
        )

        self.SALIR_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 + 180, int(self.SCREEN_HEIGHT * 0.75)),
            text_input="SALIR",
            font=self.get_font(35),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(220, 65),
        )

        self.UNIRSE_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 - 150, 420),
            text_input="UNIRSE",
            font=self.get_font(30),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(180, 60),
        )

        self.CREAR_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 + 150, 420),
            text_input="CREAR",
            font=self.get_font(30),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(180, 60),
        )

        self.PLAY_BACK = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT * 0.75),
            text_input="VOLVER",
            font=self.get_font(35),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(220, 65),
        )

        small_font = self.get_font(25)

        self.JOIN_IP_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2, 490),
            text_input="Conectar",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(160, 45),
        )

        self.JOIN_BACK_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 + 150, self.SCREEN_HEIGHT * 0.85),
            text_input="Volver",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(160, 45),
        )

        self.JOIN_REFREHS_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 - 150, self.SCREEN_HEIGHT * 0.85),
            text_input="Actualizar",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(160, 45),
        )

        self.CREATE_GAME_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 + 150, self.SCREEN_HEIGHT * 0.85),
            text_input="Crear Partida",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(160, 45),
        )

        self.CREATE_BACK_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 - 150, self.SCREEN_HEIGHT * 0.85),
            text_input="Volver",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(160, 45),
        )

        self.PLAY_GAME_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 - 150, self.SCREEN_HEIGHT * 0.85),
            text_input="INICIAR PARTIDA",
            font=self.get_font(25),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(250, 65),
        )

        self.LOBBY_BACK_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2 + 150, self.SCREEN_HEIGHT * 0.85),
            text_input="VOLVER",
            font=self.get_font(35),
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(220, 65),
        )

        self.SEND_MS_BUTTON = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2, 500),
            text_input="Enviar Mensaje",
            font=small_font,
            text_color=text_color,
            bg_color=button_base_color,
            hovering_color=button_hover_color,
            size=(300, 45),
        )

        self.credits_x_pos = self.SCREEN_WIDTH
        self.credits_y_pos = int(self.SCREEN_HEIGHT * 0.95)

        self.init_input_boxes()

    def init_input_boxes(self):
        small_font = self.get_font(28)
        smaller_font = self.get_font(20)

        self.host_input_box = InputBox(
            self.SCREEN_WIDTH // 2 + 100, 200, 300, 40, small_font
        )
        self.join_password_input_box = InputBox(
            self.SCREEN_WIDTH // 2 - 30, 390, 300, 40, small_font
        )
        self.join_player_input_box = InputBox(
            self.SCREEN_WIDTH // 2 - 30, 340, 300, 40, small_font
        )
        self.name_input_box = InputBox(
            self.SCREEN_WIDTH // 2 + 100, 240, 300, 40, small_font
        )
        self.password_input_box = InputBox(
            self.SCREEN_WIDTH // 2 + 100, 280, 300, 40, small_font
        )
        self.max_players_input_box = InputBox(
            self.SCREEN_WIDTH // 2 + 100, 320, 300, 40, small_font
        )

        text_color = "#FFFFFF"
        self.name_text = smaller_font.render("Nombre:", True, text_color)
        self.password_text = smaller_font.render("Contraseña:", True, text_color)
        self.max_players_text = smaller_font.render("Jugadores:", True, text_color)
        self.host_text = smaller_font.render("Host:", True, text_color)

        self.message_input_box = InputBox(
            self.SCREEN_WIDTH // 2 + 100, 320, 300, 40, small_font
        )

        self.messages_text = smaller_font.render("CHAT", True, text_color)
        self.message_text = smaller_font.render("Mensaje:", True, text_color)

        self.available_games = [
            "Partida 1 - 192.168.1.1",
            "Partida 2 - 192.168.1.2",
            "Partida 3 - 192.168.1.3",
        ]

    def update_animation(self, delta_time):
        self.angulo_izquierda = (self.angulo_izquierda + 50 * delta_time) % 360
        self.angulo_derecha = (self.angulo_derecha + 50 * delta_time) % 360

        self.credits_x_pos -= 100 * delta_time
        if self.credits_x_pos < -self.credits_surface.get_width():
            self.credits_x_pos = self.SCREEN_WIDTH

    def draw_background(self):
        self.SCREEN.blit(self.fondo_img, (0, 0))

        rotada_izquierda = pygame.transform.rotate(
            self.animacion_fondo_img, self.angulo_izquierda
        )
        rect_izquierda = rotada_izquierda.get_rect(center=self.pos_izquierda)
        self.SCREEN.blit(rotada_izquierda, rect_izquierda)

        rotada_derecha = pygame.transform.rotate(
            self.animacion_fondo_img, self.angulo_derecha
        )
        rect_derecha = rotada_derecha.get_rect(center=self.pos_derecha)
        self.SCREEN.blit(rotada_derecha, rect_derecha)

        self.SCREEN.blit(self.credits_surface, (self.credits_x_pos, self.credits_y_pos))

    def draw_main_menu(self):
        title_rect = self.titulo_img.get_rect(
            center=(self.SCREEN_WIDTH // 2, int(self.SCREEN_HEIGHT * 0.25))
        )
        self.SCREEN.blit(self.titulo_img, title_rect)

        MENU_MOUSE_POS = pygame.mouse.get_pos()

        for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
            button.check_hover(MENU_MOUSE_POS)
            button.update(self.SCREEN)

        return MENU_MOUSE_POS

    def draw_play_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.PLAY_BACK]:
            button.check_hover(MENU_MOUSE_POS)
            button.update(self.SCREEN)

        return MENU_MOUSE_POS

    def draw_join_menu(self):
        self.servers = self.network_manager.servers
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(20)

        box_width = 800
        box_height = 450
        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2

        join_bg_img = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(join_bg_img, (box_x, box_y))

        input_x = box_x + 400
        input_req_x = box_x + 100

        rectNameServer = pygame.draw.rect(
            self.SCREEN, (255, 255, 254), (input_x - 100, box_y + 80, 400, 48), 2
        )
        self.is_hovered = rectNameServer.collidepoint(MENU_MOUSE_POS)

        color = (
            (0, 0, 255)
            if self.isSeletedServer
            else (100, 0, 150) if self.is_hovered else (90, 90, 90)
        )
        pygame.draw.rect(self.SCREEN, color, rectNameServer)
        pygame.draw.rect(self.SCREEN, (0, 0, 0), rectNameServer, 2)

        if self.servers:
            server_text = smaller_font.render(
                f"{self.servers[0]['name']}: Jugadores {self.servers[0]['currentPlayers']}/{self.servers[0]['max_players']}",
                True,
                (0, 0, 0),
            )
            self.SCREEN.blit(server_text, (input_x - 80, box_y + 95))
        else:
            noServers = smaller_font.render("No hay servidores :( ", True, (0, 0, 0))
            self.SCREEN.blit(noServers, (input_x - 80, box_y + 95))

        if self.response == "No ha seleccionado un servidor":
            if pygame.time.get_ticks() < self.no_server_until:
                noSelectServer = smaller_font.render(
                    "Seleccione un servidor", True, (255, 255, 255)
                )
                self.SCREEN.blit(noSelectServer, (input_x + 120, box_y + 95))
            else:
                self.response = None
        elif self.response == "wrongPassword":
            if pygame.time.get_ticks() < self.wrong_password_until:
                wrongPassword = smaller_font.render(
                    "Contraseña Incorrecta", True, (255, 255, 255)
                )
                self.SCREEN.blit(wrongPassword, (input_x + 120, box_y + 95))
            else:
                self.response = None
        elif self.response == "fullserver":
            if pygame.time.get_ticks() < self.fullserver_until:
                fullserver = smaller_font.render(
                    "Servidor Lleno", True, (255, 255, 255)
                )
                self.SCREEN.blit(fullserver, (input_x + 120, box_y + 95))
            else:
                self.response = None

        text_color = "#FFFFFF"
        ip_label = smaller_font.render("Nombre Servidor:", True, text_color)
        self.SCREEN.blit(ip_label, (input_req_x, box_y + 95))

        player_label = smaller_font.render("Nombre Jugador:", True, text_color)
        self.SCREEN.blit(player_label, (input_req_x, box_y + 150))
        self.join_player_input_box.draw(self.SCREEN)
        self.join_player_input_box.rect.topleft = (input_x - 100, box_y + 145)

        pw_label = smaller_font.render("Contraseña:", True, text_color)
        self.SCREEN.blit(pw_label, (input_req_x, box_y + 205))
        self.join_password_input_box.draw(self.SCREEN)
        self.join_password_input_box.rect.topleft = (input_x - 100, box_y + 200)

        self.JOIN_IP_BUTTON.x_pos = self.SCREEN_WIDTH // 2 + 200
        self.JOIN_IP_BUTTON.y_pos = box_y + 220
        self.JOIN_IP_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_IP_BUTTON.update(self.SCREEN)

        self.JOIN_REFREHS_BUTTON.x_pos = self.SCREEN_WIDTH // 2 + 200
        self.JOIN_REFREHS_BUTTON.y_pos = box_y + 320
        self.JOIN_REFREHS_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_REFREHS_BUTTON.update(self.SCREEN)

        self.JOIN_BACK_BUTTON.x_pos = self.SCREEN_WIDTH // 2 - 200
        self.JOIN_BACK_BUTTON.y_pos = box_y + 320
        self.JOIN_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_BACK_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS

    def draw_create_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(20)

        box_width = 600
        box_height = 450
        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2

        create_bg_img = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(create_bg_img, (box_x, box_y))

        input_x = box_x + 300
        input_req_x = box_x + 80

        self.host_input_box.draw(self.SCREEN)
        self.host_input_box.rect.topleft = (input_x, box_y + 80)

        self.name_input_box.draw(self.SCREEN)
        self.name_input_box.rect.topleft = (input_x, box_y + 140)

        self.password_input_box.draw(self.SCREEN)
        self.password_input_box.rect.topleft = (input_x, box_y + 200)

        self.max_players_input_box.draw(self.SCREEN)
        self.max_players_input_box.rect.topleft = (input_x, box_y + 260)

        self.CREATE_GAME_BUTTON.x_pos = self.SCREEN_WIDTH // 2 + 140
        self.CREATE_GAME_BUTTON.y_pos = box_y + 340
        self.CREATE_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_GAME_BUTTON.update(self.SCREEN)

        self.CREATE_BACK_BUTTON.x_pos = self.SCREEN_WIDTH // 2 - 140
        self.CREATE_BACK_BUTTON.y_pos = box_y + 340
        self.CREATE_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_BACK_BUTTON.update(self.SCREEN)

        self.SCREEN.blit(self.host_text, (input_req_x, box_y + 90))
        self.SCREEN.blit(self.name_text, (input_req_x, box_y + 150))
        self.SCREEN.blit(self.password_text, (input_req_x, box_y + 210))
        self.SCREEN.blit(self.max_players_text, (input_req_x, box_y + 270))

        return MENU_MOUSE_POS

    def draw_lobby(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(20)

        box_width = 800
        box_height = 550
        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2 - 5

        join_bg_img = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(join_bg_img, (box_x, box_y))

        if self.network_manager.currentServer:
            text_surface = smaller_font.render(
                f"Servidor:{self.network_manager.currentServer['name']} Jugadores:{self.network_manager.currentServer['currentPlayers']}/{self.network_manager.currentServer['max_players']}",
                True,
                "#ffffff",
            )
        elif self.selectedServer:
            text_surface = smaller_font.render(
                f"Conectado a:{self.selectedServer['name']} Jugadores:{self.selectedServer['currentPlayers']}/{self.selectedServer['max_players']}",
                True,
                "#ffffff",
            )

        text_rect = text_surface.get_rect(center=(self.SCREEN_WIDTH // 2, box_y + 180))
        self.SCREEN.blit(text_surface, text_rect)

        input_x = box_x + 250
        input_req_x = box_x + 20

        pygame.draw.rect(
            self.SCREEN,
            (255, 255, 255),
            (box_x + 230, box_y + 200, 430, 140),
            2,
            border_radius=8,
        )

        y_offset = box_y + 210
        with self.chatLock:
            recentMsg = self.network_manager.messagesServer[-5:]

        for msg in recentMsg:
            msg_surface = smaller_font.render(msg, True, (0, 0, 0))
            if msg_surface.get_width() > box_x + 200 - 10:
                msg = msg[:17] + "..."
                msg_surface = smaller_font.render(msg, True, (0, 0, 0))
            self.SCREEN.blit(msg_surface, (input_x - 10, y_offset))
            y_offset += 25

        self.message_input_box.draw(self.SCREEN)
        self.message_input_box.rect.topleft = (input_x + 50, box_y + 340)

        self.SEND_MS_BUTTON.x_pos = self.SCREEN_WIDTH // 2
        self.SEND_MS_BUTTON.y_pos = box_y + 400
        self.SEND_MS_BUTTON.check_hover(MENU_MOUSE_POS)
        self.SEND_MS_BUTTON.update(self.SCREEN)

        if self.network_manager.is_host:
            canStart = self.network_manager.canStartGame()
            self.PLAY_GAME_BUTTON.x_pos = self.SCREEN_WIDTH // 2 - 150
            self.PLAY_GAME_BUTTON.y_pos = self.SCREEN_HEIGHT * 0.85
            self.PLAY_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
            if canStart:
                self.PLAY_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
                self.PLAY_GAME_BUTTON.update(self.SCREEN)
        elif self.playGamePlayer:
            self.PLAY_GAME_BUTTON.x_pos = self.SCREEN_WIDTH // 2 - 150
            self.PLAY_GAME_BUTTON.y_pos = self.SCREEN_HEIGHT * 0.85
            self.PLAY_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
            self.PLAY_GAME_BUTTON.update(self.SCREEN)

        if self.process_received_messages() == "launch_ui2":
            self.playGamePlayer = True

        self.LOBBY_BACK_BUTTON.x_pos = self.SCREEN_WIDTH // 2 + 150
        self.LOBBY_BACK_BUTTON.y_pos = self.SCREEN_HEIGHT * 0.85
        self.LOBBY_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.LOBBY_BACK_BUTTON.update(self.SCREEN)

        self.SCREEN.blit(self.messages_text, (input_req_x + 120, box_y + 210))
        self.SCREEN.blit(self.message_text, (input_req_x + 120, box_y + 350))

        return MENU_MOUSE_POS

    class RulesTextBox:
        def __init__(self, x, y, w, h, font, text_lines, extra_bottom_space=50):
            self.rect = pygame.Rect(x, y, w, h)
            self.font = font
            if isinstance(text_lines, list):
                raw = "\n".join(text_lines)
            else:
                raw = str(text_lines)
            self.lines = raw.splitlines()
            self.padding = 16
            self.line_height = self.font.size("Tg")[1] + 6
            self.offset = 0
            self.extra_bottom_space = extra_bottom_space
            self._wrap_lines()
            total_height = (
                len(self.wrapped_lines) * self.line_height
                + self.padding * 2
                + self.extra_bottom_space
            )
            self.max_offset = max(0, total_height - self.rect.h)

        def _wrap_lines(self):
            max_w = max(10, self.rect.w - self.padding * 2)
            wrapped = []
            for line in self.lines:
                if line.strip() == "":
                    wrapped.append("")
                    continue
                words = line.split(" ")
                cur = ""
                for word in words:
                    test = (cur + " " + word) if cur else word
                    if self.font.size(test)[0] <= max_w:
                        cur = test
                    else:
                        if cur:
                            wrapped.append(cur)
                        if self.font.size(word)[0] > max_w:
                            part = ""
                            for ch in word:
                                tp = part + ch
                                if self.font.size(tp)[0] <= max_w:
                                    part = tp
                                else:
                                    if part:
                                        wrapped.append(part)
                                    part = ch
                            if part:
                                cur = part
                            else:
                                cur = ""
                        else:
                            cur = word
                if cur:
                    wrapped.append(cur)
            self.wrapped_lines = wrapped

        def draw(self, screen):
            pygame.draw.rect(screen, (35, 35, 35), self.rect)
            old_clip = screen.get_clip()
            screen.set_clip(self.rect)
            start_y = self.rect.y + self.padding + int(self.offset)
            for i, line in enumerate(self.wrapped_lines):
                line_y = start_y + i * self.line_height
                if (
                    line_y + self.line_height < self.rect.y
                    or line_y > self.rect.y + self.rect.h
                ):
                    continue
                bg_rect = pygame.Rect(
                    self.rect.x + 4, line_y - 4, self.rect.w - 8, self.line_height + 8
                )
                pygame.draw.rect(screen, (45, 50, 45), bg_rect)
                text_surf = self.font.render(line, True, "#d7fcd4")
                screen.blit(text_surf, (self.rect.x + self.padding, line_y))
            screen.set_clip(old_clip)
            pygame.draw.rect(screen, (90, 90, 90), self.rect, 2)

        def update(self, events):
            for event in events:
                if event.type == pygame.MOUSEWHEEL:
                    self.offset += event.y * 30
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.offset += 30
                    elif event.button == 5:
                        self.offset -= 30
            total_height = (
                len(self.wrapped_lines) * self.line_height
                + self.padding * 2
                + self.extra_bottom_space
            )
            self.max_offset = max(0, total_height - self.rect.h)
            if self.offset > 0:
                self.offset = 0
            if self.offset < -self.max_offset:
                self.offset = -self.max_offset

    def options(self):
        pygame.display.set_caption("Opciones")
        game_rules = """Rummy 500
Objetivo: Ser el último jugador con menos de 500 puntos.

Jugadores: 2 - 13

Mazo: 52 cartas + 1 Joker.

Cómo ganar: El último jugador en acumular menos de 500 puntos gana la partida.
Cómo perder: El primer jugador en alcanzar o superar los 500 puntos es eliminado.
Combinaciones:
• Trío: Tres cartas del mismo valor (ej: Q♥, Q♦, Q♠).
• Seguidilla: Cuatro cartas consecutivas del mismo palo (ej: ♣7, ♣8, ♣9, ♣10).

Rondas de Juego:
1. Trío y Seguidilla
2. Dos Seguidillas
3. Tres Tríos
4. Una Seguidilla y Dos Tríos (Ronda Completa): Para finalizar esta ronda, el jugador debe descartar las diez cartas (la seguidilla de cuatro y los dos tríos) en un solo turno.

Puntuación:
• Cartas 2 - 9: 5 puntos
• Cartas 10 - K: 10 puntos
• As: 15 puntos
• Joker: 25 puntos

Desarrollo del Juego:
1. Inicio: Cada jugador recibe 10 cartas. Se coloca una carta boca arriba del mazo en el centro de la mesa para iniciar el descarte. Se designa un jugador como MANO.
2. Turno del MANO: Para la siguiente ronda, el rol de MANO pasa al jugador a la izquierda del MANO actual.
3. Primera Toma de la Carta Central: Solo el jugador MANO tiene la primera oportunidad de tomar la carta boca arriba del centro. Si decide tomarla, debe descartar una carta de su mano para mantener un total de 10 cartas. Si el MANO no toma la carta central, se pasa a la siguiente fase de toma.
4. Segunda Oportunidad de Toma de la Carta Central: Si el MANO no tomó la carta central, los demás jugadores, en orden hacia la izquierda del MANO, tienen la oportunidad de tomarla. El primer jugador que la tome debe robar una carta adicional del mazo como penalización, quedando con 12 cartas. Si nadie toma la carta central en esta segunda oportunidad, la carta se QUEMA y se descarta, quedando fuera de juego.
5. Turno Regular del Jugador: Después de la fase de toma de la carta central (haya sido tomada o quemada), y durante el resto de su turno, cada jugador puede realizar una de las siguientes acciones:
o Tomar la carta superior del mazo boca abajo (solo si no agarró la carta boca arriba o si agarra como penalización).
o Bajarse: Mostrar sobre la mesa las combinaciones de cartas requeridas para la ronda actual (tríos o seguidillas). Se puede usar un Joker para completar una combinación. Un Joker ya bajado puede ser reemplazado por la carta que representa y utilizado en otra combinación propia.
o Agregar cartas: Añadir cartas válidas a sus propias combinaciones ya bajadas (antes de descartar).
o Descartar: Colocar una carta boca arriba en el centro de la mesa para finalizar su turno.
6. Fin de la Ronda: Una ronda termina cuando un jugador se queda sin cartas al bajar todas sus combinaciones requeridas (y descartar si es necesario). El jugador que se quedó sin cartas será el primero en actuar en la siguiente ronda.
7. Puntuación de la Ronda: Los jugadores que no lograron bajarse suman los puntos de las cartas que aún tienen en su mano.
8. Fin de la Partida: El juego continúa a lo largo de las cuatro rondas. El ganador es el jugador con la menor puntuación total al final de las cuatro rondas, o el último jugador que no haya alcanzado o superado los 500 puntos."""
        box_w, box_h = 760, 400
        box_x = self.SCREEN_WIDTH // 2 - box_w // 2
        box_y = 140
        rules_box = self.RulesTextBox(
            box_x + 20,
            box_y + 20,
            box_w - 40,
            box_h - 40,
            self.get_font(18),
            game_rules,
        )

        options_back = Button(
            image=None,
            pos=(self.SCREEN_WIDTH // 2, box_y + box_h + 40),
            text_input="VOLVER",
            font=self.get_font(35),
            text_color="#FFFFFF",
            bg_color="#e35d59",
            hovering_color="#F9AA33",
            size=(220, 65),
        )

        while True:
            delta_time = self.clock.tick(60) / 1000.0
            self.update_animation(delta_time)
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                    self.SCREEN = pygame.display.set_mode(
                        (self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE
                    )
                    box_w, box_h = int(self.SCREEN_WIDTH * 0.7), int(
                        self.SCREEN_HEIGHT * 0.6
                    )
                    box_x = self.SCREEN_WIDTH // 2 - box_w // 2
                    box_y = self.SCREEN_HEIGHT // 2 - box_h // 2
                    rules_box.rect.topleft = (box_x + 20, box_y + 20)
                    rules_box._wrap_lines()
                    options_back.x_pos = self.SCREEN_WIDTH // 2
                    options_back.y_pos = box_y + box_h + 40

            self.draw_background()
            self.SCREEN.fill(
                (50, 50, 50), (self.SCREEN_WIDTH // 2 - box_w // 2, box_y, box_w, box_h)
            )

            options_text = self.get_font(45).render(
                "Reglas de Rummy 500", True, "White"
            )
            options_rect = options_text.get_rect(center=(self.SCREEN_WIDTH // 2, 100))
            bg_rect = options_rect.inflate(40, 18)
            pygame.draw.rect(self.SCREEN, (80, 80, 80), bg_rect, border_radius=6)
            self.SCREEN.blit(options_text, options_rect)

            rules_box.update(events)
            rules_box.draw(self.SCREEN)

            mouse_pos = pygame.mouse.get_pos()
            options_back.check_hover(mouse_pos)
            options_back.update(self.SCREEN)

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if options_back.checkForInput(mouse_pos):
                        return

            pygame.display.update()

    def lanzar_juego_ui2(self):
        import ui2

        pygame.quit()
        ui2.main()

    def play_click(self):
        self.click_sound.play()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.VIDEORESIZE:
                self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                self.SCREEN = pygame.display.set_mode(
                    (self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE
                )
                self.init_components()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.current_screen == "main":
                    if self.JUGAR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "play"
                    elif self.REGLAS_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.options()
                    elif self.SALIR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        return False

                elif self.current_screen == "play":
                    if self.PLAY_BACK.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "main"
                    elif self.UNIRSE_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ""
                        self.current_screen = "join"
                    elif self.CREAR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "create"

                elif self.current_screen == "join":
                    if event.button == 1 and self.is_hovered:
                        if self.servers:
                            self.selectedServer = self.servers[0]
                            self.isSeletedServer = True
                            print(f"Acabo de seleccionar este servidor")
                    if self.JOIN_BACK_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "play"
                        self.response = ""
                    elif self.JOIN_REFREHS_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ""
                    elif self.JOIN_IP_BUTTON.checkForInput(event.pos):
                        password = self.join_password_input_box.text
                        if self.servers:
                            self.servers[0]["password"] = password
                            if self.join_player_input_box.text != "":
                                playerName = self.join_player_input_box.text
                            else:
                                playerName = (
                                    f"Jugador {self.servers[0]['currentPlayers']}"
                                )

                            self.servers[0]["playerName"] = playerName
                            pygame.display.update()

                            print(f"Esto esta en el Server {self.servers}")
                        if self.selectedServer:
                            acep, resp = self.network_manager.connectToServer(
                                self.selectedServer
                            )
                            if acep:
                                self.selectedServer["currentPlayers"] += 1
                                print(f"Info de connectToServer  {(acep,resp)}")
                                print("ClaveCorrecta.... Probando")
                                self.current_screen = "lobby"
                            elif acep == False:
                                if resp == "Contraseña incorrecta":
                                    self.response = "wrongPassword"
                                    self.wrong_password_until = (
                                        pygame.time.get_ticks() + 2000
                                    )
                                    print("Contraseña incorrecta")
                                elif resp == "El servidor está lleno":
                                    self.response = "fullserver"
                                    self.fullserver_until = (
                                        pygame.time.get_ticks() + 2000
                                    )
                                    print("El servidor está lleno")
                        else:
                            self.response = "No ha seleccionado un servidor"
                            self.no_server_until = pygame.time.get_ticks() + 2000
                            print("No ha seleccionado un servidor")

                elif self.current_screen == "create":
                    if self.CREATE_BACK_BUTTON.checkForInput(event.pos):
                        self.current_screen = "play"
                    elif self.CREATE_GAME_BUTTON.checkForInput(event.pos):
                        nombre = self.name_input_box.text
                        password = self.password_input_box.text
                        host_name = self.host_input_box.text
                        try:
                            max_players = int(self.max_players_input_box.text)
                        except:
                            max_players = 7
                        exito = self.network_manager.start_server(
                            nombre, password, max_players, host_name
                        )
                        print("Servidor creado" if exito else "Error al crear servidor")
                        print(
                            f"Host: {host_name}, Servidor: {self.network_manager.gameName}"
                        )
                        self.current_screen = "lobby"

                elif self.current_screen == "lobby":
                    if self.LOBBY_BACK_BUTTON.checkForInput(event.pos):
                        self.current_screen = "play"
                        self.network_manager.connected_players.clear()
                        self.network_manager.stop()
                        if self.selectedServer:
                            self.selectedServer["currentPlayers"] = len(
                                self.network_manager.connected_players
                            )
                        print(f"Servidor cerrado...")
                    elif self.PLAY_GAME_BUTTON.checkForInput(event.pos):
                        if self.network_manager.is_host:
                            if self.network_manager.canStartGame():
                                self.network_manager.startGame()
                            else:
                                print("Se necesitan al menos dos jugadores")
                        else:
                            msg = self.network_manager.get_msgStartGame()
                            print(f"Lo que esta en el msg del lobby PLAY_BUTTON {msg}")
                            if msg == "launch_ui2":
                                return "launch_ui2"
                        return "launch_ui2"
                    elif self.SEND_MS_BUTTON.checkForInput(event.pos):
                        msg = self.message_input_box.text.strip()
                        if msg:
                            if self.network_manager.server:
                                formattedMsg = f"Host: {msg}"
                                with self.chatLock:
                                    self.network_manager.messagesServer.append(
                                        formattedMsg
                                    )
                                    print(f"en la lista de mensajes: {self.messages}")
                                self.network_manager.broadcast_message(formattedMsg)

                            if self.network_manager.player:
                                success = self.network_manager.sendData(
                                    ("chat_messages", msg)
                                )
                                if success:
                                    formattedMsg = f"Tú: {msg}"
                                    with self.chatLock:
                                        self.network_manager.messagesServer.append(
                                            formattedMsg
                                        )

                            self.message_input_box.text = ""
                            self.message_input_box.txt_surface = self.get_font(
                                20
                            ).render("", True, (0, 0, 0))

                        print(f" Mensajes: {self.messages}")

            if self.current_screen == "create":
                self.host_input_box.handle_event(event)
                self.name_input_box.handle_event(event)
                self.password_input_box.handle_event(event)
                self.max_players_input_box.handle_event(event)
            elif self.current_screen == "join":
                self.join_player_input_box.handle_event(event)
                self.join_password_input_box.handle_event(event)
            elif self.current_screen == "lobby":
                self.message_input_box.handle_event(event)

        self.process_received_messages()
        return True

    def process_received_messages(self):
        if (
            hasattr(self.network_manager, "receivedData")
            and self.network_manager.receivedData
        ):
            with self.network_manager.lock:
                data = self.network_manager.receivedData
                self.network_manager.receivedData = None

            print(f"Procesando mensaje recibido en Ui.py: {data}")

            if isinstance(data, dict) and data.get("type") == "START_GAME":
                print("Comenzando el juego")
                return "launch_ui2"

            if isinstance(data, dict) and data.get("players"):
                print("Recibiendo lista de jugadores")
                players = data.get("players")
                return players

            if isinstance(data, str) and (
                data.startswith("Host:") or data.startswith("Jugador")
            ):
                with self.chatLock:
                    if not (
                        data.startswith("Tú:")
                        or (self.network_manager.is_host and data.startswith("Host:"))
                    ):
                        self.network_manager.messagesServer.append(data)
                        if len(self.network_manager.messagesServer) > 20:
                            self.network_manager.messagesServer = (
                                self.network_manager.messagesServer[-20:]
                            )

            elif isinstance(data, tuple):
                pass

    def update(self):
        delta_time = self.clock.tick(60) / 1000.0
        self.update_animation(delta_time)
        self.draw_background()

        title_rect = self.titulo_img.get_rect(
            center=(self.SCREEN_WIDTH // 2, int(self.SCREEN_HEIGHT * 0.25))
        )
        self.SCREEN.blit(self.titulo_img, title_rect)

        if self.current_screen == "create":
            self.host_input_box.update()
            self.name_input_box.update()
            self.password_input_box.update()
            self.max_players_input_box.update()
        elif self.current_screen == "join":
            self.join_player_input_box.update()
            self.join_password_input_box.update()
        elif self.current_screen == "lobby":
            self.message_input_box.update()

        if self.current_screen == "main":
            mouse_pos = self.draw_main_menu()
            for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play":
            mouse_pos = self.draw_play_menu()
            for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.PLAY_BACK]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "join":
            mouse_pos = self.draw_join_menu()
            for button in [
                self.JOIN_IP_BUTTON,
                self.JOIN_REFREHS_BUTTON,
                self.JOIN_BACK_BUTTON,
            ]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "create":
            mouse_pos = self.draw_create_menu()
            for button in [self.CREATE_GAME_BUTTON, self.CREATE_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "lobby":
            mouse_pos = self.draw_lobby()
            for button in [
                self.SEND_MS_BUTTON,
                self.PLAY_GAME_BUTTON,
                self.LOBBY_BACK_BUTTON,
            ]:
                button.check_hover(mouse_pos)

        pygame.display.update()
        return True
