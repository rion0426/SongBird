import sys
import pygame
import time
from pygame.locals import *
import aubio
import numpy as np
import pyaudio
import threading
import random

RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,0,255)
WHITE = (255,255,255)
BLACK = (0,0,0)

# 볼륨 바(Volume) 5구간 색
VOLUME_SEGMENT_COLORS = [
    (255,102,102),   # 빨강
    (255,178,102),   # 주황
    (255,255,102),   # 노랑
    (178,255,102),   # 연두
    (102,255,178),   # 민트
]

# 피치 바(Pitch) 5구간 색
PITCH_SEGMENT_COLORS = [
    (102,178,255),   # 연한 파랑
    (102,102,255),   # 파랑
    (178,102,255),   # 보라
    (255,102,255),   # 마젠타
    (255,102,178),   # 핑크
]

# 오디오 기본 설정
BUFFER_SIZE = 1024 # 한번에 가져올 샘플 개수
CHANNELS = 1 # 채널은 하나
RATE = 44100 # 1초에 44100번 샘플링
NOISE_GATE = 80
SMOOTH = 0.9 # 새 볼륨 값을 받아들일 수치, 부드러움 수치 1에 가까울수록 부드러움

maxVolume = 1100
minVolume = 400
maxPitch = 400
minPitch = 50

pitch,volume,rawVolume = 0,0,0 # 피치와 보정 볼륨, raw 볼륨값

p = pyaudio.PyAudio() # pyaudio 장치 객체 생성!!
stream = p.open(
    format=pyaudio.paFloat32, # float 형식으로 오디오 받음
    channels=CHANNELS,
    rate=RATE,
    input=True, # 마이크를 읽기 모드로 연다
    frames_per_buffer=BUFFER_SIZE
)

# Hz 계산용 aubio pitch 객체 
pitch_o = aubio.pitch("default", BUFFER_SIZE*4, BUFFER_SIZE, RATE)
pitch_o.set_unit("Hz") # Hz 단위로 받겠다

def audioInfoLoop():
    global stream,volume,pitch,rawVolume
    while True:
        data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.float32)
     
        # 주파수
        pitch = pitch_o(samples)[0]

        # 볼륨
        rawVolume = np.sqrt(np.sum(samples**2) / len(samples))
        rawVolume = float(np.clip(rawVolume * 5000,0,maxVolume))  # 1~1000 스케일 정규화
        volume = (volume * SMOOTH) + (rawVolume * (1 - SMOOTH)) # 스파이크 완화용 지수평활

# 바 그리기 함수
def drawBar(surface, x, y, width, height, maxValue, currentValue, segmentColors):
    pygame.draw.rect(surface, WHITE, (x, y, width, height))
    segmentNum = len(segmentColors)
    if segmentNum > 0:
        sgemntSize = float(maxValue) / float(segmentNum)
        for i, color in enumerate(segmentColors):
            segMin = i * sgemntSize
            segMax = (i + 1) * sgemntSize

            minY = y + height - (segMin / maxValue) * height
            maxY = y + height - (segMax / maxValue) * height
            rangeHeight = max(minY - maxY, 1)
            pygame.draw.rect(surface, color, (x, maxY, width, rangeHeight))

    # 빨간선 표시
    ratio = max(0.0, min(float(currentValue) / maxValue, 1.0))
    currentY = y + height - (ratio * height)
    pygame.draw.line(surface, RED, (x, currentY), (x + width, currentY), 2)

audio_thread = threading.Thread(target=audioInfoLoop,daemon=True)
audio_thread.start()

pygame.init()

gameWidth = 500
sidebarWidth = 150
WIDTH = gameWidth + sidebarWidth
HEIGHT = 800
FPS = 60
clock = pygame.time.Clock()

score = 0
highScore = 0
lastScoreTime = time.time()
font = pygame.font.Font(None, 28)      # 점수 폰트
labelFont = pygame.font.Font(None, 24) # 라벨 폰트
titleFont = pygame.font.Font(None, 72) # 메뉴 제목 폰트
subTitleFont = pygame.font.Font(None, 32) # 메뉴 제목 폰트
menuFont = pygame.font.Font(None, 32)  # 메뉴 버튼 폰트

screen = pygame.display.set_mode((WIDTH,HEIGHT)) # 창 크기 설정
pygame.display.set_caption("SongBird") # 창 이름 설정

