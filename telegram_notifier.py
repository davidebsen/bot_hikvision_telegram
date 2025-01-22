#!/usr/bin/env python3.9

import imaplib
import email
from email.header import decode_header
import requests
import time

# Configurações do e-mail
EMAIL = "seuemail@example.com"  # Substitua pelo seu e-mail
PASSWORD = "suasenha"  # Substitua pela sua senha
IMAP_SERVER = "imap.exemplo.com"  # Substitua pelo servidor IMAP do seu provedor

# Configurações do Telegram
TELEGRAM_TOKEN = "seu_bot_token"  # Substitua pelo token do seu bot do Telegram
CHAT_ID = "seu_chat_id"  # Substitua pelo ID do seu chat no Telegram

def check_email():
    try:
        # Conectar ao servidor IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox", readonly=False)

        # Buscar e-mails não lidos
        status, messages = mail.search(None, 'UNSEEN')

        for num in messages[0].split():
            status, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="replace")

                    body = ""
                    attachments = []

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            # Capturando o texto do corpo do e-mail
                            if part.get_content_type() == "text/plain" and "attachment" not in content_disposition:
                                body += part.get_payload(decode=True).decode(errors="replace")
                           
                            # Capturando as imagens anexadas
                            if "attachment" in content_disposition or content_type.startswith('image/'):
                                file_name = part.get_filename()
                                if file_name:
                                    file_data = part.get_payload(decode=True)
                                    attachments.append((file_name, file_data))

                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")

                    # Enviar o texto ao Telegram
                    if body:
                        send_telegram_message("Alerta: {}\n\n{}".format(subject, body.strip()))

                    # Enviar cada imagem individualmente ao Telegram
                    for attachment in attachments:
                        send_telegram_photo(attachment[0], attachment[1])

            # Mover para a Lixeira usando o caminho correto
            mail.copy(num, 'INBOX.Trash')
            mail.store(num, '+FLAGS', '\\Deleted')

        mail.expunge()  # Expunge na Inbox para remover marcados
        mail.close()

        # Limpar a lixeira
        clear_trash(mail)
    except Exception as e:
        print("Erro durante a verificação de e-mails: {}".format(e))

def clear_trash(mail):
    try:
        # Selecionar corretamente a Lixeira 'INBOX.Trash'
        status, _ = mail.select('INBOX.Trash', readonly=False)

        if status == "OK":
            status, messages = mail.search(None, 'ALL')
            if status == "OK" and messages[0]:  # Verifica se há mensagens
                mail.store('1:*', '+FLAGS', '\\Deleted')
                mail.expunge()
            else:
                print("Lixeira já está vazia.")
        else:
            print("Não foi possível selecionar a lixeira.")
    except Exception as e:
        print("Não foi possível limpar a lixeira: {}".format(e))
    finally:
        mail.logout()

def send_telegram_message(message):
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
        payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar mensagem: {} - {}".format(response.status_code, response.text))
    except requests.exceptions.RequestException as e:
        print("Falha ao conectar ao Telegram: {}".format(e))

def send_telegram_photo(file_name, file_data):
    try:
        url = "https://api.telegram.org/bot{}/sendPhoto".format(TELEGRAM_TOKEN)
        files = {'photo': (file_name, file_data)}
        payload = {'chat_id': CHAT_ID}
        response = requests.post(url, files=files, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar foto: {} - {}".format(response.status_code, response.text))
    except requests.exceptions.RequestException as e:
        print("Falha ao enviar foto ao Telegram: {}".format(e))

if __name__ == "__main__":
    while True:
        check_email()
        time.sleep(60)
