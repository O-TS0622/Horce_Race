import pygame
import random
import sys
import time
import math
import os
import asyncio

ASSET_DIR = "assets"

# reset_race() 内で初期化
results_saved = False  # 結果保存の一度きりフラグ
recent_results = []  # Web用に過去5レースを保存するリスト


pygame.init()

# 画面サイズ
WIDTH, HEIGHT = 1200, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("競馬レース")

# 色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
PANEL = (230, 230, 230)

# フォント（Web向け）
FONT_PATH = os.path.join(ASSET_DIR, "NotoSansJP-subset.ttf")
font = pygame.font.Font(FONT_PATH, 60)
mid_font = pygame.font.Font(FONT_PATH, 40)
small_font = pygame.font.Font(FONT_PATH, 30)
title_font = pygame.font.Font(FONT_PATH, 22)

_font_cache = {}

def get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(FONT_PATH, size)
    return _font_cache[size]

def render_text_fit(text, max_width, base_size, min_size, color=BLACK):
    size = base_size
    while size >= min_size:
        surface = get_font(size).render(text, True, color)
        if surface.get_width() <= max_width:
            return surface
        size -= 1
    return surface

def get_common_font_size(strings, max_width, base_size=22, min_size=12):
    for size in range(base_size, min_size - 1, -1):
        if all(get_font(size).size(s)[0] <= max_width for s in strings):
            return size
    return min_size


# 背景

BG_FILE = os.path.join(ASSET_DIR, "horceracefield.jpg")
bg = pygame.image.load(BG_FILE)
bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))

# タイトルPNG
TITLE_FILE = os.path.join(ASSET_DIR, "tennoji.png") 
title_image = pygame.image.load(TITLE_FILE)
title_scale = 0.7
title_w = int(title_image.get_width() * title_scale)
title_h = int(title_image.get_height() * title_scale)
title_image = pygame.transform.scale(title_image, (title_w, title_h))

# 馬の画像
standing_files = [
    os.path.join(ASSET_DIR, "standing_horce1.png"),
    os.path.join(ASSET_DIR, "standing_horce2.png"),
    os.path.join(ASSET_DIR, "standing_horce3.png"),
    os.path.join(ASSET_DIR, "standing_horce4.png"),
    os.path.join(ASSET_DIR, "standing_horce5.png"),
]
running_files = [
    os.path.join(ASSET_DIR, "running_horce1.png"),
    os.path.join(ASSET_DIR, "running_horce2.png"),
    os.path.join(ASSET_DIR, "running_horce3.png"),
    os.path.join(ASSET_DIR, "running_horce4.png"),
    os.path.join(ASSET_DIR, "running_horce5.png"),
]
# 一度だけ読み込んでスケーリングしてキャッシュ
def load_and_scale(path, size=(180,120)):
    return pygame.transform.scale(pygame.image.load(path), size)

standing_horses = [load_and_scale(f) for f in standing_files]
running_horses = [load_and_scale(f) for f in running_files]

num_horses = len(standing_horses)
horse_current_images = standing_horses.copy()  # 初期は立ち姿

# デッドヒート範囲
DEADHEAT_START_X = 150
DEADHEAT_END_X = 650
DEADHEAT_UPDATE_INTERVAL = 8
GOAL_X = WIDTH - 200

# 馬の名前（神話系）
japanese_gods = ["アマテラス", "スサノオ", "ツクヨミ", "イザナギ", "イザナミ"]
nordic_gods = ["オーディン", "トール", "ロキ", "フレイ", "フレイア"]
greek_gods = ["ゼウス", "アポロ", "アテナ", "アレス", "ヘルメス"]
all_gods = japanese_gods + nordic_gods + greek_gods

# 背景スクロール
bg_speed = 3
bg_x = 0

# 馬の位置
positions = [[-250, 175 + i*80] for i in range(num_horses)]
vertical_offset = [0]*num_horses

