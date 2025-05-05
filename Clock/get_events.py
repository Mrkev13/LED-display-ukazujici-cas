from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Oprávnění pouze ke čtení
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_today_events():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + 'Z'
    end = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    if not events:
        return "Dnes žádné události."

    output = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        time_str = start[11:16] if 'T' in start else "Celý den"
        summary = event.get('summary', 'Bez názvu')
        output.append(f"{time_str} {summary}")

    return " | ".join(output)

if __name__ == '__main__':
    print(get_today_events())
