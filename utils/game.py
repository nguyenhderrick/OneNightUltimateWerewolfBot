import random
from pymessenger import Button
import time
import asyncio
from utils.bot import bot
from utils.roles import (Doppelganger, Werewolf, Minion, Mason, Seer, Robber, 
    Troublemaker, Drunk, Insomniac, Tanner, Hunter, Villager)
from utils.rolehelpers import player_carousel
from utils import urls

FULL_DECK = [0, 1, 1, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10, 11, 11, 11]
#PRE_GAME_SLEEP is the number of seconds that the 
#doppelganger has to finish his turn
PRE_GAME_SLEEP = 15
#GAME_SLEEP is the minimum number of seconds the sleep 
#turn will last for all other players
GAME_SLEEP = 15

def make_deck(message):
    deck = str.split(message)
    for d in deck:
        if not d.isdigit():
            return "Invalid"
    deck = list(map(int, deck))
    return deck

def default_deck_maker(players):
    return random.sample(FULL_DECK, players + 3)

def assign_roles(max_players, deck):
    num_cards = max_players + 3
    return random.sample(deck, num_cards)  

class GameState():
    def __init__(self, room, admin, max_players):
        self.start_time = time.time()
        self.room = room
        self.admin = admin
        self.players = {}
        self.max_players = max_players
        self.phase = ['setup']
        self.cards = []
        self._deck = None
        self.players_completed = set()
        self.no_wakers = False
        self.pre_game_time = PRE_GAME_SLEEP
        self.time_limit = False
        self.role_switch = {0 : Doppelganger,
                           1 : Werewolf,
                           2 : Minion,
                           3 : Mason,
                           4 : Seer,
                           5 : Robber,
                           6 : Troublemaker,
                           7 : Drunk,
                           8 : Insomniac,
                           9 : Tanner,
                           10 : Hunter,
                           11 : Villager}
        self.recommended_cards = {3: [1, 1, 4, 5, 6, 11],
                                  4: [1, 1, 4, 5, 6, 11 ,11],
                                  5: [1, 1, 4, 5, 6, 11, 11, 11],
                                  6: []}
        self.add_player(admin)
        self.deck_prompt()
        self.votes = []

    def deck_prompt(self):
        make = Button(title='Make Deck', 
                      type='postback', 
                      payload=self.room)
        default = Button(title='Use Default Deck', 
                         type='postback', 
                         payload=self.room)
        buttons = [make, default]
        bot.send_button_message(self.admin, "Choose Action", buttons)
         
    def post_process(self, recipient_id, pl_dict):
        if 'player_no' in pl_dict:
            if 'start' in self.phase:
                if 'day' not in self.phase:
                    player_no = pl_dict.get('player_no')
                    self.players[player_no].post(pl_dict)
                elif pl_dict.get('action') == 'vote':
                    self.vote_process(pl_dict)
                elif pl_dict.get('action') == 'kill':
                    self.players[int(pl_dict[0])].kill()
                    self.end_game()
        elif pl_dict.get('title') == 'Make Deck':
            self.deck_entry()
            return "Needs Text"
        elif pl_dict.get('title') == 'Use Default Deck':
            self.deck = default_deck_maker(self.max_players)
            #time.sleep(3/10)
            bot.send_action(self.admin, 'typing_on')
            return "Success" 
    
    def vote_process(self, pl_dict):
        player_no = pl_dict.get('player_no')
        chosen_player = int(pl_dict[0])
        if player_no not in [x['voter'] for x in self.votes]:
            self.votes.append({'voter' : player_no, 'chosen' : chosen_player})
            bot.send_text_message(self.players[player_no].id,
                "Votes are being counted.")
        else:
            bot.send_text_message(self.players[player_no].id,
                "You have already voted.")
        if len(self.votes) == self.max_players:
            self.kill_players()

    def kill_players(self):
        votes = [x['chosen'] for x in self.votes]
        #counts all the votes and organizes them by player
        votes_by_player = (
            [(i, votes.count(i)) for i in range(self.max_players)])
        highest = max([c for i, c in votes_by_player])
        if highest > 1:
            #kills all the players with the highest votes if it is more than 1
            killed_players = [i for i, c in votes_by_player if c == highest]
        else:
            killed_players = []
            msg = ("The village did not kill anyone!")
            for v in self.players.values():
                bot.send_text_message(v.id, msg)

        for k in killed_players:
            p_dead = self.players[k]
            p_dead.kill()
            dead_role_name = p_dead.role_dict[p_dead.card]
            msg = ("The village has killed {p}! He was a {r}."
                .format(p=p_dead.first_name, r=dead_role_name))
            for v in self.players.values():
                bot.send_image_url(v.id, p_dead.profile_pic)
                bot.send_text_message(v.id, msg)

        # checking if a hunter is in the deck to not end the game
        if 10 not in [v.card for v in self.players.values()]:
            self.end_game()
        else:
            for v in self.players.values():
                bot.send_text_message(v.id, 
                    "Wait for hunter to kill another player")

    def end_game(self):
        players = self.players.values()
        msgs = []

        # game only works for single doppelganger
        for v in players:
            if type(v) == Doppelganger:
                doppeled = v.copy.card


        dead_roles = [v.card if v.card != 0 else doppeled
                        for v in players if v.dead]
        player_roles = [v.card if v.card != 0 else doppeled 
                        for v in players]

        # win condition for villagers
        if (not dead_roles and 1 not in player_roles) or 1 in dead_roles:
            v_msg = "Villager team wins!"
        else:
            v_msg = "Villager team loses!"
        msgs.append(v_msg)

        # win condition for tanners
        if 9 in player_roles:
            tanners = [v for v in players 
                        if v.card == 9 or (v.card == 0 and doppeled == 9)]
            for t in tanners:
                if t.dead:
                    t_msg = "{} is a tanner and wins!".format(t.first_name)
                else:
                    t_msg = "{} is a tanner loses!".format(t.first_name)
                msgs.append(t_msg)

        # win condition for werewolves
        if 1 in player_roles and 1 not in dead_roles:
            if 9 in player_roles:
                if 9 not in dead_roles:
                    w_msg = "Werewolf team wins!"
                else:
                    w_msg = "Werewolf team loses!"
            else:
                w_msg = "Werewolf team wins!"
            msgs.append(w_msg)

        # win condition for minions without werewolves
        if 1 not in player_roles and 2 in player_roles:
            if dead_roles and 9 not in dead_roles:
                minions = [v for v in players 
                            if v.card == 2 or (v.card == 0 and doppeled == 2)]
                for m in minions:
                    if m.dead:
                        m_msg = "{} is a minion and loses!".format(m.first_name)
                    else:
                        m_msg = "{} is a minion and wins!".format(m.first_name)
                    msgs.append(m_msg)
            else:
                m_msg = "Minions lose!"
                msgs.append(m_msg)

        msgs = "\n".join(msgs)
        for v in players:
            bot.send_text_message(v.id, msgs)

    def text_process(self, recipient_id, message):
        if recipient_id == self.admin:
            result = self.deck_response(message)
            return result
        
    def add_player(self, recipient_id):
        player_no = len(self.players)
        if self.phase[-1] == 'setup':
            player_info = bot.get_user_info(recipient_id, 
                                            fields=['first_name', 
                                                    'profile_pic'])

            self.players[len(self.players)] = player_info
            if self.admin != recipient_id:
                bot.send_text_message(self.players[player_no].get('id'), 
                                      "Successfuly joined room")
        else:
            bot.send_text_message(recipient_id, "Game room is full")
            
    def deck_entry(self):
        card_lmt = {i: FULL_DECK.count(i) for i in range(max(FULL_DECK)+1)}
        msg_list = ["{k} : {v} ({l})".format(k=k, v=v.__name__, l=card_lmt[k])\
                    for k, v in self.role_switch.items()]
        msg = "\n".join(msg_list)
        bot.send_text_message(self.admin, msg)
        msg2 = ("Enter card numbers seperated by spaces " + 
                "(must be 3 more than the number of players, " +
                "limit of players per role are listed in parentheses.")
        bot.send_text_message(self.admin, msg2)

    @property
    def deck(self):
        return self._deck
    
    @deck.setter
    def deck(self, deck):
        if 'start' not in self.phase:
            self._deck = deck
            bot.send_text_message(self.admin, "Successfully set deck")
        
    def deck_response(self, message):
        deck = make_deck(message.get('text'))
        if deck != "Invalid":
            full_deck = FULL_DECK.copy()
            #check if deck is a subset of full deck
            for c in deck:
                try:
                    full_deck.remove(c)
                except ValueError:
                    bot.send_text_message(self.admin, "Not all numbers are " + 
                        "in the deck. Try again:")
                    self.deck_prompt()
                    return "Success"
            if self.max_players == len(deck) - 3:
                self.deck = deck
                return "Success"
            else:
                bot.send_text_message(self.admin, 
                    "There needs to be 3 more card than players. Try again:")
        else:
            bot.send_text_message(self.admin, "Invalid numbers. Try again:")
        self.deck_prompt()
        return "Success"
        
    async def start_game(self):
        self.cards = self.assign_roles()
        #checking if deck has any players that need to wake
        no_wake = [self.role_switch[c].post is self.role_switch[c].__base__.post 
                    for c in self.cards]
        if all(no_wake):
            self.no_wakers = True

        deck_msg = ["{}".format(self.role_switch[d].__name__) \
                    for d in sorted(self.deck)]
        deck_msg = ("Deck includes the following cards " + 
                    "and will be called in the following order:\n\n" + 
                    "\n".join(deck_msg))
        self.phase.append('start')
        for k in self.players:
            bot.send_text_message(self.players[k]['id'], "Game has started!")
            role = self.players[k]['role'] = self.cards.pop()
            self.players[k] =  self.role_switch[role](self, k, self.players[k])
            bot.send_text_message(self.players[k].id, deck_msg)
        #checking for doppelganger in the deck
        if 0 in self.deck:
            for v in self.players.values():
                v.pre_game()
            await asyncio.sleep(self.pre_game_time)
        if not self.no_wakers:
            asyncio.ensure_future(self.min_call_wake(self.pre_game_time))
        for v in self.players.values():
            v()
            
    async def start_check(self):
        if (self.max_players == len(self.players) 
            and self.deck != None 
            and 'start' not in self.phase):
            await self.start_game()

    async def min_call_wake(self, time):
        wake_min = random.uniform(time * 2/3, time * 3/2)
        await asyncio.sleep(wake_min)
        self.time_limit = True
        #use any player to initialize self.observe
        self.observe(self.players[0])
        
    def observe(self, player):
        if 'day' not in self.phase:
            if player.action_complete:
                self.players_completed.add(player.player_no)
            if (len(self.players_completed) == self.max_players 
                and self.time_limit):
                self.end_night()

    def end_night(self):
        self.phase.append('day')
        #gives the player number in role order to be resolved
        roles = [(p_no, v.role) for p_no, v in self.players.items()]
        player_order = [x[0] for x in sorted(roles, key=lambda y: y[1])] 
        for player_no in player_order:
            player = self.players[player_no]
            player.resolve()
            bot.send_text_message(player.id, "Day phase has started!")
            player.vote()

    def assign_roles(self):
        if self.deck == None:
            self.deck = self.recommended_cards[self.max_players]
        num_cards = self.max_players + 3
        return random.sample(self.deck, num_cards)

    def get_players(self, cards):
        names = []
        for k in self.players:
            #looks for players with the card or 
            #a player who has copied the role
            if (self.players[k].card in cards or 
                self.players[k].get('copy', {}).get('card') in cards):
                names.append(self.players[k].first_name)
        return names

    def swap_player_cards(self, p1, p2):
        card1 = self.players[p1].card
        card2 = self.players[p2].card
        self.players[p1].card = card2
        self.players[p2].card = card1

    def swap_with_center(self, card_no, player_no):
        player_card = self.players[player_no].card
        center_card = self.cards[card_no - 1]
        self.players[player_no].card = center_card
        self.cards[card_no - 1] = player_card