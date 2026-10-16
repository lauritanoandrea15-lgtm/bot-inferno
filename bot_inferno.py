import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Configurazione dei log per vedere cosa succede nel terminale
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token del tuo bot
TOKEN = "8804836577:AAFzc7zTiEaes6I4D_Z40ijuRErZyb3lWVs"

# Dizionario per tracciare le scadenze: {user_id: {"name": user_name, "scadenza": scadenza_datetime}}
user_deadlines = {}

# Set per memorizzare gli ID delle anime già passate per il girone
returning_souls = set()

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accoglie la nuova anima (o la riconosce), imposta il timer e manda il messaggio infernale."""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
            
        user_id = member.id
        user_name = member.first_name
        
        # Calcola la scadenza a 3 ore da adesso (10800 secondi)
        scadenza = datetime.now() + timedelta(hours=3)
        user_deadlines[user_id] = {"name": user_name, "scadenza": scadenza}
        
        # Tastiera per il Signore delle Fiamme (Admin)
        keyboard = [
            [InlineKeyboardButton("🔥 Salva quest'anima (Solo Admin)", callback_data=f"approve_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Controlla se è un nuovo dannato o un'anima di ritorno
        if user_id in returning_souls:
            message_text = (
                f"🔥 **Bentornato/a nell'Inferno, {user_name}!** 🔥\n\n"
                f"Sei voluto/a tornare a strisciare tra le fiamme... ma le regole non cambiano!\n"
                f"Hai di nuovo **3 ore** di tempo affinché un **Signore dell'Inferno (Admin)** ti conceda la grazia permanente.\n\n"
                f"💀 Scrivi `/tempo` per consultare la clessidra della tua condanna."
            )
        else:
            returning_souls.add(user_id)
            message_text = (
                f"🔥 **Benvenuto/a nell'Inferno, {user_name}!** 🔥\n\n"
                f"Sei varcato oltre la soglia dei dannati. Per rimanere in questo girone hai **3 ore** di tempo "
                f"per ricevere la benedizione da un **Signore dell'Inferno (Admin)**.\n\n"
                f"Se la clessidra scadrà senza approvazione, le fiamme ti inghiottiranno e verrai cacciato per sempre.\n\n"
                f"💀 Scrivi `/tempo` per guardare quanto tempo ti resta prima dell'oblio."
            )
        
        sent_msg = await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")
        
        # Avvia il task di controllo condanna a 3 ore (10800 secondi)
        context.application.create_task(
            check_user_expiration(context.bot, update.effective_chat.id, user_id, sent_msg.message_id, user_name)
        )

async def check_user_expiration(bot, chat_id, user_id, message_id, user_name):
    """Attende 3 ore e spinge l'anima non approvata nel baratro (ban e unban)."""
    await asyncio.sleep(10800)
    
    if user_id in user_deadlines:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            
            await bot.send_message(
                chat_id=chat_id, 
                text=f"🩸 **L'ora è giunta!** L'anima di **{user_name}** non è stata salvata dai Signori del Girone ed è stata inghiottita dalle fiamme eternali! 🕳️🔥"
            )
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Errore durante la cacciata dell'anima {user_id}: {e}")
        
        user_deadlines.pop(user_id, None)

async def check_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /tempo per il singolo utente."""
    user_id = update.effective_user.id
    
    if user_id not in user_deadlines:
        await update.message.reply_text(
            "🛡️ **La tua anima è al sicuro!**\nSei già stato consacrato dai Signori dell'Inferno o non sei soggetto alla condanna temporale."
        )
        return
        
    rimanente = user_deadlines[user_id]["scadenza"] - datetime.now()
    
    if rimanente.total_seconds() <= 0:
        await update.message.reply_text("⏳ **La tua clessidra si è svuotata!** Preparati all'oblio...")
        return
        
    ore = int(rimanente.total_seconds() // 3600)
    minuti = int((rimanente.total_seconds() % 3600) // 60)
    secondi = int(rimanente.total_seconds() % 60)
    
    await update.message.reply_text(
        f"⏳ **LA CLESSIDRA DEL DANNATO** ⏳\n\n"
        f"Ti restano **{ore} ore, {minuti} minuti e {secondi} secondi** prima che le fiamme ti caccino via da questo girone!\n\n"
        f"Prega che un **Admin** clicchi sul pulsante di salvezza!",
        parse_Mode="Markdown"
    )

async def admin_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /lista riservato agli Admin per vedere tutte le anime in prova e i tempi."""
    user_status = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if user_status.status not in ["creator", "administrator"]:
        await update.message.reply_text("❌ Solo un **Signore dell'Inferno (Admin)** può consultare il registro dei dannati!")
        return

    if not user_deadlines:
        await update.message.reply_text("📜 **Registro dei Dannati:** Nessuna anima in prova al momento. Il girone è tranquillo.")
        return

    testo = "📜 **REGISTRO DELLE ANIME IN PROVA** 📜\n\n"
    
    for uid, info in list(user_deadlines.items()):
        rimanente = info["scadenza"] - datetime.now()
        if rimanente.total_seconds() <= 0:
            tempo_str = "Scaduto (in procinto di essere espulso)"
        else:
            ore = int(rimanente.total_seconds() // 3600)
            minuti = int((rimanente.total_seconds() % 3600) // 60)
            tempo_str = f"{ore}h {minuti}m"
            
        testo += f"👤 **{info['name']}** (ID: `{uid}`)\n⏳ Tempo residuo: *{tempo_str}*\n\n"

    await update.message.reply_text(testo, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce il click del bottone per la salvezza dell'anima da parte di un Admin."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("approve_"):
        target_user_id = int(data.split("_")[1])
        
        user_status = await context.bot.get_chat_member(query.message.chat_id, query.from_user.id)
        if user_status.status not in ["creator", "administrator"]:
            await query.answer("❌ Non possiedi le chiavi di questo Inferno! Solo un Admin può salvare quest'anima.", show_alert=True)
            return
            
        if target_user_id in user_deadlines:
            user_deadlines.pop(target_user_id, None)
            
            await query.edit_message_text(
                text=(
                    f"🔥 **SALVEZZA CONCESSA!** 🔥\n\n"
                    f"Il Signore dell'Inferno **{query.from_user.first_name}** ha spezzato le catene!\n"
                    f"Quest'anima ora fa parte del girone a tutti gli effetti."
                )
            )
        else:
            await query.edit_message_text(text="⚠️ Quest'anima è già stata salvata o è già stata inghiottita dal baratro.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("tempo", check_time_command))
    application.add_handler(CommandHandler("lista", admin_list_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot dell'Inferno risvegliato con successo!")
    application.run_polling()

if __name__ == "__main__":
    main()