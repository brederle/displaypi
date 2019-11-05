import time
import sys

from displaypi.vlcplayer import VlcPlayer
from threading import Thread


class RemoteDisplayThread(Thread):
    def __init__(self, player):
        super().__init__()
        self.player = player

    def run(self):
        self.player.open("file:///media/pi/CONFVIDEOS/00_TakePart.mp4")
        self.player.play()


    def stop(self):
        self.player.stop()
        self.player.close()




if __name__ == '__main__':
    player = VlcPlayer()

    remoteDisplay = RemoteDisplayThread(player)
    remoteDisplay.run()

    player.run()
    player.stop()
    player.close()
    sys.exit(0)
