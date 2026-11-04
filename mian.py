"""
Platformer Game

python -m arcade.examples.platform_tutorial.01_open_window
"""
import os
import sys

import arcade


def resource_path(relative_path):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "The Moon Treasure"
SPRITE_PIXEL_SIZE = 128

# Constants used to scale our sprites from their original size
CHARACTER_SCALING = 1
TILE_SCALING = 0.5
COIN_SCALING = 0.5
GRID_PIXEL_SIZE = SPRITE_PIXEL_SIZE * TILE_SCALING


# Movement speed of player, in pixels per frame
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 0.2
PLAYER_JUMP_SPEED = 20
# The maximum number of consecutive jumps/最多连续跳跃次数 2
MAX_JUMPS = 2

# Player starting position
PLAYER_START_X = 64
PLAYER_START_Y = 225

# Layer Names from our TileMap
LAYER_NAME_PLATFORMS = "Platforms"
LAYER_NAME_COINS = "Coin"
LAYER_NAME_CHEST = "Chest"
CHEST_SCORE = 5
# Add Heart
LAYER_NAME_HEART = "Heart"
MAX_LIVES = 3
HEART_HEAL = 1
LIFE_ICON_SIZE = 32
LIFE_ICON_SPACING = 40 
FINAL_LEVEL = 3             # End Level/最后一关
STAR3_SCORE = 140           # Score >= 140 -> 3 stars/分数 >= 140 -> 3 星
STAR2_SCORE = 70            # Score >= 70~139 -> 2 stars,0~69 -> 1 stars/分数 70~139 -> 2 星，0~69 -> 1 星
STAR3_TIME = 300            # time used <= 300 s秒 -> 3 stars星
STAR2_TIME = 400            # time used用时 301~400 s秒-> 2 stars星，400 s over秒以上 -> 1 stars星
STAR_SIZE = 96              # star size in the end of the game
STAR_SPACING = 130          # star space
LAYER_NAME_FOREGROUND = "Foreground"
LAYER_NAME_BACKGROUND = "Background"
LAYER_NAME_DONT_TOUCH = "Non-contactable region"


