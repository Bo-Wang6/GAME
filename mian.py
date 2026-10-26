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
# ███████████████████████ 修改㉜：最多连续跳跃次数（2 = 二段跳）███████████████████████
MAX_JUMPS = 2

# Player starting position
PLAYER_START_X = 64
PLAYER_START_Y = 225

# Layer Names from our TileMap
LAYER_NAME_PLATFORMS = "Platforms"
LAYER_NAME_COINS = "Coin"
# ███████████████████████ 修改㉝：宝箱图层名（Tiled 里的图层必须叫 Chest）和每个宝箱的分数 ███████████████████████
LAYER_NAME_CHEST = "Chest"
CHEST_SCORE = 5
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

        # Load sounds
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")


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
            LAYER_NAME_DONT_TOUCH: {
                "use_spatial_hash": True,
            },
        }

        # ███████████████████████ 修改②：删除了重复的 layer_options 覆盖赋值（原代码这里又定义了一次只含 Platforms 的 layer_options，把上面完整的配置覆盖掉了） ███████████████████████

        # Read in the tiled map
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, layer_options)

        # Initialize Scene with our TileMap, this will automatically add all layers
        # from the map as SpriteLists in the scene in the proper order.
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

         # Keep track of the score, make sure we keep the score if the player finishes a level
        if self.reset_score:
            self.score = 0
        self.reset_score = True

        # ███████████████████████ 修改㉚【核心修复】：GRID_PIXEL_SIZE 是按 SPRITE_PIXEL_SIZE=128
        # 写死算出来的（那是给 arcade 内置 128px 素材用的假设）。
        # 你自己做的地图 tile 实际是 32×32 像素，用 GRID_PIXEL_SIZE 算出来的 end_of_map
        # 会比地图真实宽度大好几倍，导致玩家永远走不到触发下一关的位置。
        # 改成用 self.tile_map.tile_width（地图文件里真实的 tile 像素宽度）来算，
        # 这样不管以后地图用多大的 tile 都能正确算出地图右边缘 ███████████████████████
        self.end_of_map = self.tile_map.width * self.tile_map.tile_width * TILE_SCALING

        # ███████████████████████ 修改③【核心问题】：删除了 self.scene = arcade.Scene()
        # 原代码在这里用一个空场景把上面刚加载好的 tilemap 场景整个覆盖掉了，
        # 导致真正的关卡地图从未被绘制，这就是"第二关变空白"的根本原因。███████████████████████

        # ███████████████████████ 修改㉖：删除了所有测试用的纯色色块生成代码
        # （原修改⑯里的测试金币、测试危险区、测试前景装饰）。
        # 现在 Coin / Steps / Non-interactive items / Platforms 已经是 Tiled 里做好的真实图层，
        # 不再需要占位测试内容。如果地图里还没有 Don't Touch / Foreground 这两个真实图层，
        # 相关功能会自动跳过（不会报错），等 Tiled 里补上对应图层后自动生效 ███████████████████████

        # Set up the GUI Camera
        self.gui_camera = arcade.Camera2D()

        # Keep track of the score
        self.score = 0

        # ███████████████████████ 修改④：删除 player_list / wall_list / background 的手动初始化，
        # wall_list 不再需要（墙体现在完全来自 tile_map 的 Platforms 层）███████████████████████
        self.background = arcade.load_texture("image/background.png")


         # Add Player Spritelist before "Foreground" layer. This will make the foreground
        # be drawn after the player, making it appear to be in front of the Player.
        # Setting before using scene.add_sprite allows us to define where the SpriteList
        # will be in the draw order. If we just use add_sprite, it will be appended to the
        # end of the order.
        # ███████████████████████ 修改⑭（恢复）：Foreground 图层不再保证一定存在
        # （之前是靠修改⑯的测试代码兜底生成，现已删除），改回先判断是否存在，
        # 不存在就用普通的 add_sprite_list，避免地图没有 Foreground 层时报 KeyError ███████████████████████
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

        # ███████████████████████ 修改⑲：箱子层改名为 "Non-interactive items"（对应 Tiled 里改的新名字），
        # 仍然并入碰撞判定，玩家可以站上去。内置的第1、2关地图没有这个层，
        # 所以先判断该图层是否存在，存在才合并，避免第1、2关报错 ███████████████████████
        # ███████████████████████ 修改㉔：新增 Steps 图层（台阶）也并入碰撞判定，
        # 否则台阶层完全没有碰撞、玩家站上去等于踩空气，会出现走不动/卡住的异常表现 ███████████████████████
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
        # ███████████████████████ 修改⑳：保存为实例变量，供 on_update 里"自动上台阶"逻辑使用 ███████████████████████
        self.wall_sprites = wall_sprites

        # ███████████████████████ 修改㉕：单独保存 Steps 图层，"自动上台阶"只对这一层生效，
        # Platforms 和 Non-interactive items（箱子）仍然是普通碰撞，走到跟前会撞停，需要跳 ███████████████████████
        if self._scene_has_layer("Steps"):
            self.step_sprites = self.scene["Steps"]
        else:
            self.step_sprites = arcade.SpriteList()

        # ███████████████████████ 修改㉚（配套）：自动上台阶的抬升高度也改用地图真实 tile 高度，
        # 不再用写死的 GRID_PIXEL_SIZE（那是按 128px 假设算的，你的地图实际是 32px 一格）███████████████████████
        self.step_height = self.tile_map.tile_height * TILE_SCALING

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, gravity_constant=GRAVITY, walls=wall_sprites
        )
        self.jump_count = 0  # 修改㉜：切换关卡/重开时清零跳跃次数

        # ███████████████████████ 修改⑦：删除手动创建地面 wall 的 for 循环（硬编码坐标，与真实地图无关，
        # 且原代码这段循环写法本身有 bug：Sprite 第二个位置参数应为 scale 关键字，这里传成了裸的 TILE_SCALING）███████████████████████

        # ███████████████████████ 修改⑧：删除手动放置箱子(coordinate_list)的代码，箱子应由 tile_map 提供 ███████████████████████

        # ███████████████████████ 修改⑨：删除手动放置金币的 for 循环，金币应来自 tile_map 的 Coins 层，
        # 而不是写死在 (128, 1250, 256) 这几个固定坐标上 ███████████████████████

        # ███████████████████████ 修改⑩：删除重复的第二次 PhysicsEnginePlatformer 创建（原代码创建了两次物理引擎，
        # 第二次同样错误地引用了 wall_list）███████████████████████

    def on_draw(self):
        """Render the screen."""
        # 每次最先清空屏幕
        self.clear()

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

    def on_key_press(self, key, modifiers):

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
                self.player_sprite.change_x = -2 * PLAYER_MOVEMENT_SPEED
            else:
                self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            if modifiers & arcade.key.MOD_SHIFT:
                self.player_sprite.change_x = 2 * PLAYER_MOVEMENT_SPEED
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

    def on_update(self, delta_time):
        """Movement and game logic"""
        self.physics_engine.update()

        # ███████████████████████ 修改㉜：落地后清零跳跃次数 ███████████████████████
        if self.physics_engine.can_jump():
            self.jump_count = 0

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

        # ███████████████████████ 修改㉘：调试完成，恢复 try/except 保护。
        # 避免以后其他关卡地图没有这个危险区图层时直接报错崩溃 ███████████████████████
        try:
            if arcade.check_for_collision_with_list(
                self.player_sprite, self.scene[LAYER_NAME_DONT_TOUCH]
            ):
                self.player_sprite.change_x = 0
                self.player_sprite.change_y = 0
                self.player_sprite.center_x = PLAYER_START_X
                self.player_sprite.center_y = PLAYER_START_Y
                arcade.play_sound(self.game_over)
        except Exception:
            # 如果当前地图没有这个危险区图层，直接跳过，不报错
            pass

        # 掉出地图边界重置
        if self.player_sprite.center_y < -100:
            self.player_sprite.center_x = PLAYER_START_X
            self.player_sprite.center_y = PLAYER_START_Y
            arcade.play_sound(self.game_over)

        # 关卡结束判定
        if self.player_sprite.center_x >= self.end_of_map:
            self.level += 1
            self.reset_score = False
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