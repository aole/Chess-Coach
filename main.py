"""
Requires python-chess
Needs games.pgn, book.bin on path

TODO:
	1. cache scaled images
	2. flip board and drag
	3. move to newly created tab
"""

import sys

from threading import Thread
import chess.pgn
import chess.polyglot
import chess.uci
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QAction, QMainWindow, QVBoxLayout
from PyQt5.QtWidgets import QTabWidget, QFileDialog, QListWidget, QListWidgetItem

PIECE_IMAGE_INDEX = [0, 5, 3, 2, 4, 1, 0]


class QGame(QWidget):
    from_square = -1
    mouseMovePos = None
    offset_x = offset_y = 0
    can_move = False
    winner = True
    thread = None
    engine_busy = False

    def __init__(self, parent, chess_game):
        super().__init__(parent)

        self.width = self.width()
        self.height = self.height()
        self.cx = self.width / 8
        self.cy = self.height / 8

        self.parent = parent
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

    # moves = game.main_line()
    # print(self.board.variation_san(moves))

    def resizeEvent(self, e):
        self.width = e.size().width()
        self.height = e.size().height()
        self.cx = self.width / 8
        self.cy = self.height / 8

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.width, self.height, self.board_map)
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
                    y = self.mouseMovePos.y() - self.offset_y
                else:
                    x = self.cx * ((7 - chess.square_file(s)) if flip else chess.square_file(s))
                    y = self.cy * (chess.square_rank(s) if flip else (7 - chess.square_rank(s)))

                piece_index = PIECE_IMAGE_INDEX[p.piece_type] + (0 if p.color else 6)
                img = QImage.scaled(self.piece_map[piece_index], self.cx, self.cy, Qt.KeepAspectRatio)
                painter.drawImage(x, y, img)
            # sym = p.unicode_symbol()
            # painter.drawText(x,y,self.cx,self.cy,Qt.AlignCenter, sym)

    def mousePressEvent(self, e):
        if self.can_move:
            self.mouseMovePos = e.pos()
            x = int(e.pos().x() / self.cx)
            self.offset_x = e.pos().x() - x * self.cx
            y = int(e.pos().y() / self.cy)
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
                self.user_moved(uci_move)

        super().mouseReleaseEvent(e)
        self.from_square = -1
        self.update()

    def user_moved(self, uci_move):
        print(self.board)
        print(uci_move)
        move = chess.Move.from_uci(uci_move)
        if move in self.board.legal_moves:
            #self.parent.add_message('You made the move: ' + self.board.san(move))
            self.compare_user_move_with_game(move)
            # make losers move
            if not self.can_move:
                #print(self.game.variations[0].move)
                self.make_move(self.node.variations[0].move)
        #print(self.board)

    def compare_user_move_with_game(self, move):
        next_node = self.node.variations[0]
        next_move = next_node.move
        self.make_move(move)
        if move==next_move:
            self.parent.add_message('You made the same move as the game.')
        else:
            self.parent.add_message('You made a different move from the game.')
            self.board.pop()
            self.make_move(next_move)
        self.node = next_node

    def make_move(self, move):
        move_text = self.board.san(move)
        self.board.push(move)
        self.parent.add_message('Move made: '+move_text)
        self.can_move = self.board.turn==self.winner

        board_copy = self.board.copy()
        self.thread = Thread(target=self.evaluate, args=(board_copy, move_text))
        self.thread.start()

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

        self.add_message('initializing engine...')
        self.engine = chess.uci.popen_engine("stockfish")
        self.info_handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(self.info_handler)

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

        layout = QVBoxLayout(self)

        main_widget = QWidget()
        main_widget.setLayout(layout)

        layout.addWidget(self.tabs, 2)
        self.msg_list = QListWidget()
        layout.addWidget(self.msg_list)

        self.setCentralWidget(main_widget)

        self.resize(self.bpx, self.bpy)
        self.setWindowTitle('Oracle')
        self.show()

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

    def add_message(self, msg):
        self.msg_list.addItem(msg)

    def evaluate_board(self, board):
        self.engine.position(board)
        self.engine.go(movetime=5000)
        #print('Your move PV:', brd.variation_san(info_handler.info["pv"][1]))
        return self.info_handler.info["score"][1][0]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    sys.exit(app.exec_())

opening_names = open("ecoe.pgn")


def get_opening_name(san):
    opening_names.seek(0)
    game = chess.pgn.read_game(opening_names)
    while game is not None:
        chess_board = game.board()
        line = chess_board.variation_san(game.main_line())
        if san == line:
            break
        game = chess.pgn.read_game(opening_names)

    if game is None:
        return ''

    black_player_name = game.headers['Black']
    name = (' (' + black_player_name + ')') if black_player_name != '?' else ''
    return game.headers['White'] + name


print('opening book...')
book = chess.polyglot.open_reader("book.bin")

print('opening games...')
pgn = open("games.pgn")
offset = (x for x in chess.pgn.scan_offsets(pgn))

print('finding game to shadow...')
game, result = 0, '1-0'
header = game.headers
print(header['White'] + '(' + header['WhiteElo'] + ')', 'vs', header['Black'] + '(' + header['BlackElo'] + ')')

winner = result == '1-0'

node = game
total_moves = 0
correct_moves = 0
total_diff = 0
think_time = 5000
const_board = chess.Board()
exit_game = False

print('start shadowing game...')
while not node.is_end():
    next_node = node.variations[0]
    next_move = node.board().san(next_node.move)
    if winner == node.board().turn:
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
            if res == 'exit':
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
            opening_name = get_opening_name(const_board.variation_san(brd.move_stack))
            brd.pop()
            print('** you made a book move:', opening_name)
            book_move = True
            correct = True
            correct_moves += 1

        total_moves += 1
        user_score = 0
        if res == next_move:
            print('** your move was same as the game move.')
            correct = True
            correct_moves += 1
        else:
            if not book_move:
                # evaluate user move
                print('** evaluating your move', res, '...')
                brd = node.board()
                brd.push(user_move)
                engine.position(brd)
                engine.go(movetime=think_time)
                print('Your move PV:', brd.variation_san(info_handler.info["pv"][1]))
                brd.pop()
                user_score = info_handler.info["score"][1][0]
            else:
                brd = node.board()
                brd.push(next_node.move)
                opening_name = get_opening_name(const_board.variation_san(brd.move_stack))
                brd.pop()
            print('** you made a different move from the game:', next_move + ':' + opening_name)

        node = next_node
        if not correct:
            print('** evaluating game move', next_move, '...')
            engine.position(node.board())
            engine.go(movetime=think_time)
            game_score = info_handler.info["score"][1][0]
            diff = user_score - game_score
            if diff >= 0:
                print('** good move!')
                correct_moves += 1
            total_diff += diff
            print('Score:', diff, '(' + str(user_score), '-', str(game_score) + ')', 'total:', total_diff)
    else:
        node = next_node
        opening_name = get_opening_name(const_board.variation_san(node.board().move_stack))
        print('opponent move:', next_move + ":" + opening_name)

print(node.board())
print('** game ended!', result)
print('Score', total_diff, 'Correct:', str(correct_moves) + '/' + str(total_moves))

engine.quit()
