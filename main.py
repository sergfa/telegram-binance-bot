from dotenv import dotenv_values

env = dotenv_values('.env')
print(f'Hello Python!')
print(f'BOT: {env["TELEGRAM_BOT_TOKEN"]}')