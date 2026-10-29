import pygame 

## CORES
# FUNDO: #d7e8ba
# BOTÃO: #38b6ff
# 

WIDTH, HEIGHT =  1024, 768 
screen = pygame.display.set_mode((WIDTH,HEIGHT))

class Button(pygame.Rect):

    def __init__(self, left, top, width, height, text): 
        super().__init__(left, top, width, height)
        pygame.font.init()
        self._label_font = pygame.font.SysFont("dejavusansmono", int(width * 0.2), bold=True)
        self._content = text
        self.color = "#38b6ff"
        


    def draw(self): 
        pygame.draw.rect(screen, self.color, self, border_radius= int(self.width*0.1))
        label = self._label_font.render(self._content, True, "white")
        label_x = self.centerx - label.get_width()/2
        label_y = self.centery - label.get_height()/2 

        screen.blit(label, (label_x, label_y))


def fases(): 

    levels = []

    count = 1
    for i in range(1,4): 
        for j in range(1,6): 
            lv = Button(WIDTH * 0.15 * j, HEIGHT * 0.25  * i, WIDTH * 0.12, HEIGHT *0.12, f"{count}")
            levels.append((lv, f"fase {count}"))
            count+=1

    return levels
            

title = pygame.image.load("./title.png").convert_alpha()
title_resized =  pygame.transform.scale(title, (WIDTH * 0.6, HEIGHT *0.6))

pygame.init()

run = True



button_w = int (WIDTH * 0.15) 
button_h = int(HEIGHT * 0.2)

start_button = Button(button_w , HEIGHT * 0.7,button_w, button_h, "Start")
config_button = Button(button_w * 2 + WIDTH *0.1, HEIGHT * 0.7, button_w, button_h, "Opções") 
exit_button = Button(button_w * 3 + WIDTH *0.2, HEIGHT * 0.7, button_w, button_h, "Exit") 
niveis = fases()


part = 0

while run: 

    for event in pygame.event.get(): 

        if event.type == pygame.QUIT: 
            run = False 

        elif event.type == pygame.MOUSEBUTTONDOWN and part == 0: 
            mouse_pos = pygame.mouse.get_pos()

            if start_button.collidepoint(mouse_pos): 
                part=1 
            elif config_button.collidepoint(mouse_pos):
                pass
            elif exit_button.collidepoint(mouse_pos): 
                run = False

        elif event.type == pygame.MOUSEBUTTONDOWN and part == 1:
            mouse_pos = pygame.mouse.get_pos() 
            for s, _j in niveis: 
                if s.collidepoint(mouse_pos): 
                    s.color = "red"
                    

    screen.fill("#d7e8ba")

    if part == 0: 
        screen.blit(title_resized, (WIDTH/2 - title_resized.get_width()/2, HEIGHT/2.5- title_resized.get_height()/2))
        start_button.draw()
        config_button.draw()
        exit_button.draw()

    elif part == 1: 
        pygame.font.init()
        label = pygame.font.SysFont("dejavusansmono", int(HEIGHT * 0.05), bold=True)
        label = label.render("Selecione a fase desejada", True, "white")
        screen.blit(label, (WIDTH/2  - label.get_width()/2, HEIGHT*0.15  - label.get_height()))
        for i, _j in niveis: 
            i.draw()

    

    pygame.display.flip()

pygame.quit()

