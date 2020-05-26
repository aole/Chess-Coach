"""
Requires python-chess

"""

import traceback
import sys
import os
import random

from threading import Thread
import chess
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg

#import chess.uci
from PyQt5.QtCore import Qt, QTime, QTimer, QRectF, QSize
from PyQt5.QtGui import QPixmap, QPainter, QImage, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QAction, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QTabWidget, QFileDialog, QListWidget, QListWidgetItem, QLabel

PIECE_IMAGE_INDEX = [0, 5, 3, 2, 4, 1, 0]

show_ascii = False
#show_ascii = True

class QBoard(QWidget):
    def __init__(self, game):
        super().__init__()
        
        self.board = None
        self.flipped = False
        self.from_square = -1
        self.game = game
        self.mousePressListeners = []
        self.moveListeners = []
        
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
            
    def addMousePressListener(self, listener):
        self.mousePressListeners.append(listener)
        
    def addMoveListener(self, listener):
        self.moveListeners.append(listener)
        
    def setBoard(self, board, flipped=False):
        self.board = board
        self.flipped = flipped
        
    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        
        painter.drawPixmap(0, 0, self.width(), self.height(), self.board_map)
        if self.board:
            self.paint_pieces(painter, self.board, self.flipped)
            
        painter.end()
        
    def paint_pieces(self, painter, board, flip):
        font = painter.font()
        font.setPixelSize(min(self.cx-4, self.cy-4))
        painter.setFont(font)

        last_move = self.game.get_last_move()
        
        for s in chess.SQUARES:
            x = self.cx * ((7 - chess.square_file(s)) if flip else chess.square_file(s))
            y = self.cy * (chess.square_rank(s) if flip else (7 - chess.square_rank(s)))
            
            p = board.piece_at(s)
            if p:
                if s == self.from_square and self.mouseMovePos:
                    x = self.mouseMovePos.x() - self.offset_x
                    y = self.mouseMovePos.y() - self.offset_y
                    
                # center images
                if show_ascii:
                    sym = p.unicode_symbol()
                    painter.drawText(x, y, self.cx, self.cy, Qt.AlignCenter, sym)
                else:
                    piece_index = PIECE_IMAGE_INDEX[p.piece_type] + (0 if p.color else 6)
                    img = QImage.scaled(self.piece_map[piece_index], self.cx, self.cy, Qt.KeepAspectRatio)
                    offset_x = (self.cx-img.width())/2
                    offset_y = (self.cy-img.height())/2
                    painter.drawImage(x+offset_x, y+offset_y, img)
        
            if last_move and (last_move.from_square == s or last_move.to_square == s):
                painter.drawRect(x, y, self.cx, self.cy)
                        
    def mousePressEvent(self, e):
        if self.game.can_move:
            self.mouseMovePos = e.pos()

            x = int(e.pos().x() / self.cx)
            self.offset_x = e.pos().x() - x * self.cx
            x = 7-x if self.flipped else x

            y = int((e.pos().y()) / self.cy)
            self.offset_y = e.pos().y() - y * self.cy
            y = y if self.flipped else 7 - y

            self.from_square = (y * 8 + x) if (0 <= y < 8 and 0 <= x < 8) else -1

        for l in self.mousePressListeners:
            l.mousePressed(self.from_square)
            
        super().mousePressEvent(e)
        self.update()

    def mouseMoveEvent(self, e):
        self.mouseMovePos = e.pos()

        super().mouseMoveEvent(e)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.from_square >= 0:
            x = int(e.pos().x() / self.cx)
            x = 7-x if self.flipped else x
            y = int(8 - (e.pos().y()) / self.cy)
            y = 7 - y if self.flipped else y
            if 0 <= y < 8 and 0 <= x < 8:
                uci_move = chess.FILE_NAMES[chess.square_file(self.from_square)] + \
                           chess.RANK_NAMES[chess.square_rank(self.from_square)] + \
                           chess.FILE_NAMES[x] + \
                           chess.RANK_NAMES[y]
                # user made a move
                try:
                    for l in self.moveListeners:
                        l.userMoved(uci_move)
                except Exception as ex:
                    print(traceback.format_exc())

        super().mouseReleaseEvent(e)
        self.from_square = -1
        self.update()

    def resizeEvent(self, e):
        self.cx = self.width() / 8
        self.cy = self.height() / 8

