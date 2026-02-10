import os
import arcade

# give it a nice little tune
background_music = arcade.load_sound(":resources:music/1918.mp3")
# Contants
screen_width = 1000
screen_height = 650
screen_title = "Platformer"

# Constants used to scale our sprites from their original size
tile_scaling = 0.5
character_scaling = tile_scaling * 2
coin_scaling = tile_scaling
sprite_pixel_size = 128
grid_pixel_size = sprite_pixel_size * tile_scaling

# Movement speed of player, in pixels per frame
player_movement_speed = 7
gravity = 1.5
player_jump_speed = 30

# Player starting position
player_start_x = sprite_pixel_size * tile_scaling * 2
player_start_y = sprite_pixel_size * tile_scaling * 1

# Constants used to track if player is facing left or right
right_facing = 0
left_facing = 1

# Layer Names from our TileMap
layer_name_moving_platforms = "Moving Platforms"
layer_name_platforms = "Platforms"
layer_name_coins = "Coins"
layer_name_foreground = "Foreground"
layer_name_background = "Background"
layer_name_dont_touch = "Don't Touch"
layer_name_player = "Player"
layer_name_ladders = "Ladders"

def load_texture_pair(filename):
    """
    Load a texture pair, with the second being a mirror image.
    """
    return [
        arcade.load_texture(filename),
        arcade.load_texture(filename, flipped_horizontally=True),]

class PlayerCharacter(arcade.Sprite):
    """Player Sprite"""
    
    def __init__(self):
        
        # Set up parent class
        super().__init__()
        
        # default to face right
        self.character_face_direction = right_facing
        
        # Used for flipping between image sequences
        self.cur_texture = 0
        self.scale = character_scaling
        
        # track our state
        self.jumping = False
        self.climbing = False
        self.is_on_ladder = False
        
        # --- Load textures ---
        
        # Images from Kenney.nl's Asset Pack 3
        main_path = ":resources:images/animated_characters/male_person/malePerson"
        
        # Load textures for idle standing
        self.idle_texture_pair = load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")
        
        # Load textures for walking
        self.walk_textures = []
        for i in range(8):
            texture = load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)
            
        # Load textures for climbing
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png")
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png")
        self.climbing_textures.append(texture)
        
        # Set the inital texture
        self.texture = self.idle_texture_pair[0]
        
        # Hit box will be set based on the first image used. If you want to specify
        # a different hit box, you can do it like the code below.
        # set_hit_box = [[-22,-64],[22,-64],[22,28],[-22,28]]
        self.hit_box = self.texture.hit_box_points
    
    def update_animation(self, delta_time: float = 1 / 60):
        
        # figure out if we need to flip face left or right
        if self.change_x < 0 and self.character_face_direction == right_facing:
            self.character_face_direction = left_facing
        elif self.change_x > 0 and self.character_face_direction == left_facing:
            self.character_face_direction = right_facing
        
        # Climbing animation
        if self.is_on_ladder:
            self.climbing = True
        if not self.is_on_ladder and self.climbing:
            self.climbing = False
        if self.climbing and abs(self.change_y) > 1:
            self.cur_texture += 1
            if self.cur_texture > 7:
                self.cur_texture = 0
        if self.climbing:
            self.texture = self.climbing_textures[self.cur_texture // 4]
            return

        # Jumping animation
        if self.change_y > 0 and not self.is_on_ladder:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0 and not self.is_on_ladder:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Idle animation
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Walking animation
        self.cur_texture += 1
        if self.cur_texture > 7:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][
            self.character_face_direction
        ]

