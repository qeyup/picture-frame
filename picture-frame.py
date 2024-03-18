#! /usr/bin/env python3
# 
# This file is part of the picture-frame-broker distribution.
# Copyright (c) 2023 Javier Moreno Garcia.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#


import d2dcn
import time
import threading
import os
import base64
import sys
import argparse
import json

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSizePolicy, QPushButton
from PyQt5.QtCore import Qt, QByteArray, QBuffer
from PyQt5.QtGui import QColor, QPalette, QPixmap, QGuiApplication, QImage, QImageReader

version = "0.1.0"

class pictureBroker():

    class field:
        IMAGE = "image"
        IMAGE_PATH = "image path"
        ID = "id"
        VERTICAL_ORIENTATION = "vertical orientation"
        INCLUDED = "include"
        EXCLUDED = "exclude"
        AVALILABLE_H_FOLDER = "available_h_folders"
        AVALILABLE_v_FOLDER = "available_v_folders"
        CONNECTED_H_FRAMES = "connected_h_frames"
        CONNECTED_v_FRAMES = "connected_v_frames"

    class command:
        GET_IMAGE = "getImage"


class pictureFrame(QWidget):

    class field:
        IMAGE_PATH = "image path"


    class command:
        CHANGE_IMAGE = "changeImage"


    class param:
        CHANGE_IMAGE_TIMEOUT = 30


    def __init__(self, frame_id, update_time, vertical_orientation, fullscreen):
        super().__init__()
        self.__run = True
        self.__command = None
        self.__request_mutex = threading.Lock()
        self.__frame_id = frame_id
        self.__update_time = update_time
        self.__vertical_orientation = vertical_orientation
        self.__current = 0
        self.__buildLayout(fullscreen)

        self.d2d = d2dcn.d2d()
        self.d2d.onCommandUpdate = self.__newBrokerCommand


    def __newBrokerCommand(self, command):
        self.__command = command


    def __buildLayout(self, fullscreen):

        # Set layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)


        # Set fullscreen
        if fullscreen:
            self.showFullScreen()


        # Add label frame
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("QLabel { background-color : black; }")
        layout.addWidget(self.label)


        # Load image
        default_image = "/usr/share/picture-frame/default.drawio.png"
        if os.path.exists(default_image):
            with open(default_image, "rb") as image_file:
                raw_data = image_file.read()
                self.__loadImage(base64.b64encode(raw_data))


    def hideEvent (self, event):
        self.__run = False
        QWidget.hideEvent(self, event)


    def __configCommands(self):

        response = {}

        request = {}

        self.d2d.addServiceCommand(lambda args : self.__requestImage(args),
                                    pictureFrame.command.CHANGE_IMAGE,
                                    request, response, d2dcn.d2dConstants.category.GENERIC,
                                    protocol=d2dcn.d2dConstants.commandProtocol.JSON_UDP,
                                    timeout=pictureFrame.param.CHANGE_IMAGE_TIMEOUT)


    def __loadImage(self, base64_data):

        try:

            # Decode from base64
            decoded = base64.b64decode(base64_data)


            # Read image
            ba = QByteArray(decoded)
            buf = QBuffer(ba)
            buf.open(QBuffer.ReadOnly)
            q_image_header = QImageReader(buf)
            q_image_header.setAutoTransform(True)
            q_image = q_image_header.read()


            # Load pixmap
            pixmap = QPixmap(q_image)
            screen_size = QApplication.screens()[0].size()
            pixmap = pixmap.scaled(screen_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(pixmap)
            return True

        except:

            return False


    def __requestImage(self, args=None):
        if self.__command:

            command_arg = {}
            command_arg[pictureBroker.field.ID] = self.__frame_id
            command_arg[pictureBroker.field.VERTICAL_ORIENTATION] = self.__vertical_orientation

            response = self.__command.call(command_arg)
            if response:
                image_data = response[pictureBroker.field.IMAGE]
                image_data_path = response[pictureBroker.field.IMAGE_PATH]

                self.__loadImage(bytes(image_data, 'utf-8'))

                self.d2d.publishInfo(pictureFrame.field.IMAGE_PATH, image_data_path, d2dcn.d2dConstants.category.GENERIC)

                self.__current = 0

            return {}

        else:
            return None


    def __runFrame(self):

        self.d2d.subscribeComands(command=pictureBroker.command.GET_IMAGE)
        self.__configCommands()

        while self.__run:

            self.__requestImage()


            while self.__update_time - self.__current > 0:
                time.sleep(self.__update_time)
                self.__current += 1




    def runFrame(self):
        x = threading.Thread(target=self.__runFrame, args=())
        x.start()


if __name__ == '__main__':

    # Parse args
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)


    parser.add_argument(
        '--frame-id',
        metavar = "[FRAME ID]",
        required=False,
        default="DefaultID",
        help='Frame ID')
    parser.add_argument(
        '--update-time',
        metavar = "[UPDATE TIME]",
        required=False,
        default=15,
        help='Update image time (sec)')
    parser.add_argument(
        '--config-file',
        metavar = "[CONFIG FILE]",
        required=False,
        default="",
        help='Config file')
    parser.add_argument(
        '--vertical-orientation',
        required=False,
        default=False,
        action="store_true",
        help='Vertical orientation')
    parser.add_argument(
        '--full-screen',
        required=False,
        default=False,
        action="store_true",
        help='full screen')
    args = parser.parse_args(sys.argv[1:])
    if args.config_file:
        try:
            config = json.load(open(args.config_file))
            t_args = argparse.Namespace()
            t_args.__dict__.update(config)
            args = parser.parse_args(namespace=t_args)
        except:
            pass

    # Print config
    print(args)


    app = QApplication(sys.argv)

    window = pictureFrame(args.frame_id, int(args.update_time), args.vertical_orientation, args.full_screen)
    window.show()
    window.runFrame()

    app.exec()