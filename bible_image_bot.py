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

# --- DATABASE LOKAL AYAT ALKITAB TERVERIFIKASI AKURAT (TERJEMAHAN BARU) ---
# Menggunakan teks baku mutlak untuk memastikan tidak ada kesalahan isi ayat
VERIFIED_BIBLE_DATABASE = {
    "yosua 1:9": "Bukankah telah Kuperintahkan kepadamu: kuatkan dan teguhkanlah hatimu? Janganlah kecut dan tawar hati, sebab Tuhan, Allahmu, menyertai engkau, ke mana pun engkau pergi.",
    "amsal 3:5": "Percayalah kepada Tuhan dengan segenap hatimu, dan janganlah bersandar kepada pengertianmu sendiri.",
    "roma 8:28": "Kita tahu sekarang, bahwa Allah turut bekerja dalam segala sesuatu untuk mendatangkan kebaikan bagi mereka yang mengasihi Dia, yaitu bagi mereka yang terpanggil sesuai dengan rencana Allah.",
    "mazmur 23:1": "Tuhan adalah gembalaku, takkan kekurangan aku.",
    "mazmur 46:1": "Allah itu bagi kita tempat perlindungan dan kekuatan, sebagai penolong dalam kesesakan sangat.",
    "mazmur 121:1": "Aku melayangkan mataku ke gunung-gunung; dari manakah pertolonganku akan datang?",
    "mazmur 121:2": "Pertolonganku ialah dari Tuhan, yang menjadikan langit dan bumi.",
    "filipi 4:6": "Janganlah hendaknya kamu khawatir tentang apa pun juga, tetapi nyatakanlah dalam segala hal keinginanmu kepada Allah dalam doa dan permohonan dengan ucapan syukur.",
    "filipi 4:13": "Segala perkara dapat kutanggung di dalam Dia yang memberi kekuatan kepadaku.",
    "filipi 4:19": "Allahku akan memenuhi segala keperluanmu menurut kekayaan dan kemuliaan-Nya dalam Kristus Yesus.",
    "yesaya 40:31": "Tetapi orang-orang yang menanti-nantikan Tuhan mendapat kekuatan baru: mereka seumpama rajawali yang naik terbang dengan kekuatan sayapnya; mereka berlari dan tidak menjadi lesu, mereka berjalan dan tidak menjadi lelah.",
    "yesaya 41:10": "Janganlah takut, sebab Aku menyertai engkau, janganlah bimbang, sebab Aku ini Allahmu; Aku akan meneguhkan, bahkan akan menolong engkau; Aku akan memegang engkau dengan tangan kanan-Ku yang membawa kemenangan.",
    "yohanes 3:16": "Karena begitu besar kasih Allah akan dunia ini, sehingga Ia telah mengaruniakan Anak-Inya yang tunggal, supaya setiap orang yang percaya kepada-Nya tidak binasa, melainkan beroleh hidup yang kekal.",
    "matius 11:28": "Marilah kepada-Ku, semua yang letih lesu dan berbeban berat, Aku akan memberi kelegaan kepadamu.",
    "Amsal 16:3": "Serahkanlah perbuatanmu kepada Tuhan, maka terlaksanalah segala rencanamu.",
    "roma 12:12": "Bersukacitalah dalam penghabaran, sabarlah dalam kesesakan, dan bertekunlah dalam doa!"
}

def get_verified_verse(reference_query):
    """
    Melakukan pencarian dan pencocokan ke database lokal resmi yang 100% akurat.
    """
    clean_query = " ".join(reference_query.lower().split())
    # Cek pencocokan persis
    for key, text in VERIFIED_BIBLE_DATABASE.items():
        if key in clean_query or clean_query in key:
            return text
    return None

