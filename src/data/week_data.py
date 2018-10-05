from urllib import request
from bs4 import BeautifulSoup, Comment
import os
from datetime import datetime


class WeekData:

    bs_pg = 'https://www.pro-football-reference.com'
    bs_pg_yrs = 'https://www.pro-football-reference.com/years/'

    table_dict = {
        'week_summaries': 'summaries of all games that week (list of dicts)',
        'potw': 'players of the week (dict)',
        'player_stat': {
            'all_qb_stats': 'top passers of the week (list of dicts)',
            'all_rec_stats': 'top receivers of the week (list of dicts)',
            'all_rush_stats': 'top rushers of the week (list of dicts)',
            'all_def_stats': 'top defenders of the week (list of dicts)',
        },
    }

    def __init__(self, year, week, loc=None):
        self.year = str(year)
        self.week = str(week)
        self.loc = loc
        self.soup = self.week_soup()

    def week_soup(self):
        if self.loc is None:
            pg = request.urlopen(f'{self.bs_pg_yrs}{self.year}/week_{self.week}.htm')
            soup = BeautifulSoup(pg, 'html.parser')
        else:
            soup = BeautifulSoup(open(os.path.join(self.loc, f'week_{self.week}.htm')), 'html.parser')
        return soup

    @property
    def week_summaries(self):
        div_val = self.soup.find('div', {'class': 'game_summaries'})
        summ = div_val.find_all('div', {'class': 'game_summary expanded nohover'})
        summ_list = []
        for idx in range(15):
            summ_dict = {}
            summ_dict['date'] = str(
                datetime.strptime(summ[idx].find('tr', {'class': 'date'}).string, '%b %d, %Y').date())
            summ_dict['winning_team'] = summ[idx].find('tr', {'class': 'winner'}).find('td').string
            summ_dict['winning_team_id'] = summ[idx].find('tr', {'class': 'winner'}).find('td').a['href'].split('/')[-2]
            summ_dict['wining_team_score'] = summ[idx].find('tr', {'class': 'winner'}).find('td',
                                                                                           {'class': 'right'}).string
            summ_dict['boxscore'] = summ[idx].find(text='Final').parent['href']
            summ_dict['losing_team'] = summ[idx].find('tr', {'class': 'loser'}).find('td').string
            summ_dict['losing_team_id'] = summ[idx].find('tr', {'class': 'loser'}).find('td').a['href'].split('/')[-2]
            leaders = summ[idx].find('table', {'class': 'stats'}).find_all('td')
            for i in range(0, 9, 3):
                title = leaders[i].string
                summ_dict[title + '_leader'] = leaders[i + 1].a['title']
                summ_dict[title + '_leader_id'] = leaders[i + 1].a['href'].split('/')[-1].split('.')[0]
                summ_dict[title + '_leader_team_id'] = leaders[i + 1].contents[-1][1:].lower()
                summ_dict[title + '_leader_value'] = int(leaders[i + 2].string)
            summ_list.append(summ_dict)
        return summ_list

    @property
    def potw(self):
        div_val = self.soup.find('div', {'id': 'all_potw'})
        rows = div_val.find_all('tr')
        potw_dict = {}
        for jdx in range(1, 3):
            conf = rows[jdx].contents[0].string
            for idx in range(1, 4):
                potw_dict[conf + '_' + rows[jdx].contents[idx]['data-stat'] + '_name'] = rows[1].contents[idx].a.string
                potw_dict[conf + '_' + rows[jdx].contents[idx]['data-stat'] + '_id'] = \
                    rows[1].contents[idx].a['href'].split('/')[-1].split('.')[0]
        return potw_dict

    def player_stat(self, stat_div):
        div_val = self.soup.find('div', {'id': stat_div})
        comments = div_val.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        stat_list = []
        for rows in table.find_all('tr')[1:]:
            conts = rows.contents
            stat_dict = {}
            stat_dict['player_name'] = conts[0].a.string
            stat_dict['player_id'] = conts[0].a['href'].split('/')[-1].split('.')[0]
            stat_dict['date'] = conts[1].string
            stat_dict['boxscore'] = conts[1].a['href']
            stat_dict['team_id'] = conts[2].string.lower()
            stat_dict['opp_id'] = conts[4].string.lower()
            result = conts[5].string
            result_score = result.split()[-1].split('-')
            if result[0] == 'W':
                stat_dict['winning_team_id'] = stat_dict['team_id']
            else:
                stat_dict['winning_team_id'] = stat_dict['opp_id']
            stat_dict['team_score'] = int(result_score[0])
            stat_dict['opp_score'] = int(result_score[1])
            for idx in range(6, len(conts)):
                stat_dict[conts[idx]['data-stat']] = float(conts[idx].string)
            stat_list.append(stat_dict)
        return stat_list

    abbrev_dict = {
        'conference_id': 'Conference played in: AFC or NFC',
        'st': 'special teams',
        'pass_cmp': 'Passes completed',
        'pass_att': 'Passes attempted',
        'pass_yds': 'Yards Gained by Passing<br>For teams, sack yardage is deducted from this total',
        'pass_td': 'Passing Touchdowns',
        'pass_int': 'Interceptions thrown',
        'pass_rating': 'Quarterback Rating, see glossary for details<br>Different ratings are used by the NFL and NCAA.<br />Minimum 1500 pass attempts to qualify as career leader, minimum 150 pass attempts for playoffs leader.',
        'rec': 'Receptions',
        'rec_yds': 'Receiving Yards',
        'rec_td': 'Receiving Touchdowns',
        'rush_att': 'Rushing Attempts (sacks not included in NFL)',
        'rush_yds': 'Rushing Yards Gained (sack yardage is not included by NFL)',
        'rush_td': 'Rushing Touchdowns',
        'tackles_solo': 'Tackles<br>Before 1994: unofficial and inconsistently recorded from team to team. For amusement only.<br>1994-now: unofficial but consistently recorded.<br>',
        'tackles_assists': 'Assists on tackles<br>Before 1994: combined with solo tackles<br>1994-now: unofficial, but consistently recorded<br>',
        'def_int': 'Passes intercepted on defense',
        'def_int_yds': 'Yards interceptions were returned',
        'def_int_td': 'Interceptions returned for touchdowns',
        'pass_defended': 'Passes defended by a defensive player',
        'sacks': 'Sacks',
        'fumbles_forced': 'Number of times forced a fumble by the opposition recovered by either team'
    }