# Velke digitalni hodiny s LED panelem a Google kalendarem

## Cíl projektu
Vytvoření velkých digitálních hodin, které zobrazují aktuální čas a současně běžící text s událostmi na daný den z Google Kalendáře. Výsledkem je plně funkční zařízení založené na Raspberry Pi a LED panelu s automatickým startem po zapnutí.

---

## Použité komponenty

| Komponenta                      | Popis                                                      |
|-------------------------------|-------------------------------------------------------------|
| Raspberry Pi 3B               | Hlavní řídicí jednotka                                      |
| LED panel 64x32 RGB HUB75    | Displej pro zobrazování času a textu                          |
| Adafruit RGB Matrix Bonnet       | Propojení mezi Raspberry Pi a LED panelem                  |
| Napájecí zdroj 5V/4A         | Napájí LED panel (důležité!)                                |
| MicroSD karta (16 GB+)        | Pro OS, knihovny, skripty                                  |
| Pygame, Google API knihovny   | Knihovny pro grafiku a kalendář                            |

---

## Instalace a konfigurace

### 1. Instalace Raspberry Pi OS
- Nainstalován Raspberry Pi OS Lite (64bit)
- Povoleno SPI, SSH (pomocí `raspi-config`)

### 2. Instalace knihoven
```bash
sudo apt update
sudo apt install -y python3-pip python3-pygame fonts-dejavu
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 3. Nastavení Google API
- Na https://console.cloud.google.com vytvořen projekt
- Aktivováno "Google Calendar API"
- Vytvořen OAuth2.0 client ID (typ: Desktop)
- Stažen soubor `credentials.json`
- Soubor umístěn do složky se skripty na Raspberry Pi (`/home/pi/clock`)

### 4. Autorizace
```bash
cd ~/clock
python3 get_events.py
```
- Proběhl přístup přes prohlížeč
- Vygenerován `token.json`

---

## Spuštění hodinového skriptu

```bash
python3 led_clock_simulator.py
```
- Zobrazí se čas nahoře a události ze záznamů kalendáře scrollují dole
- Události se automaticky obnovují každých 5 minut
- Události, které už proběhly (jsou více než hodinu staré), se nezobrazují

---

## Automatický start po zapnutí

### 1. Vytvoření systemd služby

```bash
sudo nano /etc/systemd/system/led-clock.service
```

#### Obsah souboru:
```ini
[Unit]
Description=LED Clock with Google Calendar
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/clock/led_clock_simulator.py
WorkingDirectory=/home/pi/clock
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

### 2. Aktivace služby
```bash
sudo systemctl daemon-reexec
sudo systemctl enable led-clock.service
sudo systemctl start led-clock.service
```

---

## Používané skripty

### get_events.py
```python
from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_today_events():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow()
    end = now.replace(hour=23, minute=59, second=59)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat() + 'Z',
        timeMax=end.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    if not events:
        return "Dnes žádné události."

    output = []
    current_time = datetime.datetime.utcnow()
    for event in events:
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        try:
            start_time = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        except ValueError:
            output.append(f"Celý den {event.get('summary', 'Bez názvu')}")
            continue

        if (current_time - start_time).total_seconds() > 3600:
            continue  # přeskočit události starší než 1 hodina

        time_str = start_time.strftime('%H:%M')
        summary = event.get('summary', 'Bez názvu')
        output.append(f"{time_str} {summary}")

    return " | ".join(output)


if __name__ == '__main__':
    print(get_today_events())
```

### led_clock_simulator.py
```python
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
```

---

## Shrnutí
Po zapnutí Raspberry Pi se automaticky spustí digitální hodiny s LED panelem. Zobrazují aktuální čas a události z Google kalendáře pro daný den. Každých 5 minut se kalendářní události automaticky aktualizují a ty, které jsou více než hodinu staré, se již nezobrazují.

