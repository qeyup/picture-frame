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

version = "0.2.1"

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
        self.__buildLayout(fullscreen)

        self.d2d = d2dcn.d2d()
        self.__command = self.d2d.getAvailableComands(name=pictureBroker.command.GET_IMAGE)[0]
        print("Started")


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

        response = d2dcn.commandArgsDef()

        request = d2dcn.commandArgsDef()

        self.d2d.addServiceCommand(lambda args : self.__reqCommand(args),
                                    pictureFrame.command.CHANGE_IMAGE,
                                    request, response, d2dcn.constants.category.GENERIC,
                                    protocol=d2dcn.constants.commandProtocol.JSON_UDP,
                                    timeout=pictureFrame.param.CHANGE_IMAGE_TIMEOUT)

        self.current_image = self.d2d.addInfoWriter(pictureFrame.field.IMAGE_PATH, d2dcn.constants.valueTypes.STRING, d2dcn.constants.category.GENERIC)


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


    def __reqCommand(self, args):
        if self.__request_mutex.locked():
            self.__request_mutex.release()

        return {}


    def __requestImage(self):

        if self.__command:

            self.d2d.enableCommand(pictureFrame.command.CHANGE_IMAGE, False)

            command_arg = {}
            command_arg[pictureBroker.field.ID] = self.__frame_id
            command_arg[pictureBroker.field.VERTICAL_ORIENTATION] = self.__vertical_orientation

            response = self.__command.call(command_arg)
            if response.success:
                image_data = response[pictureBroker.field.IMAGE]
                image_data_path = response[pictureBroker.field.IMAGE_PATH]

                self.__loadImage(bytes(image_data, 'utf-8'))

                self.current_image.value = image_data_path


            else:
                print("Error!", response.error)

            self.d2d.enableCommand(pictureFrame.command.CHANGE_IMAGE, True)


    def __runFrame(self):

        self.__configCommands()

        while self.__run:

            # Sleep
            self.__request_mutex.acquire(timeout=self.__update_time)


            # Request
            self.__requestImage()


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