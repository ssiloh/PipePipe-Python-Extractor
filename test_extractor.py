"""
Integration tests for pipepipe_python_extractor.
Run: python test_extractor.py
"""
import sys
import traceback
from pipepipe_python_extractor import PipePipe, format_duration, format_count


def test_stream_info():
    print("=== TEST: Stream Info ===")
    pp = PipePipe()
    # Use a stable, public domain video (Big Buck Bunny)
    url = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
    info = pp.get_stream_info(url)

    assert info.id, "Missing video ID"
    assert info.name, "Missing title"
    assert info.duration > 0, "Invalid duration"
    assert info.uploader, "Missing uploader"
    assert len(info.video_streams) + len(info.video_only_streams) > 0, "No video streams"
    assert len(info.audio_streams) > 0, "No audio streams"

    print(f"  Title    : {info.name}")
    print(f"  Uploader : {info.uploader}")
    print(f"  Duration : {format_duration(info.duration)}")
    print(f"  Views    : {format_count(info.view_count)}")
    print(f"  Upload   : {info.upload_date}")
    print(f"  Streams  : {len(info.video_streams)} combined, {len(info.video_only_streams)} video-only, {len(info.audio_streams)} audio")
    print(f"  Subtitles: {len(info.subtitle_streams)}")
    print(f"  Thumbnail: {info.thumbnail_url[:60]}...")
    print("  PASS\n")
    return True


def test_search():
    print("=== TEST: Search ===")
    pp = PipePipe()
    results = pp.search("Python programming tutorial")

    assert results.query, "Missing query"
    assert len(results.streams) > 0, "No search results"

    print(f"  Results  : {len(results.streams)} videos, {len(results.channels)} channels, {len(results.playlists)} playlists")
    for item in results.streams[:3]:
        print(f"  - {item.name} | {item.uploader} | {format_duration(item.duration)}")
    print("  PASS\n")
    return True


def test_channel_info():
    print("=== TEST: Channel Info ===")
    pp = PipePipe()
    url = "https://www.youtube.com/@YouTube"
    info = pp.get_channel_info(url)

    assert info.id, "Missing channel ID"
    assert info.name, "Missing channel name"

    print(f"  Name     : {info.name}")
    print(f"  Subs     : {format_count(info.subscriber_count)}")
    print(f"  Verified : {info.verified}")
    print("  PASS\n")
    return True


def test_channel_videos():
    print("=== TEST: Channel Videos ===")
    pp = PipePipe()
    url = "https://www.youtube.com/@YouTube"
    videos, next_token = pp.get_channel_videos(url)

    assert len(videos) > 0, "No channel videos"

    print(f"  Videos fetched: {len(videos)}")
    for v in videos[:3]:
        print(f"  - {v.name} ({format_duration(v.duration)})")
    print(f"  Has next page: {bool(next_token)}")
    print("  PASS\n")
    return True


def test_playlist():
    print("=== TEST: Playlist ===")
    pp = PipePipe()
    # YouTube's official "Trending Music" playlist
    url = "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI"
    pl, next_token = pp.get_playlist(url)

    assert pl.id, "Missing playlist ID"
    assert pl.name, "Missing playlist name"
    assert len(pl.streams) > 0, "No playlist videos"

    print(f"  Name     : {pl.name}")
    print(f"  Uploader : {pl.uploader}")
    print(f"  Videos   : {pl.stream_count}")
    print(f"  Fetched  : {len(pl.streams)}")
    for v in pl.streams[:3]:
        print(f"  - {v.name} ({format_duration(v.duration)})")
    print("  PASS\n")
    return True


TESTS = [
    ("stream_info", test_stream_info),
    ("search", test_search),
    ("channel_info", test_channel_info),
    ("channel_videos", test_channel_videos),
    ("playlist", test_playlist),
]


def run_all():
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name}")
            traceback.print_exc()
            failed += 1
            print()

    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        for name, fn in TESTS:
            if name == test_name:
                fn()
                break
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available: {', '.join(n for n, _ in TESTS)}")
    else:
        run_all()
