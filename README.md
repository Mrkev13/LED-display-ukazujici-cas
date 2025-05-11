# Velké digitální hodiny s LED panelem a Google kalendářem

## Cíl projektu

Vytvoření velkých digitálních hodin, které zobrazují aktuální čas a současně běžící text s událostmi na daný den z Google Kalendáře. Výsledkem je plně funkční zařízení založené na Raspberry Pi a LED panelu s automatickým startem po zapnutí. Události starší než hodinu se nezobrazují, nové se obnovují každých 5 minut.

---

## Použité komponenty

| Komponenta                 | Popis                                     |
| -------------------------- | ----------------------------------------- |
| Raspberry Pi 4B          | Hlavní řídicí jednotka                    |
| LED panel 64x32 RGB HUB75  | Displej pro zobrazování času a textu      |
| Adafruit RGB Matrix Bonnet | Propojení mezi Raspberry Pi a LED panelem |
| Napájecí zdroj 5V/4A       | Napájí LED panel (důležité!)              |
| MicroSD karta (16 GB+)     | Pro OS, knihovny, skripty                 |
| Google API knihovny        | Pro přístup ke Google Kalendáři           |

---

## Instalace a konfigurace

### 1. Instalace Raspberry Pi OS

* Nainstaluj Raspberry Pi OS Lite (64bit)
* Povol SPI a SSH pomocí `raspi-config`

### 2. Instalace knihoven

```bash
sudo apt update
sudo apt install -y python3-venv git
python3 -m venv venv
source venv/bin/activate
pip install rgbmatrix google-api-python-client google-auth google-auth-oauthlib
```

### 3. Nastavení Google API

* Vytvoř projekt na [https://console.cloud.google.com](https://console.cloud.google.com)
* Aktivuj "Google Calendar API"
* Vytvoř OAuth2.0 klienta (typ: Desktop)
* Stáhni `credentials.json` a vlož do složky se skripty, např. `/home/pi/clock` (nahraď `pi` podle svého uživatelského jména)

### 4. Autorizace

```bash
cd ~/clock
python3 get_events.py
```

* Provede se autorizace přes prohlížeč
* Vytvoří se `token.json`

---

## Automatický start po spuštění

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
ExecStart=/home/pi/clock/venv/bin/python3 /home/pi/clock/led_clock_simulator.py
WorkingDirectory=/home/pi/clock
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

> Nahraď `/home/pi/clock` správnou cestou podle svého uživatelského jména a umístění skriptů.

### 2. Aktivace služby

```bash
sudo systemctl daemon-reexec
sudo systemctl enable led-clock.service
sudo systemctl start led-clock.service
```

Po restartu zařízení se skript automaticky spustí.

---


## Skripty

### get\_events.py

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

### led\_clock\_simulator.py

```python
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
options.brightness = 50
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

color_time = graphics.Color(255, 255, 255)
color_event = graphics.Color(255, 255, 0)

scroll_x = canvas.width
scroll_speed = 1
fps = 30
update_interval = 300  # 5 minut
last_update = 0
event_text = get_today_events()

while True:
    current_time = time.strftime("%H:%M:%S")

    if time.time() - last_update > update_interval:
        event_text = get_today_events()
        scroll_x = canvas.width
        last_update = time.time()

    canvas.Clear()

    # Zobrazení času - centrování
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
```
## Shrnutí

Po zapnutí Raspberry Pi se automaticky spustí digitální hodiny s LED panelem. Zobrazují aktuální čas a události z Google kalendáře pro daný den. Každých 5 minut se kalendářní události automaticky aktualizují a ty, které jsou více než hodinu staré, se již nezobrazují.

> Pokud panel bliká nebo zobrazuje chyby:
>
> * Ujisti se, že používáš správné `hardware_mapping` (např. `adafruit-hat`)
> * Zkus snížit `brightness` nebo zvýšit `pwm_lsb_nanoseconds`
> * Zkontroluj napájení a kabeláž panelu
> * Ověř, že síť funguje, jinak se kalendář nenačte

---
