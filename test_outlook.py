import win32com.client
import pythoncom
import datetime
import sys

def test_outlook():
    print("--- Outlook Bağlantı Testi ---")
    try:
        pythoncom.CoInitialize()
        print("1. COM Başlatıldı.")
        
        try:
            print("2. Çalışan Outlook örneği aranıyor (GetActiveObject)...")
            outlook = win32com.client.GetActiveObject("Outlook.Application")
            print("   [TAMAM] Çalışan Outlook bulundu.")
        except Exception as e:
            print(f"   [BİLGİ] Çalışan Outlook bulunamadı, DispatchEx deneniyor... ({e})")
            try:
                # DispatchEx her zaman yeni bir süreç başlatmaya çalışır
                outlook = win32com.client.DispatchEx("Outlook.Application")
                print("   [TAMAM] Outlook DispatchEx ile başlatıldı.")
            except Exception as e2:
                print(f"   [BİLGİ] DispatchEx başarısız, normal Dispatch deneniyor... ({e2})")
                try:
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    print("   [TAMAM] Outlook normal Dispatch ile başlatıldı.")
                except Exception as e3:
                    print(f"   [HATA] Outlook hiçbir yöntemle başlatılamadı! ({e3})")
                    print("\nMuhtemelen 'Yeni Outlook' (New Outlook) yüklü ve klasik COM erişimini engelliyor.")
                    return

        ns = outlook.GetNamespace("MAPI")
        print("3. MAPI Namespace alındı.")
        
        calendar = ns.GetDefaultFolder(9)
        print("4. Takvim klasörüne erişildi.")
        
        items = calendar.Items
        items.Sort("[Start]")
        items.IncludeRecurrences = True
        
        today = datetime.date.today()
        start_date = today.strftime("%Y-%m-%d 00:00")
        end_date = today.strftime("%Y-%m-%d 23:59")
        filter_str = "[Start] >= '" + start_date + "' AND [Start] <= '" + end_date + "'"
        
        print(f"5. Bugünün toplantıları listeleniyor ({today})...")
        today_items = items.Restrict(filter_str)
        
        count = 0
        for item in today_items:
            print(f"   - {item.Start}: {item.Subject}")
            count += 1
        
        if count == 0:
            print("   [BİLGİ] Bugün için takvimde toplantı bulunamadı.")
        else:
            print(f"   [TAMAM] {count} adet toplantı listelendi.")

    except Exception as e:
        print(f"\n[GENEL HATA] Beklenmedik bir sorun oluştu: {e}")
    finally:
        pythoncom.CoUninitialize()
        print("\n--- Test Bitti ---")

if __name__ == "__main__":
    test_outlook()
