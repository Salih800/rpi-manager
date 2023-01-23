import json
import logging
import subprocess as sp
import time


def create_virtual_cameras(count=1):
    logging.info(f"Creating {count} virtual camera(s)")
    try:
        command = (f"sudo modprobe v4l2loopback "
                   f"exclusive_caps=1 "
                   f"devices={count}")
        sp.check_output(command.split())
        return get_virtual_cameras()
    except Exception as e:
        logging.error(f"Failed to create virtual camera: {e}", exc_info=True)
        return


def get_virtual_cameras():
    try:
        command = "ls -1 /sys/devices/virtual/video4linux"
        return sp.check_output(command.split()).decode().splitlines()
    except Exception as e:
        logging.error(f"Failed to get virtual cameras: {e}", exc_info=True)
        return []


def remove_virtual_cameras():
    logging.info("Removing virtual camera(s)")
    try:
        command = "sudo modprobe -r v4l2loopback"
        sp.check_output(command.split())
        return True
    except Exception as e:
        logging.error(f"Failed to remove virtual camera: {e}", exc_info=True)
        return False


def stream_to_virtual_camera(real_camera, virtual_camera, width, height):
    try:
        width, height, fps = get_probe(real_camera, width, height)
        logging.info(f"Streaming from {real_camera} to {virtual_camera} with {width}x{height} @ {fps}fps")

        command = (f"ffmpeg -f v4l2 -s {width}x{height} -i {real_camera} "
                   f"-vf ""drawtext=x=10:y=10:fontsize=24:fontcolor=white:text='%{localtime}':box=1:boxcolor=black@1"" "
                   f"-f v4l2 -c:v rawvideo -pix_fmt rgb24 {virtual_camera} "
                   f"-loglevel warning")
        return sp.Popen(command.split())
    except Exception as e:
        logging.error(f"Failed to stream to virtual camera: {e}", exc_info=True)
        time.sleep(10)
        return


def stream_to_rtsp(virtual_camera, rtsp_url):
    logging.info(f"Streaming from {virtual_camera} to {rtsp_url}")
    try:
        command = (f"ffmpeg -f v4l2 -i {virtual_camera} "
                   f"-c:v libx264 -preset ultrafast -tune zerolatency "
                   f"-f rtsp -rtsp_transport tcp {rtsp_url} "
                   f"-loglevel warning")
        return sp.Popen(command.split())
    except Exception as e:
        logging.error(f"Failed to stream to rtsp: {e}", exc_info=True)
        time.sleep(10)
        return False


def get_probe(path, width, height):
    logging.info(f'Getting probe for {path} with {width}x{height}')
    command = (f"ffprobe -v quiet -print_format json "
               f"-show_format -show_streams "
               f"-video_size {width}x{height} "
               f"-f v4l2 -i {path}")
    probe = json.loads(sp.check_output(command.split()).decode())
    width = int(probe['width'])
    height = int(probe['height'])
    fps = probe['r_frame_rate']
    return width, height, fps

# def get_frames_from_virtual_camera(virtual_camera):
#     print("Starting virtual camera stream...")
#     return sp.Popen(f"ffmpeg -f v4l2 -i /dev/{virtual_camera} "
#                     f"-f rawvideo -pix_fmt rgb24 pipe: "
#                     f"-loglevel warning",
#                     shell=True, stdout=sp.PIPE)


# def read_frame(process, width, height):
#     frame_size = width * height * 3
#     in_bytes = process.stdout.read(frame_size)
#     if len(in_bytes) == 0:
#         frame = None
#     else:
#         assert len(in_bytes) == frame_size
#         frame = (
#             np
#             .frombuffer(in_bytes, np.uint8)
#             .reshape([height, width, 3])
#         )
#     return frame


# try:
#     virtual_cameras = create_virtual_cameras(1)
#     print(f"Virtual cameras: {len(virtual_cameras)}\n{virtual_cameras}")
#     if len(virtual_cameras) > 0:
#         virt_camera = stream_to_virtual_camera("/dev/video0", virtual_cameras[0])
#         time.sleep(2)
#         cap = cv2.VideoCapture(f"/dev/{virtual_cameras[0]}")
#         width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#         height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#         print(f"Virtual camera: {width}x{height}")
#         # reader = get_frames_from_virtual_camera(virtual_cameras[0])
#
#         streamer = stream_to_rtsp(virtual_cameras[0], "rtsp://93.113.96.30:8554/autopi-1")
#         while True:
#             # ~ print(f"Virtual camera: {virt_camera.poll()} | Streamer: {streamer.poll()} | Reader: {reader.poll()}")
#             # in_frame = read_frame(reader, 640, 480)
#             # if in_frame is None:
#             #     print('No frame')
#             #     break
#             # cv2.imshow('frame', in_frame[:, :, ::-1])
#             # if cv2.waitKey(1) & 0xFF == ord('q'):
#             #     break
#             ret, frame = cap.read()
#             if not ret:
#                 print("No frame")
#                 break
#             cv2.imshow('frame', frame)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
#
# finally:
#     remove_virtual_cameras()
