from process_message_system import *
import os

class SecondProc(MessageProc):
    def main(self):
        super().main()
        print(os.getpid())

if __name__=='__main__': # really do need this
    example = SecondProc().start()
    print(os.getpid())
