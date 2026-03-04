# Antigravity Agent Skill Kullanım Kılavuzu

Bu dizin altındaki yetenekler (skills), Antigravity AI asistanının belirli görevleri (kod inceleme, dokümantasyon yazma vb.) daha uzmanlaşmış ve yapılandırılmış bir şekilde yerine getirmesini sağlar.

## Mevcut Yetenekler ve Kullanım Şekilleri

### 1. Kod Gözden Geçirme (Code Reviewer)
**Ne zaman kullanılır?** Yeni yazdığınız bir kodu, bir fonksiyonu veya büyük bir değişikliği teknik olarak inceletmek istediğinizde.
**Nasıl kullanılır?** Aşağıdaki gibi komutlar verebilirsiniz:
- "Bu fonksiyon için code review yapar mısın?"
- "Yazdığım son değişiklikleri `/code-review` yeteneği ile incele."
- "Kodda hata veya performans sorunu var mı bir bak."

### 2. Dokümantasyon Yazarı (Document Writer)
**Ne zaman kullanılır?** Projenin genel yapısını, özelliklerini veya teknik detaylarını belgelemek istediğinizde.
**Nasıl kullanılır?** İstediğiniz derinliği (MODE) belirterek talep edebilirsiniz:
- "Proje için [MODE: FEATURE LIST] hazırlasın."
- "Bu sayfanın nasıl çalıştığını [MODE: DETAILED DOCS] olarak yaz."
- "Genel bir proje özeti çıkar (HIGH-LEVEL SUMMARY)."

### 3. Prompt Geliştirici (Prompt Engineer)
**Ne zaman kullanılır?** Yapay zekaya (bana veya başka bir modele) vermek istediğiniz bir talimatın daha iyi sonuç vermesini istediğinizde.
**Nasıl kullanılır?** Geliştirilmesini istediğiniz promptu paylaşarak:
- "Şu promptu optimize et: [Prompt içeriği]"
- "Bu işi yapması için en iyi promptu hazırlar mısın?"

---

## Nasıl Çalışır?
Siz bu görevlerden birini istediğinizde, ben otomatik olarak ilgili `.agent/skills/.../SKILL.md` dosyasındaki uzman talimatlarını okur ve o role bürünerek yanıt veririm. Sizin teknik bir ayar yapmanıza gerek yoktur, sadece ne yapmak istediğinizi söylemeniz yeterlidir.
