import logging
import re
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegraph import Telegraph
import requests
from bs4 import BeautifulSoup

# --- LEITURA DAS VARIÁVEIS DE AMBIENTE ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
try:
    AUTHORIZED_USER_ID = int(os.environ.get("AUTHORIZED_USER_ID"))
except (TypeError, ValueError):
    AUTHORIZED_USER_ID = None

if not TELEGRAM_BOT_TOKEN or not AUTHORIZED_USER_ID:
    sys.exit("ERRO: Variáveis de ambiente TELEGRAM_BOT_TOKEN e AUTHORIZED_USER_ID devem ser configuradas.")

# --- INICIALIZAÇÃO ---
TELEGRAPH_SHORT_NAME = "Link2InstantViewBot"
telegraph = Telegraph()
telegraph.create_account(short_name=TELEGRAPH_SHORT_NAME)
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FUNÇÕES DE EXTRAÇÃO ---
def extract_from_www_jw_org(url: str):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('h1').get_text(strip=True)
        article_body = soup.find('div', class_='docClass-106')
        if not title or not article_body:
            return None, None
        content_html = ''.join(str(p) for p in article_body.find_all(['p', 'h2']))
        return title, content_html
    except Exception as e:
        logger.error(f"Erro ao extrair de www.jw.org: {e}")
        return None, None

def extract_from_wol_jw_org(url: str):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('h1').get_text(strip=True)
        article_body = soup.find('div', class_='scalable ui-resizable')
        if not title or not article_body:
            return None, None
        content_html = ''.join(str(p) for p in article_body.find_all(['p', 'h2']))
        return title, content_html
    except Exception as e:
        logger.error(f"Erro ao extrair de wol.jw.org: {e}")
        return None, None

# --- HANDLERS DO TELEGRAM ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != AUTHORIZED_USER_ID:
        return

    url_match = re.search(r'https?://[^\s]+', update.message.text)
    if not url_match:
        await update.message.reply_text("Por favor, envie um link válido.")
        return

    url = url_match.group(0)
    title, content_html, author = None, None, "JW.ORG"

    if "www.jw.org" in url:
        title, content_html = extract_from_www_jw_org(url)
    elif "wol.jw.org" in url:
        title, content_html = extract_from_wol_jw_org(url)
    else:
        await update.message.reply_text("Desculpe, só consigo processar links dos sites configurados.")
        return

    if title and content_html:
        try:
            response = telegraph.create_page(
                title=title,
                html_content=content_html,
                author_name=author,
                author_url=url
            )
            await update.message.reply_text(f"https://telegra.ph/{response['path']}")
        except Exception as e:
            logger.error(f"Erro ao criar a página no Telegra.ph: {e}")
            await update.message.reply_text("Não foi possível criar a página no Telegra.ph.")
    else:
        await update.message.reply_text("Não foi possível processar este link.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == AUTHORIZED_USER_ID:
        await update.message.reply_text("Bot de artigos iniciado. Envie um link de um site configurado.")

# --- FUNÇÃO PRINCIPAL ---
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    main()
