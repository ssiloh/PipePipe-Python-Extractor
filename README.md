# pipepipe_python_extractor

**NewPipeExtractor의 Python 포팅 버전**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Based on](https://img.shields.io/badge/Based%20on-NewPipeExtractor-red)](https://github.com/TeamNewPipe/NewPipeExtractor)

---

## 개요

`pipepipe_python_extractor`는 Android 스트리밍 앱 [PipePipe](https://github.com/InfinityLoop1308/PipePipe) 및 [NewPipe](https://github.com/TeamNewPipe/NewPipe)의 핵심 라이브러리인 **[NewPipeExtractor](https://github.com/TeamNewPipe/NewPipeExtractor)** (Java)를 Python으로 포팅한 프로젝트입니다.

YouTube를 비롯한 스트리밍 서비스에서 공식 API 없이 영상 정보, 스트림 URL, 검색 결과, 채널 정보, 재생목록을 추출합니다.

> **원본 프로젝트**: [TeamNewPipe/NewPipeExtractor](https://github.com/TeamNewPipe/NewPipeExtractor)
> **원본 라이선스**: GNU General Public License v3.0

---

## 지원 서비스

| 서비스 | 영상 정보 | 스트림 URL | 검색 | 채널 | 재생목록 |
|--------|:---------:|:----------:|:----:|:----:|:--------:|
| YouTube | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 설치

```bash
pip install requests
```

이 프로젝트는 `requests` 외에 별도의 외부 의존성이 없습니다.

> **참고**: 스트림 URL의 n-파라미터 디코딩(YouTube 속도 제한 우회)은 Node.js가 설치된 환경에서 자동으로 활성화됩니다.
> Node.js가 없어도 기본 기능은 모두 사용 가능합니다.

---

## 빠른 시작

### Python API

```python
from pipepipe_python_extractor import PipePipe, format_duration, format_count

pp = PipePipe()

# 영상 정보 및 스트림 URL 추출
info = pp.get_stream_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(info.name)                          # 영상 제목
print(format_duration(info.duration))     # 재생 시간
print(format_count(info.view_count))      # 조회수
print(info.uploader)                      # 업로더
print(info.thumbnail_url)                 # 썸네일 URL

# 최고 화질 스트림 URL 가져오기
best_video = info.best_video_stream
best_audio = info.best_audio_stream
print(best_video.url)   # 영상 스트림 URL
print(best_audio.url)   # 오디오 스트림 URL

# 전체 스트림 목록
for vs in info.video_streams + info.video_only_streams:
    print(f"[{vs.itag}] {vs.resolution} {vs.format.format_name} codec={vs.codec}")

for a in info.audio_streams:
    print(f"[{a.itag}] {a.format.format_name} {a.bitrate // 1000}kbps")

# 자막
for sub in info.subtitle_streams:
    auto = " (자동 생성)" if sub.is_auto_generated else ""
    print(f"자막: {sub.language}{auto} → {sub.url}")
```

```python
# 검색
results = pp.search("파이썬 강의")
for item in results.streams:
    print(f"{item.name} | {item.uploader} | {format_duration(item.duration)}")

# 다음 페이지
results2 = pp.search("파이썬 강의", next_page_token=results.next_page_token)
```

```python
# 채널 정보
channel = pp.get_channel_info("https://www.youtube.com/@YouTube")
print(channel.name, format_count(channel.subscriber_count))

# 채널 영상 목록 (페이지네이션 지원)
videos, next_token = pp.get_channel_videos("https://www.youtube.com/@YouTube")
for v in videos:
    print(v.name, format_duration(v.duration))
```

```python
# 재생목록
playlist, next_token = pp.get_playlist("https://www.youtube.com/playlist?list=PLxxxxxx")
print(playlist.name, f"({playlist.stream_count}개 영상)")
for v in playlist.streams:
    print(v.name)
```

```python
# 프록시 사용
pp = PipePipe(proxy="http://127.0.0.1:8080")

# 타임아웃 설정 (기본 15초)
pp = PipePipe(timeout=30)
```

### CLI

```bash
# 영상 정보
python -m pipepipe_python_extractor info "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 검색
python -m pipepipe_python_extractor search "파이썬 튜토리얼"

# 채널 정보 + 최근 영상
python -m pipepipe_python_extractor channel "https://www.youtube.com/@YouTube"

# 재생목록
python -m pipepipe_python_extractor playlist "https://www.youtube.com/playlist?list=PLxxxxxx"
```

---

## 프로젝트 구조

```
pipepipe_python_extractor/
├── __init__.py                        # PipePipe 메인 클래스 (진입점)
├── __main__.py                        # python -m 실행 지원
├── cli.py                             # CLI 인터페이스
├── core/
│   ├── exceptions.py                  # 예외 클래스
│   ├── media_format.py                # MediaFormat enum
│   ├── stream_info.py                 # 데이터 클래스 (StreamInfo, VideoStream 등)
│   ├── downloader.py                  # HTTP 클라이언트
│   └── link_handler.py                # URL 파서 기반 클래스
├── services/
│   └── youtube/
│       ├── innertube.py               # YouTube InnerTube API 클라이언트
│       ├── cipher.py                  # 스트림 URL 서명/n-파라미터 디코딩
│       ├── link_handler.py            # YouTube URL → ID 추출
│       └── extractors/
│           ├── stream_extractor.py    # YoutubeStreamExtractor
│           ├── search_extractor.py    # YoutubeSearchExtractor
│           ├── channel_extractor.py   # YoutubeChannelExtractor
│           └── playlist_extractor.py  # YoutubePlaylistExtractor
└── utils/
    └── utils.py                       # format_duration, format_count 등
```

---

## NewPipeExtractor와의 대응 관계

| NewPipeExtractor (Java) | pipepipe_python_extractor (Python) |
|---|---|
| `NewPipe.java` | `PipePipe` 클래스 |
| `Downloader` (abstract) | `Downloader` 클래스 (`requests` 기반) |
| `StreamingService` | `InnerTubeClient` |
| `YoutubeStreamExtractor` | `YoutubeStreamExtractor` |
| `YoutubeSearchExtractor` | `YoutubeSearchExtractor` |
| `YoutubeChannelExtractor` | `YoutubeChannelExtractor` |
| Signature cipher / n-param | `cipher.py` |
| `StreamInfo`, `VideoStream`, `AudioStream` | 동명의 Python dataclass |
| `MediaFormat` enum | `MediaFormat` enum |
| `ExtractionException` 계층 | 동일한 예외 계층 구조 |

---

## 테스트

```bash
# 전체 통합 테스트
python test_extractor.py

# 개별 테스트
python test_extractor.py stream_info
python test_extractor.py search
python test_extractor.py channel_info
python test_extractor.py channel_videos
python test_extractor.py playlist
```

---

## 라이선스

이 프로젝트는 **[GNU General Public License v3.0](LICENSE)** 에 따라 배포됩니다.

원본 프로젝트 [NewPipeExtractor](https://github.com/TeamNewPipe/NewPipeExtractor)가 GPL v3.0으로 배포되므로, 해당 라이선스의 카피레프트 조항에 따라 이 포팅 버전 또한 동일한 라이선스를 적용합니다.

```
pipepipe_python_extractor — Python port of NewPipeExtractor
Copyright (C) 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

### 원본 저작권 고지

> NewPipeExtractor is Free Software: You can use, study share and improve it at your will.
> Specifically you can redistribute and/or modify it under the terms of the
> GNU General Public License as published by the Free Software Foundation,
> either version 3 of the License, or (at your option) any later version.
>
> — [TeamNewPipe/NewPipeExtractor](https://github.com/TeamNewPipe/NewPipeExtractor), GPL-3.0

---

## 관련 프로젝트

- [NewPipeExtractor](https://github.com/TeamNewPipe/NewPipeExtractor) — 원본 Java 라이브러리
- [NewPipe](https://github.com/TeamNewPipe/NewPipe) — Android 스트리밍 앱
- [PipePipe](https://github.com/InfinityLoop1308/PipePipe) — NewPipe 기반 포크 앱 (BiliBili 등 추가 지원)
