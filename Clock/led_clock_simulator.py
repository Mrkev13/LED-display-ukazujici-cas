import pygame
import time
import sys
from get_events import get_today_events

pygame.init()
screen_width, screen_height = 512, 128
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("LED Clock with Calendar")

BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

clock_font = pygame.font.SysFont("Courier", 64, bold=True)
scroll_font = pygame.font.SysFont("Arial", 28, bold=False)

event_text = get_today_events()
scroll_x = screen_width
last_update_time = time.time()
update_interval = 300  # 5 minut

fps = 30
scroll_speed = 2
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if time.time() - last_update_time > update_interval:
        event_text = get_today_events()
        last_update_time = time.time()
        scroll_x = screen_width

    screen.fill(BLACK)

    current_time = time.strftime("%H:%M:%S")
    time_surface = clock_font.render(current_time, True, YELLOW)
    time_rect = time_surface.get_rect(center=(screen_width // 2, 32))
    screen.blit(time_surface, time_rect)

    scroll_surface = scroll_font.render(event_text, True, CYAN)
    screen.blit(scroll_surface, (scroll_x, 90))

    scroll_x -= scroll_speed
    if scroll_x < -scroll_surface.get_width():
        scroll_x = screen_width

    pygame.display.flip()
    clock.tick(fps)