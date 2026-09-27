from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
assets = root / 'app/src/main/res/drawable'
out = Path(__file__).with_name('senlis-preview.png')
serif = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
sans = '/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf'
bold = '/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf'
ink, gold, cream, muted = '#120c09', '#f8deb2', '#fff5e3', '#c2ab97'
im = Image.new('RGB', (1260, 870), '#24160f')
d = ImageDraw.Draw(im)

def txt(x, y, s, n=14, color=cream, face=sans):
    d.multiline_text((x, y), s, font=ImageFont.truetype(face, n), fill=color, spacing=3)

def box(coords, color, radius=12, edge=None):
    d.rounded_rectangle(coords, radius=radius, fill=color, outline=edge)

def photo(name, w, h):
    original = Image.open(assets / name).convert('RGB')
    ratio = max(w / original.width, h / original.height)
    original = original.resize((round(original.width * ratio), round(original.height * ratio)), Image.Resampling.LANCZOS)
    left = (original.width - w) // 2
    top = (original.height - h) // 2
    return original.crop((left, top, left + w, top + h))

txt(75, 14, 'SENLIS', 62, gold, serif)
txt(80, 838, 'KOKU, SENİN HİKÂYENDİR   ·   ANDROID TASARIM ÖNİZLEMESİ', 12, muted, bold)
xs, y, w, h = (72, 463, 854), 103, 330, 709
for x in xs:
    box((x-7, y-7, x+w+7, y+h+7), '#060504', 37, '#a4815d')
    box((x, y, x+w, y+h), ink, 31)

# Welcome, with the original editorial image.
x = xs[0]
im.paste(photo('welcome_hero.jpg', w, h), (x, y))
shade = Image.new('RGBA', (w, h), (0, 0, 0, 0))
sd = ImageDraw.Draw(shade)
for row in range(h):
    alpha = round(236 * max(0, (row/h - .45) / .55))
    sd.line((0, row, w, row), fill=(18, 12, 9, alpha))
im.paste(shade, (x, y), shade)
d = ImageDraw.Draw(im)
txt(x+21, y+13, '9:41', 11, cream, bold)
txt(x+278, y+13, '● ▰', 11)
txt(x+22, y+45, 'SENLIS', 23, cream, serif)
txt(x+22, y+449, 'Koku, senin\nhikâyendir.', 32, cream, serif)
txt(x+23, y+550, 'Kendini yansıtan kokuyu keşfet.\nHer koku, hayatının farklı bir anını anlatır.', 13)
box((x+22, y+625, x+w-22, y+675), gold, 14)
txt(x+111, y+640, 'Hemen Başla  →', 15, ink, bold)

# Discover, with transparent example-data labeling.
x = xs[1]
txt(x+20, y+13, '9:41', 11, cream, bold)
txt(x+278, y+13, '● ▰', 11)
txt(x+20, y+46, 'SENLIS', 22, gold, serif)
txt(x+20, y+79, 'Koku, senin hikâyendir.', 12, muted)
im.paste(photo('fragrance_editorial.jpg', 290, 197), (x+20, y+105))
d = ImageDraw.Draw(im)
txt(x+30, y+250, 'SANA ÖZEL KEŞİF', 10, gold, bold)
txt(x+30, y+270, 'Kokunu birlikte bulalım.', 20, cream, serif)
txt(x+19, y+319, 'Sana Özel Öneriler', 22, cream, serif)
txt(x+20, y+354, 'Tercihlerine göre sıralanan editoryal örnekler', 11, muted)
box((x+19, y+383, x+311, y+442), '#2b1f17', 10, '#694a31')
txt(x+29, y+389, 'ÖNİZLEME KATALOĞU', 10, gold, bold)
txt(x+29, y+409, 'Bu isimler örnektir. Gerçek markalar\ndoğrulanmış katalogla eklenecek.', 11)
for top, name, detail, score in [(452, 'Jasmin Amber', 'EDP · çiçeksi · yasemin', '%88 tahmini uyum'), (551, 'Vanilla Veil', 'Body mist · gurme · vanilya', '%76 tahmini uyum')]:
    box((x+19, y+top, x+311, y+top+90), '#291c16', 12, '#4e3728')
    im.paste(photo('fragrance_editorial.jpg', 66, 78), (x+25, y+top+6))
    d = ImageDraw.Draw(im)
    txt(x+105, y+top+8, name, 15, cream, serif)
    txt(x+105, y+top+34, detail, 11, muted)
    txt(x+105, y+top+60, score, 12, gold, bold)
box((x, y+664, x+w, y+h), '#1b120e', 0)
for i, name in enumerate(('Keşfet', 'Ara', 'Favoriler', 'Sohbet', 'Profil')):
    txt(x+12+i*65, y+680, name, 10, gold if i == 0 else cream)

# Product detail, using an unbranded editorial image.
x = xs[2]
im.paste(photo('fragrance_editorial.jpg', w, 335), (x, y))
d = ImageDraw.Draw(im)
txt(x+19, y+13, '9:41', 11, cream, bold)
txt(x+278, y+13, '● ▰', 11)
txt(x+18, y+48, '‹  Geri', 17)
txt(x+287, y+46, '♡', 22, gold)
box((x, y+326, x+w, y+h), '#fff3df', 22)
txt(x+19, y+350, 'EDİTORYAL ÖRNEK · GERÇEK ÜRÜN DEĞİL', 9, '#805629', bold)
txt(x+19, y+375, 'Jasmin Amber', 24, ink, serif)
txt(x+19, y+414, 'Parfüm · EDP · çiçeksi', 12, '#725b4b')
txt(x+19, y+454, '%88 tahmini eşleşme', 18, '#8a551f', bold)
txt(x+19, y+481, 'Tercihlerinden hesaplanan bir tahmin.', 11, '#725b4b')
txt(x+19, y+522, 'KOKU NOTALARI', 11, '#8a551f', bold)
for i, value in enumerate(('Yasemin', 'Vanilya', 'Amber')):
    left = x+19+i*99
    box((left, y+544, left+88, y+576), '#f4e6cf', 15)
    txt(left+9, y+552, value, 11, ink)
txt(x+19, y+595, 'NEDEN ÖNERİLDİ?', 11, '#8a551f', bold)
txt(x+19, y+616, '✦  Sevdiğin notalarla uyumlu\n✦  Çiçeksi aileyi seçtin\n✦  Aradığın hisle örtüşüyor', 12, ink)
im.save(out)
print(out)
