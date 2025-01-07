import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
import zipfile
import threading
from datetime import datetime
import shutil


#=================== DATA BOT ===============
# Initialize bot with your bot token
API_TOKEN = '7360190308:AAFCXEy6tEzRvCgzF44XzlcX3PRNV-vPkxo'
ADMIN_CHAT_ID = '576495165'  # Replace with the actual admin ChatID
bot = telebot.TeleBot(API_TOKEN)

#=================== DATA BASE ================
DB_PATH = 'san_store.db'
BACKUP_DIR = 'backups'

user_data = {}

# Set up SQLite database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create tables for storing balance, rewards, referrals, and prices
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (chat_id INTEGER PRIMARY KEY, saldo INTEGER DEFAULT 0, reward INTEGER DEFAULT 0, referrer_id INTEGER)''')
                  
cursor.execute('''CREATE TABLE IF NOT EXISTS prices
                  (id INTEGER PRIMARY KEY, date TEXT, harga_1 INTEGER, harga_2 INTEGER)''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS pelanggan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE,
    nama TEXT,
    nomor_rekening TEXT
)
''')

# Create table for redeem codes
cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
                    code TEXT PRIMARY KEY, 
                    custom_name TEXT, 
                    user_limit INTEGER,  -- Renamed 'limit' to 'user_limit'
                    saldo_reward INTEGER, 
                    used INTEGER DEFAULT 0
                )''')
                
# Create table for tracking which users have redeemed codes
cursor.execute('''CREATE TABLE IF NOT EXISTS redeemed_codes (
                    chat_id INTEGER, 
                    code TEXT,
                    PRIMARY KEY (chat_id, code)
                )''')

conn.commit()

#================= DATA BASE CONNECTION =============
# Function to get user info from the database
def get_user(chat_id):
    cursor.execute("SELECT saldo, reward FROM users WHERE chat_id=?", (chat_id,))
    return cursor.fetchone()

# Function to create or update a user in the database
def create_or_update_user(chat_id, referrer_id=None):
    cursor.execute("INSERT OR IGNORE INTO users (chat_id, referrer_id) VALUES (?, ?)", (chat_id, referrer_id))
    conn.commit()


#================== BACKUP & RESTORE ===============
def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    
    with zipfile.ZipFile(zip_filename, 'w') as backup_zip:
        backup_zip.write(DB_PATH, os.path.basename(DB_PATH))
    
    return zip_filename

# Function to send the backup to the admin
def send_backup_to_admin():
    zip_filename = backup_database()
    with open(zip_filename, 'rb') as backup_file:
        bot.send_document(ADMIN_CHAT_ID, backup_file)

# Function to restore the database from a zip file
def restore_database(zip_filename):
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extract(os.path.basename(DB_PATH), os.path.dirname(DB_PATH))

# Schedule autobackup every 6 hours
def schedule_backup():
    while True:
        send_backup_to_admin()
        threading.Event().wait(21600)  # 6 hours in seconds

# Start the backup scheduler in a new thread
backup_thread = threading.Thread(target=schedule_backup, daemon=True)
backup_thread.start()

