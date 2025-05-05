import time
import datetime
import os
import threading
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
EVENT_REFRESH_INTERVAL = 300  # každých 5 minut

# Nastavení LED panelu
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.hardware_mapping = 'adafruit-hat-pwm'
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Barvy a font
font = graphics.Font()
font.LoadFont("6x13.bdf")
color = graphics.Color(0, 255, 0)
scroll_color = graphics.Color(255, 255, 0)

# Získání dnešních událostí
events_list = []
def fetch_events():
    global events_list
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    end = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          timeMax=end, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    filtered = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
        summary = event.get('summary', '')
        filtered.append((dt, summary))
    events_list = filtered

# Obnovení událostí každých 5 minut
def schedule_fetch():
    while True:
        fetch_events()
        time.sleep(EVENT_REFRESH_INTERVAL)

threading.Thread(target=schedule_fetch, daemon=True).start()

# Posuvný text
def scroll_text(canvas, font, color, text, y):
    pos = canvas.width
    while pos + len(text)*6 > 0:
        canvas.Clear()
        now_str = time.strftime("%H:%M:%S")
        graphics.DrawText(canvas, font, 1, 10, color, now_str)
        graphics.DrawText(canvas, font, pos, y, scroll_color, text)
        pos -= 1
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.03)

# Hlavní smyčka
while True:
    now = datetime.datetime.now(datetime.timezone.utc)
    active_events = []
    for ev in events_list:
        if now < ev[0] + datetime.timedelta(hours=1):
            time_str = ev[0].strftime("%H:%M")
            active_events.append(f"{time_str} {ev[1]}")
    msg = ' | '.join(active_events) if active_events else "Žádné aktuální události"
    scroll_text(canvas, font, scroll_color, msg, 28)