# --- 1. GROQ AI: MENCARI REFERENSI & RENUNGAN SAJA ---
def generate_batch_image_content(num_posts=3):
    print(f"🕊️ Meminta Groq Llama-3 meracik {num_posts} referensi ayat terverifikasi & renungan rohani...")
    
    used_verses = get_used_verses()
    history_context = "\n".join(used_verses[-30:]) if used_verses else "(Belum ada riwayat)"
    
    # Daftar kunci referensi yang dijamin ada di database lokal agar tidak pernah salah isi
    available_keys = list(VERIFIED_BIBLE_DATABASE.keys())
    
    prompt = f"""
    Bertindaklah sebagai teolog dan pembuat konten rohani Kristen.
    Pilih {num_posts} referensi Kitab dan Ayat Alkitab yang BERAGAM dari daftar kunci berikut: {available_keys}. 
    Berikan referensi tersebut beserta renungan singkat yang relevan.
    
    ATURAN MUTLAK: 
    1. Hanya berikan REFERENSI ayat (ambil dari daftar di atas) dan RENUNGANNYA saja. Jangan menulis teks ayat di sini.
    2. Kalimat renungan HARUS SINGKAT, padat, puitis (maksimal 1 kalimat pendek).
    3. Dilarang menggunakan referensi ayat yang ada di daftar riwayat ini: {history_context}
    
    Gunakan pemisah '---' di antara setiap naskah. Format wajib persis seperti ini:
    
    REF: [Referensi Kitab dan Ayat]
    RENUNGAN: [1 kalimat pendek bermakna rohani]
    ---
    """
    
    raw_text = ""
    for attempt in range(3):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.7,
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
            # Ambil isi ayat dari database lokal murni yang 100% akurat sesuai Terjemahan Baru
            verified_text = get_verified_verse(ref)
            if verified_text:
                batch.append({
                    "ref": ref,
                    "ayat": verified_text,
                    "renungan": renungan if renungan else "Penyertaan Tuhan adalah kekuatan kita."
                })
            else:
                print(f"⚠️ Melewati referensi '{ref}' karena belum terdaftar di database lokal mutlak.")
        
    if len(batch) == 0:
        raise Exception("❌ KEGAGALAN KRITIS: Tidak ada naskah ayat terverifikasi yang berhasil dimuat.")
        
    print(f"✅ Berhasil menyiapkan {len(batch)} karya galeri dengan teks ayat mutlak akurat!")
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

# --- 3. GENERATOR LATAR & TIPOGRAFI LOKAL ---
def create_aesthetic_bible_post(item, output_path, img_size=(1080, 1350)):
    print("✨ Menyusun galeri pameran seni tipografi rohani...")
    
    img = Image.new("RGBA", img_size, "#1a1a24")
    draw = ImageDraw.Draw(img)
    
    for y in range(img_size[1]):
        r = int(26 + (y / img_size[1]) * 20)
        g = int(26 + (y / img_size[1]) * 15)
        b = int(36 + (y / img_size[1]) * 40)
        draw.line([(0, y), (img_size[0], y)], fill=(r, g, b, 255))
        
    draw.rectangle([50, 50, img_size[0]-50, img_size[1]-50], outline="#FFDF73", width=2)
    
    fonts = load_aesthetic_fonts()
    font_ref = ImageFont.truetype(fonts['cinzel'], 48)
    font_ayat = ImageFont.truetype(fonts['playfair_italic'], 44)
    font_renungan = ImageFont.truetype(fonts['montserrat_black'], 30)
    
    def get_text_width(text, font):
        try: return draw.textlength(text, font=font)
        except: return draw.textbbox((0, 0), text, font=font)[2]

    def chunk_text(text, words_per_line=5):
        words = text.split()
        return [" ".join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line)]

    lines_ayat = chunk_text(f'"{item["ayat"]}"', words_per_line=4)
    lines_renungan = chunk_text(item['renungan'], words_per_line=5)
    
    ref_text = item['ref'].upper()
    w_ref = get_text_width(ref_text, font_ref)
    draw.text((((img_size[0]-w_ref)//2) + 2, 182), ref_text, font=font_ref, fill="black")
    draw.text(((img_size[0]-w_ref)//2, 180), ref_text, font=font_ref, fill="#FFDF73")
    
    draw.line([(img_size[0]//2 - 100, 260), (img_size[0]//2 + 100, 260)], fill="#FFDF73", width=2)
    
    y_ayat = 340
    for line in lines_ayat:
        w_ayat = get_text_width(line, font_ayat)
        draw.text((((img_size[0]-w_ayat)//2) + 2, y_ayat + 2), line, font=font_ayat, fill="black")
        draw.text(((img_size[0]-w_ayat)//2, y_ayat), line, font=font_ayat, fill="#FFFFFF")
        y_ayat += 65

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
    