# Restore database when a zip file is sent
@bot.message_handler(content_types=['document'])
def handle_zip_file(message):
    if str(message.chat.id) == ADMIN_CHAT_ID and message.document.mime_type == 'application/zip':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        zip_filename = os.path.join(BACKUP_DIR, message.document.file_name)
        
        with open(zip_filename, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        restore_database(zip_filename)
        bot.send_message(ADMIN_CHAT_ID, "Database berhasil dipulihkan dari backup.")


#=============== FUNGSI HARGA ==========
INITIAL_HARGA_1 = 10000
INITIAL_HARGA_2 = 15000

# Function to calculate daily price based on the current date
def get_daily_prices():
    today = datetime.now().date()
    start_of_month = today.replace(day=1)

    # Calculate the number of days since the start of the month
    days_passed = (today - start_of_month).days

    # Calculate the prices
    harga_1 = max(INITIAL_HARGA_1 - (166 * days_passed), 0)
    harga_2 = max(INITIAL_HARGA_2 - (250 * days_passed), 0)

    return harga_1, harga_2

#================== MENU UTAMA ==============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    referrer_id = message.text.split()[1] if len(message.text.split()) > 1 else None
    create_or_update_user(message.chat.id, referrer_id)
    saldo, reward = get_user(message.chat.id)

    # Get the daily prices
    harga_1, harga_2 = get_daily_prices()

    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(InlineKeyboardButton("MENU VPN", callback_data="menu_vpn"))
    markup.add(InlineKeyboardButton("TOPUP", callback_data="topup"),
               InlineKeyboardButton("MENU REFERALL", callback_data="menu_referral"))
    
    if str(message.chat.id) == ADMIN_CHAT_ID:
        markup.add(InlineKeyboardButton("LIST REWARD", callback_data="list_reward"),
                   InlineKeyboardButton("ADD BALANCE", callback_data="add_balance"))
        markup.add(InlineKeyboardButton("ADD TEXT TO FILE", callback_data="add_text"))
        markup.add(InlineKeyboardButton("📣BROADCAST📣", callback_data="informasi"))


    # Send the welcome message with prices
    bot.send_message(
        message.chat.id, 
        f"💎 𝙎𝘼𝙉𝙎𝙏𝙊𝙍𝙀 𝘽𝙊𝙏 💎\n\n"
        f"𝙍𝙚𝙖𝙙𝙮 𝙑𝙋𝙉 𝙎𝙝𝙖𝙧𝙞𝙣𝙜 𝘽𝙚𝙧𝙠𝙪𝙖𝙡𝙞𝙩𝙖𝙨 𝘿𝙖𝙣 𝘽𝙚𝙧𝙜𝙖𝙧𝙖𝙣𝙨𝙞\n"
        f"𝙍𝙚𝙜𝙞𝙤𝙣 𝙑𝙋𝙉  : 𝙎𝙞𝙣𝙜𝙖𝙥𝙪𝙧𝙖\n"
        f"𝙅𝙚𝙣𝙞𝙨 𝙑𝙋𝙉     : 𝙎𝙃𝘼𝙍𝙄𝙉𝙂\n"
        f"𝙈𝙖𝙨𝙖 𝙖𝙠𝙩𝙞𝙛     : 1 - 2 𝘽𝙪𝙡𝙖𝙣\n\n"
        f"𝙃𝙖𝙧𝙜𝙖 𝙎𝙚𝙠𝙖𝙧𝙖𝙣𝙜\n"
        f"2 𝙄𝙋 / 𝙎𝙏𝘽 : 𝙍𝙥{harga_1}\n"
        f"5 𝙄𝙋 / 𝙎𝙏𝘽 : 𝙍𝙥{harga_2}\n\n"
        f"𝙎𝙄𝙨𝙖 𝙎𝙖𝙡𝙙𝙤 𝙆𝙖𝙢𝙪 : 𝙍𝙥{saldo}\n"
        f"𝙍𝙚𝙬𝙖𝙧𝙙 𝙍𝙚𝙛𝙛𝙚𝙧𝙖𝙡 : 𝙍𝙥{reward}",
        reply_markup=markup
    )

#===================== QALBACK QUERRY ===============
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "menu_vpn":
        vpn_markup = InlineKeyboardMarkup()
        vpn_markup.row_width = 3
        vpn_markup.add(InlineKeyboardButton("SSH", callback_data="ssh"),
                       InlineKeyboardButton("VMESS", callback_data="vmess"),
                       InlineKeyboardButton("TROJAN", callback_data="trojan"))
    
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text="𝙋𝙞𝙡𝙞𝙝 𝙊𝙥𝙨𝙞 𝙐𝙣𝙩𝙪𝙠 𝙈𝙚𝙡𝙖𝙣𝙟𝙪𝙩𝙠𝙖𝙣 . . .",
            reply_markup=vpn_markup
        )
                  
    elif call.data in ["ssh", "vmess", "trojan"]:
        handle_vpn_choice(call)
    elif call.data in ["1hp_ssh", "1stb_ssh", "1hp_vmess", "1stb_vmess", "1hp_trojan", "1stb_trojan"]:
        handle_vpn_purchase(call)    
    elif call.data == 'topup':
        bot.answer_callback_query(call.id, "Masukkan jumlah nominal top up:")
        bot.send_message(call.message.chat.id, "𝙉𝙤𝙢𝙞𝙣𝙖𝙡 𝙏𝙤𝙥 𝙐𝙥")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_topup)
        
        
    elif call.data == "menu_referral":
        referral_markup = InlineKeyboardMarkup()
        referral_markup.row_width = 2
        referral_markup.add(InlineKeyboardButton("LINK REFERAL", callback_data="teman"),
                            InlineKeyboardButton("CAIRKAN REWARD", callback_data="cairkan_reward"),
                            InlineKeyboardButton("REKENING REWARD", callback_data="rek_reward"))
                            
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text="𝙋𝙞𝙡𝙞𝙝 𝙊𝙥𝙨𝙞 𝙐𝙣𝙩𝙪𝙠 𝙈𝙚𝙡𝙖𝙣𝙟𝙪𝙩𝙠𝙖𝙣 . . .",
            reply_markup=referral_markup
        )
    
    elif call.data == "teman":
        ref_link = f"https://t.me/sanstore_bot?start={call.message.chat.id}"
        bot.send_message(call.message.chat.id, f"Berikut Adalah link Referall Anda:\n{ref_link}\nDapatkan Reward Dengan Mengundang Teman Kamu")
        
        # Show list of invited friends
        cursor.execute("SELECT chat_id FROM users WHERE referrer_id = ?", (call.message.chat.id,))
        friends = cursor.fetchall()
        if friends:
            response = "Teman yang sudah Anda undang:\n"
            for friend in friends:
                response += f"Chat ID: {friend[0]}\n"
            bot.send_message(call.message.chat.id, response)
        else:
            bot.send_message(call.message.chat.id, "Belum ada teman yang diundang.")
    elif call.data == "list_reward":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            cursor.execute("SELECT chat_id, reward FROM users WHERE reward > 0")
            rewards = cursor.fetchall()
            if rewards:
                response = "Daftar pengguna dengan reward:\n"
                for r in rewards:
                    response += f"Chat ID: {r[0]}, Reward: {r[1]}\n"
                bot.send_message(call.message.chat.id, response)
            else:
                bot.send_message(call.message.chat.id, "Belum ada pengguna dengan reward.")
    elif call.data == "add_balance":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Masukkan ChatID<Spasi>Jumlah"
            )
            bot.register_next_step_handler(call.message, process_add_balance)
    elif call.data == "cairkan_reward":
        saldo, reward = get_user(call.message.chat.id)
        if reward > 0:
            bot.send_message(call.message.chat.id, f"Permintaan pencairan reward sebesar {reward} telah dikirim ke admin. Pastikan Kamu Telah Mengisi Rekening Reward")
            bot.send_message(ADMIN_CHAT_ID, f"Permintaan pencairan reward:\nChat ID: `{call.message.chat.id}`\nNominal: `{reward}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "Reward Anda saat ini adalah 0. Tidak ada yang bisa dicairkan.")
    elif call.data == 'rek_reward':
        # Periksa apakah user sudah punya data rekening
        cursor.execute('SELECT nama, nomor_rekening FROM pelanggan WHERE chat_id = ?', (call.message.chat.id,))
        data = cursor.fetchone()
        
        if data:
            # Jika data sudah ada, tampilkan datanya dengan opsi edit
            response = f"Data Rekening Anda:\n\nNama: {data[0]}\nNo Rekening: {data[1]}\n\n"
            response += "Klik tombol di bawah jika ingin mengedit data rekening Anda."
            
            markup = InlineKeyboardMarkup()
            markup.row_width = 3
            markup.add(InlineKeyboardButton("EDIT NAMA", callback_data="edit_nama"),
                       InlineKeyboardButton("EDIT NOMOR REK", callback_data="edit_rekening"))
            
            bot.send_message(call.message.chat.id, response, reply_markup=markup)
        else:
            # Jika data belum ada, mulai proses input rekening
            msg = bot.send_message(call.message.chat.id, 'Masukkan nama pemilik rekening:')
            bot.register_next_step_handler(msg, get_nama)

    elif call.data == 'edit_nama':
        msg = bot.send_message(call.message.chat.id, 'Masukkan nama baru:')
        bot.register_next_step_handler(msg, update_nama)
    elif call.data == 'edit_rekening':
        msg = bot.send_message(call.message.chat.id, 'Masukkan nomor rekening baru:')
        bot.register_next_step_handler(msg, update_rekening)
  
    elif call.data == "add_text":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:           
            bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Contoh input Text : ssh.txt|CONTOHISITEXT"
            )
            bot.register_next_step_handler(call.message, process_add_text)
            
    elif call.data == "informasi":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            msg = bot.send_message(call.message.chat.id, "𝙄𝙨𝙞 𝘽𝙧𝙤𝙖𝙙𝙘𝙖𝙨𝙩📢")
            bot.register_next_step_handler(msg, send_broadcast_message)
        

