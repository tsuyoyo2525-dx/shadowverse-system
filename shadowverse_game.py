"""
シャドーバース風カードゲーム 戦闘システム
改訂版
"""

import random
import copy

# ─────────────────────────────────────────────
#  効果定数
# ─────────────────────────────────────────────
EFCT_NONE         = 0  # 効果なし
EFCT_RUSH         = 1  # 疾走（相手フォロワーにのみ攻撃可・召喚酔いなし）
EFCT_CHARGE       = 2  # 突進（相手プレイヤーにも攻撃可・召喚酔いなし）
EFCT_WARD         = 3  # ガード（守護）
EFCT_WARD_CHARGE  = 4  # 守護＋突進

SPELL_DAMAGE = 1  # ダメージスペル
SPELL_DRAW   = 2  # ドロースペル

MAX_HAND      = 10
MAX_STAGE     = 5
INITIAL_HAND  = 4
PLAYER_HP     = 20
MAX_PP        = 10

# ─────────────────────────────────────────────
#  カードデータ（マスターリスト）
# ─────────────────────────────────────────────
CARD_MASTER = [
    {"name": "ダメージ魔法", "cost": 1, "hp": 0, "atk": 3, "efct": EFCT_NONE, "spell": SPELL_DAMAGE, "order": 0},
    {"name": "ドロー魔法",   "cost": 1, "hp": 0, "atk": 0, "efct": EFCT_NONE, "spell": SPELL_DRAW,   "order": 0},
    {"name": "トラ",         "cost": 1, "hp": 1, "atk": 1, "efct": EFCT_CHARGE, "spell": 0, "order": 0},
    {"name": "キジ",         "cost": 2, "hp": 3, "atk": 1, "efct": EFCT_RUSH,   "spell": 0, "order": 0},
    {"name": "サル",         "cost": 2, "hp": 2, "atk": 3, "efct": EFCT_RUSH,   "spell": 0, "order": 0},
    {"name": "ブタ",         "cost": 3, "hp": 1, "atk": 5, "efct": EFCT_CHARGE, "spell": 0, "order": 0},
    {"name": "リス",         "cost": 3, "hp": 5, "atk": 3, "efct": EFCT_WARD,   "spell": 0, "order": 1},
    {"name": "カバ",         "cost": 4, "hp": 7, "atk": 4, "efct": EFCT_WARD_CHARGE, "spell": 0, "order": 1},
    {"name": "ウマ",         "cost": 5, "hp": 5, "atk": 5, "efct": EFCT_NONE,   "spell": 0, "order": 0},
    {"name": "クマ",         "cost": 6, "hp": 9, "atk": 9, "efct": EFCT_NONE,   "spell": 0, "order": 0},
]


# ─────────────────────────────────────────────
#  ゲーム状態クラス
# ─────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.hp   = {"A": PLAYER_HP, "B": PLAYER_HP}
        self.hand = {"A": [], "B": []}
        self.stage= {"A": [], "B": []}
        self.deck = {
            "A": [copy.deepcopy(c) for c in CARD_MASTER],
            "B": [copy.deepcopy(c) for c in CARD_MASTER],
        }
        self.evo  = {"A": 2, "B": 2}
        self.turn  = 0     # 1から始まる。奇数=先攻、偶数=後攻
        self.pp    = 0
        self.first = ""    # 先攻プレイヤー ("A" or "B")

    def current_player(self):
        """現在のターンのプレイヤーを返す"""
        if self.first == "A":
            return "A" if self.turn % 2 == 1 else "B"
        else:
            return "B" if self.turn % 2 == 1 else "A"

    def opponent(self):
        cp = self.current_player()
        return "B" if cp == "A" else "A"


# ─────────────────────────────────────────────
#  入力ユーティリティ
# ─────────────────────────────────────────────
def safe_int(prompt, lo, hi):
    """lo〜hi の整数を安全に受け取る"""
    while True:
        try:
            val = int(input(prompt))
            if lo <= val <= hi:
                return val
            print(f"  ※ {lo}〜{hi} の数字を入力してください")
        except ValueError:
            print("  ※ 数字を入力してください")