# 이미지를 불러오기!!
groundImage = pygame.image.load("img/ground.png")
chickenImage = pygame.image.load("img/chicken.png")
birdImage = pygame.image.load("img/bird.png")
wallImage = pygame.image.load("img/wallpaper.png")
masterImage = pygame.image.load("img/sleepingGuy.png")
standedMasterImage = pygame.image.load("img/standingGuy.png")
glassImage = pygame.image.load("img/glass.png").convert_alpha() # 떨어지는 몬스터 이미지
chargedGlassImage = pygame.image.load("img/dieGlass.png").convert_alpha()  # 떨어지는 몬스터 이미지
brokenGlassImage = pygame.image.load("img/brokenGlass.png")

# 소리 불러오기
breakSound = pygame.mixer.Sound("audio/glassBreak.mp3")
gameOverSound = pygame.mixer.Sound("audio/gameOver.mp3")
masterVoice = pygame.mixer.Sound("audio/mastervoice.wav")
chickenSound = pygame.mixer.Sound("audio/chicken.mp3")

# 사이드바는 특별하니까 따로 처리
sidebarImage = pygame.image.load("img/sidebar.png")
sidebarImage = pygame.transform.scale(sidebarImage, (sidebarWidth, HEIGHT))

groundWidth = gameWidth+400
groundHeight = 100
groundRect = pygame.Rect(-200,HEIGHT - groundHeight,groundWidth,groundHeight)
groundImage = pygame.transform.scale(groundImage, (groundWidth, groundHeight))

birdHeight = 60
birdWidth = 90
birdRect = pygame.Rect(100,HEIGHT - groundHeight-60,birdWidth,birdHeight)
livingBirdImage = pygame.transform.scale(birdImage, (birdWidth,birdHeight))
birdImage = livingBirdImage.copy()

birdSpeed = 5
birdCooked = False

chickenHeight = 60
chickenWidth = 90
chickenRect = pygame.Rect(100,HEIGHT - groundHeight-60,chickenWidth,chickenHeight)
chickenImage = pygame.transform.scale(chickenImage, (chickenWidth,chickenHeight))

masterHeight = 100
masterWidth = 200
masterRect = pygame.Rect(200,HEIGHT - groundHeight - masterHeight+50,masterWidth,masterHeight)
masterImage = pygame.transform.scale(masterImage, (masterWidth, masterHeight))
# 자는 이미지 백업
sleepingMasterImage = masterImage.copy()

# 일어난 주인 이미지
standedMasterHeight = 200
standedMasterWidth = 100
standedMasterRect = pygame.Rect(180,HEIGHT - groundHeight - standedMasterHeight+50,standedMasterWidth,standedMasterHeight)
standedMasterImage = pygame.transform.scale(standedMasterImage, (standedMasterWidth, standedMasterHeight))

wallHeight = HEIGHT-groundHeight
wallWidth = gameWidth + 400
wallRect = pygame.Rect(-200,HEIGHT - groundHeight - wallHeight,wallWidth,wallHeight)
wallImage = pygame.transform.scale(wallImage, (wallWidth, wallHeight))

