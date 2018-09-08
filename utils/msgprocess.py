import asyncio
import random
from pymessenger import Button
import string
from utils.game import GameState
from utils.bot import bot

#MEM_LEN holds the last few message in case the message is resent
MEM_LEN = 5
GAME_OPEN_TIME = 60*20

def get_recipient_id(message):
    if message.get('sender'):
        if message['sender'].get('id'):
            return message['sender']['id']

def player_number_prompt(recipient_id):
    def quick_nums(i):
        return {'content_type': 'text', 'title': i, 'payload': i}
    bot.send_message(recipient_id, 
                     {'text': "How many players?",
                      'quick_replies':
                          [quick_nums(i + 3) for i in range(8)]
                      })

def payload_format(msg_pb):
    payload = msg_pb.pop('payload', None)
    payload = str.split(payload)
    room = payload.pop(0)
    p_key = ['player_no', 'action']
    p_key = p_key + [x for x in range(len(payload) - len(p_key))]
    payload = {x[0]:x[1] for x in zip(p_key, payload)}
    if payload.get('player_no'):
        payload['player_no'] = int(payload['player_no'])
    msg_pb.update(payload)
    pl_dict = msg_pb
    return room, pl_dict

class MessageProcess:
    def __init__(self):
        self.need_text = {}
        self.open_games = {}
        self.message_switch = {'message':self.msg_process, 
                               'postback':self.postback_process}
        self.pb_switch = {'join':self.join, 'init':self.init}
        self.caller_id = None
        self.last_msgs = []

    async def __call__(self, message):
        if self.repeat_msg_check(message):
            return
        self.delete_old_games(message)
        process_type = set(message).intersection(set(self.message_switch))
        for p in process_type:
            result = None
            self.caller_id = get_recipient_id(message)
            if self.caller_id in self.need_text and message[p].get('text'):
                response_dict = dict(self.need_text[self.caller_id])
                fun = response_dict.pop('fun')
                response_dict[p] = message[p]
                result = fun(**response_dict)
                if result == "Success":
                    self.need_text.pop(self.caller_id)
                elif type(result) is dict:
                    self.need_text[self.caller_id] = result    
            if result in ["Fail", None]:
                response = self.message_switch[p](message[p])
                if response:
                    self.need_text[self.caller_id] = response

        for game in self.open_games.values():
            await game.start_check()
    
    def delete_old_games(self, message):
        if 'timestamp' in message:
            current_time = message['timestamp']/1000
        for key, game in self.open_games.copy().items():
            if game.start_time + GAME_OPEN_TIME < current_time:
                print(game.start_time)
                print(GAME_OPEN_TIME)
                print(current_time)
                self.open_games.pop(key)

    def repeat_msg_check(self, message):
        if 'message' in message:
            msg_id = message['message'].get('mid')
            if msg_id in self.last_msgs:
                return True
            else:
                self.last_msgs.append(msg_id)
                if len(self.last_msgs) > MEM_LEN:
                    self.last_msgs.pop(0)
                return False

                    
    def create_game(self, message):
        max_players = int(message.get('text'))
        room = ''.join(random.choices(string.ascii_lowercase, k=5))
        pass_msg = "Passcode: {}".format(room)
        pass_prompt = ("Give passcode to {:d} other players"
                       .format(max_players-1))
        bot.send_text_message(self.caller_id, pass_msg)
        bot.send_text_message(self.caller_id, pass_prompt)
        self.open_games[room] = GameState(room, self.caller_id, max_players)
        
    def msg_process(self, message):
        bot.send_text_message(self.caller_id, message)
        self.first_message()
    
    def first_message(self):
        init = Button(title='Start New Game', type='postback', payload='init')
        join = Button(title='Join Existing Game', type='postback', payload='join')
        buttons = [init, join]
        bot.send_button_message(self.caller_id, "Choose Action", buttons)
                    
    def enter_room(self, room):
        if len(room) == 5 and room.islower():
            if self.open_games.get(room):
                self.open_games[room].add_player(self.caller_id)
                return "Success"
        bot.send_text_message(self.caller_id, 
                              "Not a valid room. Try again:")
        self.first_message()
        return "Success"
            
    def join_response(self, message):
        if 'text' in message:
            room = message['text']
        else:
            bot.send_text_message(self.caller_id, 
                                  "Not a valid passcode. Try again: ")
            self.first_message()
            return "Success"
        result = self.enter_room(room)
        return result
    
    def join(self):
        bot.send_text_message(self.caller_id, "Enter game room passcode:")
        return dict(fun = self.join_response)
                    
    def init(self):
        player_number_prompt(self.caller_id)
        return dict(fun = self.init_response)
    
    def init_response(self, message):
        if 'quick_reply' in message:
            self.create_game(message)
            return "Success"
        else:
            player_number_prompt(self.caller_id)
            return dict(fun = self.init_response)

    def default_postback(self, postback):
        room, pl_dict = payload_format(postback)
        if self.open_games.get(room):
            result = self.open_games[room].post_process(
                    self.caller_id, pl_dict)
            if result == "Needs Text":
                return dict(fun = self.open_games[room].text_process, 
                            recipient_id = self.caller_id)
        else:
            bot.send_text_message(self.caller_id, "Game no longer exists")

    def postback_process(self, postback):
        payload = postback.get('payload') 
        pb_fun = self.pb_switch.get(payload)
        if pb_fun:
            return pb_fun()
        else:
            return self.default_postback(postback)        