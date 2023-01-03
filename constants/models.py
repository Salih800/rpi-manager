GDRIVE_MODEL_FOLDER = "1aHLfQN4hjmMp_63G8UobstHE6jNHhgAL"


class DetectionModelConfig:
    def __init__(self, model_name, img_size, conf_thres, max_det=1):
        self.model_name = model_name
        self.img_size = img_size
        self.conf_thres = conf_thres
        self.max_det = max_det


GARBAGE_MODEL = DetectionModelConfig(model_name="yolov5s-i256-e300-b256-p10319",
                                     img_size=256,
                                     conf_thres=0.2)

GARBAGE_LOCATION_DETECTION_MODEL = DetectionModelConfig(model_name="garbage-counts-v3-salih-i640-pretrained2",
                                                        img_size=640,
                                                        conf_thres=0.7,
                                                        max_det=50)

FP_BLURRING_MODEL = DetectionModelConfig(model_name="fp_i256_e100_b64_220920",
                                         img_size=256,
                                         conf_thres=0.1,
                                         max_det=100)

PERCANTAGE_MODEL = DetectionModelConfig(model_name="pd-v3-i256",
                                        img_size=256,
                                        conf_thres=0.01,
                                        max_det=1)
