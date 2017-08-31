'''
Requires python-chess
Needs stockfish.exe	and fics.pgn on path
'''

import chess.pgn
import random
import chess.uci
import chess.polyglot

def getnextgame(ofst):
	rnd = random.randrange(100)
	result = '1/2-1/2'
	game = 0
	while result == '1/2-1/2':
		for i in range(rnd+1):
			index = next(ofst)
		pgn.seek(index)
		game = chess.pgn.read_game(pgn)
		result = game.headers["Result"]
	return game, result

print('opening book...')
book = chess.polyglot.open_reader("gm2001.bin")

print('opening games...')
pgn = open("C:/Users/baole/Downloads/fics.pgn")
offset = (x for x in chess.pgn.scan_offsets(pgn))

print('finding game to shadow...')
game, result = getnextgame(offset)
header = game.headers
print(header['White']+'('+header['WhiteElo']+')', 'vs', header['Black']+'('+header['BlackElo']+')')

winner = result=='1-0'

print('initializing engine...')
engine = chess.uci.popen_engine("stockfish")
info_handler = chess.uci.InfoHandler()
engine.info_handlers.append(info_handler)

node = game
totalmoves=0
correctmoves=0
totaldiff=0
thinktime = 5000
print('start shadowing game...')
while not node.is_end():
	next_node = node.variations[0]
	next_move = node.board().san(next_node.move)
	if winner==node.board().turn:
		book_moves = [x.move() for x in book.find_all(node.board())]
		print(node.board())
		user_move = None
		book_move = False
		while not user_move:
			print('your move> ', end='')
			res = input()
			try:
				user_move = node.board().parse_san(res)
			except ValueError:
				user_move = None
			if not user_move:
				print('** illegal move:', res)
				
		correct = False
		if user_move in book_moves:
			print('** you made a book move.')
			book_move = True
			correct = True
			correctmoves += 1
			
		totalmoves += 1
		user_score = 0
		if res==next_move:
			print('** your move was same as the game move.')
			correct = True
			correctmoves += 1
		else:
			print('** you made a different move from the game:', next_move)
			if not book_move:
				# evaluate user move
				print('** evaluating your move', res, '...')
				brd = node.board()
				brd.push(user_move)
				engine.position(brd)
				engine.go(movetime=thinktime)
				print('Your move PV:', brd.variation_san(info_handler.info["pv"][1]))
				brd.pop()
				user_score = info_handler.info["score"][1][0]
		node = next_node
		if not correct:
			print('** evaluating game move',next_move,'...')
			engine.position(node.board())
			engine.go(movetime=thinktime)
			game_score = info_handler.info["score"][1][0]
			diff = user_score - game_score
			if diff>=0:
				print('** good move!')
				correctmoves += 1
			totaldiff += diff
			print('Score:',diff , '('+str(user_score),'-',str(game_score)+')','total:',totaldiff)
	else:
		print('opponent move:', next_move)
		node = next_node

print(node.board())
print('** game ended!', result)
print('Score', totaldiff, 'Correct:', str(correctmoves)+'/'+str(totalmoves))

engine.quit()
