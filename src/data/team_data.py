from urllib import request
from bs4 import BeautifulSoup, Comment
import os
import re


class TeamData:
    bs_pg = 'https://www.pro-football-reference.com'
    bs_pg_yrs = 'https://www.pro-football-reference.com/years/'

    def __init__(self, year, path=None):
        self.year = str(year)
        self.path = path
        self.team_pages_dict = self.team_pages()
        self.soup_team = None
        self.soup_draft = None
        self.soup_roster = None
        self.soup_injuries = None

    @staticmethod
    def save_soup(soup, path, name):
        with open(f"{path}{name}", "w") as file:
            file.write(str(soup))

    @staticmethod
    def load_soup(path, name):
        soup = BeautifulSoup(open(os.path.join(path, name)), 'html.parser')
        return soup

    def team_pages(self):
        if self.path is None:
            pg = request.urlopen(f'{self.bs_pg_yrs}{self.year}')
            soup = BeautifulSoup(pg, 'html.parser')
        else:
            soup = BeautifulSoup(open(os.path.join(self.path, f'{self.year}.html')), 'html.parser')
        div_val = soup.find('div', {'id': 'all_team_stats'})
        comments = div_val.find_all(string=lambda text: isinstance(text, Comment))
        table = BeautifulSoup(str(comments), 'lxml')
        table_rows = table.find_all('tr')[2:-3]
        team_pages_dict = {}
        for row in table_rows:
            cell = row.contents[1]
            team_pages_dict[cell.string] = self.bs_pg + cell.a['href']
        return team_pages_dict

    def soup_team_extract(self, team_page, path_team=None, local=False, write_soup=False):
        team_id = team_page.split('/')[-2]
        if path_team is not None and local:
            soup = BeautifulSoup(open(os.path.join(path_team, f'{self.year}_{team_id}.htm')), 'html.parser')
        else:
            pg = request.urlopen(f'{team_page}')
            soup = BeautifulSoup(pg, 'html.parser')
            if write_soup and path_team is not None:
                name = f'{self.year}_{team_id}.htm'
                self.save_soup(soup, path_team, name)
        self.soup_team = soup

    def soup_draft_extract(self, path_draft=None, local=False, write_soup=False):
        if path_draft is not None and local:
            soup = BeautifulSoup(open(os.path.join(path_draft, f'{self.year}_draft.htm')), 'html.parser')
        else:
            pg = request.urlopen(f'{self.bs_pg_yrs}{self.year}/draft.htm')
            soup = BeautifulSoup(pg, 'html.parser')
            if write_soup and path_draft is not None:
                name = f'{self.year}_draft.htm'
                self.save_soup(soup, path_draft, name)
        self.soup_draft = soup

    def soup_roster_extract(self, team_page, path_roster=None, local=False, write_soup=False):
        team_id = team_page.split('/')[-2]
        if path_roster is not None and local:
            soup = BeautifulSoup(open(os.path.join(path_roster, f'{self.year}_{team_id}_roster.htm')), 'html.parser')
        else:
            roster_url = team_page.replace('.htm', '_roster.htm')
            pg = request.urlopen(roster_url)
            soup = BeautifulSoup(pg, 'html.parser')
            if write_soup and path_roster is not None:
                name = f'{self.year}_{team_id}_roster.htm'
                self.save_soup(soup, path_roster, name)
        self.soup_roster = soup

    def soup_injuries_extract(self, team_page, path_injuries=None, local=False, write_soup=False):
        team_id = team_page.split('/')[-2]
        if path_injuries is not None and local:
            soup = BeautifulSoup(open(os.path.join(path_injuries, f'{self.year}_{team_id}_injuries.htm')),
                                 'html.parser')
        else:
            injuries_url = team_page.replace('.htm', '_injuries.htm')
            pg = request.urlopen(injuries_url)
            soup = BeautifulSoup(pg, 'html.parser')
            if write_soup and path_injuries is not None:
                name = f'{self.year}_{team_id}_injuries.htm'
                self.save_soup(soup, path_injuries, name)
        self.soup_injuries = soup

    @property
    def draft(self):
        if self.soup_draft is None:
            raise AttributeError('soup_draft does not exist, first run soup_draft method')
        else:
            draft_div = self.soup_draft.find('div', {'id': 'all_drafts'})
        rows = draft_div.find_all('tr')[2:]
        draft_list = []
        for row_cont in rows:
            row = row_cont.contents
            draft_dict = {}
            if row[0].name is not None:
                for col in row[:-2]:
                    draft_dict[col['data-stat']] = col.string
                    if col.string is None:
                        draft_dict[col['data-stat']] = 0
                draft_dict['player_id'] = row[3].a['href'].split('/')[-1].split('.')[0]
                if row[-1].a is not None:
                    draft_dict['college_stats_link'] = row[-1].a['href']
                else:
                    draft_dict['college_stats_link'] = None
                draft_dict['college_name'] = row[-2].string
                draft_dict['college_id'] = row[-2].a['href'].split('/')[-2]
                draft_list.append(draft_dict)
        return draft_list

    def team_stats(self):
        div = self.soup_team.find('div', {'id': 'all_team_stats'})
        rows = div.find_all('tr')[2:4]
        stat_list = []
        for row_cont in rows:
            cont = row_cont.contents
            stat_dict = {}
            for i in cont:
                if i.string is None:
                    stat_dict[i['data-stat']] = 0
                elif re.search('[:a-zA-Z]', i.string) is None:
                    stat_dict[i['data-stat']] = float(i.string)
                elif i['data-stat'] == 'start_avg':
                    start_avg_str = cont[-5].string.split()
                    stat_dict['start_avg'] = float(start_avg_str[-1])
                    if start_avg_str[0].find('Own') > -1:
                        stat_dict['start_avg'] += 50
                elif i['data-stat'] == 'time_avg':
                    time_avg_str = cont[-4].string.split(':')
                    stat_dict['time_avg_sec'] = int(time_avg_str[0]) * 60 + int(time_avg_str[1])
            stat_list.append(stat_dict)
        return stat_list

    def team_game_results(self):
        div = self.soup_team.find('div', {'id': 'all_games'})
        rows = div.find_all('tr')[2:]
        stat_list = []
        for row_cont in rows:
            cont = row_cont.contents
            if cont[1].string is not None:
                stat_dict = {}
                for i in cont:
                    if i.string is None:
                        stat_dict[i['data-stat']] = 0
                    elif i['data-stat'] == 'boxscore_word':
                        stat_dict['game_url'] = self.bs_pg + i.a['href']
                    elif i['data-stat'] == 'opp':
                        stat_dict['opp_name'] = i.string
                        stat_dict['opp_id'] = i.a['href'].split('/')[-2]
                    else:
                        stat_dict[i['data-stat']] = i.string
                stat_list.append(stat_dict)
        return stat_list

    def team_conversion(self):
        div = self.soup_team.find('div', {'id': 'all_team_conversions'})
        rows = div.find_all('tr')[2:4]
        stat_list = []
        for row_cont in rows:
            cont = row_cont.contents
            stat_dict = {}
            for i in cont:
                if i.string is None:
                    stat_dict[i['data-stat']] = 0
                else:
                    stat_dict[i['data-stat']] = i.string
            stat_list.append(stat_dict)
        return stat_list


