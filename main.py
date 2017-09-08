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
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QFrame, QAction, QMainWindow, QPushButton
from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QListWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap, QDrag, QPainter, QPaintEvent
from PyQt5.QtCore import Qt, QMimeData, QSize

class QGame(QWidget):
	from_square = -1
	mouseMovePos = None
	offsetx = offsety = 0
	
	def __init__(self, parent, game):
		super().__init__(parent)
		
		self.piece_refs = []
		self.pixmap = QPixmap('test.jpg')
		self.game = game
		self.board = game.board()
		#moves = game.main_line()
		#print(self.board.variation_san(moves))
		
	def paintEvent(self, e):
		w = self.width()
		h = self.height()
		self.cx = w/8
		self.cy = h/8
		
		painter = QPainter(self)
		painter.drawPixmap(0,0, w, h, self.pixmap)
		try:
			self.setup_board(self.board, w, h)
		except Exception as ex:
			print(ex)
		
	def setup_board(self, board, w, h):
		for pc in self.piece_refs:
			pc.setParent(None)
		self.piece_refs.clear()
		painter = QPainter(self)
		for s in chess.SQUARES:
			p = board.piece_at(s)
			if p:
				if s==self.from_square and self.mouseMovePos:
					x = self.mouseMovePos.x()-self.offsetx
					y = self.mouseMovePos.y()-self.offsety
				else:
					x = self.cx * chess.square_file(s)
					y = self.cy * (7-chess.square_rank(s))
				sym = p.unicode_symbol()
				painter.drawText(x,y,self.cx,self.cy,Qt.AlignCenter, sym)
		
	def mousePressEvent(self, e):
		self.mouseMovePos = e.pos()
		x = int(e.pos().x() / self.cx)
		self.offsetx = e.pos().x() - x*self.cx
		y = int(e.pos().y() / self.cy)
		self.offsety = e.pos().y() - y*self.cy
		y = 7-y
		self.from_square = y*8+x if y>=0 and y<8 and x>=0 and x<8 else -1
		p = self.board.piece_at(self.from_square)
		
		super().mousePressEvent(e)
		self.update()
		

	def mouseMoveEvent(self, e):
		self.mouseMovePos = e.pos()
		
		super().mouseMoveEvent(e)
		self.update()

	def mouseReleaseEvent(self, e):
		if self.from_square>=0:
			x = int(e.pos().x() / self.cx)
			y = int(8-e.pos().y() / self.cy)
			
			if y>=0 and y<8 and x>=0 and x<8:
				ucimove = chess.FILE_NAMES[chess.square_file(self.from_square)]+\
					chess.RANK_NAMES[chess.square_rank(self.from_square)]+\
					chess.FILE_NAMES[x]+\
					chess.RANK_NAMES[y]
				self.parent().user_move(self, ucimove)

		super().mouseReleaseEvent(e)
		self.from_square = -1
		self.update()

class Game(QListWidgetItem):
	def __init__(self, offset, header):
		super().__init__(header['White']+' vs '+header['Black']+' ['+header['Result']+']')
		self.offset = offset
		self.header = header

class App(QMainWindow):
	# board dimension in pixels
	bpx = 800
	bpy = 800
	
	def __init__(self):
		super().__init__()
		self.init_ui()
	
	def init_ui(self):
		self.statusBar()
		self.statusBar().showMessage('Ready')
		
		act = QAction("shadow..", self)
		act.triggered.connect(self.shadow)
		
		mm = self.menuBar()
		fm = mm.addMenu('&File')
		fm.addAction(act)
		
		self.board = chess.Board()
		#self.qboard = QBoard(self, pixmap, self.board)
		#self.setCentralWidget(self.qboard)
		self.games_list = QListWidget()
		self.games_list.itemDoubleClicked.connect(self.on_game_create)
		
		self.tabs = QTabWidget()
		self.tabs.addTab(self.games_list, "List")
		self.setCentralWidget(self.tabs)
		
		self.resize(self.bpx, self.bpy)
		self.setWindowTitle('Oracle')
		self.show()
	
	def piece_location(self, piece):
		x = int((piece.pos().x()-self.mx) / self.cx)
		y = int((piece.pos().y()-self.my) / self.cy)
		return chess.FILE_NAMES[x], chess.RANK_NAMES[7-y]
	
	def user_move(self, brd, ucimove):
		move = chess.Move.from_uci(ucimove)
		if move in brd.board.legal_moves:
			brd.board.push(move)
		print(brd.board)
		
	def shadow(self):
		try:
			fileName, _ = QFileDialog.getOpenFileName(self, 'Get File',None,'PGN (*.pgn)')
			if fileName:
				count=1
				self.pgn_file = open(fileName)
				self.games_list.clear()
				for offset, header in chess.pgn.scan_headers(self.pgn_file):
					game = Game(offset, header)
					self.games_list.addItem(game)
					count += 1
				self.update()
		except Exception as ex:
			print(ex)

	def on_game_create(self, curr):
		self.pgn_file.seek(curr.offset)
		game = chess.pgn.read_game(self.pgn_file)
		self.tabs.addTab(QGame(self, game), curr.text())

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
