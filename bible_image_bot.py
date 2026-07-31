import os
import time
import random
import requests
import urllib.parse
import gc
from groq import Groq
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# Mengunci direktori kerja agar file tidak "nyasar"
BASE_DIR = os.path.abspath(os.getcwd())

# --- KONFIGURASI GROQ AI ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# --- MANAJEMEN MEMORI ---
HISTORY_FILE = "history_verses.txt"

def get_used_verses():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def mark_verse_as_used(verse_ref):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{verse_ref}\n")

# --- 1. GROQ AI: GENERATOR KONTEN ESTETIK ---
def generate_image_content():
    print("🕊️ Meminta Groq meracik naskah Alkitab dan imajinasi visual estetik...")
    
    used_verses = get_used_verses()
    history_context = "\n".join(used_verses[-25:]) if used_verses else "(Belum ada riwayat, buat topik bebas)"
    
    prompt = f"""
    Bertindaklah sebagai seniman rohani Kristen. Buatlah 1 naskah postingan ayat Alkitab dengan nilai seni tinggi.
    
    ATURAN ANTI-DUPLIKASI: Hindari ayat berikut: {history_context}
    
    Format wajib persis seperti ini:
    
    REF: [Referensi Kitab, cth: Mazmur 23:1]
    AYAT: [Isi ayat Alkitab]
    RENUNGAN: [1-2 kalimat renungan puitis yang menyentuh hati]
    CTA: [Ajakan lembut, cth: Ketik 'Amin' jika hatimu disentuh Tuhan.]
    PROMPT_GAMBAR: [Deskripsi bahasa Inggris yang SANGAT ARTISTIK untuk latar belakang. Gunakan kata kunci seperti: ethereal, divine holy light, renaissance oil painting style, majestic, highly aesthetic, masterpiece, 8k resolution. Jangan ada teks dalam gambar]
    """
    
    raw_text = ""
    for attempt in range(3):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024,
            )
            raw_text = chat_completion.choices[0].message.content
            break
        except Exception as e:
            print(f"⚠️ Error Groq: {e}")
            time.sleep(15)
    else:
        raise Exception("❌ Gagal menghubungi Groq AI.")

    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    ref, ayat, renungan, cta, prompt_gambar = "Yesaya 41:10", "Janganlah takut, sebab Aku menyertai engkau.", "Tuhan adalah pelukis takdir terindahmu.", "Ketik Amin.", "ethereal divine light rays breaking through clouds, renaissance masterpiece, 8k"
    
    for line in lines:
        if line.startswith("REF:"): ref = line.replace("REF:", "").strip()
        elif line.startswith("AYAT:"): ayat = line.replace("AYAT:", "").strip()
        elif line.startswith("RENUNGAN:"): renungan = line.replace("RENUNGAN:", "").strip()
        elif line.startswith("CTA:"): cta = line.replace("CTA:", "").strip()
        elif line.startswith("PROMPT_GAMBAR:"): prompt_gambar = line.replace("PROMPT_GAMBAR:", "").strip()
            
    return {"ref": ref, "ayat": ayat, "renungan": renungan, "cta": cta, "prompt_gambar": prompt_gambar}

