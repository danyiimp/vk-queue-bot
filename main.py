import vk_api
import logging
import time

from icecream import ic
from dotenv import load_dotenv
from os import getenv
from threading import Timer

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotEvent

from data import get_data, save_data, backup

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

class MyVkBotLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try: 
                for event in self.check():
                    yield event
            except Exception as e:
                logging.info(f"{e}\nПЕРЕПОДКЛЮЧЕНИЕ")
                time.sleep(3)

load_dotenv()
BOT_TOKEN = getenv("bot_token")
GROUP_ID = getenv("group_id")
DATA_FILE = "data/data.json"
ADMINS_FILE = "data/admins.json"
TIMEOUTS_FILE = "data/timeouts.json"
BACKUP_DIR = "data/backups/"

vk_session = vk_api.VkApi(token=BOT_TOKEN)
vk = vk_session.get_api()
longpoll = MyVkBotLongPoll(vk_session, group_id=GROUP_ID)

def get_name_from_user_id(user_id):
    user = vk.users.get(user_id=user_id)[0]
    name = f"{user['first_name']} {user['last_name']}"
    return name

def get_timeout_text_from_user_id(chat_timeouts, user_id):
    if user_id in chat_timeouts:
        return " &#128683;"
    return ""

def help_handler(event: VkBotEvent):
    msg = """
    Список доступных комманд:\n
    /end – встать в конец очереди.
    /list – текущая очередь.
    /skip – пропустить 24ч.
    /drop – сбросить очередь (для избранных).
    /admins – список избранных. 
    """
    vk.messages.send(
        chat_id=event.chat_id,
        message=msg,
        random_id=0
    )

def end_handler(event: VkBotEvent):
    data = get_data(DATA_FILE)

    chat_id = event.message["peer_id"] - 2000000000
    if data.get(str(chat_id)):
        chat_data = data[str(chat_id)]
    else:
        chat_data = []

    user_id = event.message["from_id"]
    if user_id in chat_data:
        chat_data.remove(user_id)
    chat_data.append(user_id)

    data[str(chat_id)] = chat_data
    save_data(data, DATA_FILE)

    name = get_name_from_user_id(int(user_id))
    msg = f"{len(chat_data)} в очереди – {name}"

    vk.messages.send(
        chat_id=event.chat_id,
        message=msg,
        random_id=0
    )

def list_handler(event: VkBotEvent):
    data = get_data(DATA_FILE)

    chat_id = event.message["peer_id"] - 2000000000
    if data.get(str(chat_id)):
        chat_data = data[str(chat_id)]
    else:
        msg = "Очередь несформирована."
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )
        return

    timeouts = get_data(TIMEOUTS_FILE)
    if timeouts.get(str(chat_id)):
        chat_timeouts = timeouts[str(chat_id)]
        timeouts_text = [get_timeout_text_from_user_id(chat_timeouts, user_id) for user_id in chat_data]
    else:
        timeouts_text = ["" for user_id in chat_data]

    names = [get_name_from_user_id(int(user_id)) for user_id in chat_data]

    names_statuses = zip(names, timeouts_text)

    msg = "\n".join(f"{i+1}. {name_status[0]}{name_status[1]}" for i, name_status in enumerate(names_statuses))
    
    vk.messages.send(
        chat_id=event.chat_id,
        message=msg,
        random_id=0
    )