#==================== FITUR HANDLE VPN  ================
# Function to handle VPN choice
def handle_vpn_choice(call):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    vpn_type = call.data.upper()
    markup.add(
        InlineKeyboardButton("2 IP / STB", callback_data=f"1hp_{call.data}"),
        InlineKeyboardButton("5 IP / STB", callback_data=f"1stb_{call.data}")
    )
    
    bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text="𝙋𝙞𝙡𝙞𝙝 𝙊𝙥𝙨𝙞 𝙐𝙣𝙩𝙪𝙠 𝙈𝙚𝙡𝙖𝙣𝙟𝙪𝙩𝙠𝙖𝙣 . . .",
            reply_markup=markup
        )

# Function to handle VPN purchase
def handle_vpn_purchase(call):
    saldo, reward = get_user(call.message.chat.id)
    harga_1, harga_2 = get_daily_prices()
    
    if "1hp" in call.data:
        amount_to_deduct = harga_1
    elif "1stb" in call.data:
        amount_to_deduct = harga_2

    if saldo >= amount_to_deduct:
        new_saldo = saldo - amount_to_deduct
        cursor.execute("UPDATE users SET saldo = ? WHERE chat_id = ?", (new_saldo, call.message.chat.id))
        conn.commit()

        vpn_type = call.data.split('_')[-1]  # ssh, vmess, or trojan
        file_path = f"/root/san/bot/{vpn_type}.txt"

        try:
            with open(file_path, 'r') as file:
                vpn_info = file.read()
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"{vpn_info}\n\nPembayaran Sukses sebanyak {amount_to_deduct}. Sisa saldo: {new_saldo}"
                )
        except FileNotFoundError:
            bot.send_message(call.message.chat.id, "File VPN tidak ditemukan.")
    else:
        bot.send_message(call.message.chat.id, "Saldo Anda tidak mencukupi untuk pembelian ini.")


