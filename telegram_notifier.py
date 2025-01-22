#!/usr/bin/env python3.9

import imaplib
import email
from email.header import decode_header
import requests
import time

# Configurações do e-mail (insira seus dados)
EMAIL = "seu_email@example.com"        # Substitua pelo seu e-mail
PASSWORD = "sua_senha"                 # Substitua pela sua senha
IMAP_SERVER = "imap.exemplo.com"       # Substitua pelo seu servidor IMAP

# Configurações do Telegram (insira seus dados)
TELEGRAM_TOKEN = "seu_token"           # Substitua pelo seu token Telegram
CHAT_ID = "seu_chat_id"                # Substitua pelo seu Chat ID

def check_email():
    """Função para verificar novos e-mails não lidos"""
    try:
        # Conectar ao servidor IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox", readonly=False)

        # Buscar e-mails não lidos
        status, messages = mail.search(None, 'UNSEEN')

        for num in messages[0].split():
            # Buscar mensagem pelo índice
            status, msg_data = mail.fetch(num, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Criar objeto de mensagem a partir dos bytes
                    msg = email.message_from_bytes(response_part[1])

                    # Decodificar o assunto do e-mail
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    # Obter corpo do e-mail
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            # Apenas obter conteúdos que não são anexos
                            if "attachment" not in content_disposition:
                                if content_type == "text/plain":
                                    body += part.get_payload(decode=True).decode("utf-8")
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8")

                    send_telegram_message("Alerta: {}\n\n{}".format(subject, body.strip()))

            # Mover e-mail analisado para a lixeira
            mail.copy(num, 'INBOX.Trash')
            mail.store(num, '+FLAGS', '\\Deleted')

        mail.expunge()  # Remover definitivamente os e-mails marcados como deletados
        mail.close()

        # Limpar lixo do servidor de e-mail
        clear_trash(mail)
    except Exception as e:
        print("Erro durante a verificação de e-mails: {}".format(e))

def clear_trash(mail):
    """Limpa conteúdo da lixeira"""
    try:
        mail.select('INBOX.Trash', readonly=False)
        mail.store("1:*", '+FLAGS', '\\Deleted')
        mail.expunge()
        mail.close()
    except Exception as e:
        print("Não foi possível limpar a lixeira: {}".format(e))
    finally:
        mail.logout()

def send_telegram_message(message):
    """Envia mensagens de e-mail para o Telegram"""
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar mensagem: {} - {}".format(response.status_code, response.text))
    except requests.exceptions.RequestException as e:
        print("Falha ao conectar ao Telegram: {}".format(e))

if __name__ == "__main__":
    while True:
        check_email()
        time.sleep(60)  # Esperar 60 segundos antes de checar novamente