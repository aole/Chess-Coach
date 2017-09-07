'''
Requires python-chess
Needs games.pgn, book.bin on path

changes
display flipped board for black
'''

import chess.pgn
import random
import chess.uci
import chess.polyglot

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QFrame, QAction, QMainWindow
from PyQt5.QtGui import QPixmap, QDrag
from PyQt5.QtCore import Qt, QMimeData, QSize

rank1=0
rank4=3
filea=0
filed=3
filee=4

class Piece(QLabel):
	rank = file = 0
	
	def __init__(self, text, parent):
		super().__init__(text, parent)
		self.parent = parent
		#self.setFrameShape(QFrame.Panel)
		#self.setLineWidth(1)
		self.setAlignment(Qt.AlignCenter)
		#self.pixmap = QPixmap('piece.png')
		#self.setPixmap(self.pixmap)

	def mousePressEvent(self, e):
		self.__mousePressPos = None
		self.__mouseMovePos = None
		self.__mousePressPos = e.globalPos()
		self.__mouseMovePos = e.globalPos()

		super().mousePressEvent(e)

	def mouseMoveEvent(self, e):
		# adjust offset from clicked point to origin of widget
		currPos = self.mapToGlobal(self.pos())
		globalPos = e.globalPos()
		diff = globalPos - self.__mouseMovePos
		newPos = self.mapFromGlobal(currPos + diff)
		self.move(newPos)

		self.__mouseMovePos = globalPos

		super().mouseMoveEvent(e)

	def mouseReleaseEvent(self, e):
		if self.__mousePressPos is not None:
			moved = e.globalPos() - self.__mousePressPos 
			if moved.manhattanLength() > 3:
				try:
					self.parent.drop(self, e.pos()+self.pos())
				except Exception as ex:
					print(ex)
				e.ignore()
				return
				
		super().mouseReleaseEvent(e)

	def scale(self, sx, sy):
		self.resize( sx, sy )
		#self.pixmap = self.pixmap.scaled(QSize(sx,sy),Qt.KeepAspectRatio)
		#self.setPixmap(self.pixmap)
	
class App(QMainWindow):
	# board dimension in pixels
	bpx = 800
	bpy = 800
	# margin
	mx = my = 20
	# cell size
	cx = (bpx-mx*2)/8
	cy = (bpy-my*2)/8
	
	def __init__(self):
		super().__init__()
		self.piece_refs = []
		self.init_ui()
	
	def init_ui(self):
		self.statusBar()
		self.statusBar().showMessage('Ready')
		
		act = QAction("shadow..", self)
		act.triggered.connect(self.shadow)
		
		mm = self.menuBar()
		fm = mm.addMenu('&File')
		fm.addAction(act)
		'''
		label = QLabel(self)
		pixmap = QPixmap('test.jpg')
		label.setPixmap(pixmap)
		'''
		self.board = chess.Board()
		#self.setup_board(self.board)
		
		self.resize(self.bpx, self.bpy)
		self.setWindowTitle('Oracle')
		self.show()
	
	def shadow(self):
		print('shadow')
		
	def setup_board(self, board):
		for pc in self.piece_refs:
			pc.setParent(None)
		self.piece_refs.clear()
		for s in chess.SQUARES:
			p = board.piece_at(s)
			if p:
				sym = p.unicode_symbol()
				piece = Piece(sym, self)
				piece.scale(self.cx, self.cy)
				self.place_piece(piece, chess.square_rank(s), chess.square_file(s))
				self.piece_refs.append(piece)
				piece.show()
		
	def drop(self, piece, pos):
		x = int((pos.x()-self.mx) / self.cx)
		if x<0:
			x=0
		if x>7:
			x=7
		file = x
		y = int((pos.y()-self.my) / self.cy)
		if y<0:
			y=0
		if y>7:
			y=7
		rank = 7-y
		
		ucimove = chess.FILE_NAMES[piece.file]+\
			chess.RANK_NAMES[piece.rank]+\
			chess.FILE_NAMES[file]+\
			chess.RANK_NAMES[rank]
		move = chess.Move.from_uci(ucimove)
		if move in self.board.legal_moves:
			self.board.push(move)
		print(self.board)
		self.setup_board(self.board)
		self.update()
		'''
		x *= self.cx
		y *= self.cy
		piece.move(x+self.mx, y+self.my)
		'''
		
	def place_piece(self, piece, rank, file):
		piece.rank = rank
		piece.file = file
		x = file * self.cx + self.mx
		y = (7-rank) * self.cy + self.my
		piece.move(x, y)

	def piece_location(self, piece):
		x = int((piece.pos().x()-self.mx) / self.cx)
		y = int((piece.pos().y()-self.my) / self.cy)
		return chess.FILE_NAMES[x], chess.RANK_NAMES[7-y]
	
if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = App()
	sys.exit(app.exec_())

def getnextgame(ofst):
	rnd = random.randrange(100)
	result = '1/2-1/2'
	game = 0
	while result == '1/2-1/2':
		for i in range(rnd+1):
			index = next(ofst)
		pgn.seek(index)
		game = chess.pgn.read_game(pgn)
		result = game.headers["Result"] if int(game.headers['PlyCount'])>10 else '1/2-1/2'		
	print('PlyCount:', game.headers['PlyCount'], 'Result:', result)
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
exit_game = False

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
			if res=='exit':
				exit_game = True
				break
			try:
				user_move = node.board().parse_san(res)
			except ValueError:
				user_move = None
			if not user_move:
				print('** illegal move:', res)
		
		if exit_game:
			break
			
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
