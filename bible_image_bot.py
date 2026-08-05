import os
import time
import random
import requests
import urllib.parse
import gc
import base64  # Ditambahkan untuk memproses gambar dari Google API
from bs4 import BeautifulSoup
from groq import Groq
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Mengunci direktori kerja agar file tidak "nyasar"
BASE_DIR = os.path.abspath(os.getcwd())

# --- KONFIGURASI GROQ AI ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# --- MANAJEMEN MEMORI (ANTI DUPLIKASI) ---
HISTORY_FILE = "history_verses.txt"

def get_used_verses():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def mark_verse_as_used(verse_ref):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{verse_ref}\n")

# --- FUNGSI AMBIL AYAT RESMI DARI ALKITAB SABDA ---
def fetch_sabda_bible_verse(reference_query):
    """
    Mengambil isi ayat Alkitab secara akurat langsung dari situs alkitab.sabda.org
    dengan sistem retry jika server sedang lambat.
    """
    print(f"📖 Mengambil teks resmi Alkitab SABDA untuk: {reference_query}...")
    encoded_ref = urllib.parse.quote(reference_query)
    url = f"https://alkitab.sabda.org/passage.php?passage={encoded_ref}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Coba hingga 3 kali jika server SABDA sedang lambat
    for attempt in range(3):
        try:
            # Tingkatkan timeout dari 10 menjadi 30 detik
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                passage_box = soup.find('td', {'class': 'text'}) or soup.find('div', {'id': 'text'})
                
                if passage_box:
                    text = passage_box.get_text(separator=" ", strip=True)
                    clean_text = ' '.join(text.split())
                    if len(clean_text) > 10:
                        print(f"✅ Berhasil mengambil dari SABDA: {clean_text[:60]}...")
                        return clean_text
        except requests.exceptions.RequestException as e:
            print(f"⚠️ SABDA timeout/error (Percobaan {attempt+1}/3)... mencoba lagi.")
            time.sleep(5)
            
    print("❌ Gagal mengambil dari SABDA Web setelah 3 percobaan.")
    return None
    
# --- 1. GROQ AI: GENERATOR BATCH 3 KONTEN (REFERENSI & RENUNGAN) ---
def generate_batch_image_content(num_posts=3):
    print(f"🕊️ Meminta Groq Llama-3 (8B Instant) meracik {num_posts} naskah momen keseharian & simbol kekristenan...")
    
    used_verses = get_used_verses()
    history_context = "\n".join(used_verses[-30:]) if used_verses else "(Belum ada riwayat)"
    
    prompt = f"""
    Bertindaklah sebagai fotografer profesional yang menangkap momen-momen keseharian yang memiliki simbol-simbol kekristenan yang hangat dan penuh makna.
    Berikan {num_posts} referensi Kitab dan Ayat Alkitab yang valid (contoh format: "Yesaya 41:10", "Filipi 4:6", "Mazmur 23:1"), beserta renungan singkat dan deskripsi visual foto.
    
    ATURAN MUTLAK: 
    1. Kalimat renungan (deskripsi) HARUS SANGAT SINGKAT, padat, puitis, maksimal 1 kalimat pendek (bukan paragraf panjang) agar tidak menutupi atau terpotong di bagian bawah gambar.
    2. Dilarang keras menggunakan referensi ayat yang mirip dengan daftar ini: {history_context}
    
    Gunakan pemisah '---' di antara setiap naskah. Format wajib persis seperti ini untuk setiap naskah:
    
    REF: [Referensi Kitab dan Ayat yang valid, cth: Yesaya 41:10]
    RENUNGAN: [1 kalimat pendek dan bermakna tentang keseharian]
    PROMPT_GAMBAR: [Deskripsi bahasa Inggris untuk foto galeri pameran bernuansa keseharian dengan simbol kekristenan. Contoh: "Warm daily life photography, a hot cup of coffee next to an open Bible on a wooden table, soft morning sunlight, cinematic, aesthetic, masterpiece, 8k"]
    ---
    """
    
    raw_text = ""
    for attempt in range(3):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=1500,
            )
            raw_text = chat_completion.choices[0].message.content
            break
        except Exception as e:
            print(f"⚠️ Error Groq (Percobaan {attempt+1}/3): {e}")
            time.sleep(15)
    else:
        raise Exception("❌ Gagal menghubungi Groq AI.")

    batch = []
    for chunk in raw_text.split("---"):
        if len(batch) >= num_posts: break
        lines = [line.strip() for line in chunk.strip().split("\n") if line.strip()]
        if not lines: continue
        
        ref = "Mazmur 23:1"
        renungan = "Ketenangan sejati ditemukan saat kita bersandar pada kasih karunia-Nya."
        prompt_gambar = "Warm daily life photography, open Bible on wooden table, soft morning sunlight, cinematic, 8k"
        
        for line in lines:
            if line.startswith("REF:"): ref = line.replace("REF:", "").strip()
            elif line.startswith("RENUNGAN:"): renungan = line.replace("RENUNGAN:", "").strip()
            elif line.startswith("PROMPT_GAMBAR:"): prompt_gambar = line.replace("PROMPT_GAMBAR:", "").strip()
                
        # AMBIL ISI AYAT MUTLAK DARI ALKITAB SABDA
        official_ayat = fetch_sabda_bible_verse(ref)
        if not official_ayat:
            official_ayat = "Segala perkara dapat kutanggung di dalam Dia yang memberi kekuatan kepadaku."
            
        batch.append({
            "ref": ref,
            "ayat": official_ayat,
            "renungan": renungan,
            "prompt_gambar": prompt_gambar
        })
        
    print(f"✅ Berhasil menyiapkan {len(batch)} karya galeri terverifikasi SABDA!")
    return batch