class TabEmpty(QWidget):
    def __init__(self, parent, caption):
        super().__init__(parent)
        
        self.can_move = True
        
        self.parent = parent
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        if caption==None:
            caption = 'Game Editor'
        self.label_caption = QLabel(caption)
        layout.addWidget(self.label_caption)

        self.boardWidget = QBoard(self)
        layout.addWidget(self.boardWidget, 1)
    
    def get_last_move(self):
        return None
        
class CoordLearn(TabEmpty):
    def __init__(self, parent, caption, gametype, color):
        super().__init__(parent, caption)
        
        self.gametype = gametype
        self.color = color
        
        self.boardWidget.addMousePressListener(self)
        self.boardWidget.setBoard(chess.Board())
        self.boardWidget.flipped = color==1
        
        self.parent.add_message('**** Click anywhere on the board to start.')
        
        self.timer = QTime()
        self.timerStarted = False

    def mousePressed(self, square):
        if not self.timerStarted:
            self.timer.start()
            self.timerStarted = True
            
            self.score = 0
        
            self.rand8 = random.randrange(8)
            self.rand64 = random.randrange(64)
            
            if self.color == 2:
                self.boardWidget.flipped = random.randrange(2)
        else:
            if self.gametype == 0:
                if self.rand8 == square >> 3:
                    self.score += 1
                    self.rand8 = random.randrange(8)
                    if self.color == 2:
                        self.boardWidget.flipped = random.randrange(2)
                else:
                    self.parent.add_message('X: ' + chess.RANK_NAMES[square >> 3])
                    
            elif self.gametype == 1:
                if self.rand8 == square & 7:
                    self.score += 1
                    self.rand8 = random.randrange(8)
                    if self.color == 2:
                        self.boardWidget.flipped = random.randrange(2)
                else:
                    self.parent.add_message('X: ' + chess.FILE_NAMES[square & 7])
                    
            elif self.gametype == 2:
                if chess.SQUARES[self.rand64] == square:
                    self.score += 1
                    self.rand64 = random.randrange(64)
                    if self.color == 2:
                        self.boardWidget.flipped = random.randrange(2)
                else:
                    self.parent.add_message('X: ' + chess.SQUARE_NAMES[square])
            
        self.parent.add_message('Score: ' + str(self.score))
            
        if self.gametype == 0: # RANK
            self.parent.add_message('**** Find Rank: ' + chess.RANK_NAMES[self.rand8])
        elif self.gametype == 1: # File
            self.parent.add_message('**** Find File: ' + chess.FILE_NAMES[self.rand8])
        elif self.gametype == 2: # Square
            self.parent.add_message('**** Find Square: ' + chess.SQUARE_NAMES[self.rand64])
        
    def elapsed(self):
        return self.timer.elapsed()
        
