#!/usr/bin/env python3.9

import imaplib
import email
from email.header import decode_header
import requests
import time
import re

# Configurações do e-mail
EMAIL = "seuemail@example.com"  # Substitua pelo seu e-mail
PASSWORD = "suasenha"  # Substitua pela sua senha
IMAP_SERVER = "imap.exemplo.com"  # Substitua pelo servidor IMAP do seu provedor

# Configurações do Telegram
TELEGRAM_TOKEN = "seu_bot_token"  # Substitua pelo token do seu bot do Telegram
CHAT_ID = "seu_chat_id"  # Substitua pelo ID do seu chat no Telegram

def extrair_dados_relevantes(texto):
    evento = re.search(r'Nome do evento/alarme:\s*(.+)', texto)
    horario = re.search(r'Horário do alarme:\s*(.+)', texto)
    fonte = re.search(r'Fonte:\s*(.+)', texto)

    mensagem = "🚨 <b>Alarme Detectado</b>\n 🚨"
    if evento:
        mensagem += f"<b>Evento:</b> {evento.group(1).strip()}\n"
    if horario:
        mensagem += f"<b>Horário:</b> {horario.group(1).strip()}\n"
    if fonte:
        mensagem += f"<b>Fonte:</b> {fonte.group(1).strip()}\n"

    return mensagem.strip()

def check_email():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox", readonly=False)

        status, messages = mail.search(None, 'UNSEEN')

        for num in messages[0].split():
            status, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    body = ""
                    attachments = []

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body += part.get_payload(decode=True).decode(errors="replace")

                            if "attachment" in content_disposition or content_type.startswith('image/'):
                                file_name = part.get_filename()
                                if file_name:
                                    file_data = part.get_payload(decode=True)
                                    attachments.append((file_name, file_data))
                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")

                    mensagem = extrair_dados_relevantes(body) if body else ""

                    for attachment in attachments:
                        send_telegram_photo(attachment[0], attachment[1], legenda=mensagem)

                    if not attachments and mensagem:
                        send_telegram_message(mensagem)

            # Marca como lido e para exclusão
            mail.store(num, '+FLAGS', '\\Seen \\Deleted')

        mail.expunge()
        mail.close()
        mail.logout()
    except Exception as e:
        print("Erro durante a verificação de e-mails: {}".format(e))

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Falha ao conectar ao Telegram: {e}")

def send_telegram_photo(file_name, file_data, legenda=""):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': (file_name, file_data)}
        payload = {'chat_id': CHAT_ID}
        if legenda:
            payload['caption'] = legenda
            payload['parse_mode'] = 'HTML'
        response = requests.post(url, files=files, data=payload)
        if response.status_code != 200:
            print(f"Erro ao enviar foto: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Falha ao enviar foto ao Telegram: {e}")

if __name__ == "__main__":
    while True:
        check_email()
        time.sleep(60)
