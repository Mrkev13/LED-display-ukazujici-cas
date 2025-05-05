# Velké digitální hodiny s LED panelem a Google kalendářem

## Cíl projektu

Vytvoření velkých digitálních hodin, které zobrazují aktuální čas a současně běžící text s událostmi na daný den z Google Kalendáře. Výsledkem je plně funkční zařízení založené na Raspberry Pi a LED panelu s automatickým startem po zapnutí. Události starší než hodinu se nezobrazují, nové se obnovují každých 5 minut.

---

## Použité komponenty

| Komponenta                 | Popis                                     |
| -------------------------- | ----------------------------------------- |
| Raspberry Pi 3B            | Hlavní řídicí jednotka                    |
| LED panel 64x32 RGB HUB75  | Displej pro zobrazování času a textu      |
| Adafruit RGB Matrix Bonnet | Propojení mezi Raspberry Pi a LED panelem |
| Napájecí zdroj 5V/4A       | Napájí LED panel (důležité!)              |
| MicroSD karta (16 GB+)     | Pro OS, knihovny, skripty                 |
| Google API knihovny        | Pro přístup ke Google Kalendáři           |

---

## Instalace a konfigurace

### 1. Instalace Raspberry Pi OS

* Nainstalován Raspberry Pi OS Lite (64bit)
* Povoleno SPI, SSH (pomocí `raspi-config`)

### 2. Instalace knihoven

```bash
sudo apt update
sudo apt install -y python3-venv git
python3 -m venv venv
source venv/bin/activate
pip install rgbmatrix google-api-python-client google-auth google-auth-oauthlib
```

### 3. Nastavení Google API

* Na [https://console.cloud.google.com](https://console.cloud.google.com) vytvořen projekt
* Aktivováno "Google Calendar API"
* Vytvořen OAuth2.0 client ID (typ: Desktop)
* Stažen soubor `credentials.json`
* Soubor umístěn do složky se skripty na Raspberry Pi (`/home/pi/clock`)

### 4. Autorizace

```bash
cd ~/clock
python3 get_events.py
```

* Proběhl přístup přes prohlížeč
* Vygenerován `token.json`

---

## Spuštění hodinového skriptu

```bash
sudo ./venv/bin/python3 clock_with_events.py
```

* Zobrazí se čas nahoře a události ze záznamů kalendáře scrollují dole
* Události se automaticky obnovují každých 5 minut
* Události, které už proběhly (jsou více než hodinu staré), se nezobrazují

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
ExecStart=/home/pi/clock/venv/bin/python3 /home/pi/clock/clock_with_events.py
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

### clock\_with\_events.py

```python
import time
import datetime
import os
import threading
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from get_events import get_today_events

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.hardware_mapping = 'adafruit-hat-pwm'
options.brightness = 70

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

font = graphics.Font()
font.LoadFont("6x13.bdf")
color = graphics.Color(255, 255, 0)
event_color = graphics.Color(0, 255, 255)

event_text = get_today_events()
scroll_x = canvas.width
last_update = time.time()

# Obnovení událostí každých 5 minut
REFRESH_INTERVAL = 300

def refresh_events():
    global event_text, last_update, scroll_x
    while True:
        event_text = get_today_events()
        scroll_x = canvas.width
        last_update = time.time()
        time.sleep(REFRESH_INTERVAL)

threading.Thread(target=refresh_events, daemon=True).start()

while True:
    canvas.Clear()
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M:%S")
    graphics.DrawText(canvas, font, 2, 12, color, time_str)
    graphics.DrawText(canvas, font, scroll_x, 28, event_color, event_text)
    scroll_x -= 1
    if scroll_x + len(event_text) * 6 < 0:
        scroll_x = canvas.width
    canvas = matrix.SwapOnVSync(canvas)
    time.sleep(0.03)
```

---

## Shrnutí

Po zapnutí Raspberry Pi se automaticky spustí digitální hodiny s LED panelem. Zobrazují aktuální čas a události z Google kalendáře pro daný den. Každých 5 minut se kalendářní události automaticky aktualizují a ty, které jsou více než hodinu staré, se již nezobrazují.

> Pokud panel zobrazuje jen 4 pruhy nebo bliká, zkontroluj napětí, chlazení RPi a zkus `--led-hardware-mapping=adafruit-hat-pwm` v konfiguraci.