# ─────────────────────────────────────────────
#  表示ユーティリティ
# ─────────────────────────────────────────────
def fmt_card(card):
    efct_label = {
        EFCT_NONE:        "",
        EFCT_RUSH:        "[疾走]",
        EFCT_CHARGE:      "[突進]",
        EFCT_WARD:        "[守護]",
        EFCT_WARD_CHARGE: "[守護+突進]",
    }.get(card["efct"], "")
    evo_mark = "★" if card.get("evo") else ""
    return f"{card['name']}{evo_mark}{efct_label}(ATK:{card['atk']} HP:{card['hp']} cost:{card['cost']})"


def show_stage(gs):
    cp  = gs.current_player()
    opp = gs.opponent()
    print(f"\n{'='*50}")
    print(f"  ── {cp}さんのターン（ターン {gs.turn} / PP {gs.pp}）──")
    print(f"  あなたのHP: {gs.hp[cp]}  相手のHP: {gs.hp[opp]}")
    print(f"  残り進化回数: {gs.evo[cp]}")
    print()
    print(f"  【相手の盤面 ({opp})】")
    if gs.stage[opp]:
        for i, c in enumerate(gs.stage[opp], 1):
            print(f"    {i}: {fmt_card(c)}")
    else:
        print("    （なし）")
    print()
    print(f"  【自分の盤面 ({cp})】")
    if gs.stage[cp]:
        for i, c in enumerate(gs.stage[cp], 1):
            atk_ok = "○" if c.get("turn_count", 0) > 0 or c["efct"] in (EFCT_RUSH, EFCT_CHARGE, EFCT_WARD_CHARGE) else "×"
            print(f"    {i}: {fmt_card(c)}  攻撃:{atk_ok}")
    else:
        print("    （なし）")
    print()
    print(f"  【手札 ({cp})】")
    for i, c in enumerate(gs.hand[cp], 1):
        print(f"    {i}: {fmt_card(c)}")
    print(f"{'='*50}")


# ─────────────────────────────────────────────
#  ゲーム開始処理
# ─────────────────────────────────────────────
def turn_zero(gs):
    """先攻決め・デッキシャッフル"""
    gs.first = random.choice(["A", "B"])
    print(f"\n【コイントス】{gs.first}さんが先攻です！")
    random.shuffle(gs.deck["A"])
    random.shuffle(gs.deck["B"])


def draw_initial_hand(gs, player):
    """初期手札を配り、マリガン処理を行う"""
    gs.hand[player] = [gs.deck[player].pop(0) for _ in range(INITIAL_HAND)]

    print(f"\n【{player}さんの初期手札】")
    for i, c in enumerate(gs.hand[player], 1):
        print(f"  {i}: {fmt_card(c)}")

    count = safe_int(f"{player}さん、引き直す枚数を選んでください（0〜{INITIAL_HAND}）: ", 0, INITIAL_HAND)
    if count == 0:
        return

    indices = []
    for _ in range(count):
        idx = safe_int(
            f"  引き直すカードの番号（1〜{len(gs.hand[player])}）: ",
            1, len(gs.hand[player])
        ) - 1
        if idx not in indices:
            indices.append(idx)

    # 対象カードをデッキに戻してシャッフル、新しいカードを引く
    for i in sorted(indices, reverse=True):
        gs.deck[player].append(gs.hand[player].pop(i))
    random.shuffle(gs.deck[player])
    for _ in range(len(indices)):
        if gs.deck[player]:
            gs.hand[player].append(gs.deck[player].pop(0))

    print(f"  【{player}さんの新しい手札】")
    for i, c in enumerate(gs.hand[player], 1):
        print(f"    {i}: {fmt_card(c)}")


