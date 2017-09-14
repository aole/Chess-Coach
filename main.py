"""
Requires python-chess

"""

import sys

from threading import Thread
import chess.pgn
import chess.polyglot
import chess.uci
from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QAction, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QTabWidget, QFileDialog, QListWidget, QListWidgetItem, QLabel

PIECE_IMAGE_INDEX = [0, 5, 3, 2, 4, 1, 0]

show_ascii = True

class QGame(QWidget):
	from_square = -1
	mouseMovePos = None
	offset_x = offset_y = 0
	can_move = False
	winner = True
	thread = None
	engine_busy = False
	total_score = 0

	def __init__(self, parent, chess_game):
		super().__init__(parent)

		self.lbltimer = QLabel('test', self)
		
		self.width = self.width()
		self.height = self.height() - self.lbltimer.height()
		self.cx = self.width / 8
		self.cy = self.height / 8

		self.parent = parent
		if show_ascii:
			self.board_map = QPixmap('test.jpg')
		else:
			self.board_map = QPixmap('chess_board.png')
		temp_map = QImage('chess_pieces.png')
		pcx = temp_map.width() / 6
		pcy = temp_map.height() / 2
		self.piece_map = []
		for y in range(2):
			for x in range(6):
				self.piece_map.append(temp_map.copy(int(x * pcx), int(y * pcy), int(pcx), int(pcy)))

		self.game = chess_game
		self.node = chess_game
		self.board = chess_game.board()

		result = chess_game.headers['Result']
		if result =='0-1':
			self.winner = False

		self.can_move = self.board.turn==self.winner
		if not self.can_move:
			game_move = self.get_next_game_move()
			self.parent.add_message('Opponent move: ' + self.board.san(game_move))
			self.make_move(game_move)
			
		self.parent.add_message('**** Make move for '+('white' if self.board.turn else 'black'))
		
		self.timer = QTime()
		self.timer.start()
		
	# moves = game.main_line()
	# print(self.board.variation_san(moves))

	def elapsed(self):
		return self.timer.elapsed()

	def resizeEvent(self, e):
		self.width = e.size().width()
		self.height = e.size().height() - self.lbltimer.height()
		self.cx = self.width / 8
		self.cy = self.height / 8

	def paintEvent(self, e):
		painter = QPainter(self)
		painter.drawPixmap(0, self.lbltimer.height(), self.width, self.height, self.board_map)
		try:
			self.setup_board(self.board, False)
		except Exception as ex:
			print(ex)

	def setup_board(self, board, flip):
		painter = QPainter(self)
		for s in chess.SQUARES:
			p = board.piece_at(s)
			if p:
				if s == self.from_square and self.mouseMovePos:
					x = self.mouseMovePos.x() - self.offset_x
					y = self.mouseMovePos.y() - self.offset_y + self.lbltimer.height()
				else:
					x = self.cx * ((7 - chess.square_file(s)) if flip else chess.square_file(s))
					y = self.cy * (chess.square_rank(s) if flip else (7 - chess.square_rank(s))) + self.lbltimer.height()
				if show_ascii:
					sym = p.unicode_symbol()
					painter.drawText(x,y,self.cx,self.cy,Qt.AlignCenter, sym)
				else:
					piece_index = PIECE_IMAGE_INDEX[p.piece_type] + (0 if p.color else 6)
					img = QImage.scaled(self.piece_map[piece_index], self.cx, self.cy, Qt.KeepAspectRatio)
					painter.drawImage(x, y, img)

	def mousePressEvent(self, e):
		if self.can_move:
			self.mouseMovePos = e.pos()
			x = int(e.pos().x() / self.cx)
			self.offset_x = e.pos().x() - x * self.cx
			y = int((e.pos().y() - self.lbltimer.height()) / self.cy)
			self.offset_y = e.pos().y() - y * self.cy
			y = 7 - y
			self.from_square = (y * 8 + x) if (0 <= y < 8 and 0 <= x < 8) else -1

		super().mousePressEvent(e)
		self.update()

	def mouseMoveEvent(self, e):
		self.mouseMovePos = e.pos()

		super().mouseMoveEvent(e)
		self.update()

	def mouseReleaseEvent(self, e):
		if self.from_square >= 0:
			x = int(e.pos().x() / self.cx)
			y = int(8 - e.pos().y() / self.cy)

			if 0 <= y < 8 and 0 <= x < 8:
				uci_move = chess.FILE_NAMES[chess.square_file(self.from_square)] + \
						   chess.RANK_NAMES[chess.square_rank(self.from_square)] + \
						   chess.FILE_NAMES[x] + \
						   chess.RANK_NAMES[y]
				# user made a move
				try:
					self.user_moved(uci_move)
				except Exception as ex:
					print(ex)

		super().mouseReleaseEvent(e)
		self.from_square = -1
		self.update()

	# process user move
	def user_moved(self, uci_move):
		move = chess.Move.from_uci(uci_move)
		
		# is it a legal move?
		if move in self.board.legal_moves:
			#self.parent.add_message('You made the move: ' + self.board.san(move))
			self.compare_user_move_with_game(move)
			# make opponents move
			if not self.can_move:
				# make the next game move as well
				game_move = self.get_next_game_move()
				self.parent.add_message('Opponent move: ' + self.board.san(game_move))
				self.make_move(game_move)
				self.parent.add_message('**** Make move for '+('white' if self.board.turn else 'black'))
				self.timer.restart()

	def get_next_game_move(self):
		next_node = self.node.variations[0]
		self.node = next_node
		return next_node.move

	def compare_user_move_with_game(self, move):
		game_move = self.get_next_game_move()
		move_text = self.board.san(move)
		self.parent.add_message('Your move: '+move_text+', Game move: '+self.board.san(game_move))
		is_book_move = self.parent.is_book_move(self.board, move)
		if is_book_move:
			opening_name = self.parent.get_opening_name(self.board)
			self.parent.add_message(move_text+' (Book move '+opening_name+')')
		if move!=game_move and not is_book_move:
			board_copy = self.board.copy()
			self.thread = Thread(target=self.evaluate_moves, args=(board_copy, move, game_move))
			self.thread.start()
		self.make_move(game_move)

	def make_move(self, move):
		self.board.push(move)
		self.can_move = self.board.turn==self.winner

	def evaluate_moves(self, board, user_move, game_move):
		# evaluate move score
		while self.engine_busy:
			pass
		self.engine_busy = True
		evaluation = self.parent.evaluate_moves(board, [user_move, game_move])
		score_diff = evaluation[user_move] - evaluation[game_move]
		self.parent.add_message('Move score ('+board.san(user_move)+' vs '+board.san(game_move)+'): '+ str(score_diff))
		self.total_score += score_diff
		self.parent.add_message('Game score: '+ str(self.total_score))
		
		self.engine_busy = False

	def evaluate(self, board, move):
		# evaluate move score
		while self.engine_busy:
			pass
		self.engine_busy = True
		evaluation = self.parent.evaluate_board(board)
		self.parent.add_message('Position Evaluation ('+move+') '+str(evaluation))
		self.engine_busy = False

