"""
Jogo educativo de Portas Lógicas (Informática na Educação)

Cada válvula do encanamento é controlada por um circuito de portas lógicas.
Clique na placa com raio de uma válvula para abrir o circuito dela; clique numa
porta para "Substituir Por" outra (AND, OR, NOT, FIO). A válvula abre quando a
saída do circuito ("Gate") é 1. Depois clique em "Ligar energia!": a água limpa
precisa chegar à banheira sem o veneno. Se o tempo acabar, a energia liga sozinha.

Controles:
  Mouse ............ tudo
  1, 2, 3... ....... abre o circuito da válvula correspondente (na fase)
  Espaço / Enter ... liga a energia (na fase)
  Esc .............. pausa / fecha janelas / volta

Para criar novas fases, veja a lista NIVEIS (tem um passo a passo logo acima dela).

Arquivos opcionais na mesma pasta:
  title.png ........ imagem do título do menu
  fonts/*.ttf ...... se existir uma fonte aqui, ela é usada no jogo todo
"""
import array
import glob
import itertools
import json
import math
import os

import pygame

BASE = os.path.dirname(os.path.abspath(__file__))

# Tudo é desenhado numa "tela virtual" 16:9 e depois escalado para a
# resolução escolhida nas opções. Assim o layout nunca quebra.
VW, VH = 1280, 720

# ============================ CORES ============================
FUNDO = "#d7e8ba"
AZUL = "#38b6ff"          # botões
AZUL_ONDAS = "#4f9fe0"
AZUL_ESCURO = "#1d3a6e"   # ícones
LARANJA = "#f26b3a"       # destaque de seleção (borda laranja do protótipo)
CINZA_PAINEL = "#cdd3da"
PRETO = "#111111"
BRANCO = "#ffffff"
VERMELHO = "#e53935"
AMARELO = "#ffd400"
VERDE = "#5cc46a"
VERDE_VENENO = "#8be04e"
AGUA = "#4aa8e8"
CANO = "#9aa3ab"
CANO_ESCURO = "#6d757c"
FIO_DESLIGADO = "#5a5a5a"

RESOLUCOES = [(960, 540), (1280, 720), (1600, 900), (1920, 1080)]
CONFIG_PADRAO = {"resolucao": 1, "volume": 5, "fonte": 12, "dicas": True, "hud": True}
PROGRESSO_PADRAO = {"desbloqueadas": 1, "concluidas": []}
# False = o progresso (fases liberadas/concluídas) some quando o jogo é fechado.
# True  = o progresso fica salvo no arquivo progresso.json.
SALVAR_PROGRESSO = False
TEMPO_FASE = 30
TOTAL_BOTOES_FASE = 15  # quantidade de botões na tela de seleção (3 x 5)

# ======================= PORTAS LÓGICAS ========================
FUNCOES = {
    "AND": lambda v: all(v),
    "OR": lambda v: any(v),
    "NOT": lambda v: not v[0],
    "FIO": lambda v: v[0],
    "NAND": lambda v: not all(v),
    "NOR": lambda v: not any(v),
    "XOR": lambda v: sum(v) % 2 == 1,
    "XNOR": lambda v: sum(v) % 2 == 0,
}
UMA_ENTRADA = {"NOT", "FIO"}          # portas que usam só 1 entrada
NOMES = {
    "AND": "E (AND)", "OR": "OU (OR)", "NOT": "NÃO (NOT)", "FIO": "FIO",
    "NAND": "NÃO-E (NAND)", "NOR": "NÃO-OU (NOR)",
    "XOR": "OU-EXCLUSIVO (XOR)", "XNOR": "XNOR",
}

# Se True, as fases marcadas com "em_desenvolvimento" podem ser jogadas (para testar).
TESTAR_FASES_EM_DESENVOLVIMENTO = False

# ============================ FASES ============================
# COMO CRIAR UM NOVO MODELO DE FASE
# ----------------------------------
# Tudo usa coordenadas da tela virtual (1280 x 720).
#  "agua":     caminho do cano principal, da torneira até a banheira (lista de pontos;
#              cada trecho precisa ser horizontal ou vertical). O último ponto é a banheira.
#  "venenos":  lista de canos de veneno. Cada um começa no barril e o último ponto
#              precisa cair EM CIMA do cano principal.
#  "valvulas": cada válvula fica sobre um cano ("pos" precisa estar em cima de um trecho,
#              longe das curvas). "caixa" é onde fica a placa ⚡ que abre o circuito.
#              "objetivo" é só para as dicas (1 = precisa abrir, 0 = precisa fechar).
#  "circuito": árvore de portas. Formato: ["PORTA", entrada1, entrada2]
#              - a entrada pode ser 0, 1 ou outra porta (lista)
#              - "NOT" e "FIO" têm só 1 entrada: ["NOT", entrada]
#              - "!" na frente trava a porta (o aluno não pode trocar): ["!OR", 0, 1]
#  "opcoes":   portas que aparecem no "Substituir Por" (padrão: AND, OR, NOT, FIO).
# Uma válvula abre quando a saída ("Gate") do circuito dela é 1.
# O jogador vence se a água chega na banheira e nenhum veneno chega.
OPCOES_PADRAO = ["AND", "OR", "NOT", "FIO"]

NIVEIS = [
    {   # ----------------------------- FASE 1 -----------------------------
        "tempo": 60,
        "dica": "Clique nas placas com raio para abrir o circuito de cada válvula. "
                "Clique numa porta para trocá-la. A válvula abre quando o Gate fica VERDE (saída 1).",
        "agua": [(150, 190), (150, 400), (1080, 400), (1080, 550)],
        "venenos": [[(760, 175), (760, 400)]],
        "valvulas": [
            {"nome": "Água", "pos": (280, 400), "caixa": (280, 490), "objetivo": 1,
             "circuito": ["AND", ["AND", 1, 1], ["NOT", ["OR", 1, 0]]]},
            {"nome": "Veneno", "pos": (760, 270), "caixa": (680, 270), "objetivo": 0,
             "circuito": ["OR", ["NOT", 0], ["AND", 1, 0]]},
            {"nome": "Banheira", "pos": (900, 400), "caixa": (900, 490), "objetivo": 1,
             "circuito": ["AND", ["OR", 0, 0], 1]},
        ],
    },
    {   # ----------------------------- FASE 2 -----------------------------
        # Modelo em construção: mude "em_desenvolvimento" para False para jogar.
        "em_desenvolvimento": True,
        "tempo": 90,
        "dica": "Agora são dois barris de veneno! As duas válvulas de veneno precisam ficar fechadas.",
        "agua": [(150, 190), (150, 330), (560, 330), (560, 470), (1080, 470), (1080, 550)],
        "venenos": [[(420, 175), (420, 330)], [(800, 175), (800, 470)]],
        "valvulas": [
            {"nome": "Água", "pos": (270, 330), "caixa": (270, 420), "objetivo": 1,
             "circuito": ["OR", ["AND", 1, 0], ["NOT", ["AND", 1, 1]]]},
            {"nome": "Veneno 1", "pos": (420, 250), "caixa": (340, 250), "objetivo": 0,
             "circuito": ["AND", ["OR", 1, 0], 1]},
            {"nome": "Veneno 2", "pos": (800, 320), "caixa": (720, 320), "objetivo": 0,
             "circuito": ["NOT", ["AND", ["OR", 0, 0], 1]]},
            {"nome": "Banheira", "pos": (940, 470), "caixa": (940, 560), "objetivo": 1,
             "circuito": ["AND", ["NOT", 0], ["!OR", 0, 1]]},
        ],
    },
]

# =========================== ARQUIVOS ==========================
def carregar_json(nome, padrao):
    dados = dict(padrao)
    try:
        with open(os.path.join(BASE, nome), encoding="utf-8") as f:
            dados.update(json.load(f))
    except (OSError, ValueError):
        pass
    return dados