# ─────────────────────────────────────────────
#  ターン開始処理
# ─────────────────────────────────────────────
def start_turn(gs):
    gs.turn += 1
    cp  = gs.current_player()
    opp = gs.opponent()

    # PP計算（先攻1ターン目は1PP、以降両プレイヤー共に毎ターン+1、上限10）
    gs.pp = min((gs.turn + 1) // 2, MAX_PP)

    # フォロワーの召喚酔いカウント更新
    for card in gs.stage[cp]:
        card["turn_count"] = card.get("turn_count", 0) + 1
    for card in gs.stage[opp]:
        card["turn_count"] = card.get("turn_count", 0) + 1

    # ドロー（手札上限超過で捨て）
    if gs.deck[cp]:
        drawn = gs.deck[cp].pop(0)
        if len(gs.hand[cp]) < MAX_HAND:
            gs.hand[cp].append(drawn)
            print(f"\n  {cp}さんが「{drawn['name']}」をドローしました")
        else:
            print(f"\n  {cp}さんの手札が上限のため「{drawn['name']}」は捨てられました")
    else:
        print(f"\n  {cp}さんのデッキが空です！")


# ─────────────────────────────────────────────
#  カードをプレイする
# ─────────────────────────────────────────────
def apply_spell(gs, card, caster):
    """スペルカードの効果を発動する"""
    opp = "B" if caster == "A" else "A"
    if card["spell"] == SPELL_DAMAGE:
        # 相手の全フォロワーに3ダメージ
        victims = [c for c in gs.stage[opp]]
        for c in victims:
            c["hp"] -= card["atk"]
        gs.stage[opp] = [c for c in gs.stage[opp] if c["hp"] > 0]
        print(f"  ✦ ダメージスペル発動！相手フォロワー全体に {card['atk']} ダメージ")
    elif card["spell"] == SPELL_DRAW:
        drawn = 0
        for _ in range(2):
            if gs.deck[caster] and len(gs.hand[caster]) < MAX_HAND:
                gs.hand[caster].append(gs.deck[caster].pop(0))
                drawn += 1
        print(f"  ✦ ドロースペル発動！{drawn} 枚ドローしました")


def play_card(gs):
    """手札からカードをプレイする"""
    cp = gs.current_player()
    while True:
        show_stage(gs)
        print(f"  PP残り: {gs.pp}")
        choice = safe_int("  プレイするカード番号（0で終了）: ", 0, len(gs.hand[cp]))
        if choice == 0:
            break

        card = gs.hand[cp][choice - 1]

        if gs.pp < card["cost"]:
            print("  ※ PPが足りません")
            continue

        gs.pp -= card["cost"]

        if card["spell"] > 0:
            # スペルカードは盤面に残らない
            apply_spell(gs, card, cp)
            gs.hand[cp].pop(choice - 1)
        else:
            # フォロワーカードを盤面に出す
            if len(gs.stage[cp]) >= MAX_STAGE:
                print(f"  ※ 盤面が満員（上限 {MAX_STAGE} 体）のため出せません")
                gs.pp += card["cost"]  # PPを戻す
                continue
            new_card = copy.deepcopy(card)
            new_card["evo"] = 0
            new_card["turn_count"] = 0  # 召喚酔い（0=出したターン）
            gs.stage[cp].append(new_card)
            gs.hand[cp].pop(choice - 1)
            print(f"  ✦ 「{new_card['name']}」を召喚！")

            # 突進・守護+突進は召喚ターンから攻撃可能
            if new_card["efct"] in (EFCT_CHARGE, EFCT_WARD_CHARGE):
                new_card["turn_count"] = 1
                print("    （突進効果：このターンから攻撃可能）")
            elif new_card["efct"] == EFCT_RUSH:
                new_card["turn_count"] = 1
                print("    （疾走効果：このターンからフォロワーに攻撃可能）")


# ─────────────────────────────────────────────
#  進化
# ─────────────────────────────────────────────
def evolution(gs):
    cp = gs.current_player()
    if not gs.stage[cp]:
        return
    if gs.evo[cp] <= 0:
        print("  ※ 進化回数が残っていません")
        return

    ans = input("  進化しますか？ (Y/N): ").strip().upper()
    if ans != "Y":
        return

    print("  【自分の盤面】")
    for i, c in enumerate(gs.stage[cp], 1):
        evo_mark = "（進化済み）" if c.get("evo") else ""
        print(f"    {i}: {fmt_card(c)} {evo_mark}")

    idx = safe_int(f"  進化するフォロワーを選んでください（1〜{len(gs.stage[cp])}）: ", 1, len(gs.stage[cp])) - 1
    target = gs.stage[cp][idx]

    if target.get("evo"):
        print("  ※ そのカードはすでに進化済みです")
        return

    target["evo"] = 1
    target["hp"]  += 2
    target["atk"] += 2
    target["turn_count"] = max(target.get("turn_count", 0), 1)  # 進化後は攻撃可能
    gs.evo[cp] -= 1
    print(f"  ★ 「{target['name']}」が進化！(ATK+2 HP+2) 残り進化回数: {gs.evo[cp]}")


# ─────────────────────────────────────────────
#  戦闘
# ─────────────────────────────────────────────
def has_ward(stage):
    return any(c["efct"] in (EFCT_WARD, EFCT_WARD_CHARGE) for c in stage)


def get_valid_attackers(gs, cp):
    """攻撃可能なフォロワーのインデックスリストを返す"""
    return [i for i, c in enumerate(gs.stage[cp])
            if c.get("turn_count", 0) > 0]


def get_valid_targets(gs, cp, attacker):
    """
    攻撃対象の (label, kind, index) リストを返す
    kind: "player" or "follower"
    """
    opp = "B" if cp == "A" else "A"
    targets = []

    # 守護持ちがいる場合は守護のみ対象
    if has_ward(gs.stage[opp]):
        for i, c in enumerate(gs.stage[opp]):
            if c["efct"] in (EFCT_WARD, EFCT_WARD_CHARGE):
                targets.append((f"フォロワー{i+1}:{fmt_card(c)}", "follower", i))
        return targets

    # 疾走はフォロワーにのみ攻撃可
    if attacker["efct"] == EFCT_RUSH:
        for i, c in enumerate(gs.stage[opp]):
            targets.append((f"フォロワー{i+1}:{fmt_card(c)}", "follower", i))
        return targets

    # 通常・突進：プレイヤー or フォロワー
    targets.append((f"プレイヤー({opp}) HP:{gs.hp[opp]}", "player", -1))
    for i, c in enumerate(gs.stage[opp]):
        targets.append((f"フォロワー{i+1}:{fmt_card(c)}", "follower", i))
    return targets


def do_attack(gs, cp, attacker_idx, target_kind, target_idx):
    """攻撃処理（反撃ダメージ込み）"""
    opp = "B" if cp == "A" else "A"
    atk = gs.stage[cp][attacker_idx]

    if target_kind == "player":
        gs.hp[opp] -= atk["atk"]
        print(f"  ⚔ 「{atk['name']}」が{opp}プレイヤーに {atk['atk']} ダメージ！（残りHP: {gs.hp[opp]}）")
    else:
        dfn = gs.stage[opp][target_idx]
        print(f"  ⚔ 「{atk['name']}」vs「{dfn['name']}」")

        # ダメージ交換
        atk["hp"] -= dfn["atk"]
        dfn["hp"] -= atk["atk"]

        # 戦闘後の破壊チェック
        atk_destroyed = atk["hp"] <= 0
        dfn_destroyed = dfn["hp"] <= 0

        if dfn_destroyed:
            print(f"    「{dfn['name']}」は破壊された！")
        else:
            print(f"    「{dfn['name']}」残りHP: {dfn['hp']}")

        if atk_destroyed:
            print(f"    「{atk['name']}」も破壊された！")
        else:
            print(f"    「{atk['name']}」残りHP: {atk['hp']}")

        # 破壊されたカードを除去
        if dfn_destroyed:
            gs.stage[opp].pop(target_idx)
        if atk_destroyed:
            gs.stage[cp].pop(attacker_idx)
            return  # 攻撃者が破壊されたので攻撃フラグ更新不要

    # 攻撃済みフラグ（turn_count をリセットしてこのターンは再攻撃不可にする）
    if attacker_idx < len(gs.stage[cp]):
        gs.stage[cp][attacker_idx]["turn_count"] = 0


def battle(gs):
    """戦闘フェイズ"""
    cp = gs.current_player()
    if not gs.stage[cp]:
        print("  盤面にフォロワーがいません")
        return

    while True:
        attackers = get_valid_attackers(gs, cp)
        if not attackers:
            print("  攻撃可能なフォロワーがいません")
            break

        show_stage(gs)
        print("  【攻撃可能なフォロワー】")
        for i in attackers:
            print(f"    {i+1}: {fmt_card(gs.stage[cp][i])}")

        at_choice = safe_int("  攻撃するフォロワー番号（0で終了）: ", 0, len(gs.stage[cp]))
        if at_choice == 0:
            break

        at_idx = at_choice - 1
        if at_idx not in attackers:
            print("  ※ そのフォロワーは攻撃できません（召喚酔い or 攻撃済み）")
            continue

        attacker = gs.stage[cp][at_idx]
        targets = get_valid_targets(gs, cp, attacker)
        if not targets:
            print("  攻撃対象がありません")
            continue

        print("  【攻撃対象】")
        for i, (label, _, _) in enumerate(targets, 1):
            print(f"    {i}: {label}")

        tgt_choice = safe_int("  攻撃対象の番号: ", 1, len(targets)) - 1
        _, kind, idx = targets[tgt_choice]
        do_attack(gs, cp, at_idx, kind, idx)


# ─────────────────────────────────────────────
#  勝敗判定
# ─────────────────────────────────────────────
def check_result(gs):
    """
    ゲームが続行可能か判定。
    False を返したら終了。
    """
    results = []
    if gs.hp["A"] <= 0:
        results.append("Bさんの勝ちです！（AのHPが0）")
    if gs.hp["B"] <= 0:
        results.append("Aさんの勝ちです！（BのHPが0）")
    if not gs.deck["A"] and not gs.hand["A"] and not gs.stage["A"]:
        results.append("Bさんの勝ちです！（Aのカードが尽きた）")
    if not gs.deck["B"] and not gs.hand["B"] and not gs.stage["B"]:
        results.append("Aさんの勝ちです！（Bのカードが尽きた）")

    if results:
        print("\n" + "="*50)
        for r in results:
            print(f"  🏆 {r}")
        print("="*50)
        return False
    return True


# ─────────────────────────────────────────────
#  メインループ
# ─────────────────────────────────────────────
def main():
    print("\n" + "="*50)
    print("  シャドーバース風カードゲーム")
    print("="*50)

    gs = GameState()

    # ゲーム開始処理
    turn_zero(gs)
    draw_initial_hand(gs, "A")
    draw_initial_hand(gs, "B")

    # メインゲームループ
    while check_result(gs):
        start_turn(gs)
        cp = gs.current_player()
        print(f"\n  ▶ {cp}さんのターン開始！（PP: {gs.pp}）")

        # カードをプレイ
        play_card(gs)

        if not check_result(gs):
            break

        # 進化フェイズ
        evolution(gs)

        # 戦闘フェイズ
        battle(gs)

        if not check_result(gs):
            break

        # ターン終了確認
        input("\n  Enterキーでターンを終了します...")

    print("\nゲーム終了。ありがとうございました！\n")


if __name__ == "__main__":
    main()