class MyGame(arcade.Window):
    """ 
    Main application class
    """
    
    def __init__(self):
        
        # Call the parent class and set up the window
        super().__init__(screen_width,screen_height,screen_title)
        
        # Set the path to start with this program
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)
        
        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_needs_reset = False
        
        # Our TileMap Object
        self.tile_map = None
        
        # Our Scene Object
        self.scene = None
        
        # Serparate variable to hold the player sprite
        self.player_sprite = None
        
        # Our physics engine
        self.physics_engine = None
        
        # A Camera that can be used for scrolling the screen
        self.camera = None
        
        # A Camera that can be used to draw GUI elements
        self.gui_camera = None
        
        # Where is the right edge of the map?
        self.end_of_map = 0
        
        # Keep track of the score
        self.score = 0

        
        # Load sounds
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")
        
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
    
    def setup(self):
        # Setup the game here. Call the function to restart the game

        # Set up the game camera
        self.camera = arcade.Camera(self.width,self.height)
        
        # Set up the GUI Camera
        self.gui_camera = arcade.Camera(self.width, self.height)
        
        # Map name
        map_name = ":resources:tiled_maps/map_with_ladders.json"
        
        # Layer specific options are defined based on Layer names in a dictionary
        # Doing this will make the SpriteList for the platforms layer
        # use spatial hashing for detection
        layer_options = {layer_name_platforms: {"use_spatial_hash" : True,},
                         layer_name_moving_platforms: {"use_spatial_hash": False,},
                         layer_name_ladders: {"use_spatial_hash": True},
                         layer_name_coins: {"use_spatial_hash":True,},
                         layer_name_dont_touch: {"use_spatial_hash": True,},}
        
        # Read in the tiled map
        self.tile_map = arcade.load_tilemap(map_name, tile_scaling, layer_options)
        
        # Initialize Scene with our TileMap, this will automatically add all layers
        # from the map as SpriteLists in hte scene in the proper order.
        self.scene = arcade.Scene.from_tilemap(self.tile_map)
        
        # Keep track of the score, make sure we keep the score if the player finishes a level
        self.score = 0
        
        # Add Player SpriteList before "foreground" layer. This will make the foreground
        # be drawn after the player, making it appear to be in front of the player.
        # Setting before using scene.add_sprite allows us to define where the SpriteList
        # will be in the draw order. If we just use add_sprite, it will be apended to
        # the end of the order        
        # Setup the player, specifically placing it at these coordinates
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = player_start_x
        self.player_sprite.center_y = player_start_y
        self.scene.add_sprite("Player", self.player_sprite)
        
        # --- Load in a map from the tiled editor ---
        
        # Calculate the right edge of the my_map in pixels
        self.end_of_map = self.tile_map.width * grid_pixel_size
        
        # --- Other stuff
        # Set the background color
        if self.tile_map.background_color: 
            arcade.set_background_color(self.tile_map.background_color)
        
        
        # Create the 'physics engine'
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, 
                                                             platforms=self.scene[layer_name_moving_platforms],
                                                             gravity_constant=gravity,
                                                             ladders = self.scene[layer_name_ladders],
                                                             walls = self.scene[layer_name_platforms])
            
        
        
    def on_draw(self):
        #Render the screen
        
        # Clear the screen to the background color
        self.clear()
        
        # Activate our Camera
        self.camera.use()
        
        # Draw our Scene
        self.scene.draw()
        
        # Activate the GUI camera before drawing GUI elements
        self.gui_camera.use()
        
        # Draw our score on the screen, scrolling it with the viewport
        score_text = f"Score: {self.score}"
        arcade.draw_text(score_text,10,10,arcade.csscolor.WHITE,18,)
    
    def process_keychange(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """
        
        # Process up/down
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = player_movement_speed
            elif (self.physics_engine.can_jump(y_distance=10)and not self.jump_needs_reset):
                self.player_sprite.change_y = player_jump_speed
                self.jump_needs_reset = True
                arcade.play_sound(self.jump_sound)
        elif self.down_pressed and not self.up_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = -player_movement_speed
        
        # Process up/down when on a ladder and no movement
        if self.physics_engine.is_on_ladder():
            if not self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = 0
            elif self.up_pressed and self.down_pressed:
                self.player_sprite.change_y = 0
        
        # Process left/right
        if self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = player_movement_speed
        elif self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -player_movement_speed
        else:
            self.player_sprite.change_x = 0
    
    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed."""
        
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

        self.process_keychange()
            
    def on_key_release(self, key, modifiers):
        """ Called whenever a key is released."""

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
            self.jump_needs_reset = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        self.process_keychange()
    
    def center_camera_to_player(self):
        screen_center_x = self.player_sprite.center_x - (self.camera.viewport_width / 2)
        screen_center_y = self.player_sprite.center_y - (self.camera.viewport_height / 2)
        
        # Don't let the camera travel past 0
        if screen_center_x < 0:
            screen_center_x = 0
        if screen_center_y < 0:
            screen_center_y = 0
        player_centered = screen_center_x, screen_center_y
        
        self.camera.move_to(player_centered, 0.2)
        
    def on_update(self, delta_time):
        """ Movement and game logic. """
        
        # move the player with the physics engine
        self.physics_engine.update()
        
        # Update animations
        if self.physics_engine.can_jump():
            self.player_sprite.can_jump = False
        else:
            self.player_sprite.can_jump = True
        
        if self.physics_engine.is_on_ladder() and not self.physics_engine.can_jump():
            self.player_sprite.is_on_ladder = True
            self.process_keychange()
        else:
            self.player_sprite.is_on_ladder = False
            self.process_keychange()
            
        # Update animations
        self.scene.update_animation(delta_time, [layer_name_coins, layer_name_background, layer_name_player])
        
        # Update walls, used with moving platforms
        self.scene.update([layer_name_moving_platforms])
        
        # See if we hit any coins
        coin_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.scene["Coins"])
        
        # Loop through each coin we hit (if any) and remove it
        for coin in coin_hit_list:
            # Remove the coin
            coin.remove_from_sprite_lists()
            # Play a sound
            arcade.play_sound(self.collect_coin_sound)
            # Add one to the score
            self.score = self.score + 1
            
        # has the player collected all the coins and flags?
        if self.score == 11: 
            pass
        # Position the camera
        self.center_camera_to_player()
def main():
    """ Main Function """
    window = MyGame()
    window.setup()
    # start music
    music_player = arcade.play_sound(background_music, volume = 0.5, looping = True)
    window.run()
    if os._exit:
        arcade.stop_sound(music_player)
    
if __name__ == "__main__":
    main()
    
