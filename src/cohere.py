import cohere
import json

class CohereClient:
    def __init__(self, api_key):
        self.client = cohere.Client(api_key)

    def generate_text(self, chat_history, message):
        try:
            response = self.client.chat(chat_history=chat_history, message=message)
            chat_reply = response.text  # Access the generated text from the response object
            # chat_history.append({"role": "CHATBOT", "message": chat_reply})
            return chat_reply
        except Exception as e:
            print(f"Error generating text: {e}")
            return "Error: Unable to generate response."

    def log_message(self, log_filename, message_data):
        with open(log_filename, 'a') as log_file:
            log_file.write(json.dumps(message_data) + "\n")