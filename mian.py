"""
Platformer Game

python -m arcade.examples.platform_tutorial.01_open_window
"""
import arcade

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
# ███████████████████████ 修改㊲：生命机制相关常量 ███████████████████████
LAYER_NAME_HEART = "Heart"  # 回血物品图层名（Tiled 里必须叫 Heart）
MAX_LIVES = 3               # 初始生命数，同时也是生命上限
HEART_HEAL = 1              # 每个 Heart 回复几条命
LIFE_ICON_SIZE = 32         # 生命图标显示大小（像素）
LIFE_ICON_SPACING = 40      # 生命图标之间的间距（像素）
# ███████████████████████ 修改㊵：通关页面相关常量 ███████████████████████
FINAL_LEVEL = 3             # 最后一关，走完它出现通关页面（修改㊷：由第4关改为第3关）
STAR3_SCORE = 140           # 分数 >= 140 → 3 星
STAR2_SCORE = 70            # 分数 70~139 → 2 星，0~69 → 1 星
STAR3_TIME = 300            # 用时 <= 300 秒 → 3 星
STAR2_TIME = 400            # 用时 301~400 秒 → 2 星，400 秒以上 → 1 星
STAR_SIZE = 96              # 通关页面星星大小（像素）
STAR_SPACING = 130          # 通关页面星星中心间距（像素）
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

        # ███████████████████████ 修改①：删除 wall_list，不再手动维护墙体列表，改用 tile_map ███████████████████████
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
        # ███████████████████████ 修改㉛：新增第0关，游戏从 map2_level_0.tmx 开始 ███████████████████████
        self.level = 0

        # Do we need to reset the score?
        self.reset_score = True


        # ███████████████████████ 修改㉓：自动上台阶的平滑过渡状态。
        # step_up_progress 为 None 表示当前没有在"上台阶"；
        # 否则是 0~1 的进度值，每帧递增，配合 start_y/target_y 做插值，
        # 让抬升动作分摊到几帧内完成，而不是一帧瞬移 ███████████████████████
        self.step_up_progress = None
        self.step_up_start_y = 0
        self.step_up_target_y = 0

        # ███████████████████████ 修改㉜：已经跳了几次（落地后清零）███████████████████████
        self.jump_count = 0

        # ███████████████████████ 修改㊱：计时器，从第1关开始累计（秒），切关不清零 ███████████████████████
        self.elapsed_time = 0.0

        # ███████████████████████ 修改㊲：当前生命数和生命图标（image/Life.png）███████████████████████
        self.lives = MAX_LIVES
        self.life_texture = arcade.load_texture("image/Life.png")

        # ███████████████████████ 修改㊵：通关页面的图片、状态 ███████████████████████
        self.star_texture = arcade.load_texture("image/star.png")
        # ███████████████████████ 修改㊶：没获得的星星用单独的图片 star-dark.png ███████████████████████
        self.star_dark_texture = arcade.load_texture("image/star-dark.png")
        self.end_background = arcade.load_texture("image/background-end.png")
        self.game_cleared = False   # True 时显示通关页面，游戏逻辑暂停
        self.clear_stars = 0        # 通关时得到的星数（1~3）

        # Load sounds
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")

        # ███████████████████████ 修改㉞：背景音乐，循环播放。
        # 放在 __init__ 里只播一次（setup 每切一关都会执行，放那里会重复叠加播放）。
        # 路径和 image/、maps/ 一样是相对运行目录的相对路径。
        # 加载失败（文件不存在、系统解码不了 mp4）时只打印错误，不让游戏崩溃 ███████████████████████
        self.music_player = None
        try:
            background_music = arcade.load_sound("Music/BackgroundMusic.mp4", streaming=True)
            self.music_player = arcade.play_sound(background_music, volume=0.5, loop=True)
        except Exception as e:
            print(f"背景音乐加载失败: {e}")


    # ███████████████████████ 修改⑰：新增辅助方法，用 try/except 判断 Scene 里是否存在某个图层。
    # arcade 3.3.3 里 Scene 的图层字典是私有属性 _name_mapping，不同版本属性名可能不同，
    # 用 self.scene[name] 触发的 SceneKeyError 来判断更稳妥，不依赖具体属性名 ███████████████████████
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
        # ███████████████████████ 修改㉙：删除官方内置关卡(json)的判断，
        # 现在第1、2关也换成了自己做的本地 tmx 地图（maps/map2_level_1.tmx、map2_level_2.tmx），
        # 所有关卡统一从本地 maps 文件夹加载 ███████████████████████
        map_name = f"maps/map2_level_{self.level}.tmx"

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

        self.background = arcade.load_texture("image/background.png")


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
        image_path = "image/Player.png"
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
        # 每次最先清空屏幕
        self.clear()

        # ███████████████████████ 修改㊵：通关后只画通关页面 ███████████████████████
        if self.game_cleared:
            self.draw_clear_screen()
            return

        # ==================== 1. 最底层：画固定不动的背景 ====================
        # ███████████████████████ 修改⑫【方案A】：背景改用 gui_camera 绘制，
        # gui_camera 不随玩家移动而滚动，所以背景图会一直铺满整个窗口，
        # 不会出现玩家移动超出图片范围后露出纯色背景的问题 ███████████████████████
        self.gui_camera.use()
        if self.background:
            arcade.draw_texture_rect(
                texture=self.background,
                rect=arcade.XYWH(self.width / 2, self.height / 2, self.width, self.height)
            )

        # ==================== 2. 中间层：画跟随镜头的游戏世界 ====================
        # 切换到游戏相机（随角色移动）
        self.camera.use()

        # 绘制地图（含金币/平台/玩家）
        self.scene.draw()

        # ==================== 3. 最顶层：画固定不动的分数文字 ====================
        # 再次切回 GUI 相机（让文字不跟随镜头移动）
        self.gui_camera.use()

        # 绘制分数文字（保证浮在所有画面的最上方）
        score_text = f"Score: {self.score}"
        arcade.draw_text(
            score_text,
            10,
            680,  # 680 刚好在顶部
            arcade.csscolor.WHITE,
            18,
        )

        # ███████████████████████ 修改㊱：显示计时器（分:秒.十分之一秒），所有关卡都显示 ███████████████████████
        minutes = int(self.elapsed_time // 60)
        seconds = self.elapsed_time % 60
        arcade.draw_text(
            f"Time: {minutes:02d}:{seconds:04.1f}",
            10,
            650,
            arcade.csscolor.WHITE,
            18,
        )

        # ███████████████████████ 修改㊲：右上角按当前生命数画生命图标 ███████████████████████
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

        # ███████████████████████ 修改㊵：通关页面只响应空格（回第1关），其他按键忽略 ███████████████████████
        if self.game_cleared:
            if key == arcade.key.SPACE:
                self.restart_from_clear()
            return

        if key == arcade.key.UP or key == arcade.key.W or key == arcade.key.SPACE:
            # ███████████████████████ 修改㉜：二段跳。
            # 在地面上时先把跳跃次数清零；之后只要已跳次数 < MAX_JUMPS 就允许再跳一次。
            # 原代码第二行 change_y = 2 * PLAYER_MOVEMENT_SPEED 不在 if 里面，
            # 会无条件覆盖跳跃速度，空中可以无限连跳，所以整段重写 ███████████████████████
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

    # ███████████████████████ 修改㊲：扣命。碰到危险区、掉出地图都会调用。
    # 生命还有剩余：送回起点继续；生命扣到 0：整个游戏重来（回第1关，分数清零）███████████████████████
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
        """生命用完：回第1关，生命回满，分数清零。
        修改㊴：计时器不再清零，时间继续累计保留"""
        self.level = 1
        self.lives = MAX_LIVES
        self.score = 0
        self.reset_score = True
        self.setup()

    # ███████████████████████ 修改㊵：通关页面 ███████████████████████
    def calc_stars(self):
        """分数星级和时间星级各算一个，取较低的（两项都达标才拿高星）"""
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
        """走完最后一关：算星级，进入通关页面（计时停止）"""
        self.clear_stars = self.calc_stars()
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0
        self.game_cleared = True

    def restart_from_clear(self):
        """通关页面按空格：回第1关，生命回满，分数和计时清零，重新开始一局"""
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

        # 修改㊸：去掉了通关页面顶部的 "LEVEL CLEAR" 标题文字

        # 星星放在正中间：3 个位置，获得的用 star.png，没获得的用 star-dark.png
        # （修改㊶：不再用透明度变暗，改成直接换图片）
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
        # 修改㊹：去掉了 "Press SPACE to restart" 提示文字，按空格重新开始的功能保留

    def on_update(self, delta_time):
        """Movement and game logic"""
        # ███████████████████████ 修改㊵：通关页面期间暂停所有游戏逻辑（计时也停）███████████████████████
        if self.game_cleared:
            return

        self.physics_engine.update()

        # ███████████████████████ 修改㉜：落地后清零跳跃次数 ███████████████████████
        if self.physics_engine.can_jump():
            self.jump_count = 0

        # ███████████████████████ 修改㊱：所有关卡都累计计时（第0关也计），
        # 第0关结束进入第1关时会清零（见下面关卡结束判定）███████████████████████
        self.elapsed_time += delta_time

        # ███████████████████████ 修改㉓【平滑过渡】：如果正在执行"上台阶"动画，
        # 每帧按进度插值抬升 y 坐标，持续 STEP_UP_DURATION 秒，
        # 覆盖掉物理引擎这一帧算出的重力下坠效果，让抬升过程平滑而不是一帧瞬移 ███████████████████████
        STEP_UP_DURATION = 0.1  # 完成一次上台阶动画所需时间（秒）
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

        # ███████████████████████ 修改㉒【修复】：物理引擎 update() 结束后，玩家已经被精确停在
        # 墙壁边缘、不再与墙重叠，所以直接检测玩家自身碰撞永远查不到东西。
        # 改为用一个"探测精灵"往玩家移动方向前方探一点点距离，检测那个位置有没有障碍，
        # 有的话再看抬高一格后探测位置是否畅通，畅通就启动平滑上台阶动画（而不是瞬移）███████████████████████
        # ███████████████████████ 修改㉕：探测"前方是否需要自动上台阶"时只检测 self.step_sprites
        # （即 Steps 图层），Platforms 和箱子不再触发自动上台阶，走到跟前会正常撞停、需要跳。
        # 确认可以抬升后，仍然用完整的 self.wall_sprites 验证抬升后的位置不会撞进其他墙体 ███████████████████████
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
                    # ███ 不再直接瞬移，改为启动平滑过渡动画 ███
                    self.step_up_start_y = self.player_sprite.center_y
                    self.step_up_target_y = self.player_sprite.center_y + STEP_HEIGHT
                    self.step_up_progress = 0

        # 1.吃金币检测（使用 try-except 保护，即使地图里没画 Coins 也绝不崩溃）
        try:
            coin_hit_list = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_COINS]
            )
            for coin in coin_hit_list:
                coin.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                self.score += 1
        except Exception:
            # 如果当前地图没有 Coins 图层，直接跳过，不报错
            pass

        # ███████████████████████ 修改㉝：吃宝箱，一个宝箱 = 5 分，碰到后像金币一样消失。
        # 同样用 try/except 保护，没有 Chest 图层的关卡直接跳过 ███████████████████████
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

        # ███████████████████████ 修改㊲：吃回血物品 Heart，每个回 HEART_HEAL 条命，不超过 MAX_LIVES，
        # 碰到后消失。没有 Heart 图层的关卡直接跳过 ███████████████████████
        try:
            heart_hit_list = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_HEART]
            )
            for heart in heart_hit_list:
                heart.remove_from_sprite_lists()
                arcade.play_sound(self.collect_coin_sound)
                # ███████████████████████ 修改㊳：生命已满时吃 Heart 也会消失，但改为加 1 分 ███████████████████████
                if self.lives >= MAX_LIVES:
                    self.score += 1
                else:
                    self.lives = min(MAX_LIVES, self.lives + HEART_HEAL)
        except Exception:
            pass

        # ███████████████████████ 修改㊲（替代原修改㉘）：碰到危险区扣 1 条命。
        # try/except 只包住"检测是否碰到"，没有这个图层的关卡直接当作没碰到；
        # 扣命逻辑放在 try 外面，避免 lose_life()/setup() 里的真实报错被吞掉 ███████████████████████
        hit_hazard = False
        try:
            hit_hazard = bool(arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_DONT_TOUCH]
            ))
        except Exception:
            pass
        if hit_hazard:
            self.lose_life()

        # ███████████████████████ 修改㊲：掉出地图扣 1 条命 ███████████████████████
        if self.player_sprite.center_y < -100:
            self.lose_life()

        # 关卡结束判定
        # ███████████████████████ 修改㊵：走完最后一关（FINAL_LEVEL）出现通关页面，不再进入下一关 ███████████████████████
        if self.player_sprite.center_x >= self.end_of_map and self.level >= FINAL_LEVEL:
            self.show_clear_screen()
        elif self.player_sprite.center_x >= self.end_of_map:
            # ███████████████████████ 修改㉟：积分规则。
            # 第0关结束（进入第1关）时分数清零；第1关及以后切关不清零，分数一直累计 ███████████████████████
            self.reset_score = (self.level == 0)
            if self.level == 0:
                self.elapsed_time = 0.0  # 修改㊱：进入第1关时计时器清零
            self.level += 1
            self.setup()

        # 动态更新镜头
        self.center_camera_to_player()



def main():
    """Main function"""
    window = GameView()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()