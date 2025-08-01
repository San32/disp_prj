import cv2

def jpeg_to_mp4(image_path, output_path, duration_sec=10, fps=30):
    # 이미지 불러오기
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")
    
    height, width, _ = image.shape

    # 비디오 라이터 설정
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 코덱
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 이미지 프레임을 duration 동안 반복해서 씀
    total_frames = duration_sec * fps
    for _ in range(total_frames):
        out.write(image)

    out.release()
    print(f"MP4 비디오가 저장되었습니다: {output_path}")

# 사용 예시
image_path = '/home/comm/data/images/stroller_56.jpg'
output_path = './output.mp4'
jpeg_to_mp4(image_path, output_path, duration_sec=10, fps=30)
