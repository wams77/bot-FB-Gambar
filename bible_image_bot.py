import os
import time
import random
import requests
import urllib.parse
import re
import gc
from bs4 import BeautifulSoup
from groq import Groq
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Mengunci direktori kerja
BASE_DIR = os.path.abspath(os.getcwd())

# --- KONFIGURASI API ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

if not PEXELS_API_KEY:
    raise Exception("PEXELS_API_KEY belum diatur di environment variable/GitHub Secrets!")

# --- MANAJEMEN MEMORI (ANTI DUPLIKASI AYAT) ---
HISTORY_FILE = "history_verses.txt"

def get_used_verses():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def mark_verse_as_used(verse_ref):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{verse_ref}\n")

# --- FITUR BARU: TARIK TEKS LANGSUNG DARI API SABDA (ANTI-BLOKIR) ---
def fetch_verse_direct_sabda(reference):
    """
    Mengambil isi ayat langsung dari API resmi Alkitab SABDA tanpa 
    melewati mesin pencari, sehingga kebal dari pemblokiran bot/CAPTCHA.
    """
    print(f"🔍 Menarik teks resmi '{reference}' langsung dari API SABDA...")
    
    # Format URL ke API SABDA
    query = urllib.parse.quote(reference)
    url = f"https://alkitab.sabda.org/api/passage.php?passage={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BibleBot/1.0"
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # SABDA mengembalikan data dalam format XML sederhana
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Mengambil semua teks di dalam tag <text>
                text_tags = soup.find_all('text')
                
                if text_tags:
                    # Gabungkan jika ada lebih dari 1 ayat, lalu bersihkan
                    full_text = " ".join([t.get_text(strip=True) for t in text_tags])
                    
                    # Bersihkan angka ayat di awal/tengah kalimat (contoh: "19 Karena..." atau "[19]")
                    clean_text = re.sub(r'^\d+\s*', '', full_text)
                    clean_text = re.sub(r'\[\d+\]\s*', '', clean_text)
                    
                    if len(clean_text) > 10:
                        print(f"   ✅ Ayat didapat: \"{clean_text[:60]}...\"")
                        return clean_text
            else:
                print(f"   ⚠️ API SABDA merespons dengan HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Error koneksi SABDA (Percobaan {attempt+1}/3): {e}")
            
        time.sleep(3)
        
    print(f"   ❌ Gagal menarik ayat '{reference}' dari SABDA.")
    return None

# --- 1. GROQ AI: MENGHASILKAN REFERENSI & RENUNGAN SAJA ---
def generate_batch_image_content(num_posts=3):
    print(f"🕊️ Meminta Groq Llama-3 menyusun {num_posts} referensi ayat yang unik...")
    
    used_verses = get_used_verses()
    history_context = "\n".join(used_verses[-50:]) if used_verses else "(Belum ada riwayat)"
    
    prompt = f"""
    Bertindaklah sebagai pendeta dan ahli teologi Alkitab.
    Pilih {num_posts} referensi Ayat Alkitab yang BERAGAM dari seluruh isi Alkitab (Perjanjian Lama & Baru), beserta renungan singkat.
    
    ATURAN MUTLAK KETAT: 
    1. Hanya berikan REFERENSI AYAT dan RENUNGAN saja. JANGAN MENULIS TEKS ISI AYAT (Kami akan mengambilnya sendiri dari SABDA).
    2. Kalimat renungan HARUS SINGKAT (maksimal 1 kalimat).
    3. DILARANG KERAS menggunakan referensi ayat yang sudah pernah dipakai dalam riwayat berikut: 
    {history_context}
    
    Gunakan pemisah '---' di antara setiap naskah. Format wajib persis seperti ini:
    
    REF: [Referensi Kitab dan Ayat, cth: Mazmur 34:19]
    RENUNGAN: [1 kalimat renungan]
    ---
    """
    
    raw_text = ""
    for attempt in range(3):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.8,
                max_tokens=1000,
            )
            raw_text = chat_completion.choices[0].message.content
            break
        except Exception as e:
            print(f"⚠️ Error Groq (Percobaan {attempt+1}/3): {e}")
            time.sleep(10)
    else:
        raise Exception("❌ Gagal menghubungi Groq AI.")

    batch = []
    for chunk in raw_text.split("---"):
        if len(batch) >= num_posts: break
        lines = [line.strip() for line in chunk.strip().split("\n") if line.strip()]
        if not lines: continue
        
        ref = None
        renungan = None
        
        for line in lines:
            line_upper = line.upper()
            if "REF:" in line_upper:
                ref = line.split(":", 1)[1].strip()
            elif "RENUNGAN:" in line_upper:
                renungan = line.split(":", 1)[1].strip()
                
        if ref: ref = ref.replace("[", "").replace("]", "").strip()
        if renungan: renungan = renungan.replace("[", "").replace("]", "").strip()
            
        if ref:
            # Mengambil isi ayat langsung dari API SABDA
            official_ayat = fetch_verse_direct_sabda(ref)
            
            if official_ayat:
                batch.append({
                    "ref": ref,
                    "ayat": official_ayat,
                    "renungan": renungan if renungan else "Tuhan selalu menyertai kita."
                })
            else:
                print(f"⚠️ Referensi '{ref}' dilewati karena teks gagal ditarik dari SABDA.")
        
    if len(batch) == 0:
        raise Exception("❌ KEGAGALAN KRITIS: Tidak ada referensi ayat yang berhasil ditarik teksnya dari SABDA.")
        
    print(f"✅ Berhasil menyiapkan {len(batch)} naskah dengan teks murni dari SABDA!")
    return batch