#======================= FITUR HANDLE TOP UP ================
def process_topup(message):
    try:
        nominal = int(message.text)  # Pastikan pengguna memasukkan angka
        chat_id = message.chat.id

        # Simpan nominal ke user_data sementara
        user_data[chat_id] = {'nominal': nominal}

        # Meminta pengguna untuk mengirimkan foto bukti transfer
        bot.send_message(chat_id, f"Anda ingin top up sebesar Rp{nominal:,}\n Silahkan Lakukan Pembayaran Ke DANA/GOPAY : 082292615651\nAtau Melalui Qris : https://tinyurl.com/SanQris\n\nKirim Bukti Screenshot Transfer Disini Jika selesai")
        bot.register_next_step_handler_by_chat_id(chat_id, process_transfer_proof)
    except ValueError:
        bot.send_message(message.chat.id, "Nominal tidak valid. Silakan masukkan angka yang benar.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, process_topup)

# Fungsi untuk memproses foto bukti transfer
def process_transfer_proof(message):
    chat_id = message.chat.id

    if message.photo:  # Jika pengguna mengirimkan foto
        # Ambil file ID foto bukti transfer
        photo_id = message.photo[-1].file_id

        # Simpan file ID foto di user_data
        user_data[chat_id]['photo'] = photo_id

        # Ambil informasi dari user_data
        nominal = user_data[chat_id]['nominal']

        # Kirim notifikasi ke admin
        bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"Permintaan Top Up\nChat ID: `{chat_id}`\nNominal: Rp `{nominal:,}`", parse_mode="Markdown")

        # Beri tahu pengguna bahwa permintaan mereka sedang diproses
        bot.send_message(chat_id, "Permintaan top up Anda telah dikirim dan sedang diproses.")

    else:
        bot.send_message(chat_id, "Silakan kirimkan foto bukti transfer")
        bot.register_next_step_handler_by_chat_id(chat_id, process_transfer_proof)
        