# --- 2. PENGUNDUH FONT (DENGAN SISTEM SELF-HEALING ANTI KORUP) ---
def download_aesthetic_fonts():
    print("📥 Memeriksa dan mengunduh koleksi Font Estetik...")
    # Menggunakan path 'static' yang 100% valid di repository Google Fonts
    fonts = {
        "cinzel": "https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/static/Cinzel-Bold.ttf",
        "playfair_italic": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/static/PlayfairDisplay-Italic.ttf",
        "playfair_regular": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/static/PlayfairDisplay-Regular.ttf"
    }
    
    font_paths = {}
    for name, url in fonts.items():
        path = os.path.join(BASE_DIR, f"{name}.ttf")
        
        # PENGECEKAN KORUPSI: Jika file ada, tes apakah itu benar-benar Font (bukan HTML)
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 10)
            except Exception:
                print(f"⚠️ File {name}.ttf korup terdeteksi! Menghapus dan memperbaiki otomatis...")
                os.remove(path)
                
        # Jika file belum ada (atau baru saja dihapus karena korup), unduh yang baru
        if not os.path.exists(path):
            r = requests.get(url, allow_redirects=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(r.content)
                print(f"   -> Font {name} berhasil diunduh!")
            else:
                raise Exception(f"Gagal mengunduh font {name}. HTTP Status: {r.status_code}")
                
        font_paths[name] = path
    return font_paths

# --- 3. GENERATOR GAMBAR POLLINATIONS ---
def generate_background_image(prompt, output_filename):
    print(f"🎨 Melukis mahakarya visual: '{prompt[:50]}...'")
    full_prompt = f"{prompt}, portrait aspect ratio, breathtaking, divine aesthetic, clean composition, masterpiece"
    encoded_prompt = urllib.parse.quote(full_prompt)
    seed = random.randint(1, 999999)
    # Meminta ukuran estetik Instagram/Facebook Portrait (1080x1350)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1350&nologo=true&seed={seed}"
    
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        with open(output_filename, 'wb') as f:
            f.write(response.content)
        return output_filename
    raise Exception("Gagal menghasilkan gambar dari AI.")

# --- 4. ENGINE TATA LETAK TEKS ARTISTIK & SOFT SHADOW ---
def draw_text_with_soft_shadow(draw, position, text, font, text_color, shadow_color="black"):
    x, y = position
    # Soft shadow (offset sedikit ke kanan bawah)
    draw.text((x + 3, y + 4), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)

def create_aesthetic_bible_post(item, output_path, img_size=(1080, 1350)):
    print("✨ Memadukan lukisan dan tipografi seni...")
    bg_path = os.path.join(BASE_DIR, "temp_bg.jpg")
    generate_background_image(item['prompt_gambar'], bg_path)
    
    # Kunci ukuran gambar secara mutlak agar tidak error mismatch
    img = Image.open(bg_path).convert("RGBA")
    img = ImageOps.fit(img, img_size, Image.Resampling.LANCZOS)
    
    # Membuat gradient vignette untuk keterbacaan teks
    vignette = Image.new('RGBA', img_size, (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(img_size[1]):
        alpha = int(255 * (abs(y - img_size[1]/2) / (img_size[1]/2)) ** 1.8)
        if alpha > 180: alpha = 180
        v_draw.line([(0, y), (img_size[0], y)], fill=(0, 0, 0, alpha))
        
    img = Image.alpha_composite(img, vignette)
    draw = ImageDraw.Draw(img)
    
    fonts = download_aesthetic_fonts()
    font_ref = ImageFont.truetype(fonts['cinzel'], 48)
    font_ayat = ImageFont.truetype(fonts['playfair_italic'], 52)
    font_renungan = ImageFont.truetype(fonts['playfair_regular'], 34)
    font_cta = ImageFont.truetype(fonts['playfair_regular'], 30)
    
    def get_text_width(text, font):
        try: return draw.textlength(text, font=font)
        except: return draw.textbbox((0, 0), text, font=font)[2]

    def chunk_text(text, words_per_line=4):
        words = text.split()
        return [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]

    lines_ayat = chunk_text(f'"{item["ayat"]}"', words_per_line=4)
    lines_renungan = chunk_text(item['renungan'], words_per_line=5)
    
    # RENDER 1: REFERENSI AYAT (Atas, Font Klasik Cinzel, Warna Gold)
    ref_text = item['ref'].upper()
    w_ref = get_text_width(ref_text, font_ref)
    draw_text_with_soft_shadow(draw, ((img_size[0]-w_ref)//2, 250), ref_text, font_ref, "#FFDF73")
    
    # RENDER 2: GARIS PEMISAH ESTETIK
    draw.line([(img_size[0]//2 - 100, 340), (img_size[0]//2 + 100, 340)], fill="#FFDF73", width=2)
    
    # RENDER 3: AYAT ALKITAB (Tengah, Playfair Italic, Putih Bersih)
    y_ayat = 450
    for line in lines_ayat:
        w_ayat = get_text_width(line, font_ayat)
        draw_text_with_soft_shadow(draw, ((img_size[0]-w_ayat)//2, y_ayat), line, font_ayat, "#FFFFFF")
        y_ayat += 75

    # RENDER 4: RENUNGAN (Bawah, Playfair Regular, Silver/Abu terang)
    y_renungan = 950
    for line in lines_renungan:
        w_ren = get_text_width(line, font_renungan)
        draw_text_with_soft_shadow(draw, ((img_size[0]-w_ren)//2, y_renungan), line, font_renungan, "#E0E0E0")
        y_renungan += 50
        
    # RENDER 5: CTA (Paling Bawah)
    cta_text = item['cta']
    w_cta = get_text_width(cta_text, font_cta)
    draw_text_with_soft_shadow(draw, ((img_size[0]-w_cta)//2, 1200), cta_text, font_cta, "#B3D4FF")

    final_img = img.convert("RGB")
    final_img.save(output_path, quality=100)
    
    if os.path.exists(bg_path): os.remove(bg_path)
    print("✅ Postingan Seni Alkitab berhasil diciptakan!")
    return output_path

# --- 5. UPLOAD KE FACEBOOK ---
def upload_photo_to_facebook(image_path, caption):
    print("🚀 Mengunggah mahakarya ke Facebook...")
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_ACCESS_TOKEN")
    
    url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
    with open(image_path, 'rb') as f:
        response = requests.post(url, files={'source': f}, data={'caption': caption, 'access_token': access_token}).json()
        
    if "id" in response: 
        print("🎉 BERHASIL MENGUNGGAH KE FACEBOOK!\n")
    else: 
        raise Exception(f"Gagal upload: {response}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("⚡ MEMULAI BOT SENI ALKITAB ESTETIK ⚡\n")
    try:
        item = generate_image_content()
        image_file = os.path.join(BASE_DIR, "aesthetic_bible_post.jpg")
        caption = f"✨ {item['ref']} ✨\n\n\"{item['ayat']}\"\n\n{item['renungan']}\n\n{item['cta']}\n\n#FirmanTuhan #RenunganHarian #AyatAlkitab #RohaniKristen #EstetikKristen #TuhanYesus"
        
        create_aesthetic_bible_post(item, image_file)
        
        if os.path.exists(image_file) and os.path.getsize(image_file) > 10000:
            upload_photo_to_facebook(image_file, caption)
        else:
            raise Exception("File gambar gagal dibuat!")
            
        mark_verse_as_used(item['ref'])
        gc.collect()
    except Exception as e:
        print(f"❌ Kesalahan pada bot: {e}\n")