# 馬のステータス
stats_list = []
horse_names = []
deadheat_ranges = []
deadheat_targets = []
deadheat_active = True
sprint_times = []
results = []
finished = False
start_time = time.time()
goal_line_x = WIDTH + 50
last_deadheat_update = time.time()

# 有利戦術選択
advantaged_type = random.choice(["差し", "逃げ", "先行", "追込"])

# 結果アニメーション制御
result_display_index = 0
result_display_start = 0

def random_deadheat_range():
    start = random.uniform(DEADHEAT_START_X, DEADHEAT_END_X - 150)
    end = random.uniform(start + 150, DEADHEAT_END_X)
    return start, end

def reset_race():
    global positions, deadheat_ranges, deadheat_targets, deadheat_active
    global start_time, finished, results, goal_line_x, sprint_times, stats_list, horse_names
    global last_deadheat_update, bg_x, advantaged_type
    global result_display_index, result_display_start, results_saved

    positions[:] = [[50, 175 + i*80] for i in range(num_horses)]
    deadheat_active = True

    # 各馬のステータスを初期化
    stats_list[:] = []
    for _ in range(num_horses):
        stats_list.append({
            "stamina": random.uniform(50, 100),
            "burst": random.uniform(3, 6),
            "strategy": random.choice(["差し", "逃げ", "先行", "追込"])
        })

    horse_names[:] = random.sample(all_gods, num_horses)
    start_time = time.time()
    finished = False
    results[:] = []
    goal_line_x = WIDTH + 50
    sprint_times[:] = [random.uniform(22, 25) for _ in range(num_horses)]
    last_deadheat_update = time.time()
    bg_x = 0
    result_display_index = 0
    result_display_start = 0
    results_saved = False

    advantaged_type = random.choice(["差し", "逃げ", "先行", "追込"])

    # --- デッドヒート範囲を戦術別に設定 ---
    deadheat_ranges[:] = []
    deadheat_targets[:] = []
    for stat in stats_list:
        strategy = stat["strategy"]
        if strategy in ["逃げ", "先行"]:
            # 右寄り
            rng = (DEADHEAT_END_X - 200, DEADHEAT_END_X)
        elif strategy == "差し":
            # 中央付近
            rng = (DEADHEAT_START_X + 100, DEADHEAT_END_X - 200)
        else:  # 追込
            # 左寄り
            rng = (DEADHEAT_START_X, DEADHEAT_START_X + 200)

        deadheat_ranges.append(rng)
        deadheat_targets.append(random.uniform(*rng))

    # --- 有利戦術による補正 ---
    for i, stat in enumerate(stats_list):
        if stat["strategy"] == advantaged_type:
            # 通常有利補正
            stat["burst"] *= random.uniform(1.3, 1.6)

            # 特別：追込が有利戦術のときはさらに強化
            if advantaged_type == "追込" and stat["strategy"] == "追込":
                stat["burst"] *= random.uniform(1.2, 1.4)
        else:
            stat["burst"] *= random.uniform(0.9, 1.2)

     # --- 順位表用フォントサイズ計算 ---
    rank_strings = [f"{i+1}位：{horse_names[i]} ({stats_list[i]['strategy']})" for i in range(len(horse_names))]
    rank_font_size = get_common_font_size(rank_strings, max_width=300, base_size=20, min_size=12)
    globals()["rank_font"] = pygame.font.Font(FONT_PATH, rank_font_size)

    # --- 過去データ用フォントサイズ計算 ---
    history_strings = []
    for row in recent_results:
        if len(row) >= 4:
            s = f"{row[1]}番 {row[2]}（{row[3]}）"
            history_strings.append(s)
    if history_strings:
        history_font_size = get_common_font_size(history_strings, max_width=250, base_size=20, min_size=12)
    else:
        history_font_size = 20
    globals()["history_font"] = pygame.font.Font(FONT_PATH, history_font_size)