class QGame(TabEmpty):
    # widget type
    # SHADOW = range(2)

    mouseMovePos = None
    offset_x = offset_y = 0
    winner = True
    thread = None
    total_score = 0

    def __init__(self, parent, chess_game=None, caption = None):
        super().__init__(parent, caption)

        self.boardWidget.addMoveListener(self)
        if chess_game==None:
            chess_game = chess.pgn.Game()
            self.board_type = 1
            self.boardWidget.board_type = 1
        else:
            self.board_type = 2
            self.boardWidget.board_type = 2
            
        self.node = chess_game
        self.board = chess_game.board()
        self.last_move = None

        result = chess_game.headers['Result']
        self.flip_board = False
        if result =='0-1':
            self.winner = False
            self.flip_board = True

        self.boardWidget.setBoard(self.board, self.flip_board)
        
        self.can_move = self.board.turn==self.winner
        
        if not self.can_move:
            game_move = self.get_next_game_move()
            if game_move:
                self.parent.add_message('Opponent move: ' + self.board.san(game_move))
                self.make_move(game_move)
                parent.game_state_changed(self)

        self.parent.add_message('**** Make move for '+('white' if self.board.turn else 'black'))

        self.timer = QTime()
        self.timer.start()

    # moves = game.main_line()
    # print(self.board.variation_san(moves))

    def elapsed(self):
        return self.timer.elapsed()

    '''
    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        # paint board
        painter.drawPixmap(0, self.label_caption.height(), self.width, self.height, self.board_map)
        # paint last move
        if self.last_move:
            x = self.cx * ((7 - chess.square_file(self.last_move.from_square)) if self.flip_board else chess.square_file(self.last_move.from_square))
            y = self.cy * (chess.square_rank(self.last_move.from_square) if self.flip_board else (7 - chess.square_rank(self.last_move.from_square))) + self.label_caption.height()
            painter.drawRect(QRectF(x, y, self.cx, self.cy))
            x = self.cx * ((7 - chess.square_file(self.last_move.to_square)) if self.flip_board else chess.square_file(self.last_move.to_square))
            y = self.cy * (chess.square_rank(self.last_move.to_square) if self.flip_board else (7 - chess.square_rank(self.last_move.to_square))) + self.label_caption.height()
            painter.drawRect(QRectF(x, y, self.cx, self.cy))
        try:
            # paint pieces
            self.paint_pieces(self.board, self.flip_board)
        except Exception as ex:
            print(ex)
        painter.end()
    '''
    def get_next_game_move(self):
        if len(self.node.variations)<1:
            return None
            
        next_node = self.node.variations[0]
        self.node = next_node
        return next_node.move

    def get_last_move(self):
        lm = None
        try:
            lm = self.board.peek()
        except:
            pass
            
        return lm
        
    def compare_user_move_with_game(self, move):
        game_move = self.get_next_game_move()
        if game_move is None:
            return
            
        move_text = self.board.san(move)
        self.parent.add_message('Your move: '+move_text+', Game move: '+self.board.san(game_move))
        is_book_move = self.parent.is_book_move(self.board, move)
        if is_book_move:
            opening_name = self.parent.get_opening_name(self.board)
            self.parent.add_message(move_text+' (Book move '+opening_name+')')
        if move!=game_move and not is_book_move:
            board_copy = self.board.copy()
            self.thread = Thread(target=self.compare_moves, args=(board_copy, move, game_move))
            self.thread.start()
        self.make_move(game_move)

    def make_move(self, move):
        self.last_move = move
        self.board.push(move)
        self.can_move = self.board.turn==self.winner if self.board_type == 2 else True

        self.parent.game_state_changed(self)

    def compare_moves(self, board, user_move, game_move):
        # evaluate move score
        evaluation = self.parent.evaluate_moves(board, [user_move, game_move])
        score_diff = evaluation[user_move] - evaluation[game_move]
        self.parent.add_message('Move score ('+board.san(user_move)+' vs '+board.san(game_move)+'): '+ str(score_diff))
        self.total_score += score_diff
        self.parent.add_message('Game score: '+ str(self.total_score))

    def evaluate(self, board, move):
        # evaluate move score
        evaluation = self.parent.evaluate_board(board)[0]
        self.parent.add_message('Position Evaluation ('+move+') '+str(evaluation))

    # process user move
    def userMoved(self, uci_move):
        move = chess.Move.from_uci(uci_move)

        # is it a legal move?
        if move in self.board.legal_moves:
            if self.board_type == 2:
                self.compare_user_move_with_game(move)
                # make opponents move
                if not self.can_move:
                    # make the next game move as well
                    game_move = self.get_next_game_move()
                    if game_move is None:
                        return
                        
                    self.parent.add_message('Opponent move: ' + self.board.san(game_move))
                    self.make_move(game_move)
                    self.parent.add_message('**** Make move for '+('white' if self.board.turn else 'black'))
                    self.timer.restart()
            else:
                self.make_move(move)
                
