'''
Requires python-chess
Needs stockfish.exe, games.pgn, book.bin on path

changes
display flipped board for black
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
	print('PlyCount:', game.headers['PlyCount'])
	return game, result

openingnames = open("ecoe.pgn")
def getOpeningName(san):
	openingnames.seek(0)
	game = chess.pgn.read_game(openingnames)
	while game is not None:
		opbrd = game.board()
		line = opbrd.variation_san(game.main_line())
		if san==line:
			break
		game = chess.pgn.read_game(openingnames)
		
	if game==None:
		return ''
		
	blkname = game.headers['Black']
	name = (' (' + blkname + ')') if blkname!='?' else ''
	return game.headers['White'] + name

print('opening book...')
book = chess.polyglot.open_reader("book.bin")

print('opening games...')
pgn = open("games.pgn")
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
constboard = chess.Board()

print('start shadowing game...')
while not node.is_end():
	next_node = node.variations[0]
	next_move = node.board().san(next_node.move)
	if winner==node.board().turn:
		book_moves = [x.move() for x in book.find_all(node.board())]
		if node.board().turn:
			print(node.board())
		else:
			print(str(node.board())[::-1])
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
			brd = node.board()
			brd.push(user_move)
			openingname = getOpeningName(constboard.variation_san(brd.move_stack))
			brd.pop()
			print('** you made a book move:', openingname)
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
			else:
				brd = node.board()
				brd.push(next_node.move)
				openingname = getOpeningName(constboard.variation_san(brd.move_stack))
				brd.pop()
			print('** you made a different move from the game:', next_move+':'+openingname)
				
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
		node = next_node
		openingname = getOpeningName(constboard.variation_san(node.board().move_stack))
		print('opponent move:', next_move+":"+openingname)

print(node.board())
print('** game ended!', result)
print('Score', totaldiff, 'Correct:', str(correctmoves)+'/'+str(totalmoves))

engine.quit()
