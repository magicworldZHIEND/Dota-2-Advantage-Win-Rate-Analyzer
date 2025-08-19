import requests
import time
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import statistics

# ==============================================================================
# 全局常量和配置
# ==============================================================================
BASE_URL = "https://api.opendota.com/api"
RANK_TIERS = {
    11: "先锋 I", 12: "先锋 II", 13: "先锋 III", 14: "先锋 IV", 15: "先锋 V", 21: "卫士 I", 22: "卫士 II",
    23: "卫士 III", 24: "卫士 IV", 25: "卫士 V", 31: "中军 I", 32: "中军 II", 33: "中军 III", 34: "中军 IV",
    35: "中军 V", 41: "统帅 I", 42: "统帅 II", 43: "统帅 III", 44: "统帅 IV", 45: "统帅 V", 51: "传奇 I",
    52: "传奇 II", 53: "传奇 III", 54: "传奇 IV", 55: "传奇 V", 61: "万古 I", 62: "万古 II", 63: "万古 III",
    64: "万古 IV", 65: "万古 V", 71: "超凡 I", 72: "超凡 II", 73: "超凡 III", 74: "超凡 IV", 75: "超凡 V", 80: "冠绝"
}
LANE_ROLES = {1: "优势路", 2: "中路", 3: "劣势路", 4: "游走"}
OUTPUT_PLOT_DIRECTORY = f"plots//dota_analysis_report_{time.strftime('%Y%m%d_%H%M')}"

# 智能重试配置
RETRY_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 5


# ==============================================================================
# 辅助函数
# ==============================================================================
def get_api_data(url):
    try:
        time.sleep(1.2)
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"  > API GET请求失败: {e}")
        return None


def post_api_request(url):
    try:
        time.sleep(1.2)
        response = requests.post(url, timeout=20)
        if response.status_code == 200:
            print(f"  > 成功提交解析请求: {url}")
    except requests.RequestException:
        pass


def set_chinese_font():
    try:
        sns.set_theme(style="whitegrid")
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        print("\n[INFO] 已尝试加载中文支持字体。")
    except Exception as e:
        print(f"[WARNING] 未能成功加载中文字体，图表中的中文可能显示为方框。错误: {e}")


def get_first_to_advantage_threshold(match_data, is_radiant, threshold):
    if not match_data.get('radiant_gold_adv'): return "N/A"
    for advantage in match_data['radiant_gold_adv']:
        if advantage >= threshold: return 1 if is_radiant else 0
        if advantage <= -threshold: return 0 if is_radiant else 1
    return 0


# ==============================================================================
# 交互式获取用户输入
# ==============================================================================
def get_user_input():
    print("--- Dota 2 胜局分析 ver.1.0.1 ---")
    print("--- @ZHIEND  ---")
    config = {}
    while True:
        mode = input(
            "请选择分析模式 (输入 1 或 2 后按回车):\n  1. 抽样调查模式 (分析与您同水平玩家的最新比赛)\n  2. 个人战绩模式 (直接分析您自己的最新比赛)\n> ")
        if mode in ['1', '2']:
            config['mode'] = mode
            break
        print("输入无效，请输入 1 或 2。")
    while True:
        try:
            account_id = int(input("请输入您的Dota 2 Account ID:\n> "))
            config['account_id'] = account_id
            break
        except ValueError:
            print("输入无效，Account ID必须是纯数字。")
    prompt_scan = "您希望从自己最近多少场比赛中【收集玩家样本】？\n> " if config[
                                                                                       'mode'] == '1' else "您希望直接分析自己最近多少场比赛？(推荐 10-50)\n> "
    while True:
        try:
            scan_count = int(input(prompt_scan))
            if scan_count > 0:
                config['scan_count'] = scan_count
                break
            else:
                print("请输入一个大于0的数字。")
        except ValueError:
            print("输入无效，必须是纯数字。")
    while True:
        try:
            threshold = int(input("请输入您想分析的经济优势阈值 (例如: 5000)\n> "))
            if threshold > 0:
                config['threshold'] = threshold
                break
            else:
                print("请输入一个大于0的数字。")
        except ValueError:
            print("输入无效，必须是纯数字。")
    return config


