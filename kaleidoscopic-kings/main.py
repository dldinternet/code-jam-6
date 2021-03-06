from kivy.core.audio import SoundLoader

from backend.card_format import Card
from backend.main import load_game, Game
from backend import path_handler
from frontend.frontend import MainWidget
from frontend.swipe import Rotater  # noqa: F401
from dataclasses import dataclass
from kivy.app import App
from kivy.config import Config
from kivy.event import EventDispatcher
from kivy.lang import global_idmap
from kivy.properties import ObjectProperty, StringProperty


class MainState:
    def __init__(self, label: str, value: float):
        self.label: str = label
        value = f"{int(value * 100)}%"
        self.value: str = value


@dataclass
class GameState:
    main_state_1: MainState
    main_state_2: MainState
    main_state_3: MainState
    main_state_4: MainState


class DataController(EventDispatcher):
    """Manages global state for the app"""

    active_card: Card = ObjectProperty(rebind=True)
    game_state = ObjectProperty(rebind=True)
    game: Game = ObjectProperty()
    story_name: StringProperty()

    def choice_handler(self, choice):
        """Used to update state for the app when the user makes a choice"""
        if self.active_card.card_type == "game_over":
            self.game = game = load_game(self.story_name)
            self.active_card = game.start_game()
            self.set_game_state()
            return
        if choice == "1" or len(self.active_card.options) == 1:
            outcome = self.active_card.options[0].get_outcome()
        else:
            card_choice = 1 if len(self.active_card.options) > 0 else 0
            outcome = self.active_card.options[card_choice].get_outcome()
        self.active_card = self.game.take_turn(outcome)
        self.set_game_state()

    def set_game_state(self):
        """
        Sets the states for the 4 main player states. Currently uses dud values til the
        backend version is done
        """
        states = [self.game.game_state.get_main_state(i) for i in range(4)]
        self.game_state = self.game_state = GameState(
            *[MainState(s.label, s.value) for s in states]
        )


class CardGameApp(App):
    def build(self):
        Config.set("graphics", "width", "900")
        Config.set("graphics", "height", "1000")

        story_name = "caveman"
        global_idmap["data"] = ctl = DataController()
        # Kivy really does not like path lib or joinpath or anything with path unless
        # it's a hardcoded string
        global_idmap[
            "all_assets"
        ] = f"{path_handler.get_game_asset_directory_path(story_name)}/"
        global_idmap["game_assets"] = f"{path_handler.get_game_art_path(story_name)}/"
        global_idmap["card_assets"] = f"{path_handler.get_card_art_path(story_name)}/"
        global_idmap[
            "sound_assets"
        ] = f"{path_handler.get_game_sounds_path(story_name)}\\"
        ctl.story_name = story_name
        ctl.game = game = load_game(story_name)
        ctl.active_card = game.start_game()
        ctl.set_game_state()
        sound = SoundLoader.load(global_idmap["sound_assets"] + "caveman.wav")
        if sound:
            sound.play()
        return MainWidget()


if __name__ == "__main__":
    CardGameApp().run()
