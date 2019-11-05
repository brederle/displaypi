from abc import ABC, abstractmethod

class IPlayer(ABC):

    @abstractmethod
    def open(self, filename):
        '''Open a file to play'''
        pass

    @abstractmethod
    def openStream(self, url):
        '''Open a stream from given url'''
        pass

    def run(self):
        """ Run the players main execution loop in main thread """
        pass

    @abstractmethod
    def play(self):
        '''Start playing'''
        pass

    @abstractmethod
    def stop(self):
        '''Stop playing'''
        pass

    def close(self):
        """ Close player and application """
        pass

    @abstractmethod
    def printSubtext(self, text):
        '''Overlay an information subtext on video'''
        pass

    @abstractmethod
    def clearSubtext(self):
        '''Clear any subtext on video'''
        pass
