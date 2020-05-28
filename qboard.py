
import chess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPixmap, QPainter, QImage

PIECE_IMAGE_INDEX = [0, 5, 3, 2, 4, 1, 0]

show_ascii = False
show_ascii = True

class QBoard(QWidget):
    def __init__(self, game):
        super().__init__()
        
        self.board = None
        self.flipped = False
        self.from_square = -1
        self.game = game
        self.mousePressListeners = []
        self.moveListeners = []
        self.text = None
        
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
        
        board_size = min(self.width(), self.height())
        piece_size = board_size/8
        
        font = painter.font()
        font.setPixelSize(piece_size-4)
        painter.setFont(font)

        painter.drawPixmap(0, 0, board_size, board_size, self.board_map)
        if self.board:
            self.paint_pieces(painter, self.board, self.flipped, piece_size)
            
        if self.text:
            painter.drawText(board_size/2-65, board_size/2-65, 130, 130, Qt.AlignCenter, self.text)
            
        painter.end()
        
    def paint_pieces(self, painter, board, flip, piece_size):
        last_move = self.game.get_last_move()
        
        for s in chess.SQUARES:
            x = piece_size * ((7 - chess.square_file(s)) if flip else chess.square_file(s))
            y = piece_size * (chess.square_rank(s) if flip else (7 - chess.square_rank(s)))
            
            p = board.piece_at(s)
            if p:
                if s == self.from_square and self.mouseMovePos:
                    x = self.mouseMovePos.x() - self.offset_x
                    y = self.mouseMovePos.y() - self.offset_y
                    
                # center images
                if show_ascii:
                    sym = p.unicode_symbol()
                    painter.drawText(x, y, piece_size, piece_size, Qt.AlignCenter, sym)
                else:
                    piece_index = PIECE_IMAGE_INDEX[p.piece_type] + (0 if p.color else 6)
                    img = QImage.scaled(self.piece_map[piece_index], piece_size, piece_size, Qt.KeepAspectRatio)
                    offset_x = (piece_size-img.width())/2
                    offset_y = (piece_size-img.height())/2
                    painter.drawImage(x+offset_x, y+offset_y, img)
        
            if last_move and (last_move.from_square == s or last_move.to_square == s):
                painter.drawRect(x, y, piece_size, piece_size)
                        
    def mousePressEvent(self, e):
        if self.game.can_move:
            self.mouseMovePos = e.pos()
            piece_size = min(self.width(), self.height())/8

            x = int(e.pos().x() / piece_size)
            self.offset_x = e.pos().x() - x * piece_size
            x = 7-x if self.flipped else x

            y = int((e.pos().y()) / piece_size)
            self.offset_y = e.pos().y() - y * piece_size
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
            piece_size = min(self.width(), self.height())/8
            x = int(e.pos().x() / piece_size)
            x = 7-x if self.flipped else x
            y = int(8 - (e.pos().y()) / piece_size)
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

    def setText(self, text = None):
        self.text = text
        