from flask import Flask, request, jsonify, send_from_directory
from flask_caching import Cache

from models import db, Game, Stats, Team, Player
from upload import StatsCalculator

import os
import json
import datetime

debug = False

client_path = '../client/build'

one_hour = 3600 # seconds
cache_timeout = one_hour

def create_app():
    app = Flask(__name__, static_folder=client_path)
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})

    if os.environ.get('APP_SETTINGS') == None:
        os.environ['APP_SETTINGS'] = 'config.DevelopmentConfig'

    app.config.from_object(os.environ['APP_SETTINGS'])
    db.init_app(app)


    # Upload
    @app.route('/upload', methods=['POST'])
    def upload():
        game = Game()

        # save response to file if debugging
        if debug:
            now = datetime.datetime.now()
            fo = open('data/test/' + str(now) + '.json', 'w')
            fo.write(json.dumps(request.json, indent=2, sort_keys=True))
            fo.close()

        # save the game to the database
        game.league = request.json['league']
        game.week = request.json['week']

        game.home_team = request.json['homeTeam']
        game.away_team = request.json['awayTeam']

        game.home_score = request.json['homeScore']
        game.away_score = request.json['awayScore']

        game.home_roster = json.dumps(request.json['homeRoster'])
        game.away_roster = json.dumps(request.json['awayRoster'])

        points = request.json['points']
        game.points = json.dumps(points)

        db.session.add(game)
        db.session.commit()

        # calculate and save stats
        stats = StatsCalculator(game.id, points).run()
        for stat in stats:
            db.session.add(stat[1])
        db.session.commit()

        # clear the stats cache
        cache.clear()

        return ('', 201)


    # API
    @app.route('/api/teams')
    def teams():
        teams = {}
        for team in Team.query.all():
            teams[team.name] = {
                'players': [],
                'malePlayers': [],
                'femalePlayers': []
            }
            for player in Player.query.filter_by(team_id=team.id):
                teams[team.name]['players'].append(player.name)
                if player.is_male:
                    teams[team.name]['malePlayers'].append(player.name)
                else:
                    teams[team.name]['femalePlayers'].append(player.name)

        return jsonify(teams)


    @app.route('/api/weeks')
    def weeks():
        query = db.session.query(Game.week.distinct().label("week"))
        weeks = [row.week for row in query.all()]
        return jsonify(sorted(weeks))


    @app.route('/api/weeks/<num>')
    def week(num):
        games = Game.query.filter_by(week=num)
        stats = build_stats_response(games)
        return jsonify({"week": num, "stats": stats})


    @app.route('/api/stats')
    def stats():
        games = Game.query.order_by("week asc")
        stats = build_stats_response(games, is_all=True)
        return jsonify({"week": 0, "stats": stats})


    @cache.cached(timeout=cache_timeout)
    def build_stats_response(games, is_all=False):
        present_players = set()
        stats = {}

        # rollup stats per game
        for game in games:
            [ present_players.add(player_name) for player_name in game.players ]

            for player_stats in Stats.query.filter_by(game_id=game.id):
                player = Player.query.get(player_stats.player_id)
                present_players.add(player.name)
                data = player_stats.to_dict()

                # sum all stats for the player
                if player.name in stats:
                    existing_data = stats[player.name]
                    stats_to_average = ['pay', 'salary_per_point', 'o_efficiency', 'd_efficiency', 'total_efficiency']
                    stats_to_sum = data.keys() - stats_to_average
                    summed_stats = { s: data.get(s, 0) + existing_data.get(s, 0) for s in stats_to_sum }
                    stats[player.name].update(summed_stats)
                    averaged_stats = { s: data.get(s, 0) + existing_data.get(s, 0) for s in stats_to_average }
                    stats[player.name].update(averaged_stats)
                else:
                    stats.update({player.name: data})

                # set the team for the player
                if is_all:
                    if player.team_id:
                        team = Team.query.get(player.team_id).name
                    else:
                        team = "Substitute"
                else:
                    if "(S)" in player.name:
                        team = "Substitute"
                    elif player.name in json.loads(game.home_roster):
                        team = game.home_team
                    elif player.name in json.loads(game.away_roster):
                        team = game.away_team
                    elif player.team_id:
                        team = Team.query.get(player.team_id).name
                    else:
                        team = 'Unknown'

                stats[player.name].update({'team': team})

                # set the salary for the player
                stats[player.name].update({'salary': player.salary})


        # handle absent players
        players = Player.query.filter(Player.team_id != None)
        absent_players = [player for player in players if player.name not in present_players]

        for player in absent_players:
            game_id = -1
            player_stats = Stats(game_id, player.id).to_dict()
            player_stats.update({'team': player.team.name})

            if player.salary > 0:
                player_stats.update({'salary': player.salary})
            else:
                team_players = Player.query.filter_by(team_id=player.team_id)
                same_gender_salaries = [p.salary for p in team_players if p.is_male == player.is_male and p.salary > 0]
                avg_salary = sum(same_gender_salaries) / len(same_gender_salaries)
                player_stats.update({'salary': avg_salary})

            stats[player.name] = player_stats


        return stats


    @app.route('/api/games')
    def games():
        games = []
        for game in Game.query.all():
            games.append(game.to_dict())

        return jsonify(games)


    @app.route('/api/games/<id>')
    def game(id):
        game = Game.query.get(id)
        return jsonify(game.to_dict(include_points=True))


    # Client
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def client(path):
        if(path == ""):
            return send_from_directory(client_path, 'index.html')
        else:
            if(os.path.exists(client_path + '/' + path)):
                return send_from_directory(client_path, path)
            else:
                return send_from_directory(client_path, 'index.html')

    return app


# Development Server
if __name__ == '__main__':
    os.environ['APP_SETTINGS'] = 'config.DevelopmentConfig'

    app = create_app()

    if app.config.get('DEVELOPMENT'):
        with app.app_context():
            db.create_all()

    app.run(use_reloader=True)
