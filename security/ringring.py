# 5-may-25
# Since i have free time right now while i find my next employee i am playing a bit with Python and
# my new cameras.  The system is nice but as usual i find things it can not do and i thought that it
# would be great idea to implement it.  But which is that idea ?
#
import cv2
import numpy as np

# RTSP URL
rtsp_url1 = "rtsp://<user>:<password>@<IP>:554/cam/realmonitor?channel=1&subtype=0"

# font
font = cv2.FONT_HERSHEY_SIMPLEX
# org
org = (200, 400)
# fontScale
fontScale = 1
# Blue color in BGR
color = (255, 0, 0)
# Line thickness of 2 px
thickness = 2
result = 0
# Open the RTSP stream
cap1 = cv2.VideoCapture(rtsp_url1)
#cap2 = cv2.VideoCapture(rtsp_url2)
if not cap1.isOpened():
    print("Cannot open RTSP stream 1")
    exit(-1)

#if not cap2.isOpened():
#    print("Cannot open RTSP stream 2")
#    exit(-1)
last_mean = 0
first_pass = True
counter = 0

while True:
    # Read a frame from the stream
    ret1, frame1 = cap1.read()
    # Read a frame from the stream
    #ret2, frame2 = cap2.read()

    # If frame is read correctly ret is True
    if not ret1:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    # If frame is read correctly ret is True
    #if not ret2:
    #    print("Can't receive frame (stream end?). Exiting ...")
    #    break

    cv2.namedWindow("Frame1", cv2.WINDOW_NORMAL) 
    cv2.resizeWindow("Frame1", 650, 450)

    # Display the resulting frame
    #cv2.imshow('Frame1', frame1)
    # Convert the frame to Gray Scale
    gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

    # Timbre area:
    #crop_img = gray[230:500, 500:600]
    # Calle area:
    # Crop the image using slicing
    #[y_start:y_end, x_start:x_end]
    crop_img = gray[230:500, 200:400]
    if result > 0.6:
        # Timbre
        #cv2.rectangle(frame1, (500, 200), (600, 500), (2, 2, 255), 3)
        # Calle
        cv2.rectangle(frame1, (200, 230), (400, 500), (2, 2, 255), 3)
        frame1 = cv2.putText(frame1, 'Motion Detected!!', org, font, 
                   fontScale, color, thickness, cv2.LINE_AA)
    else:
        # Timbre
        #cv2.rectangle(frame1, (500, 200), (600, 500), (2, 255, 2), 3)
        # Calle
        cv2.rectangle(frame1, (200, 230), (400, 500), (2, 255, 2), 3)
        
    cv2.imshow('Frame1',frame1)

    cv2.namedWindow("Cropped", cv2.WINDOW_NORMAL) 
    cv2.resizeWindow("Cropped", 200, 140)
    cv2.imshow("Cropped", crop_img)

    #cv2.waitKey(0)
    #cv2.namedWindow("Frame2", cv2.WINDOW_NORMAL) 
    #cv2.resizeWindow("Frame2", 650, 450) 
    ## Display the resulting frame
    #cv2.imshow('Frame2', frame2)
    #result = np.abs(np.mean(crop_img) - last_mean)
    #last_mean= np.mean(crop_img)
#    if first_pass:
#        first_pass = False
#        pass
#    else:

    counter = counter + 1
    if (counter % 30) == 0:
        if first_pass:
            first_pass = False
        else:
            result = np.abs(np.mean(crop_img) - last_mean)
            last_mean = np.mean(crop_img)
        #if result > 0.6:
        print(f"Counter {counter} and {result}")
    # Press q to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if counter >= 1000:
    counter = 0
# When everything done, release the capture
cap1.release()
#cap2.release()
cv2.destroyAllWindows()
