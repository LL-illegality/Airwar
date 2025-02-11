import time
import pygame

pygame.mixer.init()

msc = pygame.mixer.music.load(".\\music\\future_intro.wav")

pygame.mixer.music.play(-1)

while True:
    time.sleep(0.1)
