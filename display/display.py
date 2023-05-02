import display.epd12in48b as eink
import logging

from PIL import Image


class Display:
    def __init__(self, width, height):
        self.logger = logging.getLogger('MagInkCal')
        self.screen_width = width
        self.screen_height = height
        self.epd = eink.EPD()
        self.epd.Init()

    def update(self, black_image, red_image):
        # Updates the display with the grayscale and red images
        # start displaying on eink display
        # self.epd.clear()
        self.epd.display(black_image, red_image)
        self.logger.info('E-Ink display update complete.')

    def calibrate(self, cycles=1):
        # Calibrates the display to prevent ghosting
        white = Image.new('1', (self.screen_width, self.screen_height), 'white')
        black = Image.new('1', (self.screen_width, self.screen_height), 'black')
        for _ in range(cycles):
            self.epd.display(black, white)
            self.epd.display(white, black)
            self.epd.display(white, white)
        self.logger.info('E-Ink display calibration complete.')

    def sleep(self):
        # send E-Ink display to deep sleep
        self.epd.EPD_Sleep()
        self.logger.info('E-Ink display entered deep sleep.')
