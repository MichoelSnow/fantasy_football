import sys
import os
sys.path.append('/home/msnow/git/fantasy_football/src/src_data/')

from game_data import *
from season_data import *
from week_data import *
from team_data import *

# gurl = 'https://www.pro-football-reference.com//boxscores/201709070nwe.htm'
bs_pth = '/home/msnow/git/fantasy_football/data/external/game_data/2017/'
# gurl = '/home/msnow/git/fantasy_football/data/external/game_data/201709070nwe.html'
# gurls = []
# for idx,val in enumerate(os.listdir(bs_pth)):
#     gurls.append(bs_pth+val)
# for i in gurls:
#     gd = GameData(i, None)
#     scrbox_dict = gd.scorebox
#     scoring_list = gd.scoring
#     ginfo_dict = gd.game_info
#     off_list = gd.officials
#     summ_dict = gd.game_summ
#     prr_list = gd.stats_table('all_player_offense')
#     def_list = gd.stats_table('all_player_defense')
#     kp_ret_list = gd.stats_table('all_returns')
#     kp_list = gd.stats_table('all_kicking')
#     home_starters_list = gd.starters('home')
#     away_starters_list = gd.starters('away')
#     home_snaps_list = gd.stats_table('all_home_snap_counts')
#     away_snaps_list = gd.stats_table('all_vis_snap_counts')
#     pass_tgts_list = gd.stats_table('all_targets_directions')
#     rush_dir_list = gd.stats_table('all_rush_directions')
#     pass_tckl_list = gd.stats_table('all_pass_tackles')
#     rush_tckl_list = gd.stats_table('all_rush_tackles')
#     home_drives_list = gd.drives('home')
#     away_drives_list = gd.drives('away')
#     # pbp_list = gd.play_by_play()

td = TeamData(year=2017, loc=bs_pth)
td.draft

# self.year + ' ' + [i].string