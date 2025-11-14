import cv2
import os
import math
import numpy as np
import keyboard

#執行攝影機:0代表第一個鏡頭，1代表第二個鏡頭
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
print("執行攝影機")

i=1
name = 'normal'

while(cap.isOpened()):
  ret ,frame = cap.read()
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

  k=cv2.waitKey(1)
  if k==27:
     break
  elif k==ord('s'):
     cv2.imwrite('C:/Users/st313/Desktop/canp/normal/'+name+str(i)+'.jpg',gray)
     i+=1
  cv2.imshow("frame",gray)

cap.release()
cv2.destroyAllWindows()
