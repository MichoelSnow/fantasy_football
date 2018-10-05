from urllib import request
from bs4 import BeautifulSoup, Comment, Tag
from datetime import datetime as dt
import numpy as np
import re


class GameData:
    # Extracts all data for a given game

    table_dict = {
        'scorebox':'basic game info and results (dict)',
        'scoring':'every point scoring play in the game (list of dicts)',
        'game_info':'game errata, i.e., coin toss, roof, surface, weather (dict)',
        'officials':'refs in the game (list of dicts)',
        'game_summ':'some basic game stats (dict)',
        'stats_table':{
            'all_player_offense':'passing, rushing and receving stats (list of dicts)',
            'all_player_defense':'defensive stats (list of dicts)',
            'all_returns': 'kick and punt return stats (list of dicts)',
            'all_kicking': 'kicking and punting stats (list of dicts)',
            'all_home_snap_counts': 'home team snap stats (list of dicts)',
            'all_vis_snap_counts': 'away team snap stats (list of dicts)',
            'all_targets_directions': 'pass target stats (list of dicts)',
            'all_rush_directions': 'rushing stats (list of dicts)',
            'all_pass_tackles': 'pass tackling stats (list of dicts)',
            'all_rush_tackles': 'rush tackling stats (list of dicts)',
        },
        'starters':{
            'home': 'home team starters (list of dicts)',
            'away': 'away team starters (list of dicts)',
        },
        'drives':{
            'home': 'home team drives (list of dicts)',
            'away': 'away team drives (list of dicts)',
        }
    }

    def __init__(self, gm_url, extract):
        self.gm_url = gm_url
        self.extract = extract
        self.soupify()
        self.scrbox_dict = self.scorebox

    def soupify(self):
        if self.gm_url[:5] == 'https':
            pg = request.urlopen(self.gm_url)
            self.soup = BeautifulSoup(pg, 'html.parser')
        else:
            self.soup = BeautifulSoup(open(self.gm_url), 'html.parser')


    @property
    def scorebox(self):
        # Extract the information from the scorebox div, i.e., basic game info and results
        scrbox_dict = {}
        scrbox_div = self.soup.find('div', {'class': 'scorebox'})
        scrbox = scrbox_div.find_all('div', recursive=False)
        team_str = ['home', 'away']
        for idx, team in enumerate(team_str):
            team_name = scrbox[idx].find('a', {'itemprop': 'name'})
            coach_name = scrbox[idx].find('div', {'class': 'datapoint'}).find('a')
            score = scrbox[idx].find('div', {'class': 'score'})
            record = score.findNextSibling().string.split('-')
            scrbox_dict[team + '_team_pg'] = team_name['href']
            scrbox_dict[team + '_team_id'] = team_name['href'].split('/')[-2]
            scrbox_dict[team + '_team_name'] = team_name.string
            scrbox_dict[team + '_team_score'] = int(score.string)
            scrbox_dict[team + '_team_coach_pg'] = coach_name['href']
            scrbox_dict[team + '_team_coach_id'] = coach_name['href'].split('/')[-1].split('.')[0]
            scrbox_dict[team + '_team_coach_name'] = coach_name.string
            scrbox_dict[team + '_team_wins'] = int(record[0])
            scrbox_dict[team + '_team_losses'] = int(record[1])
            if len(record) == 3:
                scrbox_dict[team + '_team_ties'] = int(record[2])
            else:
                scrbox_dict[team + '_team_ties'] = 0
        if scrbox_dict['home_team_score'] > scrbox_dict['away_team_score']:
            scrbox_dict['home_team_wins'] = scrbox_dict['home_team_wins'] - 1
            scrbox_dict['away_team_losses'] = scrbox_dict['away_team_losses'] - 1
        elif scrbox_dict['home_team_score'] < scrbox_dict['away_team_score']:
            scrbox_dict['away_team_wins'] = scrbox_dict['away_team_wins'] - 1
            scrbox_dict['home_team_losses'] = scrbox_dict['home_team_losses'] - 1
        else:
            scrbox_dict['away_team_ties'] = scrbox_dict['away_team_ties'] - 1
            scrbox_dict['home_team_ties'] = scrbox_dict['home_team_ties'] - 1

        scrbox_meta = scrbox[2].find_all('div')
        game_datetime = scrbox_meta[0].string + scrbox_meta[1].contents[1][1:]
        scrbox_dict['datetime'] = dt.strptime(game_datetime, '%A %b %d, %Y %H:%M%p')
        for meta in scrbox_meta:
            if meta.contents[0].string == 'Stadium':
                scrbox_dict['stadium_pg'] = meta.a['href']
                scrbox_dict['stadium_name'] = meta.a.string
                scrbox_dict['stadium_id'] = meta.a['href'].split('/')[-1].split('.')[0]
        scrbox_dict['game_id'] = scrbox_dict['datetime'].strftime('%Y%m%d') + '0' + scrbox_dict['home_team_id']
        return scrbox_dict

    @property
    def scoring(self):
        scoring_list = []
        scoring_div = self.soup.find('div', {'id': 'all_scoring'})
        rows = scoring_div.find_all('tr')
        quarter = 1
        for row in rows[1:]:
            scr_dict = {}
            for cell in row.contents:
                cell_str = cell.string
                if cell['data-stat'] == 'quarter' and cell_str is not None:
                    quarter = int(cell_str)
                scr_dict['quarter'] = quarter
                if cell['data-stat'] == 'time':
                    scr_dict = self._time_left_calc(cell_str, scr_dict)
                elif cell['data-stat'] == 'team':
                    tm_name, tm_id, tm_loc = self._team_lookup(cell_str)
                    scr_dict['scoring_team_name'] = tm_name
                    scr_dict['scoring_team_id'] = tm_id
                    scr_dict['scoring_team_loc'] = tm_loc
                elif cell['data-stat'] == 'vis_team_score':
                    scr_dict['away_team_score'] = int(cell_str)
                elif cell['data-stat'] == 'home_team_score':
                    scr_dict['home_team_score'] = int(cell_str)
                elif cell['data-stat'] == 'description':
                    cont = cell.contents
                    scr_dict['play_desc'] = ' '.join(x.string.strip() for x in cont)
                    scr_str = cont[1].string.strip()
                    scr_str_splt = scr_str.split()
                    if scr_str.find('field') > -1:
                        scr_dict['score_type'] = 'field_goal'
                        scr_dict = self._id_name_add(cont[0], scr_dict, 'kicker')
                        scr_dict['xp_success'] = -1
                        scr_dict['yards'] = int(scr_str_splt[0])
                    elif scr_str_splt[2] in ['pass', 'fumble', 'rush', 'interception', 'recovery']:
                        if scr_str_splt[2].find('pass') > -1:
                            scr_dict['score_type'] = 'pass'
                            scr_dict = self._id_name_add(cont[0], scr_dict, 'pass_from')
                            scr_dict = self._id_name_add(cont[2], scr_dict, 'rec_by')
                            scr_dict['yards'] = int(scr_str_splt[0])
                        elif scr_str.find('blocked punt') > -1:
                            scr_dict['score_type'] = 'blocked_punt'
                            scr_dict = self._id_name_add(cont[0], scr_dict, 'block_by')
                            scr_dict['yards'] = 0
                        else:
                            scr_dict['score_type'] = ' '.join(scr_str_splt[2:4])
                            scr_dict['yards'] = int(scr_str_splt[0])
                        xp_str = re.findall('\([a-zA-Z\s]+\)', scr_dict['play_desc'])[0]
                        scr_dict['xp_success'] = 1 if xp_str.find('failed') == -1 else 0
                        if xp_str.find('kick') > -1:
                            scr_dict = self._id_name_add(cont[-2], scr_dict, 'xp_kicker')
                            scr_dict['xp_type'] = 'kick'
                        elif xp_str.find('run') > -1:
                            scr_dict = self._id_name_add(cont[-2], scr_dict, 'xp_rush')
                            scr_dict['xp_type'] = 'run'
                        else:
                            scr_dict['xp_type'] = 'pass'
                            if scr_dict['xp_success']:
                                scr_dict = self._id_name_add(cont[-1], scr_dict, 'xp_rec_by')
                                scr_dict = self._id_name_add(cont[-3], scr_dict, 'xp_pass_from')
                    else:
                        raise KeyError('Play Not Found')

                    for field in ['kicker_id', 'kicker_name', 'pass_from_id', 'pass_from_name', 'rec_by_id',
                                  'rec_by_name', 'rush_by_id',
                                  'rush_by_name', 'yards', 'xp_success', 'score_type', 'xp_kicker_name', 'xp_kicker_id',
                                  'xp_type',
                                  'xp_rec_by_name', 'xp_rec_by_id', 'xp_pass_from_id', 'xp_pass_from_name']:
                        if field not in scr_dict:
                            scr_dict[field] = -999
                scr_dict['game_id'] = self.scrbox_dict['game_id']
            scoring_list.append(scr_dict)
        return scoring_list

    @property
    def game_info(self):
        ginfo_dict = {}
        ginfo_div = self.soup.find('div', {'id': 'all_game_info'})
        comments = ginfo_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')
        for row in rows[1:]:
            row_lbl = row.contents[0].contents[0]
            row_val = row.contents[1].contents[0]
            if row_lbl not in ['Vegas Line', 'Over/Under']:
                ginfo_dict[row_lbl] = row_val
        ginfo_dict['game_id'] = self.scrbox_dict['game_id']
        return ginfo_dict

    @property
    def officials(self):
        off_list = []
        off_div = self.soup.find('div', {'id': 'all_officials'})
        comments = off_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')
        for row in rows[1:]:
            off_dict = {}
            off_dict['ref_title'] = row.contents[0].string
            off_dict['ref_pg'] = row.contents[1].a['href']
            off_dict['ref_id'] = off_dict['ref_pg'].split('/')[-1].split('.')[0]
            off_dict['ref_name'] = row.contents[1].string
            off_dict['game_id'] = self.scrbox_dict['game_id']
            off_list.append(off_dict)
        return off_list

    @property
    def game_summ(self):
        summ_dict = {}
        summ_div = self.soup.find('div', {'id': 'all_team_stats'})
        comments = summ_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')[1:]
        for row in rows:
            cont = row.contents
            row_lbl = cont[0].string
            summ_dict['home_' + row_lbl] = row.find('td', {'data-stat': 'home_stat'}).string
            summ_dict['away_' + row_lbl] = row.find('td', {'data-stat': 'vis_stat'}).string
        summ_dict['home_team_name'] = self.scrbox_dict['home_team_name']
        summ_dict['home_team_id'] = self.scrbox_dict['home_team_id']
        summ_dict['away_team_name'] = self.scrbox_dict['away_team_name']
        summ_dict['away_team_id'] = self.scrbox_dict['away_team_id']
        summ_dict['game_id'] = self.scrbox_dict['game_id']
        return summ_dict

    def stats_table(self, div_id):
        """
        works for the following tables and associated divs:
        Passing, Rushing and Receiving - all_player_offense
        Defense - all_player_defense
        Kick/Punt Returns - all_returns
        kicking and Punting - all_kicking
        """
        stat_list = []
        stat_div = self.soup.find('div', {'id': div_id})
        comments = stat_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')[2:]
        for row in rows:
            cells = row.contents
            if cells[0].name is not None:
                stat_dict = {}
                for cell in cells:
                    lbl = cell['data-stat']
                    cell_str = cell.string
                    if cell_str is None:
                        stat_dict[cell['data-stat']] = 0
                    elif lbl == 'player':
                        stat_dict['player_id'] = cell['data-append-csv']
                        stat_dict['player_name'] = cell_str
                    elif lbl == 'team':
                        stat_dict[cell['data-stat']] = cell_str.lower()
                    elif lbl == 'pos':
                        stat_dict[cell['data-stat']] = cell_str.lower()
                    else:
                        stat_dict[cell['data-stat']] = float(cell_str.replace('%', ''))
                stat_dict['game_id'] = self.scrbox_dict['game_id']
                stat_list.append(stat_dict)
        return stat_list

    def starters(self, loc):
        """
        loc is either home or away
        """
        loc_html = 'vis' if loc == 'away' else 'home'
        start_list = []
        start_div = self.soup.find('div', {'id': 'all_' + loc_html + '_starters'})
        comments = start_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')[1:]
        for row in rows:
            cells = row.contents
            start_dict = {}
            start_dict['player_id'] = cells[0]['data-append-csv']
            start_dict['player_name'] = cells[0].string
            start_dict['pos'] = cells[1].string.lower()
            start_dict['game_id'] = self.scrbox_dict['game_id']
            start_dict['team_name'] = self.scrbox_dict[loc + '_team_name']
            start_dict['team_id'] = self.scrbox_dict[loc + '_team_id']
            start_list.append(start_dict)
        return start_list

    def drives(self, loc):
        """
        loc is either home or away
        """
        loc_html = 'vis' if loc == 'away' else 'home'
        drive_list = []
        drive_div = self.soup.find('div', {'id': 'all_' + loc_html + '_drives'})
        comments = drive_div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')[1:]
        for row in rows:
            cells = row.contents
            drive_dict = {}
            drive_dict['game_id'] = self.scrbox_dict['game_id']
            drive_dict['team_name'] = self.scrbox_dict[loc + '_team_name']
            drive_dict['team_id'] = self.scrbox_dict[loc + '_team_id']
            for cell in cells:
                cell_data = cell['data-stat']
                cell_str = cell.string
                if cell_data in ['drive_num', 'quarter', 'net_yds']:
                    drive_dict[cell_data] = int(cell_str)
                elif cell_data == 'time_start':
                    str_split = cell_str.split(':')
                    drive_dict['sec_left_in_quarter'] = int(str_split[0]) * 60 + int(str_split[1])
                    drive_dict['sec_into_quarter'] = 15 * 60 - (int(str_split[0]) * 60 + int(str_split[1]))
                    drive_dict['sec_left_in_game'] = int(str_split[0]) * 60 + int(str_split[1]) + (
                                4 - drive_dict['quarter']) * 15 * 60
                    drive_dict['sec_into_game'] = 4 * 15 * 60 - (
                                int(str_split[0]) * 60 + int(str_split[1]) + (4 - drive_dict['quarter']) * 15 * 60)
                elif cell_data == 'start_at':
                    if cell_str is not None:
                        str_split = cell_str.split(' ')
                        start_yd = int(str_split[1].lower())
                        drive_dict['start_yrd'] = start_yd
                        drive_dict['start_side'] = str_split[0].lower()
                        if drive_dict['start_side'] == drive_dict['team_id']:
                            start_yd = 100 - start_yd
                        drive_dict['yds_to_td'] = start_yd
                    else:
                        break
                elif cell_data == 'play_count_tip':
                    drive_dict['total_plays'] = int(cell_str)
                    plays = cell.span['tip'].split(',')
                    for i in plays:
                        play_sub = i.strip().split(' ')
                        drive_dict[play_sub[1] + '_plays'] = int(play_sub[0])
                elif cell_data == 'time_total':
                    str_split = cell_str.split(':')
                    drive_dict['drive_sec'] = int(str_split[0]) * 60 + int(str_split[1])
                elif cell_data == 'end_event':
                    drive_dict[cell_data] = cell_str
                else:
                    raise KeyError('Column Not Found')
            drive_list.append(drive_dict)
        return drive_list

    def play_by_play(self):
        pbp_list = []
        rows = self.table_comments_extract(div_id='all_pbp')[2:]
        for row_idx, row in enumerate(rows):
            cells = row.contents
            if cells[0].name is not None and len(cells) == 10 and cells[5].string is None:
                pbp_dict = self._cells_extract(cells)
                pbp_dict['game_id'] = self.scrbox_dict['game_id']
                pbp_list.append(pbp_dict)
        return pbp_list

    def _cells_extract(self, cells):
        pbp_dict = {}
        for cell in cells:
            cell_str = cell.string
            cell_data = cell['data-stat']
            if cell_data in ['quarter', 'down', 'yds_to_go', 'pbp_score_aw', 'pbp_score_hm']:
                if cell_str is None:
                    pbp_dict[cell_data] = -999
                else:
                    pbp_dict[cell_data] = int(cell_str)
            elif cell_data == 'qtr_time_remain':
                pbp_dict = self._time_left_calc(cell_str, pbp_dict)
            elif cell_data == 'location':
                pbp_dict = self._play_loc(cell_str, pbp_dict)
            elif cell_data == 'detail':
                pbp_dict = self._play_detail(cell, pbp_dict)
        return pbp_dict

    def _play_detail(self, cell, pbp_dict):
        cont = cell.contents
        play_str = ''.join(x.string for x in cont if x.string is not None)
        pbp_dict['play_str'] = play_str
        pbp_dict['play_count'] = cont[0]['name'].split('_')[-1]
        pbp_dict = self._play_detail_extract(cont, play_str, pbp_dict)
        if play_str.find('no play') > -1:
            pbp_dict['play_res'] = 'no_play'
        for field in ['play_type', 'play_subtype', 'timeout_num', 'timeout_by', 'kicker_id', 'kicker_name', 'play_yds',
                      'kick_ret_id', 'kick_ret_name', 'kick_ret_yds', 'play_res', 'tackled_by_id', 'tackled_by_name',
                      'sacked_by_name', 'sacked_by_id', 'passer_id', 'passer_name', 'rec_id', 'rec_name', 'rush_id',
                      'rush_name', 'kneel_id', 'kneel_name', 'fmbl_id', 'fmbl_name', 'fmbl_forc_by_id',
                      'fmbl_forc_by_name', 'recover_id', 'recover_name', 'tackle_asst_id', 'tackle_asst_name',
                      'int_name', 'int_id', 'pen_on_id', 'pen_on_name', 'pen_cause', 'pen_res']:
            if field not in pbp_dict:
                pbp_dict[field] = -999
        return pbp_dict

    def _play_detail_extract(self, cont, play_str, pbp_dict):
        for idx, srch in enumerate(cont):
            str_srch = srch.string
            if str_srch is not None:
                str_srch = str_srch.lower()
                str_splt = str_srch.split()
                if str_splt[0] in ['kicks', 'punts'] or str_splt[0].isnumeric():
                    pbp_dict = self._play_details_kick(cont, str_splt, idx, str_srch, play_str, pbp_dict)
                if str_srch.find('timeout') > -1:
                    pbp_dict = self._play_details_to(cont, pbp_dict)
                pbp_dict = self._play_details_endpoints(cont, str_srch, idx, pbp_dict)
                if 5 > str_srch.find('pass') > -1:
                    pbp_dict = self._play_details_pass(cont, str_srch, idx, play_str, pbp_dict)
                elif max(str_srch.find(x) for x in ['right', 'middle', 'left']) > -1 and cont[idx].name is None:
                    pbp_dict = self._play_details_rush(cont, str_srch, idx, pbp_dict)
                elif str_srch.find('kneels') > -1:
                    pbp_dict = self._play_details_kneel(cont, str_srch, idx, pbp_dict)
                if str_srch.find('fumble') > -1:
                    pbp_dict = self._id_name_add(cont[idx - 1], pbp_dict, 'fmbl')
                    if str_srch.find('forced') > -1:
                        pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'fmbl_forc_by')
                if str_srch.find('recover') > -1:
                    pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'recover')
                if str_srch.find('intercept') > -1:
                    pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'int')
                    pbp_dict['play_yds'] = int(cont[idx + 4].string.split('for')[-1].split('yard')[0].strip())
                    pbp_dict['play_res'] = 'interception'
                if str_srch.find('penalty') > -1:
                    pbp_dict = self._play_details_penalty(cont, idx, pbp_dict)
                if str_srch.find('touchdown') > -1:
                    pbp_dict['play_res'] = 'touchdown'
                if str_srch.find('two point attempt') > 1:
                    pbp_dict = self._play_details_tpc(cont, pbp_dict)
                    break
        return pbp_dict

    def _play_details_kneel(self, cont, str_srch, idx, pbp_dict):
        pbp_dict['play_type'] = 'kneel'
        pbp_dict = self._id_name_add(cont[idx - 1], pbp_dict, 'kneel')
        if str_srch.find('no gain') > -1:
            pbp_dict['play_yds'] = 0
        else:
            pbp_dict['play_yds'] = int(str_srch.split('for')[-1].split('yard')[0].strip())
        return pbp_dict

    def _play_details_penalty(self, cont, idx, pbp_dict):
        pen_on_id, pen_on_name = self._name_extract(cont[idx + 1])
        if 'pen_on_id' in pbp_dict:
            pen_sfx = '_2'
        else:
            pen_sfx = ''
        pbp_dict['pen_on_id' + pen_sfx] = pen_on_id
        pbp_dict['pen_on_name' + pen_sfx] = pen_on_name
        pen_res_str = cont[idx + 2].string.lower()
        if pen_res_str.find('yard') > -1:
            pen_res = pen_res_str.split(':')[-1].split(', ')
            pbp_dict['pen_cause' + pen_sfx] = pen_res[0]
            pbp_dict['pen_res' + pen_sfx] = pen_res[1]
        else:
            pen_res = pen_res_str.split(':')[-1].split('penalty')
            pbp_dict['pen_cause' + pen_sfx] = pen_res[0]
            pbp_dict['pen_res' + pen_sfx] = -999
        if idx <= 1:
            pbp_dict['play_type'] = 'penalty'
        return pbp_dict

    def _play_details_rush(self, cont, str_srch, idx, pbp_dict):
        pbp_dict['play_type'] = 'rush'
        pbp_dict = self._id_name_add(cont[idx - 1], pbp_dict, 'rush')
        rush_splt = str_srch.split('for')
        if str_srch.find('no gain') > -1:
            pbp_dict['play_yds'] = 0
        else:
            pbp_dict['play_yds'] = int(rush_splt[-1].split('yard')[0].strip())
        pbp_dict['play_subtype'] = rush_splt[0].strip()
        return pbp_dict

    def _play_details_endpoints(self, cont, str_srch, idx, pbp_dict):
        if str_srch.find('tackle by') > -1:
            pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'tackled_by')
            if len(cont) >= idx + 3 and cont[idx + 2].find('and') > -1:
                pbp_dict = self._id_name_add(cont[idx + 3], pbp_dict, 'tackle_asst')
        if str_srch.find('sacked by') > -1:
            pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'sacked_by')
            pbp_dict['play_type'] = 'sack'
            if len(cont) >= idx + 3 and cont[idx + 2].find('and') > -1:
                pbp_dict = self._id_name_add(cont[idx + 3], pbp_dict, 'sack_asst')
                pbp_dict['play_yds'] = self._extract_yds(cont[idx + 4])
            else:
                pbp_dict['play_yds'] = self._extract_yds(cont[idx + 2])
        return pbp_dict

    def _play_details_pass(self, cont, str_srch, idx, play_str, pbp_dict):
        pbp_dict['play_type'] = 'pass'
        pbp_dict = self._id_name_add(cont[idx - 1], pbp_dict, 'passer')
        if idx+1 < len(cont):
            pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'rec')
        if str_srch.find('incomplete') > -1:
            pbp_dict['play_res'] = 'incomplete'
            pbp_dict['play_yds'] = 0
        else:
            pbp_dict['play_res'] = 'complete'
            if play_str.find('no gain') > -1:
                pbp_dict['play_yds'] = 0
            else:
                pbp_dict['play_yds'] = int(cont[idx + 2].strip().split()[1])
        return pbp_dict

    def _play_details_kick(self, cont, str_splt, idx, str_srch, play_str, pbp_dict):
        pbp_dict['play_type'] = 'kick'
        pbp_dict = self._id_name_add(cont[1], pbp_dict, 'kicker')
        if str_splt[1] == 'off':
            pbp_dict['play_subtype'] = 'kickoff'
            pbp_dict['play_yds'] = int(str_splt[2])
            if str_srch.find('touchback') > -1:
                pbp_dict['play_res'] = 'touchback'
            else:
                pbp_dict = self._id_name_add(cont[idx + 1], pbp_dict, 'kick_ret')
                pbp_dict['kick_ret_yds'] = int(cont[idx + 2].split()[1])
        elif str_splt[0] == 'punts':
            pbp_dict['play_subtype'] = 'punt'
        elif str_splt[1] == 'extra':
            pbp_dict['play_subtype'] = 'xp'
            if play_str.find('no good') > -1:
                pbp_dict['play_res'] = 'no_good'
            else:
                pbp_dict['play_res'] = 'good'
        elif str_splt[0].isnumeric():
            pbp_dict['play_subtype'] = 'field_goal'
            if play_str.find('no good') > -1:
                pbp_dict['play_res'] = 'no_good'
            else:
                pbp_dict['play_res'] = 'good'
        else:
            raise KeyError('Kicking Play Not Found')
        return pbp_dict

    def _play_details_to(self, cont, pbp_dict):
        cont_str = cont[1].split(' ')
        pbp_dict['play_type'] = 'timeout'
        pbp_dict['timeout_num'] = int(cont_str[1][1:])
        pbp_dict['timeout_by'] = ' '.join(cont_str[3:])
        return pbp_dict

    def _play_details_tpc(self, cont, pbp_dict):
        pbp_dict['play_type'] = 'tpc'
        if cont[2].find('pass') > -1:
            pbp_dict['play_subtype'] = 'pass'
            pbp_dict = self._id_name_add(cont[1], pbp_dict, 'passer')
            if type(cont[3]) == Tag:
                pbp_dict = self._id_name_add(cont[3], pbp_dict, 'rec')
        else:
            pbp_dict['play_subtype'] = 'rush'
            pbp_dict = self._id_name_add(cont[1], pbp_dict, 'rush')
        for v in cont:
            if v.find('succeed') > -1:
                pbp_dict['play_res'] = 'good'
            elif v.find('fail') > -1:
                pbp_dict['play_res'] = 'no_good'
        return pbp_dict

    def _team_lookup(self, team_string):
        if (self.scrbox_dict['home_team_name']+self.scrbox_dict['home_team_id']).find(team_string) > -1:
            tm_name = self.scrbox_dict['home_team_name']
            tm_id = self.scrbox_dict['home_team_id']
            tm_loc = 'home'
        elif (self.scrbox_dict['away_team_name']+self.scrbox_dict['away_team_id']).find(team_string) > -1:
            tm_name = self.scrbox_dict['away_team_name']
            tm_id = self.scrbox_dict['away_team_id']
            tm_loc = 'away'
        else:
            raise KeyError('Team Not Found')
        return tm_name, tm_id, tm_loc

    def _name_extract(self, cell):
        cell_id = cell['href'].split('/')[-1].split('.')[0]
        cell_name = cell.string
        return cell_id, cell_name

    def _time_left_calc(self, cell_str, fld_dict):
        if cell_str is not None:
            str_split = cell_str.split(':')
            fld_dict['sec_left_in_quarter'] = int(str_split[0]) * 60 + int(str_split[1])
            fld_dict['sec_into_quarter'] = 15 * 60 - (int(str_split[0]) * 60 + int(str_split[1]))
            fld_dict['sec_left_in_game'] = int(str_split[0]) * 60 + int(str_split[1]) + (
                        4 - fld_dict['quarter']) * 15 * 60
            fld_dict['sec_into_game'] = 4 * 15 * 60 - (
                        int(str_split[0]) * 60 + int(str_split[1]) + (4 - fld_dict['quarter']) * 15 * 60)
        else:
            fld_dict['sec_left_in_quarter'] = np.NAN
            fld_dict['sec_into_quarter'] = np.NAN
            fld_dict['sec_left_in_game'] = np.NAN
            fld_dict['sec_into_game'] = np.NAN
        return fld_dict

    def _id_name_add(self, cell, pbp_dict, id_name_str):
        id_str, name_str = self._name_extract(cell)
        pbp_dict[id_name_str + '_id'] = id_str
        pbp_dict[id_name_str + '_name'] = name_str
        return pbp_dict

    def _extract_yds(self, cell_cont):
        return int(cell_cont.string.split('for')[-1].split('yard')[0].strip())

    def table_comments_extract(self, div_id):
        div = self.soup.find('div', {'id': div_id})
        comments = div.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        rows = table.find_all('tr')
        return rows

    def _play_loc(self, cell_str, pbp_dict):
        if cell_str is None:
            pbp_dict['loc_yrd'] = -999
            pbp_dict['loc_side'] = -999
        else:
            str_split = cell_str.strip().split(' ')
            if len(str_split) == 1:
                pbp_dict['loc_yrd'] = int(str_split[0])
                pbp_dict['loc_side'] = -999
            else:
                pbp_dict['loc_yrd'] = int(str_split[1])
                pbp_dict['loc_side'] = str_split[0].lower()
        return pbp_dict
