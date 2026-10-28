import pygame 

## CORES
# FUNDO: #d7e8ba
# BOTÃO: #38b6ff
# 

WIDTH, HEIGHT =  800, 600 
screen = pygame.display.set_mode((WIDTH,HEIGHT))

class Button(pygame.Rect):

    def __init__(self, left, top, width, height, text): 
        super().__init__(left, top, width, height)
        pygame.font.init()
        self._label_font = pygame.font.SysFont("dejavusansmono", int(width * 0.2), bold=True)
        self._content = text
        


    def draw(self,color="#38b6ff"): 
        pygame.draw.rect(screen, color, self, border_radius= int(self.width*0.1))
        label = self._label_font.render(self._content, True, "white")
        label_x = self.centerx - label.get_width()/2
        label_y = self.centery - label.get_height()/2 

        screen.blit(label, (label_x, label_y))


title = pygame.image.load("./title.png").convert_alpha()
title_resized =  pygame.transform.scale(title, (WIDTH * 0.6, HEIGHT *0.6))

pygame.init()

run = True



button_w = int (WIDTH * 0.15) 
button_h = int(HEIGHT * 0.2)

start_button = Button(button_w , HEIGHT * 0.7,button_w, button_h, "Start")
config_button = Button(button_w * 2 + WIDTH *0.1, HEIGHT * 0.7, button_w, button_h, "Opções") 
exit_button = Button(button_w * 3 + WIDTH *0.2, HEIGHT * 0.7, button_w, button_h, "Exit") 

while run: 

    for event in pygame.event.get(): 

        if event.type == pygame.QUIT: 
            run = False 



    screen.fill("#d7e8ba");
    screen.blit(title_resized, (WIDTH/2 - title_resized.get_width()/2, HEIGHT/2.5- title_resized.get_height()/2))
    start_button.draw()
    config_button.draw()
    exit_button.draw()

    pygame.display.flip()

pygame.quit()

