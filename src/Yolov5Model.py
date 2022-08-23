import json
import time

import torch

from src.singleton import Singleton


class Yolov5Model(metaclass=Singleton):
    def __init__(self):
        self.img_size = 256
        self.conf_thres = 0.2
        self.model_name = 'yolov5s_p8027-i256-e300-b256-cache_v2'
        self.weights_path = "weights/"
        self.model_path = self.weights_path + self.model_name
        self.model = torch.hub.load("./yolov5", 'custom', source='local', verbose=False, path=self.model_path)
        self.model.conf = self.conf_thres

        self.total_detection_count = 0
        self.total_detect_time = 0

    def detect(self, image_path):
        detect_time = time.time()
        result = self.model(image_path, self.img_size)
        json_results = json.loads(result.pandas().xyxy[0].to_json(orient="records"))
        self.total_detect_time += time.time() - detect_time
        self.total_detection_count += 1
        return json_results

    def get_average_detection_time(self):
        if not self.total_detection_count <= 0:
            return round(self.total_detection_count/self.total_detect_time, 2)
        else:
            return 0
