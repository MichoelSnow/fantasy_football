from urllib import request
from bs4 import BeautifulSoup, Comment
import os
import re

class SeasonData:
    # Extracts all data for a given season

    bs_pg = 'https://www.pro-football-reference.com'
    bs_pg_yrs = 'https://www.pro-football-reference.com/years/'


    table_dict = {
        'week_urls': 'links to weekly summaries (dict)',
        'awards': 'award winners (dict)',
        'season_stats': {
            'all_AFC': 'AFC Standings (list of dicts)',
            'all_NFC': 'NFC Standings (list of dicts)',
            'all_playoff_results': 'playoff results (list of dicts)',
            'all_afc_playoff_standings': 'AFC playoff standings (list of dicts)',
            'all_nfc_playoff_standings': 'NFC playoff standings (list of dicts)',
            'all_team_stats': 'offensive stats by team (list of dicts)',
            'all_passing': 'offensive passing stats by team (list of dicts)',
            'all_rushing': 'offensive rushing stats by team(list of dicts)',
            'all_returns': 'kick and punt return stats by team (list of dicts)',
            'all_kicking': 'kicking and punting stats by team (list of dicts)',
            'all_team_scoring': 'scoring stats by team (list of dicts)',
            'all_team_conversions': 'conversion stats by team (list of dicts)',
            'all_drives': 'drive stats by team (list of dicts)'
        },
    }

    def __init__(self, year, loc=None):
        self.year = str(year)
        self.loc = loc
        self.soup = self.season_soup()

    def season_soup(self):
        if self.loc is None:
            pg = request.urlopen(f'{self.bs_pg_yrs}{self.year}')
            soup = BeautifulSoup(pg, 'html.parser')
        else:
            soup = BeautifulSoup(open(os.path.join(self.loc, f'{self.year}.html')), 'html.parser')
        return soup

    @property
    def week_urls(self):
        weeks = self.soup.find('div', {'id': 'all_week_games'})
        comments = weeks.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        vals = table.find_all('a')
        wurls_dict = {}
        wurls = []
        for i in vals:
            wurl_string = f"{self.bs_pg}{i['href']}"
            wurls.append(wurl_string)
            wurls_dict[i.string] = wurl_string
        return wurls, wurls_dict

    @property
    def awards(self):
        awards = self.soup.find('div', {'id': 'all_awards'})
        comments = awards.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        vals = table.find_all('a')
        awards_dict = {}
        for i in range(0, len(vals), 2):
            award_id_str = vals[i]['href']
            awards_dict[self.year + ' ' + vals[i].string] = {
                'award_url': f"{self.bs_pg}{award_id_str}",
                'award_id': award_id_str.split('/')[-1].split('.')[0],
                'player_name': vals[i+1].string,
                'player_id': vals[i+1]['href'].split('/')[-1].split('.')[0]}
        return awards_dict

    def season_stats(self, stat_table):
        div_val = self.soup.find('div', {'id': stat_table})
        table_rows = div_val.find_all('tr')
        if not table_rows:
            comments = div_val.find_all(string=lambda text: isinstance(text, Comment))
            table = BeautifulSoup(str(comments), 'lxml')
            table_rows = table.find_all('tr')
        if stat_table in ['all_AFC', 'all_NFC']:
            stat_list = self.stats_conference(table_rows)
        elif stat_table in ['all_playoff_results']:
            stat_list = self.stats_all_playoffs(table_rows)
        elif stat_table in ['all_afc_playoff_standings', 'all_nfc_playoff_standings']:
            stat_list = self.stats_conference_playoffs(table_rows)
        elif stat_table in ['all_team_stats', 'all_passing', 'all_rushing', 'all_returns', 'all_kicking',
                            'all_team_scoring', 'all_team_conversions', 'all_drives']:
            stat_list = self.stats_play_type(table_rows)
        else:
            raise KeyError('Table Not in List of Tables')
        return stat_list

    def stats_conference(self, table_rows):
        stat_list = []
        for row in table_rows[2:]:
            cells = row.contents
            if cells[0].a is not None:
                stat_dict = {}
                for cell in cells:
                    lbl = cell['data-stat']
                    cell_str = cell.string
                    if lbl in ['team']:
                        stat_dict = self._id_name_add(cell.a, stat_dict, lbl)
                    else:
                        stat_dict[cell['data-stat']] = cell_str
                stat_list.append(stat_dict)
        return stat_list

    def stats_conference_playoffs(self, table_rows):
        stat_list = []
        for row in table_rows[1:]:
            cells = row.contents
            if cells[0].a is not None:
                stat_dict = {}
                for cell in cells:
                    lbl = cell['data-stat']
                    cell_str = cell.string
                    if lbl in ['team']:
                        stat_dict = self._id_name_add(cell.a.next, stat_dict, lbl)
                    else:
                        stat_dict[cell['data-stat']] = cell_str
                stat_list.append(stat_dict)
        return stat_list

    def stats_all_playoffs(self, table_rows):
        stat_list = []
        for row in table_rows[1:]:
            cells = row.contents
            stat_dict = {}
            for cell in cells:
                if cells[0].name is not None:
                    lbl = cell['data-stat']
                    cell_str = cell.string
                    if lbl in ['team', 'loser', 'winner']:
                        stat_dict = self._id_name_add(cell.a, stat_dict, lbl)
                    elif lbl in ['game_location']:
                        if cell_str is None:
                            stat_dict[cell['data-stat']] = 'winner'
                        else:
                            stat_dict[cell['data-stat']] = 'loser'
                    elif lbl in ['boxscore_word']:
                        stat_dict['boxscore'] = cell.a['href']
                    else:
                        stat_dict[cell['data-stat']] = cell_str
            stat_list.append(stat_dict)
        return stat_list

    def stats_play_type(self, table_rows):
        stat_list = []
        for row in table_rows[1:]:
            cells = row.contents
            if cells[0].name is not None and cells[1].a is not None:
                stat_dict = {}
                for cell in cells:
                    lbl = cell['data-stat']
                    cell_str = cell.string
                    if cell_str is None:
                        stat_dict[cell['data-stat']] = 0
                    elif lbl in ['team']:
                        stat_dict = self._id_name_add(cell.a, stat_dict, lbl)
                    elif lbl.find('perc') > -1 or lbl.find('pct') > -1:
                        stat_dict[cell['data-stat']] = float(cell_str[:-1])
                    elif lbl == 'start_avg':
                        stat_dict['yards_from_endzone_avg'] = float(cell['csk'])
                    elif lbl == 'time_avg':
                        tm = cell_str.split(':')
                        stat_dict['sec_avg'] = int(tm[0]) * 60 + int(tm[1])
                    else:
                        stat_dict[cell['data-stat']] = float(cell_str)
                stat_list.append(stat_dict)
        return stat_list

    def _name_extract(self, cell):
        cell_id = re.findall('[^a-z]([a-z]{3})[^a-z]', cell['href'])[0]
        cell_name = cell.string
        return cell_id, cell_name

    def _id_name_add(self, cell, dct, id_name_str):
        id_str, name_str = self._name_extract(cell)
        dct[id_name_str + '_id'] = id_str
        dct[id_name_str + '_name'] = name_str
        return dct

    abbrev_dict = {
        'win_loss_perc': 'Win-Loss Percentage of team. After 1972, ties are counted as half-wins and half-losses. '
                         'Prior, the league did not count them as games in calculations.',
        'mov': 'Margin of Victory, (Points Scored - Points Allowed)/ Games Played',
        'sos': 'Strength of Schedule, Average quality of opponent as measured by SRS (Simple Rating System)',
        'srs': 'Simple Rating System, Team quality relative to average (0.0) as measured by SRS (Simple Rating System).'
               ' SRS = MoV + SoS = OSRS + DSRS '
               'The difference in SRS can be considered a point spread (add about 2 pt for HFA)',
        'osrs': 'Offensive SRSTeam offense quality relative to average (0.0) as measured by SRS (Simple Rating System)',
        'dsrs': 'Defensive SRSTeam defense quality relative to average (0.0) as measured by SRS (Simple Rating System)',
        'why': 'Position',
        'week_num': 'Week number in season',
        'pts_win': 'Points Scored by the winning team (first one listed)',
        'pts_lose': 'Points Scored by the losing team (second one listed)',
        'wins': 'Games Won',
        'losses': 'Games Lost',
        'ties': 'Tie Games',
        'reason': 'Reason the team is seeded the way it is, based on NFL tiebreaker rules',
        'ranker': 'This is a count of the rows from top to bottom.'
                  'It is recalculated following the sorting of a column.',
        'g': 'Games played',
        'points': 'Points Scored by team',
        'plays_offense': 'Offensive Plays: Pass Attempts + Rush Attempts + Times Sacked',
        'yds_per_play_offense': 'Yards per Offensive Play'
                                '(Rush + Pass Yards)/( Pass Attempts + Rush Attempts + Times Sacked)',
        'turnovers': 'Team Turnovers Lost',
        'fumbles_lost': 'Fumbles Lost by Team',
        'pass_cmp': 'Passes completed',
        'pass_att': 'Passes attempted',
        'pass_yds': 'Yards Gained by Passing. For teams, sack yardage is deducted from this total',
        'pass_td': 'Passing Touchdowns',
        'pass_int': 'Interceptions thrown',
        'pass_net_yds_per_att': 'Net Yards gained per pass attempt'
                                '(Passing Yards - Sack Yards) / (Passes Attempted + Times Sacked)'
                                'Minimum 14 attempts per schedule game to qualify as leader.'
                                'Minimum 1500 pass attempts to qualify as career leader.',
        'pass_fd': 'First Downs by Passing',
        'rush_att': 'Rushing Attempts (sacks not included in NFL)',
        'rush_yds': 'Rushing Yards Gained (sack yardage is not included by NFL)',
        'rush_td': 'Rushing Touchdowns',
        'rush_yds_per_att': 'Rushing Yards per Attempt'
                            'Minimum 6.25 rushes per game scheduled to qualify as leader.'
                            'Minimum 750 rushes to qualify as career leader.',
        'rush_fd': 'First Downs by Rushing',
        'penalties': 'Penalties committed by team and accepted ',
        'penalties_yds': 'Penalties in yards committed by team ',
        'pen_fd': 'First Downs by Penalty',
        'score_pct': 'Percentage of drives ending in an offensive score',
        'turnover_pct': 'Percentage of drives ending in an offensive turnover',
        'exp_pts_tot': 'Expected points contributed by all offense',
        'pass_cmp_perc': 'Percentage of Passes Completed'
                         'Minimum 14 attempts per scheduled game to qualify as leader.'
                         'Minimum 1500 pass attempts to qualify as career leader.',
        'pass_td_perc': 'Percentage of Touchdowns Thrown when Attempting to Pass '
                        'Minimum 14 attempts per scheduled game to qualify as leader'
                        'Minimum 1500 pass attempts to qualify as career leader',
        'pass_int_perc': 'Percentage of Times Intercepted when Attempting to Pass '
                         'Minimum 14 attempts per scheduled game to qualify as leader.'
                         'Minimum 1500 pass attempts to qualify as career leader',
        'pass_long': 'Longest Completed Pass Thrown (complete since 1975)',
        'pass_yds_per_att': 'Yards gained per pass attempt '
                            'Minimum 14 attempts per scheduled game to qualify as leader.'
                            'Minimum 1500 pass attempts to qualify as career leader.',
        'pass_adj_yds_per_att': 'Adjusted Yards gained per pass attempt'
                                '(Passing Yards + 20 * Passing TD - 45 * Interceptions) / (Passes Attempted)'
                                'Minimum 14 attempts per scheduled game to qualify as leader.'
                                'Minimum 1500 pass attempts to qualify as career leader.',
        'pass_yds_per_cmp': 'Yards gained per pass completion (Passing Yards) / (Passes Completed)'
                            'Minimum 14 pass attempts per schedule game to qualify as leader.'
                            'Minimum 1500 pass attempts to qualify as career leader',
        'pass_yds_per_g': 'Yards gained per game played'
                          'Minimum half a game played per scheduled game to qualify as leader.'
                          'Minimum 1500 pass attempts to qualify as career leader',
        'pass_rating': 'Quarterback Rating, see glossary for details'
                       'Different ratings are used by the NFL and NCAA.'
                       'Minimum 1500 pass attempts to qualify as career leader, '
                       'minimum 150 pass attempts for playoffs leader.',
        'pass_sacked': 'Times Sacked (first recorded in 1969, player per game since 1981)',
        'pass_sacked_yds': 'Yards lost due to sacks (first recorded in 1969, player per game since 1981)',
        'pass_adj_net_yds_per_att': 'Adjusted Net Yards per Pass Attempt'
                                    '(Passing Yards - Sack Yards + (20 * Passing TD) - '
                                    '(45 * Interceptions)) / (Passes Attempted + Times Sacked)'
                                    'Minimum 14 attempts per scheduled game to qualify as leader'
                                    'Minimum 1500 pass attempts to qualify as career leader.',
        'pass_sacked_perc': 'Percentage of Time Sacked when Attempting to Pass: '
                            'Times Sacked / (Passes Attempted + Times Sacked)'
                            'Minimum 14 attempts + sacks per scheduled game to qualify as leader'
                            'Minimum 1500 pass attempts to qualify as career leader',
        'comebacks': 'Comebacks led by quarterback.'
                     'Must be an offensive scoring drive in the 4th quarter, with the team trailing by one score, '
                     'though not necessarily a drive to take the lead. Only games ending in a win or tie are included.',
        'gwd': 'Game-winning drives led by quarterback.'
               'Must be an offensive scoring drive in the 4th quarter or '
               'overtime that puts the winning team ahead for the last time.',
        'exp_pts_pass': 'Expected points contributed by passing offense',
        'rush_long': 'Longest Rushing Attempt',
        'rush_yds_per_g': 'Rushing Yards per Game'
                          '(minimum half a game per game scheduled to qualify as leader)'
                          '(Rushing Yards)/(Games Played)',
        'fumbles': 'Number of times fumbled both lost and recovered by own team'
                   'These represent ALL fumbles by the player on offense, defense, and special teams',
        'exp_pts_rush': 'Expected points contributed by rushing offense',
        'punt_ret': 'Punts Returned',
        'punt_ret_yds': 'Punts Return Yardage',
        'punt_ret_td': 'Punts Returned for Touchdown',
        'punt_ret_long': 'Longest Punt Return',
        'punt_ret_yds_per_ret': '<b>Yards per Punt Return'
                                'Minimum one return per game scheduled to qualify as leader.'
                                'Minimum 75 punt returns to qualify as career leader.',
        'kick_ret': 'Kickoff Returns',
        'kick_ret_yds': 'Yardage for Kickoffs Returned',
        'kick_ret_td': 'Kickoffs Returned for a touchdown',
        'kick_ret_long': 'Longest Kickoff Return',
        'kick_ret_yds_per_ret': 'Yards per Kickoff Return - Kick Return Yardage/Kickoff Returns'
                                'Minimum one return per game scheduled to qualify as leader.'
                                'Minimum 75 kick returns to qualify as career leader',
        'all_purpose_yds': 'Rushing, Receiving and Kick, Punt, Interception, and Fumble Return Yardage',
        'fga1': 'Field Goals Attempted, 19 yards and under',
        'fgm1': 'Field Goals Made, 19 yards and under',
        'fga2': 'Field Goals Attempted, 20-29 yards',
        'fgm2': 'Field Goals Made, 20-29 yards',
        'fga3': 'Field Goals Attempted, 30-39 yards',
        'fgm3': 'Field Goals Made, 30-39 yards',
        'fga4': 'Field Goals Attempted, 40-49 yards',
        'fgm4': 'Field Goals Made, 40-49 yards',
        'fga5': 'Field Goals Attempted, 50+ yards',
        'fgm5': 'Field Goals Made, 50+ yards',
        'fga': 'Field Goals Attempted',
        'fgm': 'Total Field Goals Made',
        'fg_perc': 'Percentage of field goals made, 100*(FGM/FGA)'
                   'Minimum 0.75 attempts per game scheduled to qualify as a leader.'
                   'Minimum 100 FGA to qualify as career leader.',
        'xpa': 'Extra Points Attempted',
        'xpm': 'Extra Points Made',
        'xp_perc': 'Extra Point Percentage'
                   '(Extra Points Made)/(Extra Points Attempted)'
                   'Minimum 1.5 attempts per game scheduled to be a leader.',
        'punt': 'Times Punted',
        'punt_yds': 'Total Punt Yardage',
        'punt_long': 'Longest Punt',
        'punt_blocked': 'Times Punts Blocked',
        'punt_yds_per_punt': 'Yards per Punt'
                             'Minimum one punt per game scheduled to qualify as leader.'
                             'Minimum 250 punts to qualify as career leader.',
        'otd': 'Other touchdowns from blocked kicks or missed field goals returned',
        'alltd': 'All touchdowns scored',
        'two_pt_md': 'Two-Point Conversions Made',
        'two_pt_att': 'Two-Point Conversions attempted',
        'def_two_pt': 'Defensive Two-Point Conversions',
        'safety_md': 'Safeties scored by player/team',
        'scoring': 'Total points scored by all means',
        'points_per_g': 'Points per game',
        'third_down_att': '3rd Down Attempts in game',
        'third_down_success': '3rd Down Conversions in game',
        'third_down_pct': '3rd Down Conversion Percentage',
        'fourth_down_att': '4th Down Attempts in game',
        'fourth_down_success': '4th Down Conversions in game',
        'fourth_down_pct': '4th Down Conversion Percentage',
        'red_zone_att': 'Red Zone Attempts',
        'red_zone_scores': 'Red Zone Scores',
        'red_zone_pct': 'Percentage of the time a team raches the red zone and scores',
        'drives': 'Number of drives',
        'play_count_tip': 'Number of plays in drive.<br />P - Pass, R - Rush, Y - Penalty',
        'plays_per_drive': 'Average # of plays per Drive',
        'yds_per_drive': 'Net yards per drive',
        'start_avg': 'Average starting field position',
        'time_avg': 'Average time per drive',
        'points_avg': 'Average points scored per drive'
    }
