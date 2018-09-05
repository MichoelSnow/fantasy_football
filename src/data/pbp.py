import urllib
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
import argparse





def pbp_export(yr, wk, slp_tm=3):
    games_list = pbp_list(yr, wk)
    df = pd.DataFrame.from_dict(games_list)
    df.to_csv(f'{yr}_wk{wk}.csv', index=False)


def pbp_list(yr, wk, slp_tm=3):
    games_list = []
    gurls = game_urls(yr,wk)
    for gurl in gurls:
        pbp = pbp_extract(gurl, yr, wk)
        games_list += pbp
        time.sleep(slp_tm)
    return games_list


def game_urls(yr,wk):
    bs_pg = 'https://www.pro-football-reference.com/years/'
    pg_url = f'{bs_pg}{yr}/week_{wk}.htm'
    pg = urllib.request.urlopen(pg_url)
    soup = BeautifulSoup(pg, 'html.parser')
    summ = soup.find('div',{'class':'game_summaries'})
    links = summ.find_all('td',{'class':'gamelink'})
    game_urls = []
    game_urls_bs = 'https://www.pro-football-reference.com/'
    for game in links:
        game_str = game.a['href']
        game_urls.append(f'{game_urls_bs}{game_str}')
    return game_urls


def pbp_extract(pg_url, yr, wk):
    pg = urllib.request.urlopen(pg_url)
    soup = BeautifulSoup(pg, 'html.parser')
    header = soup.find('h1').string.split(' -')[0]
    header = header.split(' at ')
    comments=soup.find_all(string=lambda text:isinstance(text,Comment))
    for v in comments:
        if v.find("div_pbp") > -1:
            break
    table = BeautifulSoup(str(v), 'lxml')
    rows = table.find_all('tr')
    quarter = 1
    pbp = []
    for row in rows[1:]:
        tmp_dict = {}
        cells = row.find_all('td')
        if len(cells) == 1:
            try:
                quarter = int(cells[0].string[0])
            except:
                quarter = cells[0].string
        else:
            for cell in cells:
                if cell['data-stat'] == 'detail':
                    val =  ''.join([x.string for x in cell.contents if x.string is not None])
                    tmp_dict[cell['data-stat']] = val
                else:
                    val = cell.string
                    try:
                        tmp_dict[cell['data-stat']] = float(val)
                    except:
                        tmp_dict[cell['data-stat']] = val
            tmp_dict['quarter'] = quarter
            tmp_dict['year'] = yr
            tmp_dict['week'] = wk
            tmp_dict['away_team'] = header[0]
            tmp_dict['home_team'] = header[1]
            pbp.append(tmp_dict)
    return pbp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--year", help="season")
    parser.add_argument("-w", "--week", help="week")
    parser.add_argument("-s", "--sleep_time", help="The number of seconds to break between each webpage crawl",
                        type=int, default=3)
    args = parser.parse_args()
    pbp_export(yr=args.year, wk=args.week, slp_tm=args.sleep_time)

