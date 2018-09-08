import random
from pymessenger import Button
from utils import rolehelpers
from utils.rolehelpers import (Player, Peeker, reveal_player, card_parse, 
    player_payload, pick_center_card, player_carousel)
from utils import urls
from utils.bot import bot

class Werewolf(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.peeker = Peeker(self, max_peeks=0)
        self.reveal = [1]
        
    def __call__(self):
        names = reveal_player(self, "Werewolf")
        if not names:
            self.peeker.max_peeks = 1
            self.peeker()
        else:
            self.action_complete = True
            
    def post(self, pl_dict):
        if pl_dict.get('action') == 'peek':
            result = self.peeker.post(pl_dict)
            if result:
                self.wait()
                self.action_complete = True
        
    def resolve(self):
        self.peeker.resolve()
            
class Seer(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.peeker = Peeker(self, max_peeks=0)
        self.spy = None
        self.spied_name = None
        self.choice = None
        self.post_switch = {'choose': self._choose,
                            'peek': self._peek,
                            'spy': self._spy}
    
    def __call__(self):
        msg = ("You may look at another player’s card " + 
               "or two of the center cards.")
        payload = player_payload(self, 'choose')
        b1= Button(title="Player's Card", type='postback', payload=payload)
        b2 = Button(title="Two Center Cards", type='postback', payload=payload)
        bot.send_button_message(self.id, msg, [b1,b2])
    
    def _choose(self, pl_dict):
        if not self.choice:
            self.choice = pl_dict.get('title')
            if self.choice == "Player's Card":
                bot.send_text_message(self.id, "Look at another player's card")
                carousel = player_carousel(self, 'spy')
                bot.send_generic_message(self.id, carousel)
            else:
                self.peeker.max_peeks = 2
                self.peeker()
            
        else:
            bot.send_text_message(self.id, "You have already chosen an action")
    
    def _peek(self, pl_dict):
        result = self.peeker.post(pl_dict)
        if result:
            self.wait()
            self.action_complete = True

    def _spy(self, pl_dict):
        if not self.spy:
            #0 is the key for other player_no
            self.spy = int(pl_dict[0])
            self.spied_name = self.game_state.players[self.spy].first_name
            bot.send_text_message(self.id, "You have chosen {}'s card"
                                  .format(self.spied_name))
            self.action_complete = True
        else:
            bot.send_text_message(self.id, 
                                  "You have already chosen a player's card")
        self.wait()
        
    def post(self, pl_dict):
        self.post_switch[pl_dict.get('action')](pl_dict)
        
    def resolve(self):
        if self.spy:
            card = self.game_state.players[self.spy].card
            role_name = self.role_dict[card]
            bot.send_image_url(self.id, urls.role[role_name])
            msg = "{} is a {}".format(self.spied_name, role_name)
            bot.send_text_message(self.id, msg)
        else:
            self.peeker.resolve()
            
            
class Robber(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.chosen_player = None
    
    def __call__(self):
        msg = ("You may exchange your card with another player’s card," +
               " and then view your new card.")
        bot.send_text_message(self.id, msg)
        carousel = player_carousel(self, 'rob', do_nothing=True)
        bot.send_generic_message(self.id, carousel)
    
    def post(self, pl_dict):
        if not self.action_complete:
            #If pl_dict.get(0) exists, it implies that the player did not chose
            #to do nothing.
            if 0 in pl_dict:
                self.chosen_player = self.game_state.players[int(pl_dict[0])]
                msg = ("You will switch cards with {}"
                       .format(self.chosen_player.first_name))
                bot.send_text_message(self.id, msg)
            else:
                msg = "You have decided to do nothing."
                bot.send_text_message(self.id, msg)
            self.wait()
            self.action_complete = True
        else:
            msg = "You have already completed your action."
            bot.send_text_message(self.id, msg)
            self.wait()
        
    def resolve(self):
        if self.chosen_player:
            self.game_state.swap_player_cards(self.player_no, 
                                       self.chosen_player.player_no)
            role_name = self.role_dict[self.card]
            bot.send_image_url(self.id, urls.role[role_name])
            msg = ("You are now the {} and {} will have your card."
                   .format(role_name, 
                           self.chosen_player.first_name))
            bot.send_text_message(self.id, msg)
            
        
class Troublemaker(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.chosen_players = []
       
    def __call__(self):
        msg = ("You may exchange cards between two other players. " +
               "Pick the first card or choose to do nothing")
        bot.send_text_message(self.id, msg)
        carousel = player_carousel(self, 'switch', do_nothing=True)
        bot.send_generic_message(self.id, carousel)
        
    def post(self, pl_dict):
        picked_cards = len(self.chosen_players)
        if picked_cards < 2 and not self.action_complete:
            #If 0 exists in pl_dict, it implies that the player did not chose
            #to do nothing.
            if 0 in pl_dict:
                player_no = int(pl_dict[0])
                if player_no not in self.chosen_players:
                    self.chosen_players.append(player_no)
                name = self.game_state.players[player_no].first_name
                if picked_cards < 1:
                    msg = ("You have picked {}'s card. ".format(name) + 
                           "Pick a second card to switch.")
                    bot.send_text_message(self.id, msg)
                    carousel = player_carousel(self, 'switch')
                    bot.send_generic_message(self.id, carousel)
                else:
                    msg = ("You have picked {}'s card. ".format(name) +
                           "The cards you have chosen will be switched.")
                    bot.send_text_message(self.id, msg)
                    self.wait()
                    self.action_complete = True
            else:
                msg = "You have decided to not cause trouble."
                bot.send_text_message(self.id, msg)
                self.wait()
                self.action_complete = True
        else:
            msg = "You have already completed your action."
            bot.send_text_message(self.id, msg)
            self.wait()
    
    def resolve(self):
        if len(self.chosen_players) == 2:
            self.game_state.swap_player_cards(*self.chosen_players)
            msg = "The cards you have chosen have been switched!"
            bot.send_text_message(self.id, msg)
        
class Villager(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
    
class Minion(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.reveal = [1]
        
    def __call__(self):
        names = reveal_player(self, "Werewolf")
        if names or self.pre_game_bool == False:
            self.wait()
        self.action_complete = True
        
class Mason(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.reveal = [3]
        
    def __call__(self):
        names = reveal_player(self, "Mason")
        if names or self.pre_game_bool == False:
            self.wait()
        self.action_complete = True
        
class Drunk(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.card_no = None
    
    def __call__(self):
        msg = "Exchange your card with a card from the center"
        bot.send_text_message(self.id, msg)
        payload = player_payload(self, 'drunk')
        element = pick_center_card(payload,
                                   title="Pick",
                                   subtitle="Exchange your card with a" + 
                                   " card from the center")
        bot.send_generic_message(self.id, element)
    
    def post(self, pl_dict):
        if not self.card_no:
            self.card_no = card_parse(pl_dict)
            msg = ("You have picked Card {num}"
                   .format(num=self.card_no))
            bot.send_text_message(self.id, msg)
        else:
            bot.send_text_message(self.id, 
                                  "You cannot view more cards.")
        self.wait()
        self.action_complete = True
        
    def resolve(self):

        self.game_state.swap_with_center(self.card_no, self.player_no)
        msg = ("Your card is now Card {} ".format(self.card_no) + 
               "and your previous card is in the center.")
        bot.send_text_message(self.id, msg)
        
class Insomniac(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        
    def resolve(self):
        role_name = self.role_dict[self.card]
        bot.send_image_url(self.id, urls.role[role_name])
        msg = "Your card is now the {}".format(role_name)
        bot.send_text_message(self.id, msg)
        
class Hunter(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)

    def kill(self):
        self.dead = True
        bot.send_text_message(self.id, "Kill another player!")
        carousel = player_carousel(self, 'kill')
        bot.send_generic_message(self.id, carousel)
        
class Tanner(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
    
class Doppelganger(Player):
    def __init__(self, game_state, player_no, player_dict):
        super().__init__(player_no, game_state, player_dict)
        self.chosen_player = None
        self.player_dict = player_dict
        self._copy = None
    
    def pre_game(self):
        self.pre_game_bool = True
        msg = ("Look at another player’s card. You are now that role." + 
               "(You have {} seconds to complete the action or one will be " +
               "chosen for you.)").format(self.game_state.pre_game_time)
        bot.send_text_message(self.id, msg)
        carousel = player_carousel(self, 'doppel')
        bot.send_generic_message(self.id, carousel)
        
    def __call__(self):
        if type(self) is not type(self.copy):
            self.copy()
        else:
            self.action_complete = True
    
    def post(self, pl_dict):
        if pl_dict.get('action') == 'doppel':
            if not self.chosen_player:
               self.chosen_player = self.game_state.players[int(pl_dict[0])]
               self.copy_role()
            else:
                msg = ("You have already copied a role.")
                bot.send_text_message(self.id, msg)
        else:
            self.copy.post(pl_dict)
            
    def copy_role(self):
        copy = self.game_state.role_switch[self.chosen_player.card]
        player_dict = self.player_dict.copy()
        player_dict['role'] = self.chosen_player.card
        self.copy = copy(self.game_state, 
                         self.player_no, 
                         player_dict)
        self.action_complete = self.copy.action_complete
     
    @property
    def copy(self):
        if not self._copy:
            player_no_list = list(range(0, self.game_state.max_players))
            player_no_list.remove(self.player_no)
            player_no = random.choice(player_no_list)
            self.chosen_player = self.game_state.players[player_no]
            msg = "You have ran out of time. {} was picked for you."
            msg = msg.format(self.chosen_player.first_name)
            bot.send_text_message(self.id, msg)
            self.copy_role()
        return self._copy
    
    @copy.setter
    def copy(self, arg):
        self._copy = arg
                
    def resolve(self):
        if type(self) is not type(self.copy):
            self.copy.resolve()