# 메뉴용 UI Rect들
menuRect = pygame.Rect(0, 0, gameWidth, HEIGHT)
buttonWidth = 200
button_height = 60
startButtonRect = pygame.Rect(gameWidth // 2 - buttonWidth // 2,HEIGHT // 2 + 50,buttonWidth,button_height)
soundButtonRect = pygame.Rect(gameWidth // 2 - buttonWidth // 2,HEIGHT // 2 - 20,buttonWidth,button_height)
menuButtonRect = pygame.Rect(gameWidth // 2 - buttonWidth // 2,HEIGHT // 2+250,buttonWidth,button_height)

#음향 조정 UI Rect들
minVolumePlusButtonRect = pygame.Rect(gameWidth // 2+30, HEIGHT // 6+350-15,30,30,)
minVolumeMinusButtonRect = pygame.Rect(gameWidth // 2+60, HEIGHT // 6+350-15,30,30)
minPitchPlusButtonRect = pygame.Rect(gameWidth // 2+30, HEIGHT // 6+100-15,30,30)
minPitchMinusButtonRect = pygame.Rect(gameWidth // 2+60, HEIGHT // 6+100-15,30,30)

maxVolumePlusButtonRect = pygame.Rect(gameWidth // 2+30, HEIGHT // 6+400-15,30,30)
maxVolumeMinusButtonRect = pygame.Rect(gameWidth // 2+60, HEIGHT // 6+400-15,30,30)
maxPitchPlusButtonRect = pygame.Rect(gameWidth // 2+30, HEIGHT // 6+150-15,30,30)
maxPitchMinusButtonRect = pygame.Rect(gameWidth // 2+60, HEIGHT // 6+150-15,30,30)

monsters = pygame.sprite.Group()
monsterFallSpeed = 0.3
SPAWN_COOL_START = 9.0
MIN_SPAWN_COOL = 3.0
SPAWN_COOL_DIGIT = 0.02  # 진행 시간당 스폰 쿨다운 감소량
lastSpawn = time.time()

lastKillTime = 0 # 게임오버때 쓰는 변수들
killCool = 0.5
killGroup = []
clickTimeStamp = 0
runStartTime = None
DIFFICULTY_RATE = 0.01  # 가속 비율
MAX_DIFFICULTY = 3.0    # 가속 상한

class Monster(pygame.sprite.Sprite):

    def __init__(self, x):
        super().__init__()
        self.width = 60
        self.height = 60
        self.baseImage = pygame.transform.scale(glassImage, (self.width, self.height))
        self.chargedImage = pygame.transform.scale(chargedGlassImage, (self.width, self.height))
        self.brokenImage = pygame.transform.scale(brokenGlassImage, (self.width, self.height))
        self.image = self.baseImage.copy()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = -self.height
        self.y = float(-self.height)
        self.dead = False
        self.broken = False
        self.fallSpeed = monsterFallSpeed

        # 볼륨과 피치를 5등분한 구간 중 하나 랜덤으로 선택
        self.volumeSegmentIndex = random.randint(0, 4)
        self.pitchSegmentIndex = random.randint(0, 4)

        volSegSize = float(maxVolume-minVolume) / 5.0
        vMin = int(minVolume+self.volumeSegmentIndex * volSegSize)
        vMax = int(minVolume+(self.volumeSegmentIndex + 1) * volSegSize)
        self.deathVolumeRange = (vMin, vMax)

        pitchSegSize = float(maxPitch-minPitch) / 5.0
        pMin = int(minPitch + self.pitchSegmentIndex * pitchSegSize)
        pMax = int(minPitch + (self.pitchSegmentIndex + 1) * pitchSegSize)
        self.deathPitchRange = (pMin, pMax)
        
        self.deathTime = 0.2
        self.inRange = None
        self.chargeProgress = 0
    
    def update(self):
        # 하강하기
        if not self.dead:            
            if state == 'gameRunning':
                difficulty = 1.0
                if runStartTime:
                    elapsedRun = time.time() - runStartTime
                    difficulty = min(1.0 + elapsedRun * DIFFICULTY_RATE, MAX_DIFFICULTY)
                
                self.y += self.fallSpeed * difficulty
                print(self.fallSpeed * difficulty)
                self.rect.y = int(self.y)
                # 죽는 조건 
                in_volume = self.deathVolumeRange[0] <= volume <= self.deathVolumeRange[1]
                in_pitch = self.deathPitchRange[0] <= pitch <= self.deathPitchRange[1]

                if in_volume and in_pitch: # 모두 범위 안에 들어왔는가
                    if self.inRange is None:
                        self.inRange = time.time()
                    # 일정 시간 유지 시 죽음
                    elapsedCharge = time.time()-self.inRange

                    self.chargeProgress = max(0.0, min(elapsedCharge / self.deathTime, 1.0))

                    if time.time() - self.inRange >= self.deathTime: # 죽음 감지
                        global score
                        score += 100 # 몬스터 제거 점수
                        self.dead = True
                        breakSound.play()
                        self.deadTime = time.time()                
                else:
                    self.inRange = None

            self.image = self.baseImage.copy()
            if self.chargeProgress > 0.0:
                trans = int(255 * self.chargeProgress) # 투명도값 조정
                overlay = self.chargedImage.copy()
                overlay.set_alpha(trans)
                self.image.blit(overlay, (0, 0))
        else:
            if not self.broken:
                center = self.rect.center    
                self.image = self.brokenImage.copy()   
                self.rect = self.image.get_rect(center=center)
                self.broken = True
                self.image.blit(self.brokenImage.copy(), (0, 0))
                self.deathTime = time.time()

            if time.time() - self.deathTime >= 1.0:
                self.kill()

allRects = [birdRect,masterRect,wallRect,groundRect]

running = True
singing = False
masterAwakened = False
state = "menu"  

def drawText(font,fontColor,center,text):
    global screen
    Label = font.render(text, True, fontColor)
    LabelRect = Label.get_rect(center=center)
    screen.blit(Label,LabelRect)

# 메인 루프
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if state == "menu":
                # Start Game 버튼
                if startButtonRect.collidepoint(mouse_pos):
                    score = 0
                    lastScoreTime = time.time()
                    lastSpawn = time.time()
                    monsters.empty()
                    killGroup = []   
                    runStartTime = time.time()                 
                    state = "gameRunning"

                if soundButtonRect.collidepoint(mouse_pos):
                    state = "soundMenu"

    singing = volume > NOISE_GATE

    if singing:                 
        print(f"주파수 = {pitch:04.1f}Hz , 볼륨 = {volume:04.1f}",end = "\r")
    
    # 게임 진행중
    if state == "gameRunning":
        #새 움직이기
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            birdRect.x -= birdSpeed
        if keys[pygame.K_RIGHT]:
            birdRect.x += birdSpeed

        # 화면 밖으로 나가지 않게 막기
        if birdRect.left < 0:
            birdRect.left = 0
        if birdRect.right > gameWidth:
            birdRect.right = gameWidth

        # 바닥 닿았는지 확인
        for m in list(monsters):
            if m.rect.bottom >= HEIGHT - groundHeight:
                state = "gameOverScene"
                lastKillTime = time.time()
                killGroup = list(monsters)
                break
        
        # 몬스터 생성
        now = time.time()
        elapsedRun = (now - runStartTime) if runStartTime else 0
        curSpawnCool = max(MIN_SPAWN_COOL, SPAWN_COOL_START - elapsedRun * SPAWN_COOL_DIGIT)
        if now - lastSpawn > curSpawnCool:
            m = Monster(random.randint(0, gameWidth - 50))
            monsters.add(m)
            lastSpawn = now
            lastSpawn = time.time()

        # 화면 흔들기
        shake = 0
        if volume > NOISE_GATE:
            shake = int((volume / maxVolume) * 15)
        shakeOffset = random.randint(-shake, shake) if shake > 0 else 0

        if shakeOffset != 0:   
            for rect in allRects:
                rect.x += shakeOffset
            for sprite in monsters:
                sprite.rect.x += shakeOffset

        # 원상복구
        if shakeOffset != 0:
            for rect in allRects:
                rect.x -= shakeOffset
            for sprite in monsters:
                sprite.rect.x -= shakeOffset  
        
        # 1초마다 10점씩 점수 더함
        if time.time() - lastScoreTime >= 1:
            score += 10
            lastScoreTime = time.time()
    
    # ===== 게임오버 장면 =====
    if not masterAwakened:
        voiceTime = time.time()
    killNowTimeStamp = time.time()   

    if state == "gameOverScene":       
        # 0.5초마다 몬스터 한 마리씩 죽이기
        if killGroup and killNowTimeStamp - lastKillTime >= killCool:
            m = killGroup.pop(0)
            gameOverSound.play()     
            m.dead = True
            m.deadTime = killNowTimeStamp
            m.broken = False
            lastKillTime = killNowTimeStamp

        # 모든 몬스터 제거 후 주인 깨우고 대사
        if not monsters and not masterAwakened:
            birdRect.x = 100
            masterRect = pygame.Rect(200,HEIGHT - groundHeight - masterHeight - 70,masterWidth - 20,masterHeight + 80)
            masterImage = pygame.transform.scale(standedMasterImage, (masterWidth-20, masterHeight+80))
            masterAwakened = True
            masterVoice.play()
        
        # 대사가 끝난 후 주인을 다시 재우며 메뉴로 복귀
        if time.time() - voiceTime > 8:
            if not birdCooked:
                birdCooked = True
                chickenSound.play()
                birdImage = chickenImage

        if time.time() - voiceTime > 10:
            birdCooked = False
            birdImage = livingBirdImage
            masterAwakened = False
            masterRect = pygame.Rect(200,HEIGHT - groundHeight - masterHeight+50,masterWidth,masterHeight)
            masterImage = sleepingMasterImage
            state = "menu"
            
            highScore = max([highScore,score])
            score = 0

    monsters.update()

    # ====== 화면그리기 ======
    screen.fill(WHITE)
    screen.blit(wallImage, wallRect)
    screen.blit(birdImage, birdRect)
    screen.blit(groundImage, groundRect)
    screen.blit(masterImage, masterRect)
    monsters.draw(screen)
  
    # 볼륨/피치 동그라미
    circleSize = 8
    circle_margin = 4
    for m in monsters:
        centerY = m.rect.top - circleSize - 2
        centerX1 = m.rect.centerx - circleSize - circle_margin  
        centerX2 = m.rect.centerx + circleSize + circle_margin  
        pygame.draw.circle(screen, VOLUME_SEGMENT_COLORS[m.volumeSegmentIndex], (centerX1, centerY), circleSize)
        pygame.draw.circle(screen, PITCH_SEGMENT_COLORS[m.pitchSegmentIndex], (centerX2, centerY), circleSize)

    # 사이드바
    sidebarRect = pygame.Rect(gameWidth, 0, sidebarWidth, HEIGHT)
    screen.blit(sidebarImage, (gameWidth, 0))

    # 점수 표시
    drawText(labelFont,WHITE,(gameWidth + sidebarWidth // 2, 30),"Score")
    drawText(font,WHITE,(gameWidth + sidebarWidth // 2, 60),f"{score}")
    drawText(labelFont,RED,(gameWidth + sidebarWidth // 2, HEIGHT-200),"HighScore")
    drawText(font,RED,(gameWidth + sidebarWidth // 2, HEIGHT-170),f"{highScore}")

    # 바 설정
    barMaxHeight = 400
    barWidth = 25
    barY = 150

    # 볼륨 바
    volumeLabel = labelFont.render("Volume", True, WHITE)
    volumeLabelRect = volumeLabel.get_rect(center=(gameWidth + sidebarWidth // 4, 120))
    screen.blit(volumeLabel, volumeLabelRect)

    volumeBarX = gameWidth + sidebarWidth // 4 - barWidth // 2
    calVolumeMax = maxVolume - minVolume
    calVolume = max(volume - minVolume, 0)  
    drawBar(screen, volumeBarX, barY, barWidth, barMaxHeight, calVolumeMax, calVolume, VOLUME_SEGMENT_COLORS)

    # 피치 바
    calPitchMax = maxPitch - minPitch
    calPitch = max(pitch - minPitch, 0) 
    pitchLabel = labelFont.render("Pitch", True, WHITE)
    pitchLabelRect = pitchLabel.get_rect(center=(gameWidth + sidebarWidth * 3 // 4, 120))
    screen.blit(pitchLabel, pitchLabelRect)

    pitchBarX = gameWidth + sidebarWidth * 3 // 4 - barWidth // 2
    drawBar(screen, pitchBarX, barY, barWidth, barMaxHeight,calPitchMax, calPitch, PITCH_SEGMENT_COLORS)

    #메뉴
    if state == "menu":
        menuSurface = pygame.Surface((gameWidth, HEIGHT), pygame.SRCALPHA)
        menuSurface.fill((255, 255, 255, 180))
        screen.blit(menuSurface, (0, 0))

        drawText(titleFont,BLACK,(gameWidth // 2, HEIGHT // 3),"SongBird")
        drawText(subTitleFont,BLACK,(gameWidth // 2, (HEIGHT // 3)+60),"Dont wake him up.")

        pygame.draw.rect(screen, BLUE, soundButtonRect)
        drawText(menuFont,WHITE,soundButtonRect.center,"Sound Setting")

        pygame.draw.rect(screen, RED, startButtonRect)
        drawText(menuFont,BLACK,startButtonRect.center,"Start")
    
    if state == "soundMenu":
        menuSurface = pygame.Surface((gameWidth, HEIGHT), pygame.SRCALPHA)
        menuSurface.fill((255, 255, 255, 180))
        screen.blit(menuSurface, (0, 0))

        drawText(titleFont,BLACK,(gameWidth // 2, HEIGHT // 6-50),"Sound")

        drawText(subTitleFont,BLACK,(gameWidth // 2, HEIGHT // 6+50),"pitch")
        drawText(labelFont,BLACK,(gameWidth // 2-50, HEIGHT // 6+100),"min")
        drawText(labelFont,BLACK,(gameWidth // 2-50, HEIGHT // 6+150),"max")
        drawText(labelFont,BLACK,(gameWidth // 2, HEIGHT // 6+100),f"{minPitch}")
        drawText(labelFont,BLACK,(gameWidth // 2, HEIGHT // 6+150),f"{maxPitch}")

        drawText(subTitleFont,BLACK,(gameWidth // 2, HEIGHT // 6+300,),"volume")
        drawText(labelFont,BLACK,(gameWidth // 2-50, HEIGHT // 6+350),"min")
        drawText(labelFont,BLACK,(gameWidth // 2-50, HEIGHT // 6+400),"max")
        drawText(labelFont,BLACK,(gameWidth // 2, HEIGHT // 6+350),f"{minVolume}")
        drawText(labelFont,BLACK,(gameWidth // 2, HEIGHT // 6+400),f"{maxVolume}")
        
        pygame.draw.rect(screen,RED,minVolumePlusButtonRect)
        pygame.draw.rect(screen,BLUE,minVolumeMinusButtonRect)
        pygame.draw.rect(screen,RED,minPitchPlusButtonRect)
        pygame.draw.rect(screen,BLUE,minPitchMinusButtonRect)

        drawText(subTitleFont,WHITE,minVolumePlusButtonRect.center,"+")
        drawText(subTitleFont,WHITE,minVolumeMinusButtonRect.center,"-")
        drawText(subTitleFont,WHITE,minPitchPlusButtonRect.center,"+")
        drawText(subTitleFont,WHITE,minPitchMinusButtonRect.center,"-")

        pygame.draw.rect(screen,RED,maxVolumePlusButtonRect)
        pygame.draw.rect(screen,BLUE,maxVolumeMinusButtonRect)
        pygame.draw.rect(screen,RED,maxPitchPlusButtonRect)
        pygame.draw.rect(screen,BLUE,maxPitchMinusButtonRect)     

        drawText(subTitleFont,WHITE,maxVolumePlusButtonRect.center,"+")
        drawText(subTitleFont,WHITE,maxVolumeMinusButtonRect.center,"-")
        drawText(subTitleFont,WHITE,maxPitchPlusButtonRect.center,"+")
        drawText(subTitleFont,WHITE,maxPitchMinusButtonRect.center,"-")


        pygame.draw.rect(screen, GREEN, menuButtonRect)
        menuButtonTxt = menuFont.render("Menu", True, WHITE)
        menuButtonTxtRect = menuButtonTxt.get_rect(center=menuButtonRect.center)
        screen.blit(menuButtonTxt, menuButtonTxtRect)

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos            
            if menuButtonTxtRect.collidepoint(mouse_pos):
                state = "menu"
            if time.time() - clickTimeStamp > 0.2:
                if maxVolumePlusButtonRect.collidepoint(mouse_pos):
                    if maxVolume + 10 < 1500:
                        maxVolume += 10
                if minVolumePlusButtonRect.collidepoint(mouse_pos):
                    if minVolume + 10 <= maxVolume:
                        minVolume += 10
                if maxPitchPlusButtonRect.collidepoint(mouse_pos):
                    if maxPitch + 10 < 1500:
                        maxPitch += 10
                if minPitchPlusButtonRect.collidepoint(mouse_pos):
                    if minPitch + 10 < maxPitch:
                        minPitch += 10
                
                if maxVolumeMinusButtonRect.collidepoint(mouse_pos):
                    if maxVolume - 10 > minVolume:
                        maxVolume -= 10
                if minVolumeMinusButtonRect.collidepoint(mouse_pos):
                    if minVolume - 10 > 0:
                        minVolume -= 10
                if maxPitchMinusButtonRect.collidepoint(mouse_pos):
                    if maxPitch - 10 > minPitch:
                        maxPitch -= 10
                if minPitchMinusButtonRect.collidepoint(mouse_pos):
                    if minPitch - 10 > 0:
                        minPitch -= 10
                clickTimeStamp = time.time()
            
    pygame.display.flip()