# ==============================================================================
# 数据获取与分析的核心逻辑
# ==============================================================================
def fetch_and_analyze_match(match_id):
    match_details = None
    for attempt in range(RETRY_ATTEMPTS):
        print(f"    > 正在获取比赛详情 (第 {attempt + 1}/{RETRY_ATTEMPTS} 次尝试)...")
        details_attempt = get_api_data(f"{BASE_URL}/matches/{match_id}")
        if details_attempt and details_attempt.get('radiant_gold_adv'):
            print("    > 成功获取到经济数据！")
            match_details = details_attempt
            break
        elif attempt < RETRY_ATTEMPTS - 1:
            print(f"    > 经济数据尚未就绪，将在 {RETRY_DELAY_SECONDS} 秒后重试...")
            time.sleep(RETRY_DELAY_SECONDS)
        else:
            print("    > 已达到最大重试次数，仍未获取到经济数据。")
    return match_details


# ==============================================================================
# 模式一 & 模式二 共享的核心分析流程
# ==============================================================================
def run_analysis_flow(config, player_ids_to_scan, scan_limit):
    print(f"这个过程根据比赛的数量和样本的数量以及来计算时长, 最近30场比赛样本大概20min分析")
    print(
        f"\n步骤2/3：已确定 {len(player_ids_to_scan)} 位玩家样本，正在获取他们的最新 {scan_limit} 场比赛比赛并提交解析...")
    analysis_jobs = []
    unique_match_ids_processed = set()
    for i, player_id in enumerate(list(player_ids_to_scan)):
        # 模式1是获取1场，模式2是获取scan_count场
        matches_to_fetch = get_api_data(f"{BASE_URL}/players/{player_id}/matches?limit={scan_limit}")
        if matches_to_fetch:
            for match in matches_to_fetch:
                match_id = match['match_id']
                analysis_jobs.append({'match_id': match_id, 'player_id': player_id})
                if match_id not in unique_match_ids_processed:
                    post_api_request(f"{BASE_URL}/request/{match_id}")
                    unique_match_ids_processed.add(match_id)
    print(f"\n--- 所有解析请求已提交，一共有{len(analysis_jobs)} 个不重复且公开的比赛数据 ---")
    print(f"\n步骤3/3：开始获取并分析 {len(analysis_jobs)} 个比赛的数据...")
    results = []
    advantage_col_name = f"First_Team_to_{config['threshold']}_Adv"
    heroes_map = {h['id']: h['localized_name'] for h in get_api_data(f"{BASE_URL}/heroes")}
    for i, job in enumerate(analysis_jobs):
        match_id, player_id = job['match_id'], job['player_id']
        print(f"  分析比赛 {i + 1}/{len(analysis_jobs)} (Match: {match_id}, Player: {player_id})")
        match_details = fetch_and_analyze_match(match_id)
        row_data = {"Player_ID": player_id, "Analyzed_Match_ID": match_id}
        if not match_details:
            row_data["Analysis_Status"] = "经济数据缺失"
        else:
            player_data = next((p for p in match_details.get('players', []) if p.get('account_id') == player_id), None)
            if player_data:
                is_radiant = player_data.get('isRadiant', True)
                radiant_win = match_details.get('radiant_win', False)
                won_match = 1 if (is_radiant and radiant_win) or (not is_radiant and not radiant_win) else 0
                row_data.update(
                    {"Analysis_Status": "成功", "Medal": RANK_TIERS.get(player_data.get('rank_tier'), "未定级"),
                     "Hero": heroes_map.get(player_data.get('hero_id'), "未知"),
                     "Role": LANE_ROLES.get(player_data.get('lane_role'), f"未知({player_data.get('lane_role')})"),
                     "Won_Match": won_match,
                     advantage_col_name: get_first_to_advantage_threshold(match_details, is_radiant,
                                                                          config['threshold'])})
            else:
                row_data["Analysis_Status"] = "未找到玩家数据"
        results.append(row_data)
    return pd.DataFrame(results), advantage_col_name

