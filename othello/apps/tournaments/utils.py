import random


def chunks(v, n):
    for i in range(0, len(v), n):
        yield v[i: i + n]


def make_pairings(players, bye_player):
    matches = []
    players = sorted(players, key=lambda x: -x.ranking)

    for i in range(0, len(players), 2):
        if i + 1 > len(players):
            players.append(bye_player)
        black = random.choice((players[i], players[i + 1]))
        white = players[i] if black == players[i + 1] else players[i + 1]
        matches.append((black, white))

    return matches


def get_winners(players):
    first, second, third = (-1, None), (-1, None), (-1, None)
    for player in players:
        r = player.ranking
        if r > first:
            first = (r, player)
        elif r > second:
            second = (r, player)
        elif r > third:
            third = (r, player)

    return first[1], second[1], third[1]