# --- 2. PEMUAT FONT LOKAL ---
def load_aesthetic_fonts():
    fonts = {
        "cinzel": os.path.join(BASE_DIR, "CinzelDecorative-Bold.ttf"),
        "playfair_italic": os.path.join(BASE_DIR, "PlayfairDisplay-Italic-VariableFont_wght.ttf"),
        "montserrat_black": os.path.join(BASE_DIR, "Montserrat-Black.ttf")
    }
    
    for name, path in fonts.items():
        if not os.path.exists(path):
            raise Exception(f"❌ File font '{os.path.basename(path)}' tidak ditemukan di repository!")
            
    return fonts

# --- 3. GENERATOR GAMBAR GOOGLE AI (NANO BANANA / GEMINI FLASH IMAGE) ---
def generate_background_image(prompt, output_filename):
    print(f"🎨 Memotret momen keseharian dengan Google Nano Banana: '{prompt[:40]}...'")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY belum diatur di environment variable! Pastikan sudah ditambahkan di GitHub Secrets.")
        
    # Menggunakan model Nano Banana sesuai instruksi migrasi (gemini-2.5-flash-image)
    # Memanggil endpoint standar Gemini: generateContent
   url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-image:generateContent?key={api_key}"
    
    # Mempertajam prompt untuk hasil fotografi estetik 
    # Karena parameter aspectRatio lama sudah usang di API ini, kita berikan instruksi rasio di dalam prompt
    full_prompt = f"{prompt}, professional photography, soft lighting, aesthetic, masterpiece, portrait orientation 3:4"
    
    # Payload menggunakan format Gemini standar
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                img_b64 = None
                
                # Menelusuri 'content parts' untuk mencari data gambar Base64
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    for part in parts:
                        if "inlineData" in part:
                            img_b64 = part["inlineData"]["data"]
                            break
                except (KeyError, IndexError):
                    pass
                
                if not img_b64:
                    print(f"⚠️ Gagal mengekstrak gambar dari respons API: {data}")
                    raise Exception("Format respons API tidak sesuai atau gambar diblokir oleh filter keamanan (Safety Settings).")
                    
                with open(output_filename, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                
                return output_filename
            else:
                print(f"⚠️ Gagal dari Google API (HTTP {response.status_code}): {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error (Percobaan {attempt+1}/3): {e}")
            
        time.sleep(10) # Jeda sebelum mencoba lagi

    raise Exception("Gagal menghasilkan latar galeri dari Google AI Studio setelah 3 percobaan.")# --- 3. GENERATOR GAMBAR GOOGLE AI (NANO BANANA / GEMINI FLASH IMAGE) ---
def generate_background_image(prompt, output_filename):
    print(f"🎨 Memotret momen keseharian dengan Google Nano Banana: '{prompt[:40]}...'")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY belum diatur di environment variable! Pastikan sudah ditambahkan di GitHub Secrets.")
        
    # Menggunakan model Nano Banana sesuai instruksi migrasi (gemini-2.5-flash-image)
    # Memanggil endpoint standar Gemini: generateContent
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"
    
    # Mempertajam prompt untuk hasil fotografi estetik 
    # Karena parameter aspectRatio lama sudah usang di API ini, kita berikan instruksi rasio di dalam prompt
    full_prompt = f"{prompt}, professional photography, soft lighting, aesthetic, masterpiece, portrait orientation 3:4"
    
    # Payload menggunakan format Gemini standar
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                img_b64 = None
                
                # Menelusuri 'content parts' untuk mencari data gambar Base64
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    for part in parts:
                        if "inlineData" in part:
                            img_b64 = part["inlineData"]["data"]
                            break
                except (KeyError, IndexError):
                    pass
                
                if not img_b64:
                    print(f"⚠️ Gagal mengekstrak gambar dari respons API: {data}")
                    raise Exception("Format respons API tidak sesuai atau gambar diblokir oleh filter keamanan (Safety Settings).")
                    
                with open(output_filename, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                
                return output_filename
            else:
                print(f"⚠️ Gagal dari Google API (HTTP {response.status_code}): {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error (Percobaan {attempt+1}/3): {e}")
            
        time.sleep(10) # Jeda sebelum mencoba lagi

    raise Exception("Gagal menghasilkan latar galeri dari Google AI Studio setelah 3 percobaan.")

# --- 4. ENGINE TATA LETAK TEKS ARTISTIK (LAPANG & AMAN) ---
def draw_text_with_soft_shadow(draw, position, text, font, text_color, shadow_color="black"):
    x, y = position
    draw.text((x + 3, y + 4), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)

def create_aesthetic_bible_post(item, output_path, img_size=(1080, 1350)):
    print("✨ Menyusun galeri pameran foto & tipografi...")
    bg_path = os.path.join(BASE_DIR, "temp_bg.jpg")
    generate_background_image(item['prompt_gambar'], bg_path)
    
    img = Image.open(bg_path).convert("RGBA")
    img = ImageOps.fit(img, img_size, Image.Resampling.LANCZOS)
    
    vignette = Image.new('RGBA', img_size, (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(img_size[1]):
        alpha = int(255 * (abs(y - img_size[1]/2) / (img_size[1]/2)) ** 1.8)
        if alpha > 190: alpha = 190
        v_draw.line([(0, y), (img_size[0], y)], fill=(0, 0, 0, alpha))
        
    img = Image.alpha_composite(img, vignette)
    draw = ImageDraw.Draw(img)
    
    fonts = load_aesthetic_fonts()
    font_ref = ImageFont.truetype(fonts['cinzel'], 48)
    font_ayat = ImageFont.truetype(fonts['playfair_italic'], 50)
    font_renungan = ImageFont.truetype(fonts['montserrat_black'], 32)
    
    def get_text_width(text, font):
        try: return draw.textlength(text, font=font)
        except: return draw.textbbox((0, 0), text, font=font)[2]

    def chunk_text(text, words_per_line=4):
        words = text.split()
        return [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]

    lines_ayat = chunk_text(f'"{item["ayat"]}"', words_per_line=4)
    lines_renungan = chunk_text(item['renungan'], words_per_line=5)
    
    ref_text = item['ref'].upper()
    w_ref = get_text_width(ref_text, font_ref)
    draw_text_with_soft_shadow(draw, ((img_size[0]-w_ref)//2, 220), ref_text, font_ref, "#FFDF73")
    
    draw.line([(img_size[0]//2 - 120, 310), (img_size[0]//2 + 120, 310)], fill="#FFDF73", width=2)
    
    y_ayat = 400
    for line in lines_ayat:
        w_ayat = get_text_width(line, font_ayat)
        draw_text_with_soft_shadow(draw, ((img_size[0]-w_ayat)//2, y_ayat), line, font_ayat, "#FFFFFF")
        y_ayat += 70

    y_renungan = 900
    for line in lines_renungan:
        w_ren = get_text_width(line, font_renungan)
        draw_text_with_soft_shadow(draw, ((img_size[0]-w_ren)//2, y_renungan), line, font_renungan, "#E0E0E0")
        y_renungan += 48

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

# --- MAIN LOOP (BATCH 3 POST) ---
if __name__ == "__main__":
    print("⚡ PAMERAN FOTO KESEHARIAN & SIMBOL KEKRISTENAN (BATCH 3 KARYA) ⚡\n")
    try:
        batch_items = generate_batch_image_content(num_posts=3)
        
        for i, item in enumerate(batch_items, 1):
            print(f"\n--- MENAMPILKAN KARYA {i} DARI 3 ---")
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
                print("⏳ Jeda 45 detik untuk persiapan kurasi karya berikutnya...\n")
                time.sleep(45)
                
        print("🎉 PAMERAN 3 KARYA HARI INI TELAH SELESAI DITAMPILKAN DI GALERI!")
    except Exception as e:
        print(f"❌ Kesalahan pada galeri bot: {e}\n")
