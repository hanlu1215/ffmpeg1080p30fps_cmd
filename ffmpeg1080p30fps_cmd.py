import os
import sys
import argparse
import subprocess
import multiprocessing
import time
import json


def get_video_metadata(file_path):
    try:
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=duration,nb_frames',
            '-of', 'json',
            file_path
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )

        metadata = json.loads(result.stdout)

        if 'streams' in metadata and metadata['streams']:
            stream = metadata['streams'][0]
            duration_str = stream.get('duration')
            if duration_str:
                duration_seconds = float(duration_str)
                m, s = divmod(duration_seconds, 60)
                h, m = divmod(m, 60)
                formatted_duration = f"{int(h):02d}:{int(m):02d}:{s:.2f}"
            else:
                formatted_duration = "未知"

            frame_count = stream.get('nb_frames', '未知')
            return formatted_duration, frame_count

        return "未知", "未知"

    except FileNotFoundError:
        print("⚠️ 找不到 ffprobe。请确保 FFmpeg 已安装并添加到 PATH。")
        return "N/A", "N/A"
    except subprocess.CalledProcessError:
        print("⚠️ ffprobe 执行失败，可能文件损坏或格式不支持。")
        return "N/A", "N/A"
    except Exception as e:
        print(f"⚠️ 获取元数据时发生错误: {e}")
        return "N/A", "N/A"


def transcode_cmd(input_path):
    if not os.path.isfile(input_path):
        print(f"输入文件不存在: {input_path}")
        return 2

    directory = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    file_name_without_ext, _ = os.path.splitext(base_name)

    output_filename = f"{file_name_without_ext}_1080p30fps.mp4"
    output_path = os.path.join(directory, output_filename)

    print(f"输入: {input_path}")
    print(f"输出: {output_path}")

    duration, frames = get_video_metadata(input_path)
    print("------------------------------------------------")
    print(f"视频元数据: 总时长={duration}, 总帧数={frames}")
    print("------------------------------------------------")

    threads = multiprocessing.cpu_count()
    print(f"检测到 {threads} 个 CPU 核心，将用于 FFmpeg 的 -threads 参数。")

    ffmpeg_command = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', 'libx264',
        '-b:v', '4500k',
        '-r', '30',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        '-preset', 'medium',
        '-threads', str(threads),
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_path
    ]

    print("开始转码...")
    last_print_time = time.time()

    try:
        process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        for line in process.stdout:
            if 'frame=' in line or 'time=' in line:
                current_time = time.time()
                if current_time - last_print_time >= 1:
                    sys.stdout.write(f"\r{line.strip()}")
                    sys.stdout.flush()
                    last_print_time = current_time

        process.wait()

        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()

        if process.returncode == 0:
            print("\n转码完成！")
            print(f"文件已保存至: {output_path}")
            return 0
        else:
            print(f"\nFFmpeg 进程退出，返回码: {process.returncode}")
            print(process.communicate()[0])
            return process.returncode

    except FileNotFoundError:
        print("错误：找不到 FFmpeg 命令。请确保 FFmpeg 已安装并添加到 PATH。")
        return 3
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        return 4


def main():
    parser = argparse.ArgumentParser(description='将视频转码为 1080p 30fps，输出文件与输入同目录')
    parser.add_argument('input', help='输入视频文件路径')
    args = parser.parse_args()

    rc = transcode_cmd(args.input)
    sys.exit(rc)


if __name__ == '__main__':
    main()
