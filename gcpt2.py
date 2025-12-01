import cv2
import time
import os
import subprocess
import math
import numpy as np
import threading

#-----------------------------------------------------執行cmd指令-----------------------------------------------------

#Relay1是第一個噴氣口，Relay2是第二個噴氣口；value=1是噴氣，value=0是不噴氣。
def run_cmd_Popen_fileno():
    time.sleep(2.1)
    print('運行cmd指令：{}'.format('curl -X POST "http://localhost:8080/api/relay/Relay2?value=1"'))
    subprocess.Popen('curl -X POST "http://localhost:8080/api/relay/Relay2?value=1"', shell=True, stdout=None, stderr=None)
#---------------------------------------------------------------------------------------------------------------------

#------------------------------------------------------載入YoloV4-----------------------------------------------------
Conf_threshold = 0.2
NMS_threshold = 0.4
COLORS = [(0, 255, 0), (0, 0, 255), (255, 0, 0),
          (255, 255, 0), (255, 0, 255), (0, 255, 255)]

class_name = []
with open('C:/Users/st313/Desktop/candy/Yolo/darknet-master/build/darknet/x64/train/classes.txt', 'r') as f:
    class_name = [cname.strip() for cname in f.readlines()]

print(class_name)

net = cv2.dnn.readNet(
'C:/Users/st313/Desktop/candy/Yolo/darknet-master/build/darknet/x64/train/backup/yolov4-tiny-myobj_final.weights', 
'C:/Users/st313/Desktop/candy/Yolo/darknet-master/build/darknet/x64/train/yolov4-tiny-myobj.cfg'
)

net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)

model = cv2.dnn_DetectionModel(net)
model.setInputParams(size=(416, 416), scale=1/255, swapRB=True)
#----------------------------------------------------------------------------------------------------------------------

#計數
count = 0

prev_x = []

tracking_objects = {}
track_id = 1

total_num = 0
normal_num = 0
abnormal_num = 0

#計時
start = time.time()

#執行攝影機:0代表第一個鏡頭，1代表第二個鏡頭
#cap = cv2.VideoCapture('影片路徑')
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
print("執行攝影機")

#-----------------------------------------------------while迴圈範圍-----------------------------------------------------

while(cap.isOpened()):
    ret, frame = cap.read()
    count +=1
    if ret == False:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    cur_x = []

    classes, scores, boxes = model.detect(gray, Conf_threshold, NMS_threshold)

    for (classid, score, box) in zip(classes, scores, boxes):
        (x, y, w, h) = box
        #print("BOX", x, y, w, h)

        #紀錄中心點
        cx = int((x + x + w)/2)
        cy = int((y + y + h)/2)
        cur_x.append((cx, cy))

        color = COLORS[int(classid) % len(COLORS)]
        label = "%s : %f" % (class_name[classid], round(score, 2))
        cv2.rectangle(frame, box, color, 2)

        cv2.putText(frame, label, (box[0], box[1]-10),
                   cv2.FONT_HERSHEY_COMPLEX, 0.7, color, 3)

#----------------------------------------------------EuclideanDistTrack算法---------------------------------------------------- 

    if count <= 2:
        for pt in cur_x:
            for pt2 in prev_x:
                distance = math.hypot(pt2[0] - pt[0], pt2[1] - pt[1])

                if distance > 1000:
                    tracking_objects[track_id] = pt
                    track_id += 1

    else:
        tracking_objects_copy = tracking_objects.copy()
        cur_x_copy = cur_x.copy()

        for object_id, pt2 in tracking_objects_copy.items():
            object_exists = False
            for pt in cur_x_copy:
                distance = math.hypot(pt2[0] - pt[0], pt2[1] - pt[1])

                # Update IDs position
                if distance < 1500:
                    tracking_objects[object_id] = pt
                    object_exists = True
                    if pt in cur_x:
                        cur_x.remove(pt)
                    continue

            # Remove IDs lost
            if not object_exists:
                tracking_objects.pop(object_id)

        # Add new IDs found
        for pt in cur_x:
            if(x>500)&(x<1100):
                tracking_objects[track_id] = pt
                track_id += 1
                total_num += 1

                #計數、噴氣
                if(class_name[classid]=='normal'):
                    normal_num+=1
                    print("Tracking objects")
                    print(tracking_objects)

                elif(class_name[classid]=='abnormal'):
                    abnormal_num+=1
                    t = threading.Thread(target = run_cmd_Popen_fileno)
                    t.start()
                    print("Tracking objects")
                    print(tracking_objects)

    for object_id, pt in tracking_objects.items():
        cv2.circle(frame, pt, 5, (0, 0, 255), -1)
        cv2.putText(frame, str(object_id), (pt[0], pt[1] - 7), 0, 1, (0, 0, 255), 2)

    end = time.time()
    times = end - start

    #print("CUR FRAME LEFT PTS")
    #print(cur_x)

#------------------------------------------------------------------------------------------------------------------------    

    #判定線
    cv2.line(frame, (500, 0), (500, 1080), (200, 100, 0), 2)
    cv2.line(frame, (1100, 0), (1100, 1080), (200, 100, 0), 2)

    #顯示相關的數據，糖果數量、時間。
    #f'time: {times:.2f}'
    cv2.putText(frame, f'time: {times:.2f}', (20, 20),
               cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 150, 0), 2)

    #f'total: {total_num}'
    cv2.putText(frame, f'total: {total_num}', (20, 50),
               cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 150, 0), 2)

    #f'normal: {normal_num}'
    cv2.putText(frame, f'normal: {normal_num}', (20, 80),
               cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 150, 0), 2)

    #f'abnormal: {abnormal_num}'
    cv2.putText(frame, f'abnormal: {abnormal_num}', (220, 20),
               cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 0, 200), 2)

    #frame
    cv2.imshow('Camera 2', frame)

    #複製中心點
    prev_x = cur_x.copy()

    key = cv2.waitKey(1)
    if key == ord('q'):
        break

#-------------------------------------------------------------------------------------------------------------------------

cap.release()
cv2.destroyAllWindows()
