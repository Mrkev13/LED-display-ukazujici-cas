import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from get_events import get_today_events

# Nastavení LED panelu
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.hardware_mapping = 'adafruit-hat'
options.scan_mode = 0
options.pwm_lsb_nanoseconds = 200
options.brightness = 50  # mírně sníženo pro lepší čitelnost
options.drop_privileges = False
options.disable_hardware_pulsing = False
options.show_refresh_rate = 0

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Načtení fontů
font_clock = graphics.Font()
font_clock.LoadFont("6x13.bdf")

font_scroll = graphics.Font()
font_scroll.LoadFont("6x13.bdf")

color_time = graphics.Color(255, 255, 0)
color_event = graphics.Color(0, 255, 255)

scroll_x = canvas.width
scroll_speed = 1
fps = 5
update_interval = 300  # 5 minut
last_update = 0
event_text = get_today_events()

while True:
    current_time = time.strftime("%H:%M:%S")

    # Obnovení událostí každých 5 minut
    if time.time() - last_update > update_interval:
        event_text = get_today_events()
        scroll_x = canvas.width
        last_update = time.time()

    canvas.Clear()

    # Zobrazení času – centrování
    text_width = graphics.DrawText(canvas, font_clock, 0, 0, color_time, current_time)
    x_time = (canvas.width - text_width) // 2
    graphics.DrawText(canvas, font_clock, x_time, 14, color_time, current_time)

    # Posuvný text
    graphics.DrawText(canvas, font_scroll, scroll_x, 28, color_event, event_text)
    scroll_x -= scroll_speed
    if scroll_x + len(event_text) * 6 < 0:
        scroll_x = canvas.width

    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(1 / fps)
