import os
import ctypes
import signal
import vlc 

from tkinter import Tk
from tkinter.ttk import Frame


from displaypi.player import IPlayer


class VlcPlayer(IPlayer):


    def _loopCheckPoint(self):
        """ Regularily stop loop for signal checking and other stuff """
        self.root.after(500, self._loopCheckPoint)



    def _signal_handler(self, signal, frame):
        """ Handle SIGINT (ctrl+c)"""
        self.close()



    def __init__(self):
        """ Minimal init sequence to get a fullscreen vlc player 
            (at the moment only for a single file)"""

        # calling XInitThreads is requires to have vlc properly running und X11
        x11 = ctypes.CDLL("libX11.so.6")
        x11.XInitThreads()

        self.root = Tk()

        playerwin = Frame(self.root)
        self.vlcinstance = vlc.Instance()
        self.mediaplayer = self.vlcinstance.media_player_new()
        self.mediaplayer.set_xwindow(playerwin.winfo_id())
        self.mediaplayer.set_fullscreen(True)



    def run(self):
        """ Run the players main execution loop in main thread """
        signal.signal(signal.SIGINT, self._signal_handler)

        self.root.after(500, self._loopCheckPoint)
        self.root.mainloop()        

    def open(self, filename):
        '''Open a file to play'''
        media = self.vlcinstance.media_new(filename)
        self.mediaplayer.set_media(media)

    def openStream(self, url):
        '''Open a stream from given url'''
        pass

    def play(self):
        '''Start playing'''
        self.mediaplayer.play()

    def stop(self):
        '''Stop playing'''
        pass

    def close(self):
        """ Close player and application """
        self.stop()
        self.root.quit()     # stops mainloop
        self.root.destroy()  # this is necessary on Windows to prevent
                    # Fatal Python Error: PyEval_RestoreThread: NULL tstate
        os._exit(1)

    def printSubtext(self, text):
        '''Overlay an information subtext on video'''
        pass

    def clearSubtext(self):
        '''Clear any subtext on video'''
        pass

