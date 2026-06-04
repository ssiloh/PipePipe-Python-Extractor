"""
Simple CLI for pipepipe_python_extractor.

Usage:
    python -m pipepipe_python_extractor.cli info <URL>
    python -m pipepipe_python_extractor.cli search <query>
    python -m pipepipe_python_extractor.cli channel <URL>
    python -m pipepipe_python_extractor.cli playlist <URL>
"""
import sys
import json
from . import PipePipe, format_duration, format_count


def cmd_info(pp: PipePipe, url: str):
    info = pp.get_stream_info(url)
    print(f"\n{'='*60}")
    print(f"  Title     : {info.name}")
    print(f"  Uploader  : {info.uploader}")
    print(f"  Duration  : {format_duration(info.duration)}")
    print(f"  Views     : {format_count(info.view_count)}")
    print(f"  Likes     : {format_count(info.like_count)}")
    print(f"  Uploaded  : {info.upload_date}")
    print(f"  Category  : {info.category}")
    print(f"  Live      : {info.is_live}")
    print(f"  Tags      : {', '.join(info.tags[:5])}")
    print(f"  Thumbnail : {info.thumbnail_url}")
    print(f"\n  Video streams ({len(info.video_streams)} combined, {len(info.video_only_streams)} video-only):")
    for vs in sorted(info.video_streams + info.video_only_streams, key=lambda s: -s.height):
        vo = " [video-only]" if vs.is_video_only else ""
        print(f"    [{vs.itag:3d}] {vs.resolution:8s} {vs.format.format_name:6s} {vs.codec}{vo}")
    print(f"\n  Audio streams ({len(info.audio_streams)}):")
    for a in sorted(info.audio_streams, key=lambda s: -s.bitrate):
        print(f"    [{a.itag:3d}] {a.format.format_name:6s} {a.bitrate//1000}kbps {a.codec}")
    print(f"\n  Subtitles ({len(info.subtitle_streams)}):")
    for s in info.subtitle_streams:
        auto = " [auto]" if s.is_auto_generated else ""
        print(f"    {s.language}{auto}")
    if info.hls_url:
        print(f"\n  HLS  : {info.hls_url[:80]}...")
    if info.dash_mpd_url:
        print(f"  DASH : {info.dash_mpd_url[:80]}...")
    print()


def cmd_search(pp: PipePipe, query: str):
    results = pp.search(query)
    print(f"\nSearch results for: {query!r}\n{'='*60}")
    for i, item in enumerate(results.streams, 1):
        print(f"  {i:2d}. {item.name}")
        print(f"      {item.uploader} | {format_duration(item.duration)} | {format_count(item.view_count)} views")
        print(f"      {item.url}")
    if results.channels:
        print(f"\nChannels:")
        for ch in results.channels:
            print(f"  - {ch.name} ({format_count(ch.subscriber_count)} subs) {ch.url}")
    if results.playlists:
        print(f"\nPlaylists:")
        for pl in results.playlists:
            print(f"  - {pl.name} ({pl.stream_count} videos) {pl.url}")
    print()


def cmd_channel(pp: PipePipe, url: str):
    info = pp.get_channel_info(url)
    print(f"\n{'='*60}")
    print(f"  Channel   : {info.name}")
    print(f"  Subs      : {format_count(info.subscriber_count)}")
    print(f"  Verified  : {info.verified}")
    print(f"  URL       : {info.url}")
    print(f"\n  Recent videos:")
    videos, _ = pp.get_channel_videos(url)
    for v in videos[:10]:
        print(f"    - {v.name} ({format_duration(v.duration)})")
    print()


def cmd_playlist(pp: PipePipe, url: str):
    pl, _ = pp.get_playlist(url)
    print(f"\n{'='*60}")
    print(f"  Playlist  : {pl.name}")
    print(f"  Uploader  : {pl.uploader}")
    print(f"  Videos    : {pl.stream_count}")
    print(f"\n  Videos:")
    for v in pl.streams[:20]:
        print(f"    - {v.name} ({format_duration(v.duration)})")
    print()


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    cmd, arg = args[0], " ".join(args[1:])
    pp = PipePipe()

    try:
        if cmd == "info":
            cmd_info(pp, arg)
        elif cmd == "search":
            cmd_search(pp, arg)
        elif cmd == "channel":
            cmd_channel(pp, arg)
        elif cmd == "playlist":
            cmd_playlist(pp, arg)
        else:
            print(f"Unknown command: {cmd}")
            print(__doc__)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
