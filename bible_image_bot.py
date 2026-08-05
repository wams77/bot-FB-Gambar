import os
import time
import random
import requests
import gc
from groq import Groq
from PIL import Image, ImageDraw, ImageFont

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

# --- 1. GROQ AI: GENERATOR BATCH KONTEN (REFERENSI, AYAT LENGKAP & RENUNGAN) ---
def generate_batch_image_content(num_posts=3):
    print(f"🕊️ Meminta Groq Llama-3 meracik {num_posts} naskah ayat Alkitab & renungan yang akurat...")
    
    used_verses = get_used_verses()
    history_context = "\n".join(used_verses[-30:]) if used_verses else "(Belum ada riwayat)"
    
    prompt = f"""
    Bertindaklah sebagai teolog dan pembuat konten rohani Kristen yang akurat.
    Berikan {num_posts} referensi Ayat Alkitab (Terjemahan Baru LAI) yang BERAGAM dan unik dari seluruh Alkitab, lengkap dengan teks isi ayatnya secara utuh serta renungan singkat yang relevan.
    
    ATURAN MUTLAK: 
    1. Teks ayat HARUS SESUAI dengan Alkitab Terjemahan Baru (TB) Lembaga Alkitab Indonesia secara akurat.
    2. Kalimat renungan HARUS SINGKAT, padat, puitis (maksimal 1 kalimat pendek).
    3. Dilarang menggunakan referensi ayat yang ada di daftar riwayat ini: {history_context}
    
    Gunakan pemisah '---' di antara setiap naskah. Format wajib persis seperti ini:
    
    REF: [Referensi Kitab dan Ayat, cth: Yosua 1:9]
    AYAT: [Teks isi ayat Alkitab yang lengkap dan akurat]
    RENUNGAN: [1 kalimat pendek bermakna rohani]
    ---
    """
    
    raw_text = ""
    for attempt in range(3):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.8,
                max_tokens=1500,
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
        ayat = None
        renungan = None
        
        for line in lines:
            line_upper = line.upper()
            if "REF:" in line_upper:
                ref = line.split(":", 1)[1].strip()
            elif "AYAT:" in line_upper:
                ayat = line.split(":", 1)[1].strip()
            elif "RENUNGAN:" in line_upper:
                renungan = line.split(":", 1)[1].strip()
                
        # Pembersihan teks dari tanda kurung siku jika ada
        if ref: ref = ref.replace("[", "").replace("]", "").strip()
        if ayat: ayat = ayat.replace("[", "").replace("]", "").strip()
        if renungan: renungan = renungan.replace("[", "").replace("]", "").strip()
            
        # Jika data lengkap, masukkan ke batch
        if ref and ayat:
            batch.append({
                "ref": ref,
                "ayat": ayat,
                "renungan": renungan if renungan else "Penyertaan Tuhan adalah kekuatan kita."
            })
        
    if len(batch) == 0:
        raise Exception("❌ KEGAGALAN KRITIS: AI gagal menghasilkan format naskah yang sesuai.")
        
    print(f"✅ Berhasil menyiapkan {len(batch)} karya galeri terverifikasi!")
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

# --- 3. GENERATOR LATAR & TIPOGRAFI LOKAL (100% AMAN TANPA KETERGANTUNGAN API LUAR) ---
def create_aesthetic_bible_post(item, output_path, img_size=(1080, 1350)):
    print("✨ Menyusun galeri pameran seni tipografi rohani...")
    
    # Membuat latar belakang gradasi artistik elegan (Nuansa galeri pameran berkelas)
    img = Image.new("RGBA", img_size, "#1a1a24")
    draw = ImageDraw.Draw(img)
    
    # Efek gradasi halus vertikal
    for y in range(img_size[1]):
        r = int(26 + (y / img_size[1]) * 20)
        g = int(26 + (y / img_size[1]) * 15)
        b = int(36 + (y / img_size[1]) * 40)
        draw.line([(0, y), (img_size[0], y)], fill=(r, g, b, 255))
        
    # Bingkai artistik tipis ala galeri seni
    draw.rectangle([50, 50, img_size[0]-50, img_size[1]-50], outline="#FFDF73", width=2)
    
    fonts = load_aesthetic_fonts()
    font_ref = ImageFont.truetype(fonts['cinzel'], 48)
    font_ayat = ImageFont.truetype(fonts['playfair_italic'], 46)
    font_renungan = ImageFont.truetype(fonts['montserrat_black'], 30)
    
    def get_text_width(text, font):
        try: return draw.textlength(text, font=font)
        except: return draw.textbbox((0, 0), text, font=font)[2]

    def chunk_text(text, words_per_line=5):
        words = text.split()
        return [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]

    lines_ayat = chunk_text(f'"{item["ayat"]}"', words_per_line=4)
    lines_renungan = chunk_text(item['renungan'], words_per_line=5)
    
    # Render Referensi Ayat
    ref_text = item['ref'].upper()
    w_ref = get_text_width(ref_text, font_ref)
    draw.text((((img_size[0]-w_ref)//2) + 2, 182), ref_text, font=font_ref, fill="black")
    draw.text(((img_size[0]-w_ref)//2, 180), ref_text, font=font_ref, fill="#FFDF73")
    
    # Garis pemisah
    draw.line([(img_size[0]//2 - 100, 260), (img_size[0]//2 + 100, 260)], fill="#FFDF73", width=2)
    
    # Render Isi Ayat
    y_ayat = 340
    for line in lines_ayat:
        w_ayat = get_text_width(line, font_ayat)
        draw.text((((img_size[0]-w_ayat)//2) + 2, y_ayat + 2), line, font=font_ayat, fill="black")
        draw.text(((img_size[0]-w_ayat)//2, y_ayat), line, font=font_ayat, fill="#FFFFFF")
        y_ayat += 68

    # Render Renungan Singkat
    y_renungan = 950
    for line in lines_renungan:
        w_ren = get_text_width(line, font_renungan)
        draw.text((((img_size[0]-w_ren)//2) + 2, y_renungan + 2), line, font=font_renungan, fill="black")
        draw.text(((img_size[0]-w_ren)//2, y_renungan), line, font=font_renungan, fill="#D0D0D0")
        y_renungan += 44

    final_img = img.convert("RGB")
    final_img.save(output_path, quality=100)
    
    print("✅ Karya galeri tipografi berhasil dicetak!")
    return output_path

# --- 4. UPLOAD KE FACEBOOK ---
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
    print("⚡ PAMERAN TIPOGRAFI ROHANI & SIMBOL KEKRISTENAN (BATCH 3 KARYA) ⚡\n")
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
        exit(1)