# --- 2. GENERATOR LATAR BELAKANG ESTETIK (PEXELS API) ---
def generate_background_image(output_filename):
    print("🎨 Mencari foto latar belakang estetik dari Pexels...")
    
    themes = ["aesthetic morning nature", "peaceful landscape", "warm coffee table", 
              "cinematic nature sunset", "calm ocean wave", "soft sunlight forest"]
    search_query = random.choice(themes)
    
    random_page = random.randint(1, 4)
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=15&page={random_page}&orientation=portrait"
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                if not data.get("photos"):
                    raise Exception("Pexels tidak menemukan foto.")
                
                selected_photo = random.choice(data["photos"])
                image_url = selected_photo["src"]["large2x"] 
                
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    with open(output_filename, 'wb') as f:
                        f.write(img_response.content)
                    return output_filename
            else:
                print(f"⚠️ Pexels Error {response.status_code}. Mencoba ulang...")
        except Exception as e:
            print(f"⚠️ Jaringan lambat (Percobaan {attempt+1}/3): {e}")
        time.sleep(5)

    raise Exception("Gagal mengunduh latar galeri dari Pexels.")

# --- 3. PEMUAT FONT LOKAL ---
def load_aesthetic_fonts():
    fonts = {
        "cinzel": os.path.join(BASE_DIR, "CinzelDecorative-Bold.ttf"),
        "playfair_italic": os.path.join(BASE_DIR, "PlayfairDisplay-Italic-VariableFont_wght.ttf"),
        "montserrat_black": os.path.join(BASE_DIR, "Montserrat-Black.ttf")
    }
    for name, path in fonts.items():
        if not os.path.exists(path):
            raise Exception(f"❌ File font '{os.path.basename(path)}' tidak ditemukan!")
    return fonts