class GameView(arcade.Window):
    """
    Main application class.
    """

    def __init__(self):

        # Call the parent class to set up the window
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)

        # Our TileMap Object
        self.tile_map = None

        # These are 'lists' that keep track of our sprites. Each sprite should go into a list.

        self.player_list = None
        self.background = None

        # A Camera that can be used to draw GUI elements
        self.gui_camera = None

        # Keep track of the score
        self.score = 0

        # Separate variable that holds the player sprite

        self.player_sprite = None

        # Python Arcade physics engine
        self.physics_engine = None

        # A Camera that can be used for scrolling the screen
        self.camera = None

        # pure color 纯色
        # self.background_color = arcade.csscolor.CORNFLOWER_BLUE

        # Do we need to reset the score?
        self.reset_score = True

        # Where is the right edge of the map?
        self.end_of_map = 0

        # Level
        self.level = 0

        # Do we need to reset the score?
        self.reset_score = True


        # Step
        self.step_up_progress = None
        self.step_up_start_y = 0
        self.step_up_target_y = 0

        self.jump_count = 0

        # After lever 1 time not be 0
        self.elapsed_time = 0.0

        # Lives
        self.lives = MAX_LIVES
        self.life_texture = arcade.load_texture(resource_path("image/Life.png"))

        # The end level
        self.star_texture = arcade.load_texture(resource_path("image/star.png"))
        # The dark stars(stars don't got)
        self.star_dark_texture = arcade.load_texture(resource_path("image/star-dark.png"))
        self.end_background = arcade.load_texture(resource_path("image/background-end.png"))
        self.game_cleared = False   # if it is True, game ends
        self.clear_stars = 0        # got stars at the ends（1~3）

        # Load sounds
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")

        # Add background Music-it made by ChatGPT
        self.music_player = None
        try:
            background_music = arcade.load_sound(resource_path("Music/BackgroundMusic.mp4"), streaming=True)
            self.music_player = arcade.play_sound(background_music, volume=0.5, loop=True)
        except Exception as e:
            print(f"背景音乐加载失败: {e}")


    def _scene_has_layer(self, name):
        try:
            self.scene[name]
            return True
        except arcade.scene.SceneKeyError:
            return False

    def setup(self):
        """Set up the game here. Call this function to restart the game."""
         # Create the Sprite lists

         # Set up the Camera
        self.camera = arcade.Camera2D()

       # Map name

        map_name = resource_path(f"maps/map2_level_{self.level}.tmx")

        # Layer Specific Options for the Tilemap
        layer_options = {
            LAYER_NAME_PLATFORMS: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_COINS: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_CHEST: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_HEART: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_DONT_TOUCH: {
                "use_spatial_hash": True,
            },
        }

        # Read in the tiled map
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, layer_options)

        # Initialize Scene with our TileMap, this will automatically add all layers
        # from the map as SpriteLists in the scene in the proper order.
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

         # Keep track of the score, make sure we keep the score if the player finishes a level
        if self.reset_score:
            self.score = 0
        self.reset_score = True

        self.end_of_map = self.tile_map.width * self.tile_map.tile_width * TILE_SCALING

        # Set up the GUI Camera
        self.gui_camera = arcade.Camera2D()

        self.background = arcade.load_texture(resource_path("image/background.png"))


         # Add Player Spritelist before "Foreground" layer. This will make the foreground
        # be drawn after the player, making it appear to be in front of the Player.
        # Setting before using scene.add_sprite allows us to define where the SpriteList
        # will be in the draw order. If we just use add_sprite, it will be appended to the
        # end of the order.

        if self._scene_has_layer(LAYER_NAME_FOREGROUND):
            self.scene.add_sprite_list_after("Player", LAYER_NAME_FOREGROUND)
        else:
            self.scene.add_sprite_list("Player")

        # Set up the player, specifically placing it at these coordinates.
        image_path = resource_path("image/Player.png")
        self.player_sprite = arcade.Sprite(image_path, scale=0.2)
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = PLAYER_START_Y
        self.scene.add_sprite("Player", self.player_sprite)

        # --- Other stuff
        # Set the background color
        if self.tile_map.background_color:
            arcade.set_background_color(self.tile_map.background_color)

        wall_sprites = self.scene[LAYER_NAME_PLATFORMS]
        extra_wall_layers = []
        if self._scene_has_layer("Non-interactive items"):
            extra_wall_layers.append("Non-interactive items")
        if self._scene_has_layer("Steps"):
            extra_wall_layers.append("Steps")
        if extra_wall_layers:
            wall_sprites = arcade.SpriteList()
            wall_sprites.extend(self.scene[LAYER_NAME_PLATFORMS])
            for layer_name in extra_wall_layers:
                wall_sprites.extend(self.scene[layer_name])
        # Automatic Step Climbing/自动上台阶
        self.wall_sprites = wall_sprites

        if self._scene_has_layer("Steps"):
            self.step_sprites = self.scene["Steps"]
        else:
            self.step_sprites = arcade.SpriteList()

        self.step_height = self.tile_map.tile_height * TILE_SCALING

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, gravity_constant=GRAVITY, walls=wall_sprites
        )
        self.jump_count = 0  # Reset the number of jumps when switching levels or reopening 修改：切换关卡/重开时清零跳跃次数

    def on_draw(self):
        """Render the screen."""
        # clear the scren/清空屏幕  
        self.clear()

        # only draw the end background, no player, heart...
        if self.game_cleared:
            self.draw_clear_screen()
            return

        # Background following camera(player)/背景跟随摄像机（玩家）
        self.gui_camera.use()
        if self.background:
            arcade.draw_texture_rect(
                texture=self.background,
                rect=arcade.XYWH(self.width / 2, self.height / 2, self.width, self.height)
            )

        
        # Switch to the game camera (as the character moves)/切换到游戏相机（随角色移动）
        self.camera.use()

        # draw the map(coin,platfrom/player)绘制地图（含金币/平台/玩家）
        self.scene.draw()

        # score not moving
        # turn back to GUI camera
        self.gui_camera.use()

        # draw the score
        score_text = f"Score: {self.score}"
        arcade.draw_text(
            score_text,
            10,
            680,  # 680 刚好在顶部
            arcade.csscolor.WHITE,
            18,
        )

        # draw the time/For example-> 10m/10s/10
        minutes = int(self.elapsed_time // 60)
        seconds = self.elapsed_time % 60
        arcade.draw_text(
            f"Time: {minutes:02d}:{seconds:04.1f}",
            10,
            650,
            arcade.csscolor.WHITE,
            18,
        )

        # draw the life
        for i in range(self.lives):
            arcade.draw_texture_rect(
                texture=self.life_texture,
                rect=arcade.XYWH(
                    self.width - 30 - i * LIFE_ICON_SPACING,
                    690,
                    LIFE_ICON_SIZE,
                    LIFE_ICON_SIZE,
                ),
            )

    def on_key_press(self, key, modifiers):

        # press space turn level-end to level-1(level-0 is for teaching how to play this game)
        if self.game_cleared:
            if key == arcade.key.SPACE:
                self.restart_from_clear()
            return

        if key == arcade.key.UP or key == arcade.key.W or key == arcade.key.SPACE:
            # the max jump times only 2
            if self.physics_engine.can_jump():
                self.jump_count = 0
            if self.jump_count < MAX_JUMPS:
                self.player_sprite.change_y = 2 * PLAYER_MOVEMENT_SPEED
                self.jump_count += 1
                arcade.play_sound(self.jump_sound)
        elif key == arcade.key.LEFT or key == arcade.key.A:
            if modifiers & arcade.key.MOD_SHIFT:
                self.player_sprite.change_x = -1.5 * PLAYER_MOVEMENT_SPEED
            else:
                self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            if modifiers & arcade.key.MOD_SHIFT:
                self.player_sprite.change_x = 1.5 * PLAYER_MOVEMENT_SPEED
            else:
                self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
        

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key."""
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = 0
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = 0

    def center_camera_to_player(self):
        target_x = self.player_sprite.center_x
        target_y = self.player_sprite.center_y


        if target_x < WINDOW_WIDTH / 2:
            target_x = WINDOW_WIDTH / 2
        if target_y < WINDOW_HEIGHT / 2:
            target_y = WINDOW_HEIGHT / 2

        self.camera.position = (target_x, target_y)

    # The Non-contactable region
    def lose_life(self):
        self.lives -= 1
        arcade.play_sound(self.game_over)
        if self.lives <= 0:
            self.restart_game()
            return
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = PLAYER_START_Y
        self.step_up_progress = None
        self.jump_count = 0

    def restart_game(self):
        """Out of lives: back to level 1, lives full, score reset to 0. The timer is not reset, time keeps counting/生命用完：回第1关，生命回满，分数清零；计时器不清零，时间继续累计"""
        self.level = 1
        self.lives = MAX_LIVES
        self.score = 0
        self.reset_score = True
        self.setup()

    # the level-end(the end of the game)
    def calc_stars(self):
        """The score star and the time star are each counted as one, and the lower one is taken (only when both are met can a high star be obtained)/分数星级和时间星级各算一个，取较低的（两项都达标才拿高星）"""
        if self.score >= STAR3_SCORE:
            score_stars = 3
        elif self.score >= STAR2_SCORE:
            score_stars = 2
        else:
            score_stars = 1

        if self.elapsed_time <= STAR3_TIME:
            time_stars = 3
        elif self.elapsed_time <= STAR2_TIME:
            time_stars = 2
        else:
            time_stars = 1

        return min(score_stars, time_stars)

    def show_clear_screen(self):
        """After completing the last level: Calculate the star rating and enter the clearance page (the timer stops)/走完最后一关：算星级，进入通关页面（计时停止）"""
        self.clear_stars = self.calc_stars()
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0
        self.game_cleared = True

    def restart_from_clear(self):
        """press space turn back to level 1(score=0, life=3 and time =0/0/0)/按空格键返回第1关得分=0-生命值=3-时间=0/0/0"""
        self.game_cleared = False
        self.level = 1
        self.lives = MAX_LIVES
        self.score = 0
        self.reset_score = True
        self.elapsed_time = 0.0
        self.setup()

    def draw_clear_screen(self):
        self.gui_camera.use()
        cx = self.width / 2
        cy = self.height / 2

        # 通关背景，铺满窗口
        arcade.draw_texture_rect(
            texture=self.end_background,
            rect=arcade.XYWH(cx, cy, self.width, self.height),
        )



        # draw stars, stars is you got, star-dark is you not got
        for i in range(3):
            star_x = cx + (i - 1) * STAR_SPACING
            star_texture = self.star_texture if i < self.clear_stars else self.star_dark_texture
            arcade.draw_texture_rect(
                texture=star_texture,
                rect=arcade.XYWH(star_x, cy, STAR_SIZE, STAR_SIZE),
            )

        # 星星下面显示分数和用时
        minutes = int(self.elapsed_time // 60)
        seconds = self.elapsed_time % 60
        arcade.draw_text(
            f"Score: {self.score}    Time: {minutes:02d}:{seconds:04.1f}",
            cx, cy - 110, arcade.csscolor.WHITE, 24,
            anchor_x="center",
        )
        # No "Press SPACE to restart" text on this page, but pressing space still restarts/页面上没有"Press SPACE to restart"提示文字，但按空格仍然可以重新开始

    def on_update(self, delta_time):
        """Movement and game logic"""
        # game set
        if self.game_cleared:
            return

        self.physics_engine.update()

        # reset the number of jumps after landing/落地后清零跳跃次数
        if self.physics_engine.can_jump():
            self.jump_count = 0

        # All levels are cumulatively timed (Level 0 is also counted)/所有关卡都累计计时（第0关也计），
        # When entering level 1 at the end of level 0, it will reset to zero (see the level end determination below)/第0关结束进入第1关时会清零（见下面关卡结束判定)
        self.elapsed_time += delta_time

        # The step 
        STEP_UP_DURATION = 0.1  # the time for step
        if self.step_up_progress is not None:
            self.step_up_progress += delta_time / STEP_UP_DURATION
            if self.step_up_progress >= 1:
                self.step_up_progress = 1
                self.player_sprite.center_y = self.step_up_target_y
                self.step_up_progress = None
            else:
                self.player_sprite.center_y = (
                    self.step_up_start_y
                    + (self.step_up_target_y - self.step_up_start_y) * self.step_up_progress
                )

        # 物理引擎 update() 结束后，玩家已经被精确停在
        # 墙壁边缘、不再与墙重叠，所以直接检测玩家自身碰撞永远查不到东西。
        # 改为用一个"探测精灵"往玩家移动方向前方探一点点距离，检测那个位置有没有障碍，
        # 有的话再看抬高一格后探测位置是否畅通，畅通就启动平滑上台阶动画（而不是瞬移）
        # 探测"前方是否需要自动上台阶"时只检测 self.step_sprites
        # （即 Steps 图层），Platforms 和箱子不再触发自动上台阶，走到跟前会正常撞停、需要跳。
        # 确认可以抬升后，仍然用完整的 self.wall_sprites 验证抬升后的位置不会撞进其他墙体 
        STEP_HEIGHT = self.step_height  # 一格 tile 的高度（按地图真实 tile 尺寸算）
        STEP_PROBE_DISTANCE = 4  # 往前方探测的距离（像素）
        if (
            self.step_up_progress is None
            and self.player_sprite.change_x != 0
            and self.physics_engine.can_jump()
        ):
            direction = 1 if self.player_sprite.change_x > 0 else -1
            probe = arcade.SpriteSolidColor(
                int(self.player_sprite.width), int(self.player_sprite.height),
                color=arcade.color.RED
            )
            probe.center_x = self.player_sprite.center_x + direction * STEP_PROBE_DISTANCE
            probe.center_y = self.player_sprite.center_y
            if arcade.check_for_collision_with_list(probe, self.step_sprites):
                probe.center_y += STEP_HEIGHT
                if not arcade.check_for_collision_with_list(probe, self.wall_sprites):
                    self.step_up_start_y = self.player_sprite.center_y
                    self.step_up_target_y = self.player_sprite.center_y + STEP_HEIGHT
                    self.step_up_progress = 0

        # eat coin
        try:
            coin_hit_list = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_COINS]
            )
            for coin in coin_hit_list:
                coin.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                self.score += 1
        except Exception:
            # if no coin nothing happen
            pass

        # Coin=1point chest=5
        try:
            chest_hit_list = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_CHEST]
            )
            for chest in chest_hit_list:
                chest.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                self.score += CHEST_SCORE
        except Exception:
            pass

        # eat the heart+1life,if life=3 +1point +0life
        try:
            heart_hit_list = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_HEART]
            )
            for heart in heart_hit_list:
                heart.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                if self.lives >= MAX_LIVES:
                    self.score += 1
                else:
                    self.lives = min(MAX_LIVES, self.lives + HEART_HEAL)
        except Exception:
            pass

        # touch the Non-contactable region, life - 1
        hit_hazard = False
        try:
            hit_hazard = bool(arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_DONT_TOUCH]
            ))
        except Exception:
            pass
        if hit_hazard:
            self.lose_life()

        # out the map life - 1
        if self.player_sprite.center_y < -100:
            self.lose_life()

        # end of the game/关卡结束判定
        if self.player_sprite.center_x >= self.end_of_map and self.level >= FINAL_LEVEL:
            self.show_clear_screen()
        elif self.player_sprite.center_x >= self.end_of_map:
            # The score is reset to zero at the end of level 0 (entering level 1). For the first level and subsequent levels, the score will not be reset and will keep accumulating/第0关结束（进入第1关）时分数清零；第1关及以后切关不清零，分数一直累计
            self.reset_score = (self.level == 0)
            if self.level == 0:
                self.elapsed_time = 0.0  
            self.level += 1
            self.setup()

        # Dynamic update of the camera/动态更新镜头
        self.center_camera_to_player()



def main():
    """Main function"""
    window = GameView()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()

# The picture and the background music is made by ChatGPT
# Eat coin, chest sound and jump sound from Python Arcade.
# The Claude help to fix the bugs and for add some things(steps and chang the maps to I made, not from the Python Arcade...)
# The website(https://www.photoroom.com/zh/tools/background-remover) help to remove the background of the picture.
# Vscode is the coding tools and the use the Tutorials from Python Arcade(https://api.arcade.academy/en/2.6.17/examples/platform_tutorial/index.html)
# Python is 3.13.13，Python Arcade Version: 3.3.3