# ==============================================================================
# 最终步骤：生成报告和图表
# ==============================================================================
def generate_report_and_plots(df, advantage_col_name, config):
    print("\n--- 分析完成，正在生成最终报告和图表 ---")
    if df is None or df.empty:
        print("没有收集到有效数据，无法生成报告。")
        return
    if advantage_col_name not in df.columns:
        print(f"\n[ERROR] 关键数据列 '{advantage_col_name}' 不存在。")
        print("这通常意味着在所有分析的比赛中，都未能获取到有效的经济数据。")
        output_excel_file = f"dota_analysis_report_(partial)_{time.strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(output_excel_file, index=False, engine='openpyxl')
        print(f"\n已保存部分分析报告至: {os.path.abspath(output_excel_file)}")
        return

    valid_df = df[df[advantage_col_name].isin([0, 1])].copy()
    valid_df['Won_Match'] = pd.to_numeric(valid_df['Won_Match'])
    valid_df[advantage_col_name] = pd.to_numeric(valid_df[advantage_col_name])

    mode = config['mode']
    threshold = config['threshold']

    # --- 核心统计计算 ---
    summary_stats = {"分析模式": "抽样调查" if mode == '1' else "个人战绩", "经济领先阈值": threshold}
    first_to_adv_games = pd.DataFrame()

    if not valid_df.empty:
        first_to_adv_games = valid_df[valid_df[advantage_col_name] == 1]
        summary_stats["总有效分析样本数"] = len(valid_df)
        summary_stats[f"率先达到{threshold}G领先的样本数"] = len(first_to_adv_games)

        if not first_to_adv_games.empty:
            win_rate = first_to_adv_games['Won_Match'].mean() * 100
            summary_stats[f"率先达到{threshold}G领先后胜率"] = f"{win_rate:.2f}%"
        else:
            summary_stats[f"率先达到{threshold}G领先后胜率"] = "0% (无此类样本)"

        comeback_possible_games = valid_df[valid_df[advantage_col_name] == 0]
        if not comeback_possible_games.empty:
            comeback_wins = comeback_possible_games['Won_Match'].sum()
            total_comeback_possible = len(comeback_possible_games)
            comeback_win_rate = (comeback_wins / total_comeback_possible) * 100
            summary_stats["翻盘成功率 (未率先达到领先)"] = f"{comeback_win_rate:.2f}%"
        else:
            summary_stats["翻盘成功率 (未率先达到领先)"] = "N/A (无劣势对局样本)"
    else:
        summary_stats["说明"] = "未能找到足够的数据进行统计"

    summary_df = pd.DataFrame(list(summary_stats.items()), columns=['统计项', '结果'])
    output_excel_file = f"dota_analysis_report_{'sample' if mode == '1' else 'personal'}_{time.strftime('%Y%m%d_%H%M')}.xlsx"
    with pd.ExcelWriter(output_excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='详细数据 (Raw Data)', index=False)
        summary_df.to_excel(writer, sheet_name='统计概要 (Summary)', index=False)
    print(f"\n[SUCCESS] 最终报告已保存至: {os.path.abspath(output_excel_file)}")

    # --- 绘图 ---
    if not os.path.exists(OUTPUT_PLOT_DIRECTORY): os.makedirs(OUTPUT_PLOT_DIRECTORY)
    set_chinese_font()

    if valid_df.empty:
        print("[INFO] 无有效数据，跳过绘图步骤。")
        return

    # --- 图1: 总局数构成图 ---
    print("正在生成图表1：总对局构成分析...")
    total_composition = valid_df[advantage_col_name].value_counts()
    if 1 not in total_composition: total_composition[1] = 0
    if 0 not in total_composition: total_composition[0] = 0
    labels_total = {1: f'经济优势局数\n({total_composition[1]} 场)', 0: f'经济劣势局数\n({total_composition[0]} 场)'}
    plt.figure(figsize=(8, 8));
    plt.pie(total_composition, labels=[labels_total[i] for i in total_composition.index], autopct='%1.1f%%',
            startangle=90, colors=['#87CEFA', '#FFB6C1'], wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'fontsize': 14})
    plt.title(f'总局数构成分析 (总样本: {len(valid_df)} 场)', fontsize=16)
    formula_text = f"计算公式: 总局数 ({len(valid_df)}) = 经济优势局数 ({total_composition[1]}) + 经济劣势局数 ({total_composition[0]})"
    plt.figtext(0.5, 0.02, formula_text, ha="center", fontsize=11, bbox={"facecolor": "gray", "alpha": 0.2, "pad": 5})
    chart1_path = os.path.join(OUTPUT_PLOT_DIRECTORY, f"01_总对局构成_{time.strftime('%Y%m%d_%H%M')}.png")
    plt.savefig(chart1_path);
    plt.close()
    print(f"[SUCCESS] 图表1 (总对局构成分析) 已保存至: {chart1_path}")

    # --- 图2: 胜利失败占比图 ---
    print("正在生成图表2：总对局胜负占比...")
    win_loss_total = valid_df['Won_Match'].value_counts()
    if 1 not in win_loss_total: win_loss_total[1] = 0
    if 0 not in win_loss_total: win_loss_total[0] = 0
    labels_win_loss = {1: f'胜利\n({win_loss_total[1]} 场)', 0: f'失败\n({win_loss_total[0]} 场)'}
    plt.figure(figsize=(8, 8));
    plt.pie(win_loss_total, labels=[labels_win_loss[i] for i in win_loss_total.index], autopct='%1.1f%%', startangle=90,
            colors=['#90EE90', '#F08080'], wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'fontsize': 14})
    plt.title(f'总对局胜负占比 (总样本: {len(valid_df)} 场)', fontsize=16)
    win_rate_percent = (win_loss_total[1] / len(valid_df)) * 100 if len(valid_df) > 0 else 0
    formula_text = f"计算公式: 胜率 ({win_rate_percent:.1f}%) = 胜利的总局数 ({win_loss_total[1]}) / 总局数 ({len(valid_df)})"
    plt.figtext(0.5, 0.02, formula_text, ha="center", fontsize=11, bbox={"facecolor": "gray", "alpha": 0.2, "pad": 5})
    chart2_path = os.path.join(OUTPUT_PLOT_DIRECTORY, f"02_总对局胜负占比_{time.strftime('%Y%m%d_%H%M')}.png")
    plt.savefig(chart2_path);
    plt.close()
    print(f"[SUCCESS] 图表2 (总对局胜负占比) 已保存至: {chart2_path}")

    # --- 图3: 经济优势局结果分布图 ---
    print("正在生成图表3：经济优势局结果分布...")
    if not first_to_adv_games.empty:
        lead_win_loss_counts = first_to_adv_games['Won_Match'].value_counts()
        if 1 not in lead_win_loss_counts: lead_win_loss_counts[1] = 0
        if 0 not in lead_win_loss_counts: lead_win_loss_counts[0] = 0
        labels_lead = {1: f'经济优势获胜\n({lead_win_loss_counts[1]} 场)',
                       0: f'经济优势被翻盘\n({lead_win_loss_counts[0]} 场)'}
        plt.figure(figsize=(8, 8));
        plt.pie(lead_win_loss_counts, labels=[labels_lead[i] for i in lead_win_loss_counts.index], autopct='%1.1f%%',
                startangle=90, colors=['#90EE90', '#FFB6C1'], wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                textprops={'fontsize': 14})
        plt.title(f'率先达到 {threshold}G 经济领先后比赛结果分布', fontsize=16)
        lead_win_rate_percent = (lead_win_loss_counts[1] / len(first_to_adv_games)) * 100 if len(
            first_to_adv_games) > 0 else 0
        formula_text = f"计算公式: 领先致胜率 ({lead_win_rate_percent:.1f}%) = 经济优势获胜 ({lead_win_loss_counts[1]}) / 经济优势局数 ({len(first_to_adv_games)})"
        plt.figtext(0.5, 0.02, formula_text, ha="center", fontsize=11,
                    bbox={"facecolor": "gray", "alpha": 0.2, "pad": 5})
        chart3_path = os.path.join(OUTPUT_PLOT_DIRECTORY, f"03_经济优势胜负_{time.strftime('%Y%m%d_%H%M')}.png")
        plt.savefig(chart3_path);
        plt.close()
        print(f"[SUCCESS] 图表3 (经济优势局结果) 已保存至: {chart3_path}")

    # --- 图4: 经济劣势局结果分布图 ---
    print("正在生成图表4：经济劣势局结果分布...")
    disadvantage_games_df = valid_df[valid_df[advantage_col_name] == 0]
    if not disadvantage_games_df.empty:
        comeback_distribution = disadvantage_games_df['Won_Match'].value_counts()
        if 1 not in comeback_distribution: comeback_distribution[1] = 0
        if 0 not in comeback_distribution: comeback_distribution[0] = 0
        labels_comeback = {1: f'经济劣势获胜 (翻盘)\n({comeback_distribution[1]} 场)',
                           0: f'经济劣势失败\n({comeback_distribution[0]} 场)'}
        plt.figure(figsize=(8, 8));
        plt.pie(comeback_distribution, labels=[labels_comeback[i] for i in comeback_distribution.index],
                autopct='%1.1f%%', startangle=90, colors=['#FFD700', '#A9A9A9'],
                wedgeprops={'edgecolor': 'white', 'linewidth': 2}, textprops={'fontsize': 14})
        plt.title(f'经济劣势局结果分布 (总样本: {len(disadvantage_games_df)} 场)', fontsize=16)
        comeback_rate_percent = (comeback_distribution[1] / len(disadvantage_games_df)) * 100 if len(
            disadvantage_games_df) > 0 else 0
        formula_text = f"计算公式: 翻盘概率 ({comeback_rate_percent:.1f}%) = 经济劣势获胜 ({comeback_distribution[1]}) / 经济劣势局数 ({len(disadvantage_games_df)})"
        plt.figtext(0.5, 0.02, formula_text, ha="center", fontsize=11,
                    bbox={"facecolor": "gray", "alpha": 0.2, "pad": 5})
        chart4_path = os.path.join(OUTPUT_PLOT_DIRECTORY,
                                   f"04_经济劣势胜负_{time.strftime('%Y%m%d_%H%M')}.png")
        plt.savefig(chart4_path);
        plt.close()
        print(f"[SUCCESS] 图表4 (经济劣势局结果) 已保存至: {chart4_path}")

    # --- 图5: 胜利组成图 ---
    print("正在生成图表5：胜利组成分析...")
    wins_df = valid_df[valid_df['Won_Match'] == 1]
    if not wins_df.empty:
        win_composition = wins_df[advantage_col_name].value_counts()
        if 1 not in win_composition: win_composition[1] = 0
        if 0 not in win_composition: win_composition[0] = 0
        labels = {1: f'领先致胜', 0: f'翻盘获胜'}
        plt.figure(figsize=(8, 8));
        plt.pie(win_composition, labels=[labels[i] for i in win_composition.index], autopct='%1.1f%%', startangle=90,
                colors=['#87CEFA', '#FFD700'], textprops={'fontsize': 14})
        plt.title(f'所有胜利对局的组成分析 (总胜场: {len(wins_df)})', fontsize=16)
        lead_wins = win_composition[1]
        comeback_wins = win_composition[0]
        formula_text = f"计算公式: 总胜场 ({len(wins_df)}) = 领先致胜 ({lead_wins}) + 翻盘获胜 ({comeback_wins})"
        plt.figtext(0.5, 0.02, formula_text, ha="center", fontsize=11,
                    bbox={"facecolor": "gray", "alpha": 0.2, "pad": 5})
        chart5_path = os.path.join(OUTPUT_PLOT_DIRECTORY, f"05_胜利组成_{time.strftime('%Y%m%d_%H%M')}.png")
        plt.savefig(chart5_path);
        plt.close()
        print(f"[SUCCESS] 图表5 (胜利组成分析) 已保存至: {chart5_path}")

    # --- 图6: 按段位分析柱状图 ---
    if mode == '1' and 'Medal' in valid_df.columns and valid_df['Medal'].notna().any():
        print("正在生成图表6：按段位分析的胜率柱状图...")
        valid_df['Rank_Group'] = valid_df['Medal'].apply(lambda x: str(x).split(' ')[0])
        first_adv_df_for_rank = valid_df[valid_df[advantage_col_name] == 1]
        rank_analysis = first_adv_df_for_rank.groupby('Rank_Group')['Won_Match'].agg(['mean', 'count'])
        if not rank_analysis.empty:
            rank_order = ["冠绝", "超凡", "万古", "传奇", "统帅", "中军", "卫士", "先锋", "未定级"]
            ordered_index = [rank for rank in rank_order if rank in rank_analysis.index]
            rank_analysis = rank_analysis.reindex(ordered_index)
            plt.figure(figsize=(12, 7))
            ax = sns.barplot(x=rank_analysis.index, y=rank_analysis['mean'] * 100, hue=rank_analysis.index,
                             palette="viridis", legend=False)
            ax.set_title(f'各段位下 率先达到 {threshold}G 经济领先后胜率', fontsize=16)
            ax.set_xlabel('玩家段位 (Rank Group)', fontsize=12);
            ax.set_ylabel('胜率 (%)', fontsize=12);
            ax.set_ylim(0, 105)
            plt.xticks(rotation=0);
            plt.tight_layout()
            for i, p in enumerate(ax.patches):
                height = p.get_height()
                count = rank_analysis['count'].iloc[i]
                label_text = f"{height:.1f}% | {count}"
                ax.annotate(label_text, (p.get_x() + p.get_width() / 2., height), ha='center', va='center',
                            xytext=(0, 5), textcoords='offset points', fontsize=11)
            chart6_path = os.path.join(OUTPUT_PLOT_DIRECTORY, f"06_段位经济优势胜率_{time.strftime('%Y%m%d_%H%M')}.png")
            plt.savefig(chart6_path);
            plt.close()
            print(f"[SUCCESS] 图表6 (段位胜率分析) 已保存至: {chart6_path}")