#=================== FITUR ADD SALDO =================
def process_add_balance(message):
    try:
        chat_id, amount = map(int, message.text.split())
        cursor.execute("SELECT saldo FROM users WHERE chat_id = ?", (chat_id,))
        saldo = cursor.fetchone()

        if saldo:
            new_saldo = saldo[0] + amount
            cursor.execute("UPDATE users SET saldo = ? WHERE chat_id = ?", (new_saldo, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"Saldo Anda telah ditambahkan sebesar {amount}. Saldo saat ini: {new_saldo}")

            # Handle referral reward if the user was referred
            cursor.execute("SELECT referrer_id FROM users WHERE chat_id = ?", (chat_id,))
            referrer_id = cursor.fetchone()[0]
            if referrer_id:
                reward_amount = int(amount * 0.1) 
                cursor.execute("UPDATE users SET reward = reward + ? WHERE chat_id = ?", (reward_amount, referrer_id))
                conn.commit()
                bot.send_message(referrer_id, f"Anda menerima reward sebesar {reward_amount} dari top up teman Anda. Reward saat ini: {reward_amount}")

            bot.send_message(ADMIN_CHAT_ID, f"Saldo pengguna dengan Chat ID {chat_id} telah ditambahkan sebesar {amount}.")
        else:
            bot.send_message(ADMIN_CHAT_ID, "Chat ID tidak ditemukan. Silakan coba lagi.")
    except (ValueError, IndexError):
        bot.send_message(ADMIN_CHAT_ID, "Format tidak valid. Silakan masukkan Chat ID dan jumlah saldo yang benar, dipisahkan dengan spasi.")
        
#====================== FITUR ADD TEXT ===================
def process_add_text(message):
    try:
        file_name, text = message.text.split('|', 1)
        directory = "/root/san/bot/"

        # Ensure the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)

        file_path = os.path.join(directory, file_name.strip())

        # Write the text to the file
        with open(file_path, 'a') as file:
            file.write(text.strip() + "\n")

        bot.send_message(ADMIN_CHAT_ID, f"Teks telah berhasil ditambahkan ke file {file_name}.")
    except ValueError:
        bot.send_message(ADMIN_CHAT_ID, "Format tidak valid. Pastikan Anda memasukkan nama file dan teks, dipisahkan oleh tanda '|'.")
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"Terjadi kesalahan: {e}")
        