# --- 4. ENGINE TATA LETAK TEKS ARTISTIK ---
def create_aesthetic_bible_post(item, output_path, img_size=(1080, 1350)):
    print("✨ Menyusun galeri pameran foto & tipografi...")
    
    bg_path = os.path.join(BASE_DIR, "temp_bg.jpg")
    generate_background_image(bg_path)
    
    img = Image.open(bg_path).convert("RGBA")
    img = ImageOps.fit(img, img_size, Image.Resampling.LANCZOS)
    
    vignette = Image.new('RGBA', img_size, (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(img_size[1]):
        alpha = int(255 * (abs(y - img_size[1]/2) / (img_size[1]/2)) ** 1.3)
        if alpha > 220: alpha = 220
        v_draw.line([(0, y), (img_size[0], y)], fill=(0, 0, 0, alpha))
        
    img = Image.alpha_composite(img, vignette)
    draw = ImageDraw.Draw(img)
    
    fonts = load_aesthetic_fonts()
    font_ref = ImageFont.truetype(fonts['cinzel'], 48)
    font_ayat = ImageFont.truetype(fonts['playfair_italic'], 48)
    font_renungan = ImageFont.truetype(fonts['montserrat_black'], 30)
    
    def get_text_width(text, font):
        try: return draw.textlength(text, font=font)
        except: return draw.textbbox((0, 0), text, font=font)[2]

    def chunk_text(text, words_per_line=5):
        words = text.split()
        return [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]

    lines_ayat = chunk_text(f'"{item["ayat"]}"', words_per_line=4)
    lines_renungan = chunk_text(item['renungan'], words_per_line=5)
    
    def draw_shadowed_text(pos, text, font, color):
        x, y = pos
        draw.text((x+2, y+2), text, font=font, fill="black") 
        draw.text((x, y), text, font=font, fill=color)       

    ref_text = item['ref'].upper()
    w_ref = get_text_width(ref_text, font_ref)
    draw_shadowed_text(((img_size[0]-w_ref)//2, 220), ref_text, font_ref, "#FFDF73")
    draw.line([(img_size[0]//2 - 120, 300), (img_size[0]//2 + 120, 300)], fill="#FFDF73", width=2)
    
    y_ayat = 400
    for line in lines_ayat:
        w_ayat = get_text_width(line, font_ayat)
        draw_shadowed_text(((img_size[0]-w_ayat)//2, y_ayat), line, font_ayat, "#FFFFFF")
        y_ayat += 65

    y_renungan = 950
    for line in lines_renungan:
        w_ren = get_text_width(line, font_renungan)
        draw_shadowed_text(((img_size[0]-w_ren)//2, y_renungan), line, font_renungan, "#E0E0E0")
        y_renungan += 44

    final_img = img.convert("RGB")
    final_img.save(output_path, quality=100)
    
    if os.path.exists(bg_path): os.remove(bg_path)
    print("✅ Karya galeri berhasil dicetak!")
    return output_path

# --- 5. UPLOAD KE FACEBOOK ---
def upload_photo_to_facebook(image_path, caption):
    print("🚀 Mengunggah karya galeri ke Facebook...")
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_ACCESS_TOKEN")
    
    url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
    with open(image_path, 'rb') as f:
        response = requests.post(url, files={'source': f}, data={'caption': caption, 'access_token': access_token}).json()
        
    if "id" in response: 
        print("🎉 BERHASIL MENGUNGGAH KARYA KE GALERI FACEBOOK!\n")
    else: 
        raise Exception(f"Gagal upload: {response}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("⚡ PAMERAN FOTO KESEHARIAN & SIMBOL KEKRISTENAN (BATCH 3 KARYA) ⚡\n")
    try:
        batch_items = generate_batch_image_content(num_posts=3)
        
        for i, item in enumerate(batch_items, 1):
            print(f"\n--- MENAMPILKAN KARYA {i} DARI {len(batch_items)} ---")
            image_file = os.path.join(BASE_DIR, f"gallery_exhibit_{i}.jpg")
            caption = f"✨ {item['ref']} ✨\n\n\"{item['ayat']}\"\n\n{item['renungan']}\n\n#GaleriRohani #RenunganHarian #AyatAlkitab #SeniKristen #PameranIman"
            
            create_aesthetic_bible_post(item, image_file)
            
            if os.path.exists(image_file) and os.path.getsize(image_file) > 10000:
                upload_photo_to_facebook(image_file, caption)
            else:
                raise Exception(f"File karya ke-{i} gagal dibuat!")
                
            mark_verse_as_used(item['ref'])
            
            if os.path.exists(image_file):
                os.remove(image_file)
                
            gc.collect()
            
            if i < len(batch_items):
                print("⏳ Jeda 45 detik untuk kurasi karya berikutnya...\n")
                time.sleep(45)
                
        print("🎉 PAMERAN KARYA HARI INI TELAH SELESAI DITAMPILKAN DI GALERI!")
    except Exception as e:
        print(f"❌ Kesalahan pada galeri bot: {e}\n")
        exit(1)