# ==============================================================================
# 主程序入口
# ==============================================================================
if __name__ == "__main__":
    config = get_user_input()
    results_df, advantage_col_name = (None, None)

    if config['mode'] == '1':
        print("\n--- 已选择：抽样调查模式 ---")
        print(f"步骤1/3：正在扫描您的最近 {config['scan_count']} 场比赛以收集玩家...")
        my_matches = get_api_data(f"{BASE_URL}/players/{config['account_id']}/matches?limit={config['scan_count']}")
        if my_matches:
            all_player_ids = set()
            for i, match_summary in enumerate(my_matches):
                print(f"  扫描您的比赛 {i + 1}/{len(my_matches)}...")
                match_details = get_api_data(f"{BASE_URL}/matches/{match_summary['match_id']}")
                if match_details and 'players' in match_details:
                    for player in match_details['players']:
                        if player.get('account_id') and player['account_id'] != config['account_id']:
                            all_player_ids.add(player['account_id'])

            # 模式1获取每个样本的最新1场比赛
            results_df, advantage_col_name = run_analysis_flow(config, all_player_ids, scan_limit=1)

    elif config['mode'] == '2':
        print("\n--- 已选择：个人战绩模式 ---")
        # 模式2的样本只有自己，获取scan_count场比赛
        player_ids_to_scan = {config['account_id']}
        results_df, advantage_col_name = run_analysis_flow(config, player_ids_to_scan, scan_limit=config['scan_count'])
        # 个人模式下，重命名列以保持一致性
        if results_df is not None:
            results_df = results_df.rename(columns={"Player_ID": "My_Account_ID", "Analyzed_Match_ID": "Match_ID"})

    generate_report_and_plots(results_df, advantage_col_name, config)
    print("\n--- 执行完毕 ---")