#=================== FITUR WD REWARD SUKSES ===========
@bot.message_handler(commands=['sukses'])
def acc_cairkan_reward(message):
    try:
        parts = message.text.split()
        chat_id = int(parts[1])

        # Reset the reward to 0 after admin approval
        cursor.execute("UPDATE users SET reward = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()

        bot.send_message(message.chat.id, f"Permintaan pencairan reward untuk Chat ID {chat_id} telah disetujui.")
        bot.send_message(chat_id, "Permintaan Pencairan Reward Telah Dikirim Ke Rekening mu")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Format tidak valid. Pastikan Anda memasukkan Chat ID yang benar.")
        
#================= MENAMBAHKAN & EDIT DATA REKENING ===========
# Fungsi untuk mendapatkan nama dari pengguna
def get_nama(message):
    nama = message.text
    msg = bot.send_message(message.chat.id, 'Masukkan nomor rekening. Nomor DANA/GOPAY:')
    bot.register_next_step_handler(msg, get_nomor_rekening, nama)

# Fungsi untuk mendapatkan nomor rekening dan menyimpan ke database
def get_nomor_rekening(message, nama):
    nomor_rekening = message.text

    # Simpan atau update data ke SQLite
    cursor.execute('INSERT OR REPLACE INTO pelanggan (chat_id, nama, nomor_rekening) VALUES (?, ?, ?)', 
                   (message.chat.id, nama, nomor_rekening))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Data rekening Anda telah disimpan!')

# Fungsi untuk mengupdate nama pelanggan
def update_nama(message):
    nama_baru = message.text
    
    # Update nama di database
    cursor.execute('UPDATE pelanggan SET nama = ? WHERE chat_id = ?', (nama_baru, message.chat.id))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Nama rekening Anda telah diperbarui!')

# Fungsi untuk mengupdate nomor rekening pelanggan
def update_rekening(message):
    nomor_rekening_baru = message.text
    
    # Update nomor rekening di database
    cursor.execute('UPDATE pelanggan SET nomor_rekening = ? WHERE chat_id = ?', (nomor_rekening_baru, message.chat.id))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Nomor rekening Anda telah diperbarui!')
  

#================= FUNGSI MELIHAT DATA REKENING ================
# Fungsi untuk menampilkan data rekening kepada admin secara perorangan
@bot.message_handler(commands=['rekening'])
def lihat_data_rekening(message):
    if str(message.chat.id) == ADMIN_CHAT_ID:
        try:
            # Mengambil ChatID dari perintah /lihat_data {ChatID}
            command_parts = message.text.split()
            if len(command_parts) != 2:
                bot.send_message(message.chat.id, 'Gunakan format: /lihat_data {ChatID}')
                return
            
            target_chat_id = command_parts[1]
            
            # Ambil data rekening dari database berdasarkan ChatID yang diberikan
            cursor.execute('SELECT nama, nomor_rekening FROM pelanggan WHERE chat_id = ?', (target_chat_id,))
            data = cursor.fetchone()
            
            if data:
                response = f"Data Rekening Pelanggan (ChatID: {target_chat_id}):\n\nNama: {data[0]}\nNo Rekening: {data[1]}"
                bot.send_message(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, f"Tidak ada data rekening untuk ChatID: {target_chat_id}")
        
        except Exception as e:
            bot.send_message(message.chat.id, f"Terjadi kesalahan: {str(e)}")
    else:
        bot.send_message(message.chat.id, 'Anda tidak memiliki izin untuk melihat data ini.')

#=================== FUNGSI BROADCAST ==============
def send_broadcast_message(message):
    broadcast_text = message.text
    
    # Get all users' chat IDs from the database
    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()
    
    # Send the broadcast message to each user
    for user in users:
        try:
            bot.send_message(user[0], f"📢 INFORMASI 📢\n\n{broadcast_text}")
        except Exception as e:
            print(f"Failed to send message to {user[0]}: {e}")
    
    bot.send_message(message.chat.id, "Pesan telah berhasil dikirim ke semua pengguna.")
    
    
#============= FITUR REDEEM CODE ===================

# Admin check (replace with actual admin ID check)
def is_admin(chat_id):
    admin_ids = [576495165]  # Replace with actual admin chat IDs
    return chat_id in admin_ids
    
# Function to add balance to a user's account
def add_saldo(chat_id, saldo_amount):
    cursor.execute("UPDATE users SET saldo = saldo + ? WHERE chat_id = ?", (saldo_amount, chat_id))
    conn.commit()

# Admin command to create a redeem code
@bot.message_handler(commands=['redeem'])
def create_redeem(message):
    if is_admin(message.chat.id):
        msg = bot.send_message(message.chat.id, "Buat nama untuk kode redeem")
        bot.register_next_step_handler(msg, process_custom_name)
    else:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")

def process_custom_name(message):
    custom_name = message.text
    msg = bot.send_message(message.chat.id, "Konfirmasi kode redeem")
    bot.register_next_step_handler(msg, lambda m: process_redeem_code(m, custom_name))

def process_redeem_code(message, custom_name):
    code = message.text
    msg = bot.send_message(message.chat.id, "Batas jumlah claim kode redeem")
    bot.register_next_step_handler(msg, lambda m: process_redeem_limit(m, code, custom_name))

def process_redeem_limit(message, code, custom_name):
    user_limit = int(message.text)
    msg = bot.send_message(message.chat.id, "Jumlah saldo yang di dapat")
    bot.register_next_step_handler(msg, lambda m: finalize_redeem_code(m, code, custom_name, user_limit))

def finalize_redeem_code(message, code, custom_name, user_limit):
    saldo_reward = int(message.text)
    
    # Insert the redeem code into the database
    cursor.execute('INSERT INTO redeem_codes (code, custom_name, user_limit, saldo_reward) VALUES (?, ?, ?, ?)',
                   (code, custom_name, user_limit, saldo_reward))
    conn.commit()
    
    bot.send_message(message.chat.id, f"Redeem code '{custom_name}' created with limit {user_limit} and saldo reward {saldo_reward}.")

@bot.message_handler(func=lambda message: True)
def check_redeem_code(message):
    redeem_code = message.text.strip()

    # Fetch the redeem code from the database
    cursor.execute('SELECT * FROM redeem_codes WHERE code = ?', (redeem_code,))
    code_data = cursor.fetchone()

    if code_data:
        code, custom_name, user_limit, saldo_reward, used = code_data
        
        # Check if user already redeemed this code
        cursor.execute('SELECT * FROM redeemed_codes WHERE chat_id = ? AND code = ?', (message.chat.id, redeem_code))
        redeemed = cursor.fetchone()

        if redeemed:
            bot.send_message(message.chat.id, "Kamu telah menggunakan kode ini😁")
            return

        if used < user_limit:
            # Check if user is registered
            cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (message.chat.id,))
            user = cursor.fetchone()

            if user:
                # Update the redeem code usage and add saldo to user
                cursor.execute('UPDATE redeem_codes SET used = used + 1 WHERE code = ?', (redeem_code,))
                add_saldo(message.chat.id, saldo_reward)
                
                # Record that the user has redeemed this code
                cursor.execute('INSERT INTO redeemed_codes (chat_id, code) VALUES (?, ?)', (message.chat.id, redeem_code))
                conn.commit()
                
                bot.send_message(message.chat.id, f"Selamat! Kamu telah redeem '{custom_name}' Dan menerima {saldo_reward} saldo.")
            else:
                bot.send_message(message.chat.id, "Kamu tidak terdaftar untuk mendapatkan ini")
        else:
            bot.send_message(message.chat.id, "Maaf, Kode redeem sudah habis🥲")
    else:
        bot.send_message(message.chat.id, "Ketik /start untuk memulai bot ini")


# Start polling
bot.polling()
