#拼圖 (Puzzle)
import cv2
import numpy as np
import os
import sys
from pathlib import Path

# image information
def read_image(filename, flags):
    img = cv2.imread(filename, flags)
    row = len(img)
    col = len(img[0])
    chn = len(img[0][0]) if flags == cv2.IMREAD_COLOR else 1
    return img, row, col, chn

import math
def get_pieces(img, img_row, img_col, img_chn):
    #一塊拼圖資料
    column = 9   
    row = 16     
    total = row * column
    horizontal = 120
    vertical = 120
    p_list = []

    # creation of pieces
    for pIt in range(total):
        #切塊
        temp = np.zeros((vertical, horizontal, img_chn), dtype=np.uint8)
        start_row = vertical * math.floor(pIt / row)
        start_col = horizontal * (pIt % row)
        for i in range(start_row, start_row + vertical):
            if i >= img_row:
                break
            for j in range(start_col, start_col + horizontal):
                if j >= img_col:
                    continue
                temp[i - start_row][j - start_col] = img[i][j]
        p_list.append(Piece(pIt, vertical, horizontal, img_chn, (start_row, start_col), temp, total))
    return p_list, vertical, horizontal, row, column, total

# get pieces together in a single image
def combine_pieces(size_vertical, size_horizontal, cnt_row, cnt_col, cnt_total, chn, plist):
    temp = np.zeros((size_vertical * cnt_col, size_horizontal * cnt_row, chn), dtype=np.uint8)
    for pIt in range(cnt_total):
        start_row = size_vertical * math.floor(pIt / cnt_row)
        start_col = size_horizontal * (pIt % cnt_row)
        temp[start_row:start_row + size_vertical, start_col:start_col + size_horizontal] =\
            plist[pIt].pieceData[:size_vertical, :size_horizontal]
    return temp


# show result puzzle image
def draw_image(temp, window_name):
    cv2.imshow(window_name, temp)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# Piece class, holds data of each piece
class Piece:
    def __init__(self, num, s_vert, s_horz, chn, start, data, total):
        self.pieceNum = num
        self.size_vertical = s_vert
        self.size_horizontal = s_horz
        self.pieceChn = chn
        self.pieceStart = start
        self.pieceData = np.ndarray((s_vert, s_horz, chn), buffer=data, dtype=np.uint8)
        self.pieceTotal = total

        # 一塊的4個邊界
        self.sideUp = []
        self.sideRight = []
        self.sideDown = []
        self.sideLeft = []

        for i in range(self.size_horizontal):
            self.sideUp.append(self.pieceData[0][i])
            self.sideDown.append(self.pieceData[-1][i])

        for i in range(self.size_vertical):
            self.sideRight.append(self.pieceData[i][-1])
            self.sideLeft.append(self.pieceData[i][0])

        self.sides = [self.sideUp, self.sideRight, self.sideDown, self.sideLeft]

        self.difference = [None for x in range(total)]

        self.neighbors = [None for x in range(4)]


# determine difference of pixel's each channel value
def pixel_difference(px1, px2):
    PIXEL_DIFFERENCE_THRESHOLD = 30
    diff = 0
    for i in range(len(px1)):
        diff += abs(int(px1[i] - int(px2[i])))
    return False if diff < PIXEL_DIFFERENCE_THRESHOLD else True


# calculate different pixels between two sides
def side_difference(side1, side2):
    difference = 0
    for i in range(len(side1)):
        difference += 1 if pixel_difference(side1[i], side2[i]) else 0
    return difference

# calculate difference between two pieces in all directions
def piece_difference(piece1: Piece, piece2: Piece):
    vertical_12 = side_difference(piece1.sideDown, piece2.sideUp)
    vertical_21 = side_difference(piece2.sideDown, piece1.sideUp)
    horizontal_12 = side_difference(piece1.sideRight, piece2.sideLeft)
    horizontal_21 = side_difference(piece2.sideRight, piece1.sideLeft)

    # clockwise direction
    temp1 = [vertical_21, horizontal_12, vertical_12, horizontal_21]
    temp2 = [vertical_12, horizontal_21, vertical_21, horizontal_12]

    for i in range(len(temp1)):
        temp1[i] = (temp1[i], i)
        temp2[i] = (temp2[i], i)

    # non-decreasing sort of difference
    piece1.difference[piece2.pieceNum] = sorted(temp1)
    piece2.difference[piece1.pieceNum] = sorted(temp2)

# search for neighbors
def find_neighbors(piece: Piece):
    DIFFERENCE_RATE_THRESHOLD = 0.6
    candidates = [None for x in range(4)]
    # find the best candidate for each direction
    for i in range(len(piece.difference)):
        if piece.difference[i] is None:
            continue
        temp = piece.difference[i][0]
        if candidates[temp[1]] is None or candidates[temp[1]][1][0] > temp[0]:
            candidates[temp[1]] = (i, temp)

    # test if candidate is eligible as neighbor
    for entry in candidates:
        if entry is not None and entry[1][0] <= DIFFERENCE_RATE_THRESHOLD *\
                (piece.size_vertical if (entry[1][1] == 1 or entry[1][1] == 3) else piece.size_horizontal):
            piece.neighbors[entry[1][1]] = entry[0]

if __name__ == "__main__":
    #讀檔
    print("請輸入影像檔: ", end = '' )
    filename = input()
    #設定column那些
    img, imgRow, imgCol, imgChn = read_image(filename, cv2.IMREAD_COLOR)

    #得到切塊
    pList, pSize_vertical, pSize_horizontal, pCnt_row, pCnt_column, pCnt_total = get_pieces(img, imgRow, imgCol, imgChn)

    # calculate difference between every piece
    for i in range(pCnt_total):
        for j in range(i + 1, pCnt_total):
            if i == j:
                continue
            piece_difference(pList[i], pList[j])
 
    # determine starting pixel to fill in image
    startPiece = None
    for piece in pList:
        find_neighbors(piece)
        if piece.neighbors[0] is None and piece.neighbors[3] is None:
            startPiece = piece
    if startPiece is None:
        startPiece = pList[0]

    # fill in image using neighbor information
    black = np.zeros((pSize_vertical, pSize_horizontal, imgChn), dtype=np.uint8)
    blackPiece = Piece(-1, pSize_vertical, pSize_horizontal, imgChn, (0, 0), black, pCnt_total)
    temp = [blackPiece for x in range(pCnt_total)]
    temp[0] = startPiece
    for i in range(pCnt_total):
        if i % pCnt_row < pCnt_row - 1 and temp[i].neighbors[1] is not None:
            temp[i + 1] = pList[temp[i].neighbors[1]]
        if i / pCnt_row < pCnt_column - 1 and temp[i].neighbors[2] is not None:
            temp[i + pCnt_row] = pList[temp[i].neighbors[2]]

    # show and save result image
    fileName = os.path.splitext(filename)[0] + "_result.bmp"
    temp = combine_pieces(pSize_vertical, pSize_horizontal, pCnt_row, pCnt_column, pCnt_total, imgChn, temp)
    #draw_image(temp, filename + " - Solved Image")
    cv2.imwrite(fileName, temp)
    print("輸出影像檔: " , fileName )
