import requests
import getpass
import os, re
from bs4 import BeautifulSoup
from models import db, Team, Player

class ZuluruSync:
    def __init__(self):
        self.base_url = 'https://www.ocua.ca/zuluru'
        self.login_url = 'https://www.ocua.ca/user/login'
        self.league_path = self.base_url + '/leagues/view/league:'
        self.team_path = self.base_url + '/teams/view/team:'

        self.team_id_preamble = 'teams_team_'
        self.player_id_preamble = 'people_person_'


    def sync_teams(self, league_id):
        session = self.login()

        print('Fetching Teams')
        team_ids = self.get_team_ids(session, league_id)

        for x in team_ids:
            self.sync_team(session, x)


    def get_team_ids(self, session, league_id):
        soup = self.get_soup(session, self.league_path + str(league_id))
        ids = [int(x.get('id').replace(self.team_id_preamble, '')) for x in \
               soup.findAll(id=re.compile(self.team_id_preamble + '\d+'))]
        return ids


    def sync_team(self, session, zuluru_id):
        soup = self.get_soup(session, self.team_path + str(zuluru_id))
        name = soup.findAll('h2')[-1].get_text()

        team = self.update_or_create_team(zuluru_id, name)

        self.reset_team_players(team)
        self.sync_players(soup, team)


    def reset_team_players(self, team):
        for current_player in Player.query.filter_by(team_id=team.id):
            current_player.team_id = None
            db.session.add(current_player)

        db.session.commit()


    def sync_players(self, soup, team):
        player_elems = soup.findAll(id=re.compile(self.player_id_preamble + '\d+'))

        if not player_elems:
            print('No players found. Login probably failed.')
            return

        table = soup.find('table', {'class': 'list'})

        genders_regex = '(Male|Female)'
        gender_elems = table.findAll(text=re.compile(genders_regex))
        assert(len(player_elems) == len(gender_elems))

        roles_regex = '(Regular player|Rules keeper|Captain$|Assistant captain|Non-playing coach)'
        role_elems = table.findAll(text=re.compile(roles_regex))
        assert(len(player_elems) == len(role_elems))

        for p,r,g in zip(player_elems, role_elems, gender_elems):
            if r == 'Non-playing coach':
                continue

            zuluru_id = int(p.get('id').replace(self.player_id_preamble, ''))
            name = p.get_text()
            gender = 'male' if g == 'Male' else 'female'
            self.update_or_create_player(zuluru_id, name, gender, team)


    def update_or_create_team(self, zuluru_id, name):
        instance = Team.query.filter_by(zuluru_id=zuluru_id).first()

        if instance:
            print('Found Team: ', name)
        else:
            print('Creating Team: ', name)
            instance = Team(zuluru_id=zuluru_id)

        instance.name = name

        db.session.add(instance)
        db.session.commit()

        return instance


    def update_or_create_player(self, zuluru_id, name, gender, team):
        instance = Player.query.filter_by(zuluru_id=zuluru_id).first()

        if instance:
            print('Found Player: ', name)
        else:
            print('Creating Player: ', name)
            instance = Player(zuluru_id=zuluru_id)

        instance.name = name
        instance.gender = gender
        instance.team_id = team.id

        db.session.add(instance)
        db.session.commit()


    def login(self):
        username = os.environ.get('ZULURU_USER') or self.get_user()
        password = os.environ.get('ZULURU_PASSWORD') or getpass.getpass()

        # Extract nonce
        session = requests.Session()
        soup = self.get_soup(session, self.login_url)
        nonce = soup.find(attrs={'name':'form_build_id'}).get('value')

        # Authenticate
        login_data = {
            'name':  username,
            'pass':  password,
            'form_build_id': nonce,
            'form_id': 'user_login',
            'op': 'log_in'
        }

        print('Logging in')
        r = session.post(self.login_url, data=login_data)
        return session


    def get_user(self):
        print('Username:')
        return input()


    def get_soup(self, session, url):
        return BeautifulSoup(session.get(url).text, 'html.parser')