# --- リプレイ用変数 ---
replay_mode = False       # リプレイ中かどうか
replay_frames = []        # フレーム履歴からコピーしたリプレイ用フレーム
replay_index = 0          # リプレイの現在フレーム
photo_finish_timer = 0    # リプレイ終了後の写真判定表示用（必要なら残す）
frame_history = []        # 常時最新フレームを保存
HISTORY_LENGTH = 180      # 3秒分の履歴（60FPS×3秒）

async def opening_sequence():
    global positions, horse_current_images

    # 馬入場初期位置
    start_x_positions = [-250]*num_horses
    target_y = [175 + i*80 for i in range(num_horses)]
    target_x = [50]*num_horses

    horse_current_images[:] = running_horses.copy()
    for idx in range(num_horses):
        positions[idx][0] = start_x_positions[idx]
        positions[idx][1] = target_y[idx]

    clock = pygame.time.Clock()
    frame_count = 0

    # 入場アニメーション＋タイトル
    while frame_count < 240:
        screen.fill(WHITE)
        screen.blit(bg, (0, 0))

        # タイトルフェード＋拡縮
        if frame_count < 60:
            alpha = int((frame_count/60)*255)
            scale_factor = 0.5 + 0.5*(frame_count/60)
        elif frame_count < 180:
            alpha = 255
            scale_factor = 1.0
        else:
            alpha = int(((240-frame_count)/60)*255)
            scale_factor = 1.0 - 0.3*((frame_count-180)/60)

        temp_image = pygame.transform.scale(
            title_image,
            (int(title_image.get_width()*scale_factor), int(title_image.get_height()*scale_factor))
        )
        temp_image.set_alpha(alpha)
        screen.blit(temp_image, (WIDTH//2 - temp_image.get_width()//2, HEIGHT//2 - temp_image.get_height()//2))

        # 馬入場
        for idx in range(num_horses):
            if positions[idx][0] < target_x[idx]:
                positions[idx][0] += 5
            screen.blit(horse_current_images[idx], (positions[idx][0], positions[idx][1]))

        pygame.display.flip()
        frame_count += 1
        await asyncio.sleep(1/60)

    # 入場後は立ち姿に切り替え
    horse_current_images[:] = standing_horses.copy()

    # --- 出走馬紹介スライド（3秒×頭数） ---
    for i in range(num_horses):
        slide_timer = time.time()
        showing = True
        while showing:
            screen.fill(WHITE)
            screen.blit(bg, (0, 0))
            # 馬名・作戦
            text = mid_font.render(f"{i+1}番  {horse_names[i]}", True, BLACK)
            strat = small_font.render(f"作戦：{stats_list[i]['strategy']}", True, RED)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 120))
            screen.blit(strat, (WIDTH//2 - strat.get_width()//2, HEIGHT//2 - 70))
            # 立ち姿センター
            screen.blit(standing_horses[i], (WIDTH//2 - 90, HEIGHT//2 - 10))
            pygame.display.flip()
            if time.time() - slide_timer > 3:
                showing = False
            await asyncio.sleep(1/60)

    # --- 待機画面（Sキー押下まで）---
    showing = True
    while showing:
        screen.fill(WHITE)
        screen.blit(bg, (0, 0))

        # 右上有利戦術（待機画面でも表示）
        adv_text = small_font.render(f"有利戦術：{advantaged_type}", True, RED)
        screen.blit(adv_text, (WIDTH - adv_text.get_width() - 20, 20))

        # 馬立ち姿
        for idx in range(num_horses):
            screen.blit(standing_horses[idx], (positions[idx][0], positions[idx][1]))

        # 出走馬タイトル＆一覧
        title = font.render("今回の出走馬", True, BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        for i in range(num_horses):
            text = small_font.render(f"{i+1}番：{horse_names[i]} ({stats_list[i]['strategy']})", True, BLACK)
            screen.blit(text, (WIDTH//2 - 200, 150 + i*40))

        # --- 直近5レースの1位描画 ---
        box_x = WIDTH - 300
        box_y = HEIGHT - 230
        box_w = 280
        box_h = 190
        pygame.draw.rect(screen, PANEL, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, BLACK, (box_x, box_y, box_w, box_h), 2)

        recent_title = small_font.render("直近5レースの1位", True, BLACK)
        screen.blit(recent_title, (box_x + 12, box_y + 8))

        for i, row in enumerate(recent_results):
            first_place_horse_no = row[1]
            first_place_name = row[2]
            first_place_strategy = row[3]
            display_str = f"{first_place_horse_no}番 {first_place_name}（{first_place_strategy}）"
            text = history_font.render(display_str, True, BLACK)
            screen.blit(text, (box_x + 12, box_y + 40 + i*28))



        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                showing = False
                # ←ここで走り始めの時間をセット
                global start_time
                start_time = time.time()  # 走り出す瞬間から計測


        await asyncio.sleep(1/60)

    # カウントダウン
    for count in range(3, 0, -1):
        for _ in range(60):
            screen.fill(WHITE)
            screen.blit(bg, (0, 0))
            for idx in range(num_horses):
                screen.blit(standing_horses[idx], (positions[idx][0], positions[idx][1]))
            count_text = font.render(str(count), True, RED)
            screen.blit(count_text, (WIDTH//2 - count_text.get_width()//2, HEIGHT//2 - 50))
            pygame.display.flip()
            await asyncio.sleep(1/60)

    # カウントダウン後は走る姿へ
    horse_current_images[:] = running_horses.copy()

# 初期化＆オープニング
async def main():
    global finished, results_saved, replay_mode, last_deadheat_update, bg_x, start_time
    global deadheat_active, deadheat_ranges, deadheat_targets, results
    global goal_line_x, vertical_offset, horse_current_images, advantaged_type
    global result_display_index, result_display_start 

    reset_race()
    await opening_sequence()

    clock = pygame.time.Clock()
    global replay_mode
    replay_mode = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_race()
                    await opening_sequence()
                    replay_mode = False
                    finished = False

        elapsed = time.time() - start_time

        # 背景スクロール
        if not finished:
            bg_x -= bg_speed
            if bg_x <= -WIDTH:
                bg_x = 0

        # 背景描画（ループスクロール）
        screen.fill(WHITE)
        screen.blit(bg, (bg_x, 0))
        screen.blit(bg, (bg_x + WIDTH, 0))

        # レース進行
        if not finished:
            # デッドヒート更新
            if deadheat_active and time.time() - last_deadheat_update >= DEADHEAT_UPDATE_INTERVAL:
                deadheat_ranges = [random_deadheat_range() for _ in range(num_horses)]
                deadheat_targets = [random.uniform(*deadheat_ranges[i]) for i in range(num_horses)]
                last_deadheat_update = time.time()

            # ----- ゴールライン描画 -----
            if elapsed >= 20 and goal_line_x > GOAL_X:
                goal_line_x -= bg_speed
            if elapsed >= 20:
                pygame.draw.line(screen, RED, (goal_line_x, 0), (goal_line_x, HEIGHT), 5)

            # ----- 馬移動（ゴール後も右に進む） -----
            for i in range(num_horses):
                stat = stats_list[i]
                if deadheat_active and elapsed < sprint_times[i]:
                    # デッドヒート移動（既存）
                    start, end = deadheat_ranges[i]
                    target = deadheat_targets[i]
                    current_order = sorted(range(num_horses), key=lambda x: positions[x][0], reverse=True)
                    idx_in_order = current_order.index(i)
                    speed_factor = 1.0
                    if idx_in_order > 0:
                        front_idx = current_order[idx_in_order - 1]
                        dist_front = positions[front_idx][0] - positions[i][0]
                        if dist_front < 15:
                            speed_factor = 0.3
                    delta = random.uniform(2.5, 4.0) * speed_factor * stat["burst"]/5.0
                    if positions[i][0] < target:
                        positions[i][0] += delta
                        if positions[i][0] > target:
                            positions[i][0] = target
                    else:
                        positions[i][0] -= delta
                        if positions[i][0] < target:
                            positions[i][0] = target
                    if positions[i][0] == target:
                        deadheat_targets[i] = random.uniform(*deadheat_ranges[i])
                else:
                    deadheat_active = False

                    # 基本スピード
                    base_delta = random.uniform(5, 10) * stat["burst"] / 5.0

                    # --- 案4：戦術＋スタミナ補正 ---
                    stamina_factor = stat["stamina"] / 100  # 0.5～1.0
                    strategy = stat["strategy"]

                    if strategy in ["逃げ", "先行"]:
                        # 序盤はスタミナ依存で少し早く、スタミナ消費で減速
                        delta = base_delta * (0.8 + 0.4 * stamina_factor)
                        stat["stamina"] -= 0.2  # 消費
                    else:  # 差し・追込
                        # 序盤は控えめ、終盤はスタミナに応じて加速
                        if positions[i][0] < GOAL_X - 200:
                            delta = base_delta * (0.6 + 0.6 * stamina_factor) * 0.6  # 前半控えめ
                        else:
                            delta = base_delta * (0.6 + 0.6 * stamina_factor) * 1.8  # 終盤加速
                        stat["stamina"] -= 0.15  # 消費

                    # スタミナが少ないと減速
                    if stat["stamina"] < 10:
                        delta *= 0.5

                    positions[i][0] += delta

                    # ゴール判定（順位記録のみ）
                    if positions[i][0] >= GOAL_X and i not in results:
                        results.append(i)


            # --- フレーム履歴に保存 ---
            frame_snapshot = [pos[0] for pos in positions]
            if len(frame_history) >= HISTORY_LENGTH:
                frame_history.pop(0)  # 古いの削除してから
            frame_history.append(frame_snapshot)

            # ------------------------
            # 全馬ゴールしたら → リプレイ突入
            # ------------------------
            if not replay_mode and not finished and all(pos[0] >= GOAL_X for pos in positions):
                # 1位馬のインデックス
                first_place_idx = max(range(num_horses), key=lambda j: positions[j][0])
    
                # リプレイ用フレームにコピー
                replay_frames = frame_history.copy()
                replay_index = 0
                replay_mode = True
                photo_finish_timer = 0

                replay_mode = True
                photo_finish_timer = 0

            # 全馬ゴールしたら
            if not results_saved and all(pos[0] >= GOAL_X for pos in positions):
                idx = results[0]  # 1位の馬のインデックス
                recent_results.append([1, idx+1, horse_names[idx], stats_list[idx]["strategy"]])
                if len(recent_results) > 5:
                    recent_results.pop(0)  # 最新5件だけ保持
                results_saved = True

        # -----------------------------
        # 左上順位表（背景パネル＋黒線のみ）
        # -----------------------------
        table_x = 20
        table_y = 20
        row_height = 28         # 各行の高さ
        table_w = 320           # 横幅を少し広く
        table_h = row_height * num_horses + 36  # タイトル分含む

        # 表背景（薄い灰色）
        pygame.draw.rect(screen, PANEL, (table_x, table_y, table_w, table_h))
        pygame.draw.rect(screen, BLACK, (table_x, table_y, table_w, table_h), 2)  # 外枠

        # タイトル用フォント（少し小さく）
        title_text = title_font.render("順位表", True, BLACK)
        screen.blit(title_text, (table_x + 7, table_y ))

        # レース中は位置順、ゴール後は確定順位
        if finished or replay_mode:
            display_order = results.copy()
        else:
            display_order = sorted(range(num_horses), key=lambda x: positions[x][0], reverse=True)

        # 各行フォント
        for rank, horse_idx in enumerate(display_order, start=1):
            row_y = table_y + 30 + (rank-1)*row_height
            # 行を黒線で区切る
            pygame.draw.line(screen, BLACK, (table_x, row_y), (table_x + table_w, row_y), 1)
            display_str = f"{rank}位：{horse_idx+1}番 {horse_names[horse_idx]} ({stats_list[horse_idx]['strategy']})"
            text = rank_font.render(display_str, True, BLACK)
            screen.blit(text, (table_x + 5, row_y + 2))


        # 馬描画（上下揺れ）
        for i in range(num_horses):
            vertical_offset[i] = 5 * math.sin(elapsed*5 + i)
            y_pos = positions[i][1] + vertical_offset[i]
            screen.blit(horse_current_images[i], (positions[i][0], y_pos))


        # 右上有利戦術
        adv_text = small_font.render(f"有利戦術：{advantaged_type}", True, RED)
        screen.blit(adv_text, (WIDTH - adv_text.get_width() - 20, 20))

        # 結果表示（ランキング風 or リプレイ）
        if finished:
            if replay_mode:
                title_text = font.render("リプレイ", True, BLACK)
                screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT - 420))
                # シンプルに順位と名前だけ
                for rank, idx in enumerate(results, start=1):
                    result_text = small_font.render(f"{rank}着：{horse_names[idx]}", True, BLACK)
                    screen.blit(result_text, (WIDTH//2 - 120, HEIGHT - 330 + (rank-1)*28))
            else:
                # 背景パネル
                panel_rect = (WIDTH//2 - 260, HEIGHT - 420, 520, 340)
                pygame.draw.rect(screen, PANEL, panel_rect)
                pygame.draw.rect(screen, BLACK, panel_rect, 2)

                title_text = font.render("結果", True, BLACK)
                screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT - 410))

                now = time.time()
                if result_display_index < len(results):
                    if now - result_display_start > result_display_index * 1.0:  # 1秒ごと追加
                        result_display_index += 1

                for rank, idx in enumerate(results[:result_display_index], start=1):
                    color = BLACK  # すべて黒
                    result_text = small_font.render(
                        f"{rank}着：{idx+1}番 {horse_names[idx]}（{stats_list[idx]['strategy']}）",
                        True, color
                    )
                    screen.blit(result_text, (WIDTH//2 - 220, HEIGHT - 330 + (rank-1)*32))

        # 終了後に一度だけ保存
        if not results_saved and all(pos[0] >= GOAL_X for pos in positions):
            idx = results[0]  # 1位の馬
            recent_results.append([1, idx+1, horse_names[idx], stats_list[idx]["strategy"]])
            if len(recent_results) > 5:
                recent_results.pop(0)  # 最新5件だけ保持
            results_saved = True


        # --- リプレイモード処理 ---
        if replay_mode:
            slow_factor = 0.5  # 0.5倍速（スロー）
    
            if replay_index < len(replay_frames):
                for i in range(num_horses):
                    x = replay_frames[int(replay_index)][i]  # floatインデックスをintで変換
                    y = positions[i][1] + 5 * math.sin(elapsed*5 + i)  # 上下揺れ
                    screen.blit(running_horses[i], (x, y))
                replay_index += slow_factor  # 少しずつ進める
            else:
                # リプレイ終了 → 写真判定演出
                photo_finish_timer += 1
                if photo_finish_timer < 120:
                    text = font.render("写真判定中...", True, RED)
                    screen.blit(text, (WIDTH//2 - 100, HEIGHT//2))
                elif photo_finish_timer < 240:
                    text = font.render("確定！", True, BLACK)
                    screen.blit(text, (WIDTH//2 - 50, HEIGHT//2))
                else:
                    replay_mode = False
                    finished = True
                    result_display_start = time.time()

            # ゴールライン描画
            pygame.draw.line(screen, RED, (GOAL_X, 0), (GOAL_X, HEIGHT), 5)

        pygame.display.flip()
        await asyncio.sleep(1/60)


# --- 非同期実行 ---
if __name__ == "__main__":
    asyncio.run(main())