def drop_handler(event: VkBotEvent):
    data = get_data(DATA_FILE)
    user_id = event.message["from_id"]
    chat_id = event.message["peer_id"] - 2000000000
    if data.get(str(chat_id)):
        admins = get_data(ADMINS_FILE)
        try: 
            admins_id_in_chat = admins[str(chat_id)]
            #TODO Бэкапы сейчас общие на все беседы
            if user_id in admins_id_in_chat:
                backup(DATA_FILE, BACKUP_DIR)
                data[str(chat_id)] = []
                save_data(data, DATA_FILE)
                msg = "Очередь сброшена."
                vk.messages.send(
                    chat_id=event.chat_id,
                    message=msg,
                    random_id=0
                )    
            else:
                msg = "Недостаточно прав."
                vk.messages.send(
                    chat_id=event.chat_id,
                    message=msg,
                    random_id=0
                )      
        except:
            #TODO Добавить возможность добавлять админов из интерфейса
            msg = "Админы не выбраны."
            vk.messages.send(
                chat_id=event.chat_id,
                message=msg,
                random_id=0
            )      
    else:
        msg = "Очередь несформирована."
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )

def admins_handler(event: VkBotEvent):
    admins = get_data(ADMINS_FILE)
    chat_id = event.message["peer_id"] - 2000000000
    try: 
        admins_id_in_chat = admins[str(chat_id)]
        admins_names = [get_name_from_user_id(int(admin_id)) for admin_id in admins_id_in_chat]

        msg = "\n".join(f"{i+1}. {name}" for i, name in enumerate(admins_names))
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )     

    except:
        msg = "Админы не выбраны."
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )     

def skip_handler(event: VkBotEvent):
    data = get_data(DATA_FILE)
    timeouts = get_data(TIMEOUTS_FILE)
    user_id = event.message["from_id"]
    chat_id = event.message["peer_id"] - 2000000000

    msg = f"Сначала встаньте в очередь – /end."
    if data.get(str(chat_id)):
        chat_data = data[str(chat_id)]
        if user_id not in chat_data:
            vk.messages.send(
                chat_id=event.chat_id,
                message=msg,
                random_id=0
            )
            return            
    else:
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )
        return


    if timeouts.get(str(chat_id)):
        chat_timeouts = timeouts[str(chat_id)]
    else:
        chat_timeouts = []

    if user_id in chat_timeouts:
        msg = f"Вы уже пропускате день."
        vk.messages.send(
            chat_id=event.chat_id,
            message=msg,
            random_id=0
        )
        return

    chat_timeouts.append(user_id)

    #Создание потока с таймером
    timeout_in_sec = 60 * 60 * 24
    t = Timer(timeout_in_sec, remove_skip, args=(chat_id, user_id))
    t.start()

    timeouts[str(chat_id)] = chat_timeouts
    save_data(timeouts, TIMEOUTS_FILE)

    name = get_name_from_user_id(int(user_id))
    msg = f"{name} пропускает день."

    vk.messages.send(
        chat_id=event.chat_id,
        message=msg,
        random_id=0
    )     

def remove_skip(chat_id: int, user_id: int):
    timeouts = get_data(TIMEOUTS_FILE)

    e = Exception("ОШИБКА УДАЛЕНИЯ TIMEOUT")

    if timeouts.get(str(chat_id)):
        chat_timeouts: list = timeouts[str(chat_id)]
        if user_id not in chat_timeouts:
            raise e
        chat_timeouts.remove(user_id)
        timeouts[str(chat_id)] = chat_timeouts
        save_data(timeouts, TIMEOUTS_FILE)

        name = get_name_from_user_id(int(user_id))
        # msg = f"{name} возвращается в строй."

        # vk.messages.send(
        #     chat_id=chat_id,
        #     message=msg,
        #     random_id=0
        # )  

    else:
        raise e

def main():
    filter_dict = {
        "/help": help_handler,
        "/end": end_handler,
        "/list": list_handler,
        "/drop": drop_handler,
        "/admins": admins_handler,
        "/skip": skip_handler
    }

    for event in longpoll.listen():
        try: 
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                msg = event.message["text"].lower()
                handler = filter_dict.get(msg)
                if handler:
                    handler(event)
                else:
                    logging.info(f"НЕ КОМАНДА БОТА")
        except Exception as e:
            logging.error(f"Ошибка в обработке запроса:\n")

if __name__ == "__main__":
    main()