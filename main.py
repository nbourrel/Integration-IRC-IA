import socket
import re
import json
from colorama import Fore, Style, init
from datetime import datetime
import os
from src.cohere import CohereClient

init()

class IRCBot:
    def __init__(self, config):
        self.server = config['server']
        self.port = config['port']
        self.nickname = config['nickname']
        self.channel = config['channel']
        self.cohere_api_key = config['cohere_api_key']
        self.irc_socket = None
        self.co = CohereClient(self.cohere_api_key)

        self.chat_history_storage_mode = config.get('chat_history_storage_mode', 'by_user')  # Default to 'by_user'
        # Initialize chat history based on storage mode
        if self.chat_history_storage_mode == 'by_user':
            self.user_sessions = {}  # Dictionary to store chat history for each user
        elif self.chat_history_storage_mode == 'by_channel':
            self.channel_sessions = {}  # Dictionary to store chat history for each channel
            self.channel_sessions[self.channel] = []  # Initialize chat history for the default channel

    def start_bot(self):
        self.irc_socket = self.irc_login()
        if self.irc_socket:
            self.listen_irc()

    def irc_login(self):
        irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            irc_socket.connect((self.server, self.port))
            irc_socket.send(f"NICK {self.nickname}\r\n".encode())
            irc_socket.send(f"USER {self.nickname} {self.nickname} {self.nickname} :{self.nickname}\r\n".encode())
            return irc_socket
        except Exception as e:
            print("An error occurred during IRC login:", e)
            return None

    def listen_irc(self):
        with open("irc_log.txt", "a") as log_file:
            motd_received = False
            try:
                while True:
                    server_response = self.irc_socket.recv(2048).decode('utf-8', 'ignore')
                    if not server_response:
                        break
                    log_file.write(server_response)
                    if not motd_received:
                        print(server_response)
                        if "376" in server_response:
                            motd_received = True
                            self.join_channel()
                        continue

                    if server_response.startswith("PING"):
                        self.pong(server_response)
                        continue

                    self.handle_irc_message(server_response)
            except Exception as e:
                print("An error occurred during IRC communication:", e)
            finally:
                self.irc_socket.close()

    def pong(self, server_response):
        token = server_response.split()[1]
        self.irc_socket.send(f"PONG {token}\r\n".encode())
        print(f"PONG {token}")

    def join_channel(self):
        self.irc_socket.send(f"JOIN {self.channel}\r\n".encode())

    def send_message(self, message):
        if self.irc_socket:
            try:
                # Split message by lines
                lines = message.splitlines()
                for line in lines:
                    if line.strip():  # Ensure the line is not empty
                        self.irc_socket.send(f"PRIVMSG {self.channel} :{line}\r\n".encode())
            except Exception as e:
                print("An error occurred while sending message:", e)
        else:
            print("IRC socket is not connected.")

    def handle_irc_message(self, message):
        nickname_pattern = re.compile(r":([^!]+)!")
        nickname_match = nickname_pattern.search(message)
        if nickname_match:
            nickname = nickname_match.group(1)
        else:
            nickname = ""

        content_pattern = re.compile(r"PRIVMSG #([^ ]+) :([^\x00-\x1F\x7F-\x9F]+)")
        content_match = content_pattern.search(message)
        if content_match:
            channel = content_match.group(1)
            content = content_match.group(2)
        else:
            channel = ""
            content = ""

        if nickname and channel and content:
            print(f"{Fore.WHITE}[#{channel.upper()}]{Fore.RED}<{nickname}{Fore.WHITE}@{Fore.BLUE}{channel}> {Fore.GREEN}{content}{Style.RESET_ALL}")
            log_filename = f"logs/{channel}_log.txt"
            channel_history = []
            if os.path.exists(log_filename):
                with open(log_filename, 'r') as log_file:
                    channel_history = [json.loads(line.strip()) for line in log_file]
            if self.chat_history_storage_mode == 'by_user':
                if nickname not in self.user_sessions:
                    self.user_sessions[nickname] = []  # Initialize chat history for new users
                response = self.co.generate_text(self.user_sessions.get(nickname, []), content)
                self.co.log_message(f"logs/{nickname}_log.txt", {"role": "USER", "message": content})
                self.co.log_message(f"logs/{nickname}_log.txt", {"role": "CHATBOT", "message": response})  # Log bot's response
            elif self.chat_history_storage_mode == 'by_channel':
                if channel not in self.channel_sessions:
                    self.channel_sessions[channel] = []  # Initialize chat history for new channels
                response = self.co.generate_text(channel_history, content)
                self.co.log_message(f"logs/{channel}_log.txt", {"role": "USER", "message": content})
                self.co.log_message(f"logs/{channel}_log.txt", {"role": "CHATBOT", "message": response})  # Log bot's response
            self.send_message(response)
            print(f"{Fore.WHITE}[#{channel.upper()}]{Fore.RED}<{self.nickname}{Fore.WHITE}@{Fore.BLUE}{channel}> {Fore.GREEN}{response}{Style.RESET_ALL}")

if __name__ == "__main__":
    with open("config/config.json", "r") as config_file:
        config = json.load(config_file)

    bot = IRCBot(config)
    bot.start_bot()