def salvar_json(nome, dados):
    try:
        with open(os.path.join(BASE, nome), "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ============================ CORES ============================
def misturar(c1, c2, t):
    a, b = pygame.Color(c1), pygame.Color(c2)
    return pygame.Color(int(a.r + (b.r - a.r) * t), int(a.g + (b.g - a.g) * t),
                        int(a.b + (b.b - a.b) * t))


def escurecer(c, t=0.25):
    return misturar(c, "#000000", t)


def clarear(c, t=0.25):
    return misturar(c, "#ffffff", t)


# ============================ TEXTO ============================
ESCALA_FONTE = [1.0]   # muda com "Tamanho da Fonte" nas opções (12 pt = 1.0)
_cache_fontes = {}
_arquivo_fonte = sorted(glob.glob(os.path.join(BASE, "fonts", "*.ttf")))


def fonte(tam):
    tam = max(8, int(tam * ESCALA_FONTE[0]))
    if tam not in _cache_fontes:
        if _arquivo_fonte:
            _cache_fontes[tam] = pygame.font.Font(_arquivo_fonte[0], tam)
        else:
            _cache_fontes[tam] = pygame.font.SysFont(
                "dejavuserif,georgia,cambria,timesnewroman,arial", tam, bold=True)
    return _cache_fontes[tam]


def texto(surf, txt, tam, cor=BRANCO, centro=None, topleft=None, midleft=None,
          contorno=None, esp=2):
    f = fonte(tam)
    img = f.render(txt, True, cor)
    r = img.get_rect()
    if centro is not None:
        r.center = centro
    elif midleft is not None:
        r.midleft = midleft
    elif topleft is not None:
        r.topleft = topleft
    if contorno:
        borda = f.render(txt, True, contorno)
        for dx in range(-esp, esp + 1):
            for dy in range(-esp, esp + 1):
                if (dx or dy) and dx * dx + dy * dy <= esp * esp + 1:
                    surf.blit(borda, (r.x + dx, r.y + dy))
    surf.blit(img, r)
    return r


def quebrar_linhas(txt, tam, largura):
    f = fonte(tam)
    linhas, atual = [], ""
    for palavra in txt.split():
        teste = (atual + " " + palavra).strip()
        if f.size(teste)[0] <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def paragrafo(surf, txt, tam, cor, centro_x, y, largura):
    for linha in quebrar_linhas(txt, tam, largura):
        r = texto(surf, linha, tam, cor, centro=(centro_x, y))
        y += r.height + 4
    return y


# ============================= SONS ============================
class Sons:
    """Sons gerados por código (não precisa de arquivos)."""

    def __init__(self):
        self.volume = 5
        self.sons = {}
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            freq, tam, canais = pygame.mixer.get_init()
        except (pygame.error, TypeError):
            return
        if tam != -16:
            return
        self.freq, self.canais = freq, canais
        self.sons = {
            "clique": self._tom([660], 0.05),
            "ligar": self._tom([520, 780], 0.05),
            "desligar": self._tom([780, 520], 0.05),
            "agua": self._tom([300, 360, 300, 360], 0.06),
            "vitoria": self._tom([523, 659, 784, 1046], 0.12),
            "derrota": self._tom([392, 330, 262], 0.18),
        }

    def _tom(self, freqs, dur):
        amostras = array.array("h")
        for fr in freqs:
            n = int(self.freq * dur)
            for i in range(n):
                env = min(1.0, i / 150, (n - i) / 150)
                onda = 1 if math.sin(2 * math.pi * fr * i / self.freq) > 0 else -1
                v = int(onda * env * 6000)
                amostras.extend([v] * self.canais)
        return pygame.mixer.Sound(buffer=amostras.tobytes())

    def tocar(self, nome):
        som = self.sons.get(nome)
        if som and self.volume > 0:
            som.set_volume(self.volume / 10)
            som.play()


# ============================ ÍCONES ===========================
# Todos recebem (superfície, centro, tamanho, cor_de_fundo)

def icone_play(s, c, t, fundo=AZUL):
    pygame.draw.circle(s, AZUL_ESCURO, c, int(t * 0.5))
    r = t * 0.22
    pygame.draw.polygon(s, BRANCO, [(c[0] - r * 0.7, c[1] - r), (c[0] - r * 0.7, c[1] + r),
                                    (c[0] + r * 1.1, c[1])])


def _engrenagem(s, c, raio, cor, furo, dentes=8, ang=0.0):
    pts = []
    n = dentes * 4
    for i in range(n):
        a = ang + 2 * math.pi * i / n
        rr = raio if i % 4 in (0, 1) else raio * 0.76
        pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    pygame.draw.polygon(s, cor, pts)
    pygame.draw.circle(s, furo, (int(c[0]), int(c[1])), max(2, int(raio * 0.36)))


def icone_engrenagens(s, c, t, fundo=AZUL):
    _engrenagem(s, (c[0] + t * 0.12, c[1] + t * 0.1), t * 0.34, AZUL_ESCURO, fundo)
    _engrenagem(s, (c[0] - t * 0.28, c[1] - t * 0.22), t * 0.2, "#7f8c9a", fundo, 7, 0.3)
    _engrenagem(s, (c[0] - t * 0.3, c[1] + t * 0.28), t * 0.15, "#7f8c9a", fundo, 6, 0.6)


def icone_engrenagem(s, c, t, fundo=FUNDO):
    _engrenagem(s, c, t * 0.42, "#222222", fundo)


def icone_sair(s, c, t, fundo=AZUL):
    porta = pygame.Rect(0, 0, t * 0.5, t * 0.8)
    porta.midleft = (c[0] - t * 0.45, c[1])
    pygame.draw.rect(s, AZUL_ESCURO, porta, border_radius=3)
    pygame.draw.rect(s, clarear(fundo, 0.3), porta.inflate(-t * 0.14, -t * 0.14))
    pygame.draw.circle(s, AZUL_ESCURO, (int(porta.right - t * 0.15), int(c[1])), max(2, int(t * 0.04)))
    y = c[1]
    x0, x1 = c[0] - t * 0.02, c[0] + t * 0.45
    pygame.draw.line(s, AZUL_ESCURO, (x0, y), (x1 - t * 0.1, y), max(3, int(t * 0.1)))
    pygame.draw.polygon(s, AZUL_ESCURO, [(x1, y), (x1 - t * 0.2, y - t * 0.17), (x1 - t * 0.2, y + t * 0.17)])


def icone_x(s, c, t, fundo=None):
    r = t * 0.28
    w = max(3, int(t * 0.13))
    pygame.draw.line(s, VERMELHO, (c[0] - r, c[1] - r), (c[0] + r, c[1] + r), w)
    pygame.draw.line(s, VERMELHO, (c[0] - r, c[1] + r), (c[0] + r, c[1] - r), w)


def icone_lampada(s, c, t, fundo=None, aceso=True):
    cor = AMARELO if aceso else "#a8a8a8"
    centro = (int(c[0]), int(c[1] - t * 0.08))
    if aceso:
        for i in range(5):
            a = math.pi + math.pi * i / 4
            p1 = (c[0] + math.cos(a) * t * 0.36, centro[1] + math.sin(a) * t * 0.36)
            p2 = (c[0] + math.cos(a) * t * 0.46, centro[1] + math.sin(a) * t * 0.46)
            pygame.draw.line(s, "#f0a500", p1, p2, 3)
    pygame.draw.circle(s, cor, centro, int(t * 0.25))
    base = pygame.Rect(0, 0, t * 0.24, t * 0.2)
    base.midtop = (c[0], centro[1] + t * 0.18)
    pygame.draw.rect(s, "#6d6d6d", base, border_radius=3)


def icone_voltar(s, c, t, fundo=None):
    r = t * 0.32
    pygame.draw.polygon(s, BRANCO, [(c[0] - r, c[1]), (c[0] + r, c[1] - r), (c[0] + r * 0.35, c[1]),
                                    (c[0] + r, c[1] + r)])


def icone_proximo(s, c, t, fundo=None):
    r = t * 0.3
    for dx in (-r * 0.5, r * 0.5):
        pygame.draw.polygon(s, BRANCO, [(c[0] + dx - r * 0.5, c[1] - r), (c[0] + dx + r * 0.5, c[1]),
                                        (c[0] + dx - r * 0.5, c[1] + r)])


def icone_reiniciar(s, c, t, fundo=None):
    r = t * 0.3
    rect = pygame.Rect(0, 0, r * 2, r * 2)
    rect.center = c
    pygame.draw.arc(s, BRANCO, rect, 0.6, 2 * math.pi - 0.2, max(3, int(t * 0.1)))
    a = 0.6
    px, py = c[0] + r * math.cos(a), c[1] - r * math.sin(a)
    pygame.draw.polygon(s, BRANCO, [(px - t * 0.14, py - t * 0.02), (px + t * 0.12, py - t * 0.06),
                                    (px + t * 0.02, py + t * 0.16)])


def icone_cadeado(s, c, t, fundo=None):
    corpo = pygame.Rect(0, 0, t * 0.5, t * 0.38)
    corpo.midtop = (c[0], c[1] - t * 0.02)
    arco = pygame.Rect(0, 0, t * 0.34, t * 0.4)
    arco.midbottom = (c[0], corpo.top + t * 0.08)
    pygame.draw.arc(s, "#2a2a2a", arco, 0, math.pi, max(3, int(t * 0.08)))
    pygame.draw.rect(s, "#2a2a2a", corpo, border_radius=4)
    pygame.draw.circle(s, "#d0d0d0", corpo.center, max(2, int(t * 0.05)))


def icone_menos(s, c, t, fundo=None):
    pygame.draw.line(s, PRETO, (c[0] - t * 0.3, c[1]), (c[0] + t * 0.3, c[1]), 4)


def icone_mais(s, c, t, fundo=None):
    icone_menos(s, c, t)
    pygame.draw.line(s, PRETO, (c[0], c[1] - t * 0.3), (c[0], c[1] + t * 0.3), 4)


def icone_check(s, c, t, fundo=None):
    pygame.draw.lines(s, BRANCO, False, [(c[0] - t * 0.3, c[1]), (c[0] - t * 0.08, c[1] + t * 0.22),
                                         (c[0] + t * 0.32, c[1] - t * 0.25)], max(3, int(t * 0.12)))


def octogono(c, r):
    return [(c[0] + r * math.cos(math.pi / 8 + i * math.pi / 4),
             c[1] + r * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]


def raio_eletrico(s, c, t, ligado):
    forma = [(0.1, -0.5), (-0.28, 0.06), (-0.02, 0.06), (-0.12, 0.5), (0.3, -0.08), (0.04, -0.08)]
    pts = [(c[0] + x * t, c[1] + y * t) for x, y in forma]
    pygame.draw.polygon(s, AMARELO if ligado else "#a0a0a0", pts)
    pygame.draw.polygon(s, PRETO if ligado else "#777777", pts, 2)


def placa_raio(s, c, raio, ligado, brilho=True):
    if ligado and brilho:
        pygame.draw.circle(s, "#fff3a0", (int(c[0]), int(c[1])), int(raio * 1.25))
    pygame.draw.polygon(s, BRANCO, octogono(c, raio))
    pygame.draw.polygon(s, "#444444", octogono(c, raio), 3)
    raio_eletrico(s, c, raio * 1.3, ligado)


def rosto(s, c, r, feliz):
    c = (int(c[0]), int(c[1]))
    pygame.draw.circle(s, "#f7c948", c, r)
    pygame.draw.circle(s, "#d99a00", c, r, 2)
    if feliz:
        for dx in (-0.33, 0.33):
            pygame.draw.circle(s, PRETO, (int(c[0] + dx * r), int(c[1] - 0.2 * r)), max(2, r // 8))
        boca = pygame.Rect(c[0] - r * 0.5, c[1] - r * 0.25, r, r * 0.8)
        pygame.draw.arc(s, PRETO, boca, math.pi + 0.35, 2 * math.pi - 0.35, 3)
    else:
        for dx in (-0.35, 0.35):
            olho = pygame.Rect(0, 0, r * 0.36, r * 0.24)
            olho.center = (c[0] + dx * r, c[1] - 0.12 * r)
            pygame.draw.arc(s, PRETO, olho, math.pi + 0.3, 2 * math.pi - 0.3, 3)
            pygame.draw.line(s, PRETO, (c[0] + dx * r - r * 0.18, c[1] - r * 0.42 + (dx > 0) * r * 0.08),
                             (c[0] + dx * r + r * 0.18, c[1] - r * 0.42 + (dx < 0) * r * 0.08), 2)
        boca = pygame.Rect(c[0] - r * 0.35, c[1] + r * 0.3, r * 0.7, r * 0.5)
        pygame.draw.arc(s, PRETO, boca, 0.35, math.pi - 0.35, 3)


def ondas(s, x0, x1, y, fase, linhas=4):
    for k in range(linhas):
        pts = []
        for x in range(int(x0), int(x1) + 1, 6):
            pts.append((x, y + k * 26 + math.sin(x / 24 + fase) * 9))
        pygame.draw.lines(s, AZUL_ONDAS, False, pts, 7)


# ======================== WIDGETS DE UI ========================
UI = {"mao": False}  # se algum elemento clicável está sob o mouse


class Botao:
    """Botão com retorno visual: passa o mouse -> borda laranja e clareia;
    pressiona -> afunda e escurece; solta -> clique (com som)."""

    def __init__(self, rect, texto="", tam=22, cor=AZUL, icone=None, cor_texto=BRANCO,
                 raio=14, transparente=False, contorno=PRETO, habilitado=True,
                 selecionado=False, tam_icone=None, som="clique"):
        self.rect = pygame.Rect(rect)
        self.texto, self.tam, self.cor, self.icone = texto, tam, cor, icone
        self.cor_texto, self.raio, self.transparente = cor_texto, raio, transparente
        self.contorno, self.habilitado, self.selecionado = contorno, habilitado, selecionado
        self.tam_icone, self.som = tam_icone, som
        self.pressionado = False

    def evento(self, ev, jogo):
        if not self.habilitado:
            return False
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            self.pressionado = True
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            clicou = self.pressionado and self.rect.collidepoint(ev.pos)
            self.pressionado = False
            if clicou:
                jogo.sons.tocar(self.som)
                return True
        return False

    def desenhar(self, s, mouse):
        hover = self.habilitado and self.rect.collidepoint(mouse)
        if hover:
            UI["mao"] = True
        apertado = self.pressionado and hover
        r = self.rect.move(0, 4 if apertado else (-2 if hover else 0))
        fundo = pygame.Color(self.cor if self.habilitado else "#93a9b8")
        if not self.transparente:
            if hover and not apertado:
                fundo = clarear(fundo, 0.15)
            if apertado:
                fundo = escurecer(fundo, 0.15)
            if not apertado:
                pygame.draw.rect(s, escurecer(fundo, 0.35), r.move(0, 5), border_radius=self.raio)
            pygame.draw.rect(s, fundo, r, border_radius=self.raio)
        else:
            fundo = pygame.Color(FUNDO)
        if hover or self.selecionado:
            pygame.draw.rect(s, LARANJA, r.inflate(10, 10), 4, border_radius=self.raio + 5)

        if self.icone and self.texto:
            t = self.tam_icone or int(min(r.w, r.h) * 0.5)
            self.icone(s, (r.centerx, r.y + r.h * 0.4), t, fundo)
            texto(s, self.texto, self.tam, self.cor_texto, centro=(r.centerx, r.bottom - r.h * 0.17),
                  contorno=self.contorno, esp=2 if self.tam >= 18 else 1)
        elif self.icone:
            t = self.tam_icone or int(min(r.w, r.h) * 0.8)
            self.icone(s, r.center, t, fundo)
        else:
            texto(s, self.texto, self.tam, self.cor_texto, centro=r.center,
                  contorno=self.contorno, esp=2 if self.tam >= 20 else 1)


class Dropdown:
    def __init__(self, rect, opcoes, indice, tam=15):
        self.rect = pygame.Rect(rect)
        self.opcoes, self.indice, self.tam = opcoes, indice, tam
        self.aberto = False

    def _itens(self):
        return [pygame.Rect(self.rect.x, self.rect.bottom + i * self.rect.h, self.rect.w, self.rect.h)
                for i in range(len(self.opcoes))]

    def evento(self, ev, jogo):
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
            return self.aberto  # se aberto, "segura" os outros eventos
        if self.aberto:
            for i, r in enumerate(self._itens()):
                if r.collidepoint(ev.pos):
                    self.indice = i
                    jogo.sons.tocar("clique")
            self.aberto = False
            return True
        if self.rect.collidepoint(ev.pos):
            self.aberto = True
            jogo.sons.tocar("clique")
            return True
        return False

    def desenhar(self, s, mouse):
        hover = self.rect.collidepoint(mouse) or self.aberto
        if hover:
            UI["mao"] = True
        pygame.draw.rect(s, clarear(AZUL, 0.1) if hover else AZUL, self.rect, border_radius=4)
        pygame.draw.rect(s, PRETO, self.rect, 2, border_radius=4)
        if hover:
            pygame.draw.rect(s, LARANJA, self.rect.inflate(8, 8), 3, border_radius=7)
        texto(s, self.opcoes[self.indice], self.tam, PRETO,
              centro=(self.rect.x + (self.rect.w - 26) / 2 + 4, self.rect.centery))
        x, y = self.rect.right - 16, self.rect.centery
        seta = [(x - 8, y - 5), (x + 8, y - 5), (x, y + 6)] if not self.aberto else \
               [(x - 8, y + 5), (x + 8, y + 5), (x, y - 6)]
        pygame.draw.polygon(s, PRETO, seta)

    def desenhar_lista(self, s, mouse):
        if not self.aberto:
            return
        for i, r in enumerate(self._itens()):
            hover = r.collidepoint(mouse)
            pygame.draw.rect(s, LARANJA if hover else (AZUL if i == self.indice else BRANCO), r)
            pygame.draw.rect(s, PRETO, r, 1)
            texto(s, self.opcoes[i], self.tam, PRETO, centro=r.center)


class Seletor:
    """[ − ] [ valor ] [ + ]"""

    def __init__(self, x, y, valor, minimo, maximo, sufixo=""):
        self.valor, self.minimo, self.maximo, self.sufixo = valor, minimo, maximo, sufixo
        self.menos = Botao((x, y, 36, 36), icone=icone_menos, transparente=True, tam_icone=30)
        self.caixa = pygame.Rect(x + 44, y + 4, 96, 28)
        self.mais = Botao((x + 148, y, 36, 36), icone=icone_mais, transparente=True, tam_icone=30)

    def evento(self, ev, jogo):
        if self.menos.evento(ev, jogo):
            self.valor = max(self.minimo, self.valor - 1)
        if self.mais.evento(ev, jogo):
            self.valor = min(self.maximo, self.valor + 1)

    def desenhar(self, s, mouse):
        self.menos.habilitado = self.valor > self.minimo
        self.mais.habilitado = self.valor < self.maximo
        self.menos.desenhar(s, mouse)
        self.mais.desenhar(s, mouse)
        pygame.draw.rect(s, AZUL, self.caixa, border_radius=4)
        pygame.draw.rect(s, PRETO, self.caixa, 2, border_radius=4)
        texto(s, f"{self.valor}{self.sufixo}", 15, PRETO, centro=self.caixa.center)


# ============================ DIÁLOGOS =========================
class Dialogo:
    """Janela modal cinza com borda preta, título e X vermelho (igual ao protótipo)."""

    pausa = True   # enquanto a janela está aberta, o tempo da fase para

    def __init__(self, jogo, w, h, titulo, tam_titulo=34, com_x=True, centro=None, cor_fundo=CINZA_PAINEL):
        self.jogo = jogo
        self.cor_fundo = cor_fundo
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = centro or (VW // 2, VH // 2 + 15)
        self.titulo, self.tam_titulo = titulo, tam_titulo
        self.btn_x = Botao((self.rect.right - 56, self.rect.y + 10, 44, 44), icone=icone_x,
                           transparente=True, tam_icone=36) if com_x else None
        self.botoes = []  # (Botao, função)

    def fechar(self):
        self.jogo.fechar_dialogo(self)

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.btn_x:
            self.fechar()
            return
        if self.btn_x and self.btn_x.evento(ev, self.jogo):
            self.fechar()
            return
        for b, acao in self.botoes:
            if b.evento(ev, self.jogo):
                acao()
                return

    def desenhar(self, s, mouse):
        veu = pygame.Surface((VW, VH), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 70))
        s.blit(veu, (0, 0))
        pygame.draw.rect(s, self.cor_fundo, self.rect)
        pygame.draw.rect(s, PRETO, self.rect, 6)
        if self.titulo:
            texto(s, self.titulo, self.tam_titulo, BRANCO, centro=(self.rect.centerx, self.rect.y + 48),
                  contorno=PRETO, esp=3)
        if self.btn_x:
            self.btn_x.desenhar(s, mouse)
        self.conteudo(s, mouse)
        for b, _ in self.botoes:
            b.desenhar(s, mouse)
        self.sobreposicao(s, mouse)

    def conteudo(self, s, mouse):
        pass

    def sobreposicao(self, s, mouse):
        pass


class DialogoSair(Dialogo):
    def __init__(self, jogo):
        super().__init__(jogo, 560, 250, "Deseja mesmo fechar o jogo?", 26)
        cx, y = self.rect.centerx, self.rect.bottom - 90
        self.botoes = [
            (Botao((cx - 170, y, 130, 48), "Sim", 20, raio=24), self.sair),
            (Botao((cx + 40, y, 130, 48), "Não", 20, raio=24), self.fechar),
        ]

    def sair(self):
        self.jogo.rodando = False


class DialogoOpcoes(Dialogo):
    def __init__(self, jogo, em_jogo=False):
        super().__init__(jogo, 760, 540, "OPÇÕES", 38)
        self.em_jogo = em_jogo
        cfg = jogo.config
        self.x_rotulo = self.rect.x + 70
        x = self.rect.x + 370
        y0 = self.rect.y + 110
        self.linhas_y = [y0 + i * 66 for i in range(5)]
        nomes_res = [f"{w} x {h}" for w, h in RESOLUCOES]
        self.resolucao = Dropdown((x, self.linhas_y[0] + 2, 190, 32), nomes_res, cfg["resolucao"])
        self.nome_res = nomes_res[cfg["resolucao"]]
        self.volume = Seletor(x - 44, self.linhas_y[1], cfg["volume"], 0, 10)
        self.tam_fonte = Seletor(x - 44, self.linhas_y[2], cfg["fonte"], 9, 16, " pt")
        self.dicas = Dropdown((x, self.linhas_y[3] + 2, 150, 32), ["Ligado", "Desligado"],
                              0 if cfg["dicas"] else 1)
        self.hud = Dropdown((x, self.linhas_y[4] + 2, 150, 32), ["Ligado", "Desligado"],
                            0 if cfg["hud"] else 1)
        self.dropdowns = ([] if em_jogo else [self.resolucao]) + [self.dicas, self.hud]
        self.botoes = [(Botao((self.rect.centerx - 85, self.rect.bottom - 80, 170, 50), "Salvar", 22,
                              raio=25), self.salvar)]

    def evento(self, ev):
        aberto = next((d for d in self.dropdowns if d.aberto), None)
        if aberto:
            aberto.evento(ev, self.jogo)
            return
        for d in self.dropdowns:
            if d.evento(ev, self.jogo):
                return
        self.volume.evento(ev, self.jogo)
        self.tam_fonte.evento(ev, self.jogo)
        if self.volume.valor != self.jogo.sons.volume:   # ouvir o volume na hora
            self.jogo.sons.volume = self.volume.valor
            self.jogo.sons.tocar("clique")
        super().evento(ev)

    def fechar(self):
        self.jogo.sons.volume = self.jogo.config["volume"]  # X descarta mudanças
        super().fechar()

    def salvar(self):
        cfg = self.jogo.config
        mudou_res = (not self.em_jogo) and self.resolucao.indice != cfg["resolucao"]
        cfg["resolucao"] = self.resolucao.indice
        cfg["volume"] = self.volume.valor
        cfg["fonte"] = self.tam_fonte.valor
        cfg["dicas"] = self.dicas.indice == 0
        cfg["hud"] = self.hud.indice == 0
        self.jogo.aplicar_config(mudou_res)
        salvar_json("config.json", cfg)
        self.jogo.fechar_dialogo(self)

    def conteudo(self, s, mouse):
        rotulos = ["Resolução:", "Volume:", "Tamanho da Fonte:", "Dicas:", "HUD:"]
        for txt, y in zip(rotulos, self.linhas_y):
            texto(s, txt, 20, PRETO, midleft=(self.x_rotulo, y + 18), contorno=BRANCO, esp=1)
        if self.em_jogo:  # na partida a resolução não pode mudar (igual ao protótipo)
            texto(s, self.nome_res, 16, PRETO, midleft=(self.resolucao.rect.x + 8, self.linhas_y[0] + 18))
        else:
            self.resolucao.desenhar(s, mouse)
        self.volume.desenhar(s, mouse)
        self.tam_fonte.desenhar(s, mouse)
        self.dicas.desenhar(s, mouse)
        self.hud.desenhar(s, mouse)

    def sobreposicao(self, s, mouse):
        for d in self.dropdowns:  # listas abertas ficam por cima de tudo
            d.desenhar_lista(s, mouse)


class DialogoPausa(Dialogo):
    def __init__(self, jogo, fase):
        super().__init__(jogo, 620, 340, "Qual ação você deseja tomar?", 26)
        self.fase = fase
        x, y = self.rect.centerx - 230, self.rect.y + 100
        self.botoes = [
            (Botao((x, y, 460, 52), "Desistir e voltar ao menu", 20, raio=26), self.desistir),
            (Botao((x, y + 72, 460, 52), "Reiniciar a fase atual", 20, raio=26), self.reiniciar),
            (Botao((x, y + 144, 460, 52), "Seguir jogando", 20, raio=26, selecionado=True), self.fechar),
        ]

    def desistir(self):
        self.jogo.trocar_cena(MenuPrincipal(self.jogo))

    def reiniciar(self):
        self.jogo.iniciar_fase(self.fase.indice)


class DialogoResultado(Dialogo):
    def __init__(self, jogo, fase, venceu, mensagem):
        super().__init__(jogo, 780, 430, "", com_x=False)
        self.venceu, self.mensagem, self.fase = venceu, mensagem, fase
        prox = fase.indice + 1
        tem_prox = prox < len(NIVEIS) and jogo.progresso["desbloqueadas"] > prox
        cx, y = self.rect.centerx, self.rect.bottom - 165
        self.botoes = [
            (Botao((cx - 255, y, 150, 120), "Voltar ao Menu", 13, icone=icone_voltar, tam_icone=56),
             lambda: jogo.trocar_cena(MenuPrincipal(jogo))),
            (Botao((cx - 75, y, 150, 120), "Jogar Novamente", 13, icone=icone_reiniciar, tam_icone=56),
             lambda: jogo.iniciar_fase(fase.indice)),
            (Botao((cx + 105, y, 150, 120), "Próximo Nível", 13,
                   icone=icone_proximo if tem_prox else icone_cadeado, tam_icone=56,
                   habilitado=tem_prox, selecionado=venceu and tem_prox),
             lambda: jogo.iniciar_fase(prox)),
        ]

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.botoes[2 if self.botoes[2][0].habilitado else 1][1]()
            return
        super().evento(ev)

    def conteudo(self, s, mouse):
        titulo = "Você Venceu!!" if self.venceu else "Você Perdeu!!"
        r = texto(s, titulo, 50, BRANCO, centro=(self.rect.centerx, self.rect.y + 70), contorno=PRETO, esp=4)
        rosto(s, (r.left - 50, r.centery), 34, self.venceu)
        rosto(s, (r.right + 50, r.centery), 34, self.venceu)
        paragrafo(s, self.mensagem, 17, "#222222", self.rect.centerx, self.rect.y + 140, self.rect.w - 80)


class DialogoAviso(Dialogo):
    def __init__(self, jogo, titulo, mensagem):
        super().__init__(jogo, 640, 300, titulo, 34)
        self.mensagem = mensagem
        self.botoes = [(Botao((self.rect.centerx - 75, self.rect.bottom - 80, 150, 50), "OK", 22, raio=25),
                        self.fechar)]

    def conteudo(self, s, mouse):
        faixa = pygame.Rect(self.rect.x + 6, self.rect.y + 84, self.rect.w - 12, 14)
        desenhar_barreira(s, faixa)
        paragrafo(s, self.mensagem, 18, "#222222", self.rect.centerx, self.rect.y + 130, self.rect.w - 80)


class DialogoDica(Dialogo):
    def __init__(self, jogo, fase):
        super().__init__(jogo, 940, 600, "DICA", 34)
        self.fase = fase
        self.botoes = [(Botao((self.rect.centerx - 85, self.rect.bottom - 72, 170, 50), "Entendi!", 20,
                              raio=25), self.fechar)]

    def conteudo(self, s, mouse):
        f = self.fase
        y = paragrafo(s, f.nivel["dica"], 16, "#222222", self.rect.centerx, self.rect.y + 98,
                      self.rect.w - 100)
        for tipo, x in (("AND", -300), ("OR", 0), ("NOT", 300)):
            self.tabela(s, tipo, self.rect.centerx + x, y + 30)
        texto(s, "FIO: a saída é igual à entrada (só passa o sinal adiante).", 15, "#333333",
              centro=(self.rect.centerx, self.rect.bottom - 118))
        texto(s, "NOT e FIO têm 1 entrada: AND e OR não cabem nos lugares de 1 entrada.", 15, "#333333",
              centro=(self.rect.centerx, self.rect.bottom - 94))

    def tabela(self, s, tipo, cx, y):
        texto(s, NOMES[tipo], 18, AZUL_ESCURO, centro=(cx, y))
        n = 1 if tipo in UMA_ENTRADA else 2
        cols = ["A", "B"][:n] + ["S"]
        cw, ch = 60, 30
        x0, y0 = cx - cw * len(cols) / 2, y + 20
        for j, nome in enumerate(cols):
            r = pygame.Rect(x0 + j * cw, y0, cw, ch)
            pygame.draw.rect(s, AZUL, r)
            pygame.draw.rect(s, PRETO, r, 1)
            texto(s, nome, 15, PRETO, centro=r.center)
        for i, linha in enumerate(itertools.product([0, 1], repeat=n)):
            saida = int(FUNCOES[tipo]([bool(v) for v in linha]))
            for j, v in enumerate(list(linha) + [saida]):
                r = pygame.Rect(x0 + j * cw, y0 + (i + 1) * ch, cw, ch)
                pygame.draw.rect(s, BRANCO, r)
                pygame.draw.rect(s, PRETO, r, 1)
                texto(s, str(v), 15, VERDE if (j == len(cols) - 1 and v) else PRETO, centro=r.center)


def desenhar_opcao_porta(s, c, tipo, habilitado):
    """Linha do painel 'Substituir Por': símbolo à esquerda, nome à direita."""
    ix, iy = c[0] - 75, c[1]
    cor = PRETO if habilitado else "#9a9a9a"
    if tipo == "FIO":
        pygame.draw.line(s, cor, (ix - 50, iy), (ix + 50, iy), 9)
    else:
        img = forma_porta(tipo, 70, 46)
        r = img.get_rect(center=(ix, iy))
        n = 1 if tipo in UMA_ENTRADA else 2
        ys = [iy] if n == 1 else [iy - 11, iy + 11]
        for yy in ys:
            pygame.draw.line(s, cor, (r.x - 14, yy), (r.x + 12, yy), 3)
        pygame.draw.line(s, cor, (r.right - 8, iy), (r.right + 12, iy), 3)
        s.blit(img, r)
    texto(s, tipo, 26, BRANCO if habilitado else "#d8d8d8", centro=(c[0] + 70, c[1]),
          contorno=PRETO if habilitado else "#9a9a9a", esp=2)


class DialogoCircuito(Dialogo):
    """Janela com o circuito (árvore de portas) que controla uma válvula (Fig. 9 do protótipo)."""
    pausa = False            # o tempo continua correndo enquanto o aluno pensa!
    GW, GH, PINO = 70, 90, 17

    def __init__(self, jogo, fase, valvula):
        super().__init__(jogo, 600, 640, "", centro=(600, 375), cor_fundo="#e8e9f3")
        self.fase, self.valvula = fase, valvula
        self.selecionado = None
        self.opcoes = []
        self.btn_fechar_painel = None
        self.painel = None
        self.montar_layout()

    # ---------- layout automático da árvore ----------
    def montar_layout(self):
        raiz = self.valvula.circuito
        folhas = []

        def coletar(no, pai):
            if isinstance(no, Entrada):
                folhas.append((no, pai))
            else:
                for f in no.filhos:
                    coletar(f, no)
        coletar(raiz, None)

        # entradas da mesma porta ficam coladas (nos pinos); entre portas diferentes, espaço grande
        juntos = [i > 0 and folhas[i][1] is folhas[i - 1][1] and
                  all(isinstance(c, Entrada) for c in folhas[i][1].filhos) for i in range(len(folhas))]
        n_grandes = sum(1 for i in range(1, len(folhas)) if not juntos[i])
        n_peq = sum(juntos)
        largura_util = self.rect.w - 130
        grande = min(190, (largura_util - n_peq * self.PINO * 2) / max(1, n_grandes))
        x = 0.0
        for i, (f, _) in enumerate(folhas):
            if i > 0:
                x += self.PINO * 2 if juntos[i] else grande
            f.x = x

        def pos_x(no):
            if isinstance(no, Entrada):
                return no.x
            xs = [pos_x(f) for f in no.filhos]
            no.x = sum(xs) / len(xs)
            return no.x
        pos_x(raiz)
        nos = list(raiz.todos())
        minx, maxx = min(n.x for n in nos), max(n.x for n in nos)
        desloc = self.rect.centerx - (minx + maxx) / 2
        for n in nos:
            n.x += desloc

        base = self.rect.bottom - 70 - self.GH / 2
        topo = self.rect.y + 175 + self.GH / 2
        maxn = raiz.nivel()
        passo = min(170, (base - topo) / (maxn - 1)) if maxn > 1 else 0
        for n in nos:
            if isinstance(n, NoPorta):
                n.y = base - (n.nivel() - 1) * passo
        self.gate_c = (raiz.x, self.rect.y + 92)

    def rect_porta(self, no):
        return pygame.Rect(no.x - self.GW / 2 - 8, no.y - self.GH / 2 - 8, self.GW + 16, self.GH + 16)

    def ligacoes(self, no):
        """(filho, ponto do pino, conectado?) para cada entrada da porta."""
        py = no.y + self.GH / 2 - 10
        if no.tipo in UMA_ENTRADA:
            res = [(no.filhos[0], (no.x, py), True)]
            if len(no.filhos) == 2:
                res.append((no.filhos[1], (no.x + self.PINO, py + 22), False))
            return res
        return [(no.filhos[0], (no.x - self.PINO, py), True), (no.filhos[1], (no.x + self.PINO, py), True)]

    def saida_de(self, filho):
        if isinstance(filho, Entrada):
            return (filho.x, self.rect.bottom - 4)
        return (filho.x, filho.y - self.GH / 2 + 6)

    # ---------- painel "Substituir Por" ----------
    def abrir_painel(self, no):
        self.selecionado = no
        opcoes = self.fase.nivel.get("opcoes", OPCOES_PADRAO)
        self.painel = pygame.Rect(0, 0, 300, 86 + len(opcoes) * 70)
        self.painel.topleft = (min(self.rect.right - 110, VW - 310), self.rect.y + 70)
        self.btn_fechar_painel = Botao((self.painel.right - 48, self.painel.y + 8, 40, 40), icone=icone_x,
                                       transparente=True, tam_icone=32)
        self.opcoes = []
        for i, tipo in enumerate(opcoes):
            ok = len(no.filhos) == 2 or tipo in UMA_ENTRADA
            r = (self.painel.x + 12, self.painel.y + 70 + i * 70, self.painel.w - 24, 60)
            b = Botao(r, icone=lambda s, c, t, f, tp=tipo, h=ok: desenhar_opcao_porta(s, c, tp, h),
                      transparente=True, habilitado=ok, selecionado=(tipo == no.tipo), raio=8)
            self.opcoes.append((b, tipo))

    def fechar_painel(self):
        self.selecionado = self.painel = None
        self.opcoes = []

    def evento(self, ev):
        j = self.jogo
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.painel:
                self.fechar_painel()
            else:
                self.fechar()
            return
        if self.jogo.config["dicas"] and self.fase.btn_dica.evento(ev, j):
            j.abrir_dialogo(DialogoDica(j, self.fase))
            return
        if self.painel:
            if self.btn_fechar_painel.evento(ev, j):
                self.fechar_painel()
                return
            for b, tipo in self.opcoes:
                if b.evento(ev, j):
                    if tipo != self.selecionado.tipo:
                        self.selecionado.tipo = tipo
                        self.fase.trocas += 1
                        j.sons.tocar("ligar")
                    self.fechar_painel()
                    return
            if ev.type == pygame.MOUSEBUTTONDOWN and self.painel.collidepoint(ev.pos):
                return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for no in self.valvula.circuito.portas():
                if self.rect_porta(no).collidepoint(ev.pos):
                    if no.fixo:
                        j.sons.tocar("desligar")
                    else:
                        j.sons.tocar("clique")
                        self.abrir_painel(no)
                    return
            if self.painel and not self.btn_x.rect.collidepoint(ev.pos):
                self.fechar_painel()
                return
        super().evento(ev)

    # ---------- desenho ----------
    def conteudo(self, s, mouse):
        v = self.valvula
        raiz = v.circuito
        mostrar = self.jogo.config["hud"]

        def cor_sinal(no):
            return AMARELO if (mostrar and no.calcular()) else PRETO

        # fios
        for no in raiz.portas():
            for filho, pino, conectado in self.ligacoes(no):
                x0, y0 = self.saida_de(filho)
                x1, y1 = pino
                if x0 == x1:
                    pts = [(x0, y0), (x1, y1)]
                else:
                    ym = y1 + 34
                    pts = [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]
                if conectado:
                    linha_grossa(s, cor_sinal(filho), pts, 9)
                else:  # entrada sobrando (porta de 1 entrada num lugar de 2)
                    linha_grossa(s, "#b8b8b8", pts, 5)
                    pygame.draw.circle(s, "#b8b8b8", (int(x1), int(y1)), 7, 2)
        # saída da raiz até o Gate
        linha_grossa(s, cor_sinal(raiz), [(raiz.x, raiz.y - self.GH / 2 + 6), self.gate_c], 9)

        # portas
        for no in raiz.portas():
            r = self.rect_porta(no)
            hover = r.collidepoint(mouse) and not no.fixo and not (self.painel and self.painel.collidepoint(mouse))
            if hover:
                UI["mao"] = True
            if no.tipo == "FIO":
                linha_grossa(s, cor_sinal(no), [(no.x, no.y + self.GH / 2 - 10), (no.x, no.y - self.GH / 2 + 6)], 9)
                if hover or no is self.selecionado:
                    pygame.draw.rect(s, "#9a9a9a", r.inflate(-14, -6), 2, border_radius=8)
            else:
                img = forma_porta(no.tipo, self.GH, self.GW, vertical=True)
                s.blit(img, img.get_rect(center=(no.x, no.y)))
            if no is self.selecionado:
                pygame.draw.rect(s, LARANJA, r, 5, border_radius=10)
            elif hover:
                pygame.draw.rect(s, LARANJA, r, 3, border_radius=10)
            if no.fixo:
                icone_cadeado(s, (r.right - 4, r.y + 6), 26)

        # Gate (verde = 1, vermelho = 0)
        saida = raiz.calcular()
        cor_gate = "#16a05a" if saida else "#ff5a2a"
        if not mostrar:
            cor_gate = "#9aa3ab"
        pygame.draw.circle(s, cor_gate, (int(self.gate_c[0]), int(self.gate_c[1])), 46)
        texto(s, "Gate", 18, PRETO, centro=self.gate_c)

        texto(s, f"Válvula: {v.nome}", 18, AZUL_ESCURO, topleft=(self.rect.x + 22, self.rect.y + 18))
        texto(s, f"Tempo: {math.ceil(self.fase.tempo)} s", 15, "#333333",
              topleft=(self.rect.right - 170, self.rect.bottom - 34))

    def sobreposicao(self, s, mouse):
        if not self.painel:
            return
        p = self.painel
        pygame.draw.rect(s, "#e8e9f3", p)
        pygame.draw.rect(s, PRETO, p, 3)
        texto(s, "Substituir Por", 26, BRANCO, centro=(p.centerx - 18, p.y + 34), contorno=PRETO, esp=2)
        self.btn_fechar_painel.desenhar(s, mouse)
        for b, tipo in self.opcoes:
            b.desenhar(s, mouse)


# ======================== CAMINHOS (canos) =====================
def _segmentos(caminho):
    for a, b in zip(caminho, caminho[1:]):
        yield a, b, math.dist(a, b)


def comprimento(caminho):
    return sum(d for _, _, d in _segmentos(caminho))


def ponto_em(caminho, dist):
    for a, b, d in _segmentos(caminho):
        if dist <= d:
            t = dist / d if d else 0
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
        dist -= d
    a, b = caminho[-2], caminho[-1]
    d = math.dist(a, b)
    return b, ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def trecho(caminho, d0, d1):
    if d1 <= d0:
        return []
    pts = [ponto_em(caminho, d0)[0]]
    acum = 0
    for a, b, d in _segmentos(caminho):
        acum += d
        if d0 < acum < d1:
            pts.append(b)
    pts.append(ponto_em(caminho, d1)[0])
    return pts


def linha_grossa(s, cor, pts, larg):
    if len(pts) < 2:
        return
    pygame.draw.lines(s, cor, False, pts, larg)
    for p in pts:
        pygame.draw.circle(s, cor, (int(p[0]), int(p[1])), larg // 2)


def desenhar_cano(s, caminho):
    pts = trecho(caminho, 0, comprimento(caminho))
    linha_grossa(s, CANO_ESCURO, pts, 42)
    linha_grossa(s, CANO, pts, 32)
    total = comprimento(caminho)
    d = 60
    while d < total - 20:  # luvas/emendas do cano
        (x, y), (dx, dy) = ponto_em(caminho, d)
        r = pygame.Rect(0, 0, 14 if dx else 48, 48 if dx else 14)
        r.center = (x, y)
        pygame.draw.rect(s, "#b9c0c6", r, border_radius=3)
        pygame.draw.rect(s, CANO_ESCURO, r, 2, border_radius=3)
        d += 120


def desenhar_barreira(s, r):
    pygame.draw.rect(s, AMARELO, r)
    clip = s.get_clip()
    s.set_clip(r)
    passo = 12
    for x in range(r.x - r.h, r.right + r.h, passo * 2):
        pygame.draw.polygon(s, PRETO, [(x, r.bottom), (x + passo, r.bottom), (x + passo + r.h, r.y),
                                       (x + r.h, r.y)])
    s.set_clip(clip)
    pygame.draw.rect(s, PRETO, r, 2)


def bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def dist_no_caminho(caminho, p):
    """Distância, ao longo do caminho, até o ponto p (que precisa estar sobre o caminho)."""
    acum = 0.0
    for a, b, d in _segmentos(caminho):
        if min(a[0], b[0]) - 2 <= p[0] <= max(a[0], b[0]) + 2 and \
           min(a[1], b[1]) - 2 <= p[1] <= max(a[1], b[1]) + 2:
            return acum + math.dist(a, p)
        acum += d
    raise ValueError(f"O ponto {p} não está sobre o cano {caminho}")


_cache_formas = {}


def forma_porta(tipo, w, h, vertical=False):
    """Símbolo da porta lógica (branco com contorno preto). Horizontal: entrada à esquerda e
    saída à direita. Vertical: entradas embaixo e saída em cima (como na Fig. 9)."""
    chave = (tipo, w, h, vertical)
    if chave in _cache_formas:
        return _cache_formas[chave]
    pad = 4
    s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    x0, x1, y0, y1 = pad, pad + w, pad, pad + h
    cy = pad + h / 2
    bolha = tipo in ("NAND", "NOR", "NOT", "XNOR")
    rb = max(4, h // 10)
    xf = x1 - (2 * rb if bolha else 0)
    base = {"NAND": "AND", "NOR": "OR", "XNOR": "XOR"}.get(tipo, tipo)
    if base == "AND":
        r = h / 2
        xm = xf - r
        pts = [(x0, y0), (xm, y0)]
        pts += [(xm + r * math.cos(-math.pi / 2 + math.pi * i / 20),
                 cy + r * math.sin(-math.pi / 2 + math.pi * i / 20)) for i in range(21)]
        pts.append((x0, y1))
    elif base in ("OR", "XOR"):
        xs = x0 + (w * 0.1 if base == "XOR" else 0)
        topo = bezier((xs, y0), (xs + (xf - xs) * 0.6, y0), (xf, cy))
        baixo = bezier((xf, cy), (xs + (xf - xs) * 0.6, y1), (xs, y1))
        tras = bezier((xs, y1), (xs + (xf - xs) * 0.25, cy), (xs, y0))
        pts = topo + baixo[1:] + tras[1:]
    else:  # NOT (e qualquer outra coisa de 1 entrada)
        pts = [(x0, y0), (xf, cy), (x0, y1)]
    pygame.draw.polygon(s, BRANCO, pts)
    pygame.draw.lines(s, PRETO, True, pts, 4)
    if base == "XOR":
        pygame.draw.lines(s, PRETO, False, bezier((x0, y1), (x0 + (xf - x0) * 0.2, cy), (x0, y0)), 4)
    if bolha:
        pygame.draw.circle(s, BRANCO, (int(xf + rb), int(cy)), rb)
        pygame.draw.circle(s, PRETO, (int(xf + rb), int(cy)), rb, 3)
    if vertical:
        s = pygame.transform.rotate(s, 90)
    _cache_formas[chave] = s
    return s


# ======================= MODELO DO CIRCUITO =====================
class Entrada:
    """Sinal fixo (0 ou 1) que entra por baixo do circuito."""

    def __init__(self, valor):
        self.valor = bool(valor)
        self.x = self.y = 0.0

    def calcular(self):
        return self.valor

    def nivel(self):
        return 0

    def todos(self):
        yield self


class NoPorta:
    def __init__(self, tipo, filhos, fixo=False):
        self.tipo, self.filhos, self.fixo = tipo, filhos, fixo
        self.x = self.y = 0.0
        if len(filhos) not in (1, 2):
            raise ValueError("Cada porta precisa ter 1 ou 2 entradas")
        if len(filhos) == 1 and tipo not in UMA_ENTRADA:
            raise ValueError(f"A porta {tipo} precisa de 2 entradas")

    def calcular(self):
        if self.tipo in UMA_ENTRADA:
            return FUNCOES[self.tipo]([self.filhos[0].calcular()])
        return FUNCOES[self.tipo]([f.calcular() for f in self.filhos])

    def nivel(self):
        return 1 + max(f.nivel() for f in self.filhos)

    def todos(self):
        yield self
        for f in self.filhos:
            yield from f.todos()

    def portas(self):
        return [n for n in self.todos() if isinstance(n, NoPorta)]

    def entradas(self):
        return [n for n in self.todos() if isinstance(n, Entrada)]


def montar_circuito(spec):
    if isinstance(spec, int):
        return Entrada(spec)
    tipo = spec[0]
    return NoPorta(tipo.lstrip("!"), [montar_circuito(s) for s in spec[1:]], fixo=tipo.startswith("!"))


class Valvula:
    def __init__(self, dados, caminho, cano):
        self.nome, self.objetivo = dados["nome"], dados["objetivo"]
        self.pos, self.caixa = dados["pos"], dados["caixa"]
        self.cano = cano  # "agua" ou o índice do veneno
        self.d = dist_no_caminho(caminho, self.pos)
        _, (dx, dy) = ponto_em(caminho, self.d)
        self.cano_horizontal = abs(dx) > abs(dy)
        self.circuito = montar_circuito(dados["circuito"])
        self.abertura = 0.0
        self.rect_caixa = pygame.Rect(0, 0, 60, 60)
        self.rect_caixa.center = self.caixa

    def saida(self):
        return bool(self.circuito.calcular())

    def barreira(self):
        if self.cano_horizontal:   # barreira em pé, sobe para abrir
            r = pygame.Rect(0, 0, 28, 84)
            r.center = (self.pos[0], self.pos[1] - 80 * self.abertura)
        else:                      # barreira deitada, vai para a direita para abrir
            r = pygame.Rect(0, 0, 84, 28)
            r.center = (self.pos[0] + 80 * self.abertura, self.pos[1])
        return r


# ============================ CENAS ============================
class MenuPrincipal:
    def __init__(self, jogo):
        self.jogo = jogo
        self.t = 0.0
        w, h, y = 210, 170, 470
        self.btn_jogar = Botao((VW * 0.28 - w / 2, y, w, h), "JOGAR", 24, icone=icone_play, tam_icone=80)
        self.btn_opcoes = Botao((VW * 0.5 - w / 2, y, w, h), "OPÇÕES", 24, icone=icone_engrenagens,
                                tam_icone=90)
        self.btn_sair = Botao((VW * 0.72 - w / 2, y, w, h), "SAIR", 24, icone=icone_sair, tam_icone=90)

    def evento(self, ev):
        j = self.jogo
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            j.abrir_dialogo(DialogoSair(j))
        if self.btn_jogar.evento(ev, j):
            j.trocar_cena(SelecaoFases(j))
        if self.btn_opcoes.evento(ev, j):
            j.abrir_dialogo(DialogoOpcoes(j, em_jogo=False))
        if self.btn_sair.evento(ev, j):
            j.abrir_dialogo(DialogoSair(j))

    def atualizar(self, dt):
        self.t += dt

    def desenhar(self, s, mouse):
        ondas(s, 0, 360, 70, self.t * 1.5)
        ondas(s, VW - 360, VW, 70, self.t * 1.5 + 2)
        img = self.jogo.titulo_img
        if img:
            s.blit(img, img.get_rect(center=(VW / 2, 250)))
        else:
            texto(s, "PORTAS LÓGICAS", 72, BRANCO, centro=(VW / 2, 230), contorno=PRETO, esp=5)
            texto(s, "o desafio das válvulas", 26, AZUL_ESCURO, centro=(VW / 2, 310))
        for b in (self.btn_jogar, self.btn_opcoes, self.btn_sair):
            b.desenhar(s, mouse)


class SelecaoFases:
    def __init__(self, jogo):
        self.jogo = jogo
        prog = jogo.progresso
        self.voltar = Botao((30, 24, 150, 52), "Voltar", 20, icone=None, raio=26)
        self.botoes = []
        w, h, gap = 150, 110, 40
        x0 = (VW - (5 * w + 4 * gap)) / 2
        for i in range(TOTAL_BOTOES_FASE):
            lin, col = divmod(i, 5)
            existe = i < len(NIVEIS)
            em_dev = existe and NIVEIS[i].get("em_desenvolvimento", False)
            liberada = existe and not em_dev and i < prog["desbloqueadas"]
            concluida = (i + 1) in prog["concluidas"]
            b = Botao((x0 + col * (w + gap), 190 + lin * (h + 45), w, h), str(i + 1), 40,
                      cor=VERDE if concluida else AZUL, habilitado=liberada)
            self.botoes.append((b, i, existe, concluida, em_dev))

    def evento(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.jogo.trocar_cena(MenuPrincipal(self.jogo))
            return
        if self.voltar.evento(ev, self.jogo):
            self.jogo.trocar_cena(MenuPrincipal(self.jogo))
            return
        for b, i, *_ in self.botoes:
            if b.evento(ev, self.jogo):
                self.jogo.iniciar_fase(i)
                return

    def atualizar(self, dt):
        pass

    def desenhar(self, s, mouse):
        texto(s, "Selecione a fase desejada", 36, BRANCO, centro=(VW / 2, 110), contorno=PRETO, esp=3)
        self.voltar.desenhar(s, mouse)
        dica = None
        for b, i, existe, concluida, em_dev in self.botoes:
            b.desenhar(s, mouse)
            if not b.habilitado:
                icone_cadeado(s, (b.rect.right - 22, b.rect.y + 22), 34)
                if b.rect.collidepoint(mouse):
                    em_breve = not existe or em_dev
                    dica = ("Em breve!" if em_breve else "Complete a fase anterior para liberar", b.rect)
            elif concluida:
                icone_check(s, (b.rect.right - 22, b.rect.y + 22), 26)
        if dica:
            txt, r = dica
            img = fonte(14).render(txt, True, BRANCO)
            caixa = img.get_rect(midtop=(r.centerx, r.bottom + 8)).inflate(16, 10)
            pygame.draw.rect(s, "#333333", caixa, border_radius=6)
            s.blit(img, img.get_rect(center=caixa.center))


class Fase:
    VELOCIDADE = 420  # pixels por segundo

    def __init__(self, jogo, indice):
        self.jogo, self.indice = jogo, indice
        self.nivel = NIVEIS[indice]
        self.caminho = self.nivel["agua"]
        self.venenos = self.nivel.get("venenos", [])
        self.L = comprimento(self.caminho)
        self.valvulas = []
        for dados in self.nivel["valvulas"]:
            cano = "agua"
            for i, cv in enumerate(self.venenos):   # em qual cano a válvula está?
                try:
                    dist_no_caminho(cv, dados["pos"])
                    cano = i
                    break
                except ValueError:
                    pass
            self.valvulas.append(Valvula(dados, self.caminho if cano == "agua" else self.venenos[cano], cano))
        self.juncoes = [dist_no_caminho(self.caminho, cv[-1]) for cv in self.venenos]

        self.tempo = float(self.nivel.get("tempo", TEMPO_FASE))
        self.estado = "config"   # config -> fluindo -> fim
        self.travadas = None     # saídas dos circuitos quando a energia foi ligada
        self.t_fluxo = 0.0
        self.t_anim = 0.0
        self.trocas = 0
        self.aviso, self.t_aviso = "", 0.0

        # HUD (canto superior direito, igual ao protótipo)
        self.btn_dica = Botao((1094, 12, 54, 54), icone=lambda s, c, t, f: icone_lampada(
            s, c, t, f, self.jogo.config["dicas"]), transparente=True)
        self.btn_opcoes = Botao((1154, 12, 54, 54), icone=icone_engrenagem, transparente=True)
        self.btn_pausa = Botao((1214, 12, 54, 54), icone=icone_x, transparente=True)
        self.btn_energia = Botao((24, 646, 240, 56), "Ligar energia!", 19, raio=28, som="agua")

    # ---------- lógica ----------
    def valvula_aberta(self, v):
        return self.estado != "config" and self.travadas[self.valvulas.index(v)]

    def _limite(self, cano, caminho_len, desde=0.0, considerar_estado=True):
        """Até onde o líquido vai num cano: para na primeira válvula fechada depois de 'desde'."""
        for v in sorted((v for v in self.valvulas if v.cano == cano), key=lambda v: v.d):
            if v.d > desde and not (considerar_estado and self.valvula_aberta(v)):
                return v.d - 16
        return caminho_len

    def frentes(self):
        """Quanto de cada cano está cheio: (água, [(veneno_no_cano_dele, veneno_no_cano_principal)])."""
        avanco = max(0.0, self.t_fluxo) * self.VELOCIDADE
        pre_agua = self._limite("agua", self.L, considerar_estado=False)
        agua = min(pre_agua + avanco, self._limite("agua", self.L))
        res = []
        for i, cv in enumerate(self.venenos):
            lv = comprimento(cv)
            pre = self._limite(i, lv, considerar_estado=False)
            lim = self._limite(i, lv)
            frente = min(pre + avanco, lim)
            no_principal = 0.0
            if lim >= lv:
                fim = self._limite("agua", self.L, desde=self.juncoes[i])
                no_principal = min(max(0.0, pre + avanco - lv), max(0.0, fim - self.juncoes[i]))
            res.append((frente, no_principal))
        return agua, res

    def chegou(self):
        agua, venenos = self.frentes()
        chegou_agua = agua >= self.L - 1
        chegou_veneno = any(self.juncoes[i] + vp >= self.L - 1 for i, (_, vp) in enumerate(venenos))
        return chegou_agua, chegou_veneno

    def ligar_energia(self, por_tempo=False):
        if self.estado != "config":
            return
        self.estado = "fluindo"
        self.t_fluxo = -0.7          # primeiro as válvulas se mexem, depois o líquido anda
        self.travadas = [v.saida() for v in self.valvulas]
        self.jogo.dialogos = [d for d in self.jogo.dialogos if not isinstance(d, DialogoCircuito)]
        if por_tempo:
            self.aviso, self.t_aviso = "O tempo acabou! A energia ligou sozinha!", 3.0
            self.jogo.sons.tocar("agua")

    def evento(self, ev):
        j = self.jogo
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                j.abrir_dialogo(DialogoPausa(j, self))
            elif ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.estado == "config":
                    j.sons.tocar("agua")
                self.ligar_energia()
            else:   # teclas 1, 2, 3... abrem o circuito de cada válvula
                nome = pygame.key.name(ev.key)
                if nome.isdigit() and 1 <= int(nome) <= len(self.valvulas) and self.estado == "config":
                    j.sons.tocar("clique")
                    j.abrir_dialogo(DialogoCircuito(j, self, self.valvulas[int(nome) - 1]))
            return
        if self.btn_pausa.evento(ev, j):
            j.abrir_dialogo(DialogoPausa(j, self))
        if self.btn_opcoes.evento(ev, j):
            j.abrir_dialogo(DialogoOpcoes(j, em_jogo=True))
        self.btn_dica.habilitado = j.config["dicas"]
        if self.btn_dica.evento(ev, j):
            j.abrir_dialogo(DialogoDica(j, self))
        self.btn_energia.habilitado = self.estado == "config"
        if self.btn_energia.evento(ev, j):
            self.ligar_energia()
        if self.estado == "config" and ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            for v in self.valvulas:
                if v.rect_caixa.collidepoint(ev.pos):
                    j.sons.tocar("clique")
                    j.abrir_dialogo(DialogoCircuito(j, self, v))
                    return

    def atualizar(self, dt):
        self.t_anim += dt
        self.t_aviso = max(0.0, self.t_aviso - dt)
        for i, v in enumerate(self.valvulas):
            alvo = 0.0 if self.estado == "config" else float(self.travadas[i])
            v.abertura += (alvo - v.abertura) * min(1.0, dt * 8)

        if self.estado == "config":
            self.tempo -= dt
            if self.tempo <= 0:
                self.tempo = 0
                self.ligar_energia(por_tempo=True)
        elif self.estado == "fluindo":
            self.t_fluxo += dt
            maior = self.L + max([comprimento(cv) for cv in self.venenos] + [0])
            if self.t_fluxo >= maior / self.VELOCIDADE + 1.0:
                self.terminar()

    def terminar(self):
        self.estado = "fim"
        chegou_agua, chegou_veneno = self.chegou()
        venceu = chegou_agua and not chegou_veneno
        j = self.jogo
        if venceu:
            prog = j.progresso
            prog["desbloqueadas"] = min(len(NIVEIS), max(prog["desbloqueadas"], self.indice + 2))
            if self.indice + 1 not in prog["concluidas"]:
                prog["concluidas"].append(self.indice + 1)
            if SALVAR_PROGRESSO:
                salvar_json("progresso.json", prog)
            msg = (f"Água limpa na banheira! Você trocou {self.trocas} porta(s) "
                   f"e sobraram {int(self.tempo)} s.")
            j.sons.tocar("vitoria")
        else:
            if chegou_veneno:
                msg = "O veneno chegou à banheira!"
            else:
                msg = "A água não chegou na banheira!"
            j.sons.tocar("derrota")
        j.abrir_dialogo(DialogoResultado(j, self, venceu, msg))

    # ---------- desenho ----------
    def desenhar(self, s, mouse):
        cfg = self.jogo.config
        hud = cfg["hud"]
        agua, venenos = self.frentes()
        chegou_agua, chegou_veneno = self.chegou()

        # canos e líquidos
        for cv in self.venenos:
            desenhar_cano(s, cv)
        desenhar_cano(s, self.caminho)
        linha_grossa(s, AGUA, trecho(self.caminho, 0, agua), 20)
        for i, (frente, no_principal) in enumerate(venenos):
            linha_grossa(s, VERDE_VENENO, trecho(self.venenos[i], 0, frente), 20)
            if no_principal > 0:
                linha_grossa(s, VERDE_VENENO, trecho(self.caminho, self.juncoes[i],
                                                     self.juncoes[i] + no_principal), 20)
        fim = self.caminho[-1]
        if (chegou_agua or chegou_veneno) and self.estado == "fluindo":   # jato caindo
            pygame.draw.line(s, VERDE_VENENO if chegou_veneno else AGUA,
                             (fim[0], fim[1] + 18), (fim[0], fim[1] + 45), 12)

        # torneira e barris
        ini = self.caminho[0]
        pygame.draw.rect(s, CANO_ESCURO, (ini[0] - 24, ini[1] - 22, 48, 24), border_radius=4)
        gota_y = ini[1] - 55 + math.sin(self.t_anim * 4) * 3
        pygame.draw.circle(s, AGUA, (ini[0], int(gota_y + 6)), 11)
        pygame.draw.polygon(s, AGUA, [(ini[0] - 10, gota_y + 2), (ini[0] + 10, gota_y + 2), (ini[0], gota_y - 16)])
        for cv in self.venenos:
            self.desenhar_barril(s, cv[0])

        # válvulas
        for v in self.valvulas:
            self.desenhar_valvula(s, v, mouse, hud, cfg["dicas"])

        self.desenhar_banheira(s, chegou_agua, chegou_veneno)

        # HUD superior
        if hud:
            seg = math.ceil(self.tempo)
            texto(s, f"Tempo: {seg // 60}:{seg % 60:02d}", 22, BRANCO if seg > 10 else "#ff5252",
                  topleft=(24, 22), contorno=PRETO, esp=2)
            texto(s, f"Trocas: {self.trocas}", 16, BRANCO, topleft=(24, 56), contorno=PRETO, esp=1)
        texto(s, f"Fase {self.indice + 1}", 36, BRANCO, centro=(VW / 2, 38), contorno=PRETO, esp=3)
        self.btn_dica.habilitado = cfg["dicas"]
        self.btn_energia.habilitado = self.estado == "config"
        for b in (self.btn_dica, self.btn_opcoes, self.btn_pausa):
            b.desenhar(s, mouse)
        if self.estado == "config":
            self.btn_energia.desenhar(s, mouse)
            raio_eletrico(s, (self.btn_energia.rect.x + 26, self.btn_energia.rect.centery), 30, True)

        if self.t_aviso > 0:
            r = texto(s, self.aviso, 20, BRANCO, centro=(VW / 2, 88))
            pygame.draw.rect(s, LARANJA, r.inflate(24, 12), border_radius=10)
            texto(s, self.aviso, 20, BRANCO, centro=(VW / 2, 88))

    def desenhar_valvula(self, s, v, mouse, hud, dicas):
        """Antes de ligar a energia: placa desligada (raio cinza).
        Depois: ENERGIZADA = brilho amarelo pulsando, faíscas e corrente correndo pela haste;
        SEM ENERGIA = placa escura com raio apagado."""
        barreira = v.barreira()
        energizada = self.estado != "config" and self.travadas[self.valvulas.index(v)]
        sem_energia = self.estado != "config" and not energizada
        t = self.t_anim
        r = v.rect_caixa
        cx, cy = r.center
        bx, by = barreira.center

        # haste da válvula (com corrente elétrica correndo quando energizada)
        pygame.draw.line(s, "#555555", v.caixa, barreira.center, 8)
        if energizada:
            pygame.draw.line(s, AMARELO, v.caixa, barreira.center, 4)
            dist = math.dist(v.caixa, barreira.center)
            if dist > 1:
                ux, uy = (bx - cx) / dist, (by - cy) / dist
                d = (t * 90) % 18
                while d < dist:
                    pygame.draw.circle(s, BRANCO, (int(cx + ux * d), int(cy + uy * d)), 3)
                    d += 18
        desenhar_barreira(s, barreira)

        # brilho pulsante atrás da placa
        if energizada:
            ligou_ha = max(0.0, self.t_fluxo + 0.7)        # flash forte logo que liga
            pulso = 0.5 + 0.5 * math.sin(t * 6)
            raio_brilho = int(52 + 10 * pulso + max(0.0, 30 * (1 - ligou_ha * 3)))
            halo = pygame.Surface((raio_brilho * 2, raio_brilho * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 220, 0, 70), (raio_brilho, raio_brilho), raio_brilho)
            pygame.draw.circle(halo, (255, 240, 120, 110), (raio_brilho, raio_brilho), int(raio_brilho * 0.75))
            s.blit(halo, (cx - raio_brilho, cy - raio_brilho))

        hover = self.estado == "config" and r.collidepoint(mouse)
        if hover:
            UI["mao"] = True
        rr = r.move(0, -2) if hover else r
        if energizada:
            fundo, borda, larg = "#fff3a0", "#e0a800", 5
        elif sem_energia:
            fundo, borda, larg = "#5e5e5e", "#2a2a2a", 3
        else:
            fundo, borda, larg = "#eeeeee", PRETO, 3
        pygame.draw.rect(s, fundo, rr)
        pygame.draw.rect(s, LARANJA if hover else borda, rr, 4 if hover else larg)
        pygame.draw.polygon(s, BRANCO if not sem_energia else "#8a8a8a", octogono(rr.center, 24))
        pygame.draw.polygon(s, "#444444", octogono(rr.center, 24), 3)
        raio_eletrico(s, rr.center, 31, energizada)

        # faíscas em volta da placa energizada
        if energizada:
            for k in range(6):
                if math.sin(t * 13 + k * 2.1) < 0.1:      # piscam em momentos diferentes
                    continue
                ang = k * math.pi / 3 + t * 1.5
                x0, y0 = cx + math.cos(ang) * 38, cy + math.sin(ang) * 38
                x1, y1 = cx + math.cos(ang + 0.15) * 46, cy + math.sin(ang + 0.15) * 46
                x2, y2 = cx + math.cos(ang - 0.05) * 54, cy + math.sin(ang - 0.05) * 54
                pygame.draw.lines(s, "#ffb000", False, [(x0, y0), (x1, y1), (x2, y2)], 3)

    def desenhar_barril(self, s, topo_cano):
        x, y = topo_cano
        corpo = pygame.Rect(x - 32, y - 87, 64, 80)
        pygame.draw.rect(s, "#2b2b2b", corpo, border_radius=10)
        for yy in (corpo.y + 18, corpo.bottom - 18):
            pygame.draw.line(s, "#555555", (corpo.x + 3, yy), (corpo.right - 3, yy), 4)
        pygame.draw.ellipse(s, VERDE_VENENO, (corpo.x + 4, corpo.y - 8, corpo.w - 8, 18))
        pygame.draw.ellipse(s, "#1a1a1a", (corpo.x + 4, corpo.y - 8, corpo.w - 8, 18), 2)
        c = corpo.center  # caveirinha
        pygame.draw.circle(s, BRANCO, c, 11)
        pygame.draw.rect(s, BRANCO, (c[0] - 6, c[1] + 6, 12, 7))
        for dx in (-4, 4):
            pygame.draw.circle(s, "#2b2b2b", (c[0] + dx, c[1] - 1), 3)

    def desenhar_banheira(self, s, chegou_agua, chegou_veneno):
        fx, fy = self.caminho[-1]
        cab = (fx + 82, fy + 28)
        morto = self.estado != "config" and chegou_veneno
        feliz = chegou_agua and not chegou_veneno
        if morto:   # caveira
            pygame.draw.circle(s, "#f4f4f4", cab, 22)
            pygame.draw.circle(s, "#999999", cab, 22, 2)
            pygame.draw.rect(s, "#f4f4f4", (cab[0] - 12, cab[1] + 12, 24, 12), border_radius=3)
            for dx in (-8, 8):
                pygame.draw.circle(s, PRETO, (cab[0] + dx, cab[1] - 2), 6)
            pygame.draw.polygon(s, PRETO, [(cab[0], cab[1] + 6), (cab[0] - 3, cab[1] + 11),
                                           (cab[0] + 3, cab[1] + 11)])
        else:
            pygame.draw.circle(s, "#f1c27d", cab, 22)
            pygame.draw.ellipse(s, BRANCO, (cab[0] - 22, cab[1] - 32, 44, 24))  # toalha
            pygame.draw.ellipse(s, "#cfcfcf", (cab[0] - 22, cab[1] - 32, 44, 24), 2)
            for dx in (-7, 7):
                pygame.draw.circle(s, PRETO, (cab[0] + dx, cab[1] + 2), 3)
            boca = pygame.Rect(cab[0] - 7, cab[1] + 4, 14, 10)
            if feliz:
                pygame.draw.arc(s, PRETO, boca, math.pi, 2 * math.pi, 2)
            elif self.estado == "fim":
                pygame.draw.arc(s, PRETO, boca.move(0, 5), 0, math.pi, 2)
            else:
                pygame.draw.line(s, PRETO, (cab[0] - 5, cab[1] + 11), (cab[0] + 5, cab[1] + 11), 2)
        corpo = pygame.Rect(fx - 40, fy + 42, 180, 66)
        pygame.draw.rect(s, BRANCO, corpo, border_bottom_left_radius=40, border_bottom_right_radius=40)
        pygame.draw.rect(s, "#777777", corpo, 2, border_bottom_left_radius=40, border_bottom_right_radius=40)
        borda = pygame.Rect(fx - 50, fy + 34, 200, 14)
        pygame.draw.rect(s, "#e8e8e8", borda, border_radius=6)
        pygame.draw.rect(s, "#777777", borda, 2, border_radius=6)
        for x in (fx - 20, fx + 120):
            pygame.draw.circle(s, "#777777", (x, fy + 112), 7)
        if chegou_agua or chegou_veneno:
            pygame.draw.ellipse(s, VERDE_VENENO if chegou_veneno else AGUA, (fx - 44, fy + 26, 110, 16))
            if feliz:
                for i in range(4):
                    y = fy + 20 - ((self.t_anim * 30 + i * 12) % 40)
                    pygame.draw.circle(s, BRANCO, (fx - 30 + i * 22, int(y)), 4, 1)


# ============================= JOGO ============================
class Jogo:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Portas Lógicas - Jogo Educativo")
        self.config = carregar_json("config.json", CONFIG_PADRAO)
        if SALVAR_PROGRESSO:
            self.progresso = carregar_json("progresso.json", PROGRESSO_PADRAO)
        else:   # cada vez que o jogo abre, começa do zero
            self.progresso = {"desbloqueadas": 1, "concluidas": []}
        self.janela = None
        self.aplicar_config(True)
        self.tela = pygame.Surface((VW, VH), 0, 32)
        self.sons = Sons()
        self.sons.volume = self.config["volume"]
        self.titulo_img = self.carregar_titulo()
        self.cena = MenuPrincipal(self)
        self.dialogos = []
        self.rodando = True
        self.mouse = (0, 0)
        self.cursor_mao = None
        self.relogio = pygame.time.Clock()

    def carregar_titulo(self):
        caminho = os.path.join(BASE, "title.png")
        if not os.path.exists(caminho):
            return None
        img = pygame.image.load(caminho).convert_alpha()
        esc = min(VW * 0.6 / img.get_width(), VH * 0.45 / img.get_height())
        return pygame.transform.smoothscale(img, (int(img.get_width() * esc), int(img.get_height() * esc)))

    def aplicar_config(self, mudar_resolucao=False):
        ESCALA_FONTE[0] = self.config["fonte"] / 12
        _cache_fontes.clear()
        if hasattr(self, "sons"):
            self.sons.volume = self.config["volume"]
        if mudar_resolucao or self.janela is None:
            w, h = RESOLUCOES[self.config["resolucao"]]
            flags = 0
            try:
                dw, dh = pygame.display.get_desktop_sizes()[0]
                if w > dw or h > dh:
                    flags = pygame.FULLSCREEN
            except (AttributeError, IndexError, pygame.error):
                pass
            self.janela = pygame.display.set_mode((w, h), flags)

    def iniciar_fase(self, i):
        if NIVEIS[i].get("em_desenvolvimento") and not TESTAR_FASES_EM_DESENVOLVIMENTO:
            # abre o aviso por cima da tela atual (ex.: por cima do "Você Venceu!!")
            self.abrir_dialogo(DialogoAviso(
                self, f"Fase {i + 1}",
                "Esta fase ainda está em desenvolvimento. Em breve, novos desafios com portas lógicas!"))
        else:
            self.trocar_cena(Fase(self, i))

    def abrir_dialogo(self, d):
        self.dialogos.append(d)

    def fechar_dialogo(self, d):
        if d in self.dialogos:
            self.dialogos.remove(d)

    def trocar_cena(self, cena):
        self.cena = cena
        self.dialogos.clear()

    def para_virtual(self, pos):
        ww, wh = self.janela.get_size()
        esc = min(ww / VW, wh / VH)
        ox, oy = (ww - VW * esc) / 2, (wh - VH * esc) / 2
        return (int((pos[0] - ox) / esc), int((pos[1] - oy) / esc))

    def executar(self):
        while self.rodando:
            dt = min(self.relogio.tick(60) / 1000, 0.05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.rodando = False
                    continue
                if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    ev = pygame.event.Event(ev.type, pos=self.para_virtual(ev.pos), button=ev.button)
                elif ev.type != pygame.KEYDOWN:
                    continue
                alvo = self.dialogos[-1] if self.dialogos else self.cena
                alvo.evento(ev)

            self.mouse = self.para_virtual(pygame.mouse.get_pos())
            if all(not d.pausa for d in self.dialogos):   # a maioria das janelas pausa o jogo
                self.cena.atualizar(dt)

            UI["mao"] = False
            self.tela.fill(FUNDO)
            sem_mouse = (-999, -999)
            self.cena.desenhar(self.tela, sem_mouse if self.dialogos else self.mouse)
            for d in self.dialogos:
                d.desenhar(self.tela, self.mouse if d is self.dialogos[-1] else sem_mouse)

            if UI["mao"] != self.cursor_mao:
                self.cursor_mao = UI["mao"]
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if UI["mao"]
                                            else pygame.SYSTEM_CURSOR_ARROW)
                except (AttributeError, pygame.error):
                    pass

            if self.janela.get_size() == (VW, VH):
                self.janela.blit(self.tela, (0, 0))
            else:
                self.janela.blit(pygame.transform.smoothscale(self.tela, self.janela.get_size()), (0, 0))
            pygame.display.flip()

        if SALVAR_PROGRESSO:
            salvar_json("progresso.json", self.progresso)
        pygame.quit()


if __name__ == "__main__":
    Jogo().executar()