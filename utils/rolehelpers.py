from pymessenger import Button, Element
from utils import urls
from utils.bot import bot

def reveal_player(player, role_name):
    names = player.game_state.get_players(player.reveal)
    try:
        names.remove(player.first_name)
    except ValueError:
        pass
    for n in names:
        msg = "{name} is a {role}".format(name=n, 
               role=role_name)
        bot.send_text_message(player.id, msg)
    return names

def card_parse(pl_dict):
    #takes string e.g. "Card 1" and returns integer 1
    card_no = pl_dict.get('title')
    card_no = filter(str.isdigit, card_no)
    card_no = list(card_no)
    return int(card_no[0])

def player_payload(player, action, *args):
    payload = " ".join([player.game_state.room, 
                        str(player.player_no), 
                        action] 
                        + list(args))
    return payload

def pick_center_card(payload_str, title, subtitle):
    buttons = []
    for x in range(3):
        button_title = "Card {:d}".format(x+1)
        buttons.append(Button(title=button_title, 
                              type='postback', 
                              payload=payload_str))
    element = Element(title=title, 
                      image_url= urls.center_img, 
                      subtitle=subtitle,
                      buttons=buttons)
    return [element] 

def player_carousel(player, action, do_nothing = False):
    elements = []
    players = player.game_state.players
    if do_nothing:
        nothing_button = Button(title="Do Nothing",
                                type='postback',
                                payload=player_payload(player, action))
    for k in players:
        if k != player.player_no:
            #player_no as k will be passed payload formatted in a dictionary 
            #with key 0
            payload = player_payload(player, action, str(k))
            button = Button(title="Pick", 
                            type='postback', 
                            payload=payload)
            if do_nothing:
                buttons = [button, nothing_button]
            else:
                buttons = [button]
            elements.append(Element(title=players[k].first_name,
                    image_url=players[k].profile_pic,
                    buttons=buttons))
    return elements

class Peeker:
    def __init__(self, player, max_peeks=1):
        self.player = player
        self.max_peeks = max_peeks
        self.seen = set()
        
    def __call__(self):
        self.request()
        
    def request(self):
        payload = player_payload(self.player, 'peek')
        element = pick_center_card(payload,
                                   title = "Peek",
                                   subtitle = "Look at a card in the center")
        bot.send_generic_message(self.player.id, element)
        
    def post(self, pl_dict):
        card_no = card_parse(pl_dict)
        if len(self.seen) < self.max_peeks or card_no in self.seen:
            msg = ("You have picked Card {num}"
                   .format(num=card_no))
            bot.send_text_message(self.player.id, msg)
            self.seen.add(card_no)
            new_tot = len(self.seen)
            if new_tot != self.max_peeks:
                remaining = self.max_peeks - new_tot
                msg = ("Pick {:d} more card(s) to look at."
                       .format(remaining))
                bot.send_text_message(self.player.id, msg)
                self.request()
            else:
                return "Wait"
        else:
            bot.send_text_message(self.player.id, 
                                  "You cannot view more cards.")
            return "Wait"
            
    def resolve(self):
        for card_no in self.seen:
            center = self.player.game_state.cards[card_no - 1]
            role_name = self.player.role_dict[center]
            bot.send_image_url(self.player.id, urls.role[role_name])
            msg = ("Card {num} is the {card}."
                   .format(num=card_no, card=role_name))
            bot.send_text_message(self.player.id, msg)

class Player:
    def __init__(self, player_no, game_state, player_dict):
        self.__dict__.update(player_dict,
                             player_no = player_no)
        self.game_state = game_state
        self.card = self.role
        self.pre_game_bool = False
        self._action_complete = False
        self.role_dict = {0: 'Doppelganger',
                          1: 'Werewolf',
                          2: 'Minion',
                          3: 'Mason',
                          4: 'Seer',
                          5: 'Robber',
                          6: 'Troublemaker',
                          7: 'Drunk',
                          8: 'Insomniac',
                          9: 'Tanner',
                          10: 'Hunter',
                          11: 'Villager'}
        self.dead = False
        self.reveal_self()

    def reveal_self(self):
        role_name = self.role_dict[self.card]
        bot.send_image_url(self.id, urls.role[role_name])
        msg = "You are a {}".format(role_name)
        bot.send_text_message(self.id, msg)
        
    def __call__(self):
        if not self.pre_game_bool:
            self.wait()
        self.action_complete = True
    
    def pre_game(self):
        self.pre_game_bool = True
        self.wait()
        
    @property    
    def action_complete(self):
        return self._action_complete
    
    @action_complete.setter
    def action_complete(self, action_complete):
        self._action_complete = action_complete
        self.game_state.observe(self)
    
    def get(self, key, default=None):
        return self.__dict__.get(key, default)
    
    def post(self, *args, **kwargs):
        return 'No post action'
    
    def wait(self):
        bot.send_text_message(self.id, "Waiting for other players to " +
                              "complete their action.")
        bot.send_action(self.id, 'typing_on')
    
    def resolve(self):
        return 'No resolve action'

    def vote(self):
        bot.send_text_message(self.id, "Vote to kill the werewolf!")
        carousel = player_carousel(self, 'vote')
        bot.send_generic_message(self.id, carousel)

    def kill(self):
        self.dead = True