class GameListItem(QListWidgetItem):
    def __init__(self, pgn_offset, pgn_header, index=''):
        welo = pgn_header['WhiteElo']
        belo = pgn_header['BlackElo']
        super().__init__((str(index) + '. ' if index!='' else '') + '[' + pgn_header['Result'] + '] ' + pgn_header['White'] + ' ' + welo + ' vs ' + pgn_header['Black'] + ' ' + belo)
        self.offset = pgn_offset
        self.header = pgn_header
        self.index = index

class OpeningListItem(QListWidgetItem):
    def __init__(self, key, value, index=''):
        super().__init__((str(index) + '. ' if index!='' else '') + value[0]+' ('+key+')')
        self.key = key
        self.value = value

class TacticsListItem(QListWidgetItem):
    def __init__(self, pgn_offset, pgn_header, index=''):
        super().__init__((str(index) + '. ' if index!='' else '') + '[' + pgn_header['Result'] + '] ' + pgn_header['White'] + ' vs ' + pgn_header['Black'])
        self.offset = pgn_offset
        self.header = pgn_header
        self.index = index

class CoordListItem(QListWidgetItem):
    # Caption, File/Rank/Position (0/1/2), White/Black/Both (0/1/2)
    def __init__(self, caption, gametype, color):
        super().__init__(caption)
        self.gametype = gametype
        self.color = color

