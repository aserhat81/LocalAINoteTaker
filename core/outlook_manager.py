import datetime
import win32com.client
import pythoncom
import requests
from icalendar import Calendar
from dateutil import tz, rrule

class OutlookManager:
    def __init__(self, ics_url=None):
        self.ics_url = ics_url

    def get_upcoming_meetings(self, filter_str=None):
        """Bugün için yaklaşan toplantıları getirir. ICS URL varsa onu önceler, yoksa COM kullanır."""
        if self.ics_url:
            return self._get_meetings_from_ics()
        return self._get_meetings_from_com(filter_str=filter_str)

    def _get_meetings_from_ics(self):
        meetings = []
        try:
            response = requests.get(self.ics_url, timeout=10)
            response.raise_for_status()
            
            cal = Calendar.from_ical(response.content)
            now = datetime.datetime.now(tz.tzlocal())
            today = datetime.date.today()

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get('summary'))
                    start_val = component.get('dtstart').dt
                    
                    # Eğer datetime değilse (tüm gün etkinliği) datetime'a çevir
                    if isinstance(start_val, datetime.date) and not isinstance(start_val, datetime.datetime):
                        start_dt = datetime.datetime.combine(start_val, datetime.time.min).replace(tzinfo=tz.tzlocal())
                    elif start_val.tzinfo is None:
                        start_dt = start_val.replace(tzinfo=tz.tzlocal())
                    else:
                        start_dt = start_val.astimezone(tz.tzlocal())

                    # Süre hesapla
                    duration_obj = component.get('duration')
                    duration = 0
                    if duration_obj:
                        duration = int(duration_obj.dt.total_seconds() / 60)
                    else:
                        end = component.get('dtend')
                        if end:
                            end_dt = end.dt
                            if isinstance(end_dt, datetime.date) and not isinstance(end_dt, datetime.datetime):
                                end_dt = datetime.datetime.combine(end_dt, datetime.time.min).replace(tzinfo=tz.tzlocal())
                            elif end_dt.tzinfo is None:
                                end_dt = end_dt.replace(tzinfo=tz.tzlocal())
                            else:
                                end_dt = end_dt.astimezone(tz.tzlocal())
                            duration = int((end_dt - start_dt).total_seconds() / 60)

                    location = str(component.get('location', ''))

                    # TEKRARLAMA (RRULE) KONTROLÜ
                    rrule_prop = component.get('rrule')
                    if rrule_prop:
                        try:
                            # icalendar'ın rrule'unu dateutil'in anlayacağı stringe çevir
                            rrule_str = rrule_prop.to_ical().decode()
                            # rrulestr, dtstart parametresi ile birlikte kullanıldığında başlangıç tarihini baz alarak hesaplar
                            # Ancak dtstart'ın timezone bilgisi dateutil'de bazen karmaşa yaratır, 
                            # Bu yüzden başlangıç tarihini rrule'un başlangıcı olarak set ediyoruz.
                            rule = rrule.rrulestr(rrule_str, dtstart=start_dt)
                            
                            # Bugün için olası tarihler (Gün başlangıcı ve sonu arasında)
                            day_start = datetime.datetime.combine(today, datetime.time.min).replace(tzinfo=tz.tzlocal())
                            day_end = datetime.datetime.combine(today, datetime.time.max).replace(tzinfo=tz.tzlocal())
                            
                            # Bugün gerçekleşen tüm instance'ları bul
                            occurrences = rule.between(day_start, day_end, inc=True)
                            for occ in occurrences:
                                meetings.append({
                                    "subject": summary,
                                    "start": occ.replace(tzinfo=None),
                                    "duration": duration,
                                    "location": location
                                })
                        except Exception as re:
                            print(f"Rrule işleme hatası: {re}")
                    else:
                        # Tek seferlik toplantı
                        if start_dt.date() == today:
                            meetings.append({
                                "subject": summary,
                                "start": start_dt.replace(tzinfo=None),
                                "duration": duration,
                                "location": location
                            })
        except Exception as e:
            print(f"ICS verisi alınırken hata: {e}")
        return meetings

    def _get_meetings_from_com(self, filter_str=None):
        """Klasik COM yöntemi."""
        meetings = []
        try:
            pythoncom.CoInitialize()
            outlook = None
            try:
                outlook = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                try:
                    outlook = win32com.client.DispatchEx("Outlook.Application")
                except Exception:
                    try:
                        outlook = win32com.client.Dispatch("Outlook.Application")
                    except Exception:
                        return []
            
            if not outlook:
                return []

            ns = outlook.GetNamespace("MAPI")
            calendar = ns.GetDefaultFolder(9)
            items = calendar.Items
            items.Sort("[Start]")
            items.IncludeRecurrences = True
            
            if not filter_str:
                today = datetime.date.today()
                start_date = today.strftime("%Y-%m-%d 00:00")
                end_date = today.strftime("%Y-%m-%d 23:59")
                filter_str = "[Start] >= '" + start_date + "' AND [Start] <= '" + end_date + "'"
            
            try:
                today_items = items.Restrict(filter_str)
            except Exception:
                return []
            
            now = datetime.datetime.now()
            for item in today_items:
                try:
                    start_time = item.Start.replace(tzinfo=None)
                    meetings.append({
                        "subject": item.Subject,
                        "start": start_time,
                        "duration": item.Duration,
                        "location": item.Location
                    })
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            pythoncom.CoUninitialize()
        return meetings
