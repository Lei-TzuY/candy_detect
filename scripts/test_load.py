import cv2

cfg_path = r'D:\專案\candy\models\yolov4-tiny-myobj.cfg'
weights_path = r'D:\專案\candy\models\yolov4-tiny-myobj_final.weights'

print('Reading files...')
with open(cfg_path, 'rb') as f:
    cfg_buffer = f.read()
    
with open(weights_path, 'rb') as f:
    weights_buffer = f.read()

print(f'CFG size: {len(cfg_buffer)} bytes')
print(f'Weights size: {len(weights_buffer)} bytes')

print('Loading net from buffers...')
net = cv2.dnn.readNetFromDarknet(cfg_buffer, weights_buffer)
print('Success! Net loaded.')