class GameListItem(QListWidgetItem):
	def __init__(self, pgn_offset, pgn_header):
		super().__init__(pgn_header['White'] + ' vs ' + pgn_header['Black'] + ' [' + pgn_header['Result'] + ']')
		self.offset = pgn_offset
		self.header = pgn_header

class App(QMainWindow):
	# board dimension in pixels
	bpx = 800
	bpy = 1000

	def __init__(self):
		super().__init__()
		self.init_ui()
		
		self.openings = {}
		
		self.static_board = chess.Board()
		self.add_message('initializing opening book...')
		self.book = chess.polyglot.open_reader("book.bin")
		
		self.thread = Thread(target=self.init_openings)
		self.thread.start()
		
		self.add_message('initializing engine...')
		self.engine = chess.uci.popen_engine("stockfish")
		self.info_handler = chess.uci.InfoHandler()
		self.engine.info_handlers.append(self.info_handler)
		
		self.add_message('Ready')

		self.timer = QTimer()
		self.timer.timeout.connect(self.tick)
		self.timer.start(100)
	
	def tick(self):
		tab = self.tabs.currentWidget()
		try:
			elapsed = tab.elapsed() / 1000
			msg = "{:.2f}".format(elapsed)
			self.statusBar().showMessage(msg)
		except Exception as ex:
			pass
		
	def init_openings(self):
		opening_file = open("ecoe.pgn")
		game = chess.pgn.read_game(opening_file)
		while game is not None:
			chess_board = game.board()
			line = chess_board.variation_san(game.main_line())
			black_player_name = game.headers['Black']
			name = (' (' + black_player_name + ')') if black_player_name != '?' else ''
			self.openings[line] = game.headers['White'] + name
			game = chess.pgn.read_game(opening_file)
		
	def get_opening_name(self, board):
		san = self.static_board.variation_san(board.move_stack)
		if san in self.openings:
			return '- '+self.openings[san]
		return ''
		
	def is_book_move(self, board, move):
		return any(move==x.move() for x in self.book.find_all(board))
		
	def init_ui(self):
		self.statusBar()
		self.statusBar().showMessage('Ready')

		act = QAction("shadow..", self)
		act.triggered.connect(self.shadow)

		mm = self.menuBar()
		fm = mm.addMenu('&File')
		fm.addAction(act)

		self.games_list = QListWidget()
		self.games_list.itemDoubleClicked.connect(self.on_list_dbl_click)

		self.tabs = QTabWidget()
		# self.tabs.setTabsClosable(True)
		self.tabs.addTab(self.games_list, "List")
		self.populate_game_list_from_pgn('games.pgn')

		main_widget = QWidget()
		main_layout = QHBoxLayout(main_widget)
		
		game_msg_widget = QWidget()
		game_msg_layout = QVBoxLayout(game_msg_widget)

		game_msg_layout.addWidget(self.tabs, 2)
		self.msg_list = QListWidget()
		game_msg_layout.addWidget(self.msg_list)

		main_layout.addWidget(game_msg_widget, 2)
		self.check_list = QListWidget()
		self.populate_check_list()
		main_layout.addWidget(self.check_list)
		
		self.setCentralWidget(main_widget)

		#self.resize(self.bpx, self.bpy)
		self.setWindowTitle('Chess Coach')
		self.show()

	def populate_check_list(self):
		file = open('check_list.txt')
		for line in file:
			self.check_list.addItem(line.rstrip())
			
	def piece_location(self, piece):
		x = int((piece.pos().x() - self.mx) / self.cx)
		y = int((piece.pos().y() - self.my) / self.cy)
		return chess.FILE_NAMES[x], chess.RANK_NAMES[7 - y]

	def shadow(self):
		try:
			fileName, _ = QFileDialog.getOpenFileName(self, 'Get File', None, 'PGN (*.pgn)')
			if fileName:
				self.populate_game_list_from_pgn(fileName)
		except Exception as ex:
			print(ex)

	def populate_game_list_from_pgn(self, file_name):
		self.pgn_file = open(file_name)
		self.games_list.clear()
		for offset, header in chess.pgn.scan_headers(self.pgn_file):
			game = GameListItem(offset, header)
			self.games_list.addItem(game)
		self.update()

	def on_list_dbl_click(self, selected_item):
		self.pgn_file.seek(selected_item.offset)
		selected_game = chess.pgn.read_game(self.pgn_file)
		self.tabs.addTab(QGame(self, selected_game), selected_item.text())
		# open the latest tab
		self.tabs.setCurrentIndex(self.tabs.count()-1)
		self.add_message('Shadowing game: '+selected_item.text())

	def add_message(self, msg):
		#self.msg_list.addItem(msg)
		self.msg_list.insertItem(0, msg)

	def evaluate_board(self, board):
		self.engine.setoption({"MultiPV":1})
		self.engine.position(board)
		self.engine.go(movetime=5000)
		return self.info_handler.info["score"][1][0]

	def evaluate_moves(self, board, moves_list):
		self.engine.setoption({"MultiPV":len(moves_list)})
		self.engine.position(board)
		self.engine.go(movetime=5000, searchmoves=moves_list)
		
		moves_score = {}
		for i in range(1, len(self.info_handler.info['pv'])+1):
			moves_score[self.info_handler.info['pv'][i][0]]=self.info_handler.info['score'][i][0]
		return moves_score

	def closeEvent(self, e):
		print('... quitting!')
		self.engine.quit()
		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = App()
	sys.exit(app.exec_())