class App(QMainWindow):
    # board dimension in pixels
    bpx = 600
    bpy = 600

    def __init__(self):
        super().__init__()
        
        self.openings = {}
        
        self.init_ui()

        self.static_board = chess.Board()
        self.add_message('initializing opening book...')
        self.book = chess.polyglot.open_reader("book.bin")

        self.thread = Thread(target=self.init_openings)
        self.thread.start()

        self.add_message('initializing engine...')
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.engine_busy = False

        self.add_message('Ready')

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(200)

    def init_openings(self):
        opening_file = open("ecoe.pgn")
        game = chess.pgn.read_game(opening_file)
        while game is not None:
            chess_board = game.board()
            line = chess_board.variation_san(game.mainline_moves())
            black_player_name = game.headers['Black']
            name = (' (' + black_player_name + ')') if black_player_name != '?' else ''
            self.openings[line] = (game.headers['White'] + name, game.mainline_moves())
            game = chess.pgn.read_game(opening_file)
        self.populate_opening_list()

    def get_opening_name(self, board):
        san = self.static_board.variation_san(board.move_stack)
        if san in self.openings:
            return '- '+self.openings[san][0]
        return ''

    def is_book_move(self, board, move):
        return any(move==x.move for x in self.book.find_all(board))

    def init_ui(self):
        self.statusBar()
        self.statusBar().showMessage('Ready')

        mm = self.menuBar()
        fm = mm.addMenu('&File')

        act = QAction("New", self)
        act.triggered.connect(self.new_game)
        fm.addAction(act)

        act = QAction("Shadow..", self)
        act.triggered.connect(self.shadow)
        fm.addAction(act)

        act = QAction("Analyze", self)
        act.triggered.connect(self.analyze)
        fm.addAction(act)

        self.games_list = QListWidget()
        self.games_list.itemDoubleClicked.connect(self.on_list_dbl_click)

        self.opening_list = QListWidget()
        self.opening_list.itemDoubleClicked.connect(self.on_opening_list_dbl_click)
        
        self.tactics_list = QListWidget()
        self.tactics_list.itemDoubleClicked.connect(self.on_tactics_list_dbl_click)

        self.coord_learn = QListWidget()
        self.coord_learn.itemDoubleClicked.connect(self.on_coord_learn_dbl_click)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)

        self.tabs.currentChanged.connect(self.tab_changed)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.tabs.addTab(self.games_list, "Games")
        self.populate_game_list_from_pgn('games.pgn')

        self.tabs.addTab(self.opening_list, "Openings")
        
        self.tabs.addTab(self.tactics_list, "Tactics")
        self.populate_tactics_list_from_pgn('tactics.pgn')

        self.tabs.addTab(self.coord_learn, "Coordinates")
        self.populate_coord_learn_list()

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        game_msg_widget = QWidget()
        game_msg_layout = QVBoxLayout(game_msg_widget)

        game_msg_layout.addWidget(self.tabs, 2)
        self.msg_list = QListWidget()
        game_msg_layout.addWidget(self.msg_list)

        main_layout.addWidget(game_msg_widget, 2)

        moves_check_widget = QWidget()
        moves_check_layout = QVBoxLayout(moves_check_widget)

        self.moves_list = QLabel()
        self.moves_list.setWordWrap(True)
        moves_check_layout.addWidget(self.moves_list)

        self.check_list = QListWidget()
        self.populate_check_list()
        moves_check_layout.addWidget(self.check_list, 2)

        main_layout.addWidget(moves_check_widget)

        self.setCentralWidget(main_widget)

        self.resize(self.bpx, self.bpy)
        self.setWindowTitle('Chess Coach')
        self.show()

    def tab_changed(self, index):
        tab = self.tabs.currentWidget()
        if isinstance(tab, QGame):
            self.game_state_changed(tab)

    def close_tab(self, index):
        tab = self.tabs.currentWidget()
        if isinstance(tab, TabEmpty):
            self.tabs.removeTab(index)

    def game_state_changed(self, qgame):
        msg = self.static_board.variation_san(qgame.board.move_stack)
        self.moves_list.setText(msg)

    def analyze(self):
        tab = self.tabs.currentWidget()
        if isinstance(tab, QGame):
            board_copy = tab.board.copy()
            self.thread = Thread(target=self.analyze_board, args=(board_copy,))
            self.thread.start()

    def analyze_board(self, board):
        self.eval_msg = QListWidgetItem('Analyzing Position...')
        self.add_message(self.eval_msg)
        msg = self.evaluate_board(board)
        self.eval_msg = QListWidgetItem('... ('+str(msg[0])+') '+board.variation_san(msg[1]))
        self.add_message(self.eval_msg)

    def tick(self):
        tab = self.tabs.currentWidget()
        try:
            elapsed = tab.elapsed() / 1000
            seconds = int(elapsed)
            minutes = seconds/60.0
            seconds = seconds % 60
            hours = minutes/60.0
            minutes = minutes%60
            msg = "%02d:%02d:%02d" % (hours, minutes, seconds)
            self.statusBar().showMessage(msg)
        except Exception as ex:
            pass

    def populate_check_list(self):
        file = open('check_list.txt')
        for line in file:
            self.check_list.addItem(line.rstrip())

    def piece_location(self, piece):
        x = int((piece.pos().x() - self.mx) / self.cx)
        y = int((piece.pos().y() - self.my) / self.cy)
        return chess.FILE_NAMES[x], chess.RANK_NAMES[7 - y]

    def new_game(self):
        try:
            self.tabs.addTab(QGame(self), 'Game')
            self.tabs.setCurrentIndex(self.tabs.count()-1)
            self.add_message('New Game')
        except Exception as ex:
            print(ex)
            
    def shadow(self):
        try:
            fileName, _ = QFileDialog.getOpenFileName(self, 'Get File', None, 'PGN (*.pgn)')
            if fileName:
                self.populate_game_list_from_pgn(fileName)
        except Exception as ex:
            print(ex)

    def populate_opening_list(self):
        self.opening_list.clear()
        grouping = ''
        index = 1
        for k, v in self.openings.items():
            c = k[:6].strip()
            if grouping != c:
                grouping = c
                self.opening_list.addItem('==== '+grouping+' ====')
            
            opening = OpeningListItem(k, v, index)
            self.opening_list.addItem(opening)
            index += 1
            
    def populate_game_list_from_pgn(self, file_name):
        self.pgn_file = open(file_name)
        self.games_list.clear()
        index = 1
        while True:
            offset = self.pgn_file.tell()
            header = chess.pgn.read_headers(self.pgn_file)
            if header is None:
                break
            
            game = GameListItem(offset, header, index)
            self.games_list.addItem(game)
            index += 1
            
        self.update()

    def populate_tactics_list_from_pgn(self, file_name):
        self.tactics_file = open(file_name)
        self.tactics_list.clear()
        index = 1
        while True:
            offset = self.tactics_file.tell()
            header = chess.pgn.read_headers(self.tactics_file)
            if header is None:
                break
            
            game = TacticsListItem(offset, header, index)
            self.tactics_list.addItem(game)
            index += 1
            
        self.update()

    def populate_coord_learn_list(self):
        self.coord_learn.addItem(CoordListItem('Rank (white)', 0, 0))
        self.coord_learn.addItem(CoordListItem('File (white)', 1, 0))
        self.coord_learn.addItem(CoordListItem('Position (white)', 2, 0))
        self.coord_learn.addItem(CoordListItem('Rank (black)', 0, 1))
        self.coord_learn.addItem(CoordListItem('File (black)', 1, 1))
        self.coord_learn.addItem(CoordListItem('Position (black)', 2, 1))
        self.coord_learn.addItem(CoordListItem('Random (both)', 2, 2))
        self.update()
        
    # Game list Double Clicked
    def on_list_dbl_click(self, selected_item):
        self.pgn_file.seek(selected_item.offset)
        selected_game = chess.pgn.read_game(self.pgn_file)
        self.static_board = selected_game.board()
        
        tab_caption = selected_item.text()[:7]+'...'
        self.tabs.addTab(QGame(self, selected_game, selected_item.text()), tab_caption)
        # open the latest tab
        self.tabs.setCurrentIndex(self.tabs.count()-1)
        self.add_message('Shadowing game: '+selected_item.text())

    # Tactics list Double Clicked
    def on_tactics_list_dbl_click(self, selected_item):
        self.tactics_file.seek(selected_item.offset)
        selected_game = chess.pgn.read_game(self.tactics_file)
        self.static_board = selected_game.board()
        
        tab_caption = selected_item.text()[:7]+'...'
        self.tabs.addTab(QGame(self, selected_game, selected_item.text()), tab_caption)
        # open the latest tab
        self.tabs.setCurrentIndex(self.tabs.count()-1)
        self.add_message('Tactics: '+selected_item.text())

    # Opening list Double Clicked
    def on_opening_list_dbl_click(self, selected_item):
        selected_game = chess.pgn.Game()
        self.static_board = selected_game.board()
        selected_game.add_line(selected_item.value[1])
        
        tab_caption = selected_item.text()[:7]+'...'
        self.tabs.addTab(QGame(self, selected_game, selected_item.text()), tab_caption)
        self.add_message('Opening: '+selected_item.text())
        self.tabs.setCurrentIndex(self.tabs.count()-1)
        self.add_message('Opening: '+selected_item.text())
        
    # Opening list Double Clicked
    def on_coord_learn_dbl_click(self, selected_item):
        self.static_board = None
        tab_caption = selected_item.text()
        self.tabs.addTab(CoordLearn(self, selected_item.text(), selected_item.gametype, selected_item.color), tab_caption)
        self.tabs.setCurrentIndex(self.tabs.count()-1)
        self.add_message('Learn: '+selected_item.text())
        
    def add_message(self, msg):
        #self.msg_list.addItem(msg)
        self.msg_list.insertItem(0, msg)

    def evaluate_board(self, board, time=1):
        # evaluate move score
        while self.engine_busy:
            pass
        self.engine_busy = True
        info = self.engine.analyse(board, chess.engine.Limit(time=time))
        self.engine_busy = False
        return info['score'].relative.score(mate_score=100000), info['pv']

    def evaluate_moves(self, board, moves_list):
        # evaluate move score
        while self.engine_busy:
            pass
            
        moves_score = {}
        self.engine_busy = True
        
        info = self.engine.analyse(board, chess.engine.Limit(time=1), multipv=len(moves_list), root_moves=moves_list)
        for i in range(len(info)):
            moves_score[info[i]['pv'][0]] = info[i]['score'].relative.score(mate_score=100000)
            
        self.engine_busy = False
        return moves_score

    def closeEvent(self, e):
        print('... quitting!')
        self.book.close()
        self.engine.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    sys.exit(app.exec_())

