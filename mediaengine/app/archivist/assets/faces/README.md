# Face finder of "Clips from a long video"

`face_detection_yunet_2023mar.onnx` - YuNet, a small face finder (232,589 bytes), from OpenCV Zoo
(https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet, commit 48b10fa505aeb51fbd127fc60a5c660040e823b7).
SHA-256 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4. MIT License: `LICENSE-YuNet.txt`
(Copyright (c) 2020 Shiqi Yu). Run by OpenCV's own `FaceDetectorYN` (opencv-python-headless of the program); no
other download, nothing sent anywhere. Without it (or with an OpenCV that cannot run it) the program falls back to
OpenCV's older face finder files (Haar cascades).
