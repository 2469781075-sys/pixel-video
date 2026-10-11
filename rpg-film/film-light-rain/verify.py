"""Check this film's real media, original text, audio, and declared motion regions.

These checks establish technical properties. They do not approve anatomy,
pronunciation, aesthetic quality, or the user's creative review.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import wave
import zipfile

import numpy as np
from PIL import Image

import render as r

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
VIDEO = P / 'window-light-rain-mambo.mp4'


def run(command):
    return subprocess.run(command, check=True, capture_output=True)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wav_seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as audio:
        return audio.getnframes() / audio.getframerate()


def subtitles():
    original = ''.join((P / 'original.txt').read_text().splitlines())
    blocks = (P / 'subtitles.srt').read_text().strip().split('\n\n')
    assert len(blocks) == len(r.CUES)
    for block, cue in zip(blocks, r.CUES):
        number, timecode, text = block.split('\n', 2)
        assert int(number) == cue['id']
        assert timecode == f"{r.code(cue['start_seconds'])} --> {r.code(cue['end_seconds'])}"
        assert text == cue['text']
    assert ''.join(cue['text'] for cue in r.CUES) == original
    layout = json.loads((P / 'subtitle-layout.json').read_text())
    ass = defaultdict(list)
    for line in (P / 'subtitles.ass').read_text().splitlines():
        if line.startswith('Dialogue: '):
            fields = line.split(',', 9)
            ass[fields[1]].append(re.sub(r'\{[^}]*\}', '', fields[9]))
    assert len(ass) == len(r.CUES)
    for cue, item in zip(r.CUES, layout):
        assert ''.join(ass[r.code(cue['start_seconds'], True)]) == cue['text']
        assert ''.join(item['lines']) == cue['text']
        assert 1 <= len(item['lines']) <= 3
        assert max(item['widths']) <= r.CAPTION_WIDTH
        assert min(item['line_centers']) - r.EM_SIZE / 2 >= r.SCENE_H * r.SCALE
        assert max(item['line_centers']) + r.EM_SIZE / 2 <= r.H * r.SCALE - 8
        assert item['start'] < item['end'] <= r.SECONDS
    return {'sentences': len(blocks), 'full_srt_and_burned_ass_match_original': True,
            'actual_glyph_em_pixels': r.EM_SIZE, 'maximum_lines': max(len(x['lines']) for x in layout),
            'final_caption_display_end': layout[-1]['end']}


def narration():
    archive_path = ROOT / 'rpg-film/narration/mambo/mambo-narration.zip'
    with zipfile.ZipFile(archive_path) as archive:
        source = archive.read('narration.wav')
        lengths = []
        for cue in r.CUES:
            actual = wav_seconds(archive.read(cue['audio_file']))
            expected = cue['end_seconds'] - cue['start_seconds']
            assert abs(actual - expected) < .002
            lengths.append(round(actual, 6))
        assert archive.read('narration.mp3') == (P / 'mambo-narration.mp3').read_bytes()
    assert source == r.voice_wave().read_bytes()
    duration = wav_seconds(source)
    assert abs(duration - r.CUES[-1]['end_seconds']) < .002
    assert r.SECONDS - duration >= 1.5
    return {'voice': 'Existing full Mambo narration', 'speed': 1.0,
            'full_wav_seconds': duration, 'source_wav_sha256': sha(source),
            'all_segment_durations_match_cues': True, 'segment_seconds': lengths,
            'original_mp3_preserved': True, 'ending_tail_seconds': r.SECONDS - duration,
            'phonetic_review': 'Existing voice reused; no new pronunciation approval inferred'}


def motion(film):
    records = []
    for shot in r.SHOTS:
        times = [shot['start'] + .4, (shot['start'] + shot['end']) / 2, shot['end'] - .4]
        frames = [np.asarray(film.raw(shot, t)) for t in times]
        outside = np.asarray(film.allowed[shot['number']]) == 0
        changed = np.zeros(outside.shape, dtype=bool)
        for frame in frames[1:]:
            delta = np.any(frame != frames[0], axis=2)
            assert not np.any(delta & outside), f"Undeclared motion outside mask in shot {shot['number']}"
            changed |= delta
        assert changed.any(), f"No sampled local animation in shot {shot['number']}"
        records.append({'shot': shot['number'], 'sample_seconds': times,
                        'outside_motion_mask_unchanged': True,
                        'changed_native_pixels': int(changed.sum())})
    states = [film.window_state(t) for t in np.arange(75.05, 86.35, 1 / r.FPS)]
    assert all(x['pane_width'] == 105 and x['top'] == 5 and x['bottom'] == 166 for x in states)
    assert all(a['left_x'] >= b['left_x'] and a['right_x'] <= b['right_x'] for a, b in zip(states, states[1:]))
    assert states[0]['left_x'] + 105 == states[0]['right_x']
    assert states[-1]['right_x'] - (states[-1]['left_x'] + 105) == 166
    assert states[-1]['lower'] == 1.0
    return {'fixed_canvas': [r.W, r.SCENE_H], 'shots': records,
            'window': {'sampled_states': len(states), 'fixed_native_pane_size': [105, 161],
                       'horizontal_monotonic_slide': True, 'full_open_gap_pixels': 166,
                       'hands_lowered_at_end': True},
            'scope': 'Renderer pixels outside all declared local-motion masks; excludes intro/end fades. Not an anatomy test.'}


def encoded_frame(at):
    result = run(['ffmpeg', '-v', 'error', '-ss', str(at), '-i', str(VIDEO),
                  '-vf', 'scale=480:270:flags=neighbor', '-frames:v', '1',
                  '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
    return np.frombuffer(result.stdout, np.uint8).reshape(r.H, r.W, 3)[:r.SCENE_H].astype(np.int16)


def encoded_voice():
    with wave.open(str(r.voice_wave())) as source:
        rate = source.getframerate()
        assert source.getsampwidth() == 2 and source.getnchannels() == 1
        reference = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float32) / 32768
    decoded = run(['ffmpeg', '-v', 'error', '-i', str(VIDEO), '-map', '0:a:0',
                   '-ar', str(rate), '-ac', '1', '-f', 'f32le', 'pipe:1'])
    mix = np.frombuffer(decoded.stdout, '<f4')
    matches = []
    for cue in r.CUES:
        lo, hi = round(cue['start_seconds'] * rate), round(cue['end_seconds'] * rate)
        correlation = float(np.corrcoef(reference[lo:hi], mix[lo:hi])[0, 1])
        assert correlation >= .98, f"Encoded voice missing/shifted in sentence {cue['id']}"
        matches.append({'sentence': cue['id'], 'waveform_correlation': round(correlation, 6)})
    return {'sentences': matches, 'all_original_voice_segments_present_at_expected_times': True,
            'scope': 'Compare actual decoded soundtrack with source PCM at every original sentence timestamp. Not a phonetic judgement.'}


def camera(film):
    records = []
    for number in (1, 2, 5, 9, 10, 15, 16):
        shot = r.SHOTS[number - 1]
        first, second = shot['start'] + .8, shot['end'] - 1.2
        a, b = encoded_frame(first), encoded_frame(second)
        fixed = np.asarray(film.allowed[number]) == 0
        errors = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                shifted = np.roll(b, (dy, dx), axis=(0, 1))
                keep = fixed & np.roll(fixed, (dy, dx), axis=(0, 1))
                keep[:3, :] = False; keep[-3:, :] = False
                keep[:, :3] = False; keep[:, -3:] = False
                errors.append((float(np.abs(a - shifted)[keep].mean()), dx, dy))
        best = min(errors)
        assert best[1:] == (0, 0), f'Encoded camera registration failed: shot {number}, {best}'
        records.append({'shot': number, 'sample_seconds': [first, second],
                        'best_displacement_native_pixels': [best[1], best[2]],
                        'mean_channel_error': round(best[0], 3)})
    return {'registration_range_native_pixels': [-2, 2], 'sampled_shots': records,
            'scope': 'Actual encoded frames, all non-motion-mask pixels. Compression errors are allowed; no image identity claim.'}


def retained_sources():
    files = sorted((ROOT / 'rpg-film/complete-storyboard').glob('*.png'))
    files += sorted((ROOT / 'rpg-film/style-refinement-review').glob('*.png'))
    files += sorted((ROOT / 'rpg-film/style-refinement-review/grain-light').glob('*.png'))
    files += sorted((ROOT / 'rpg-film/style-refinement-review/grain-strong').glob('*.png'))
    records = []
    for file in files:
        relative = file.relative_to(ROOT).as_posix()
        previous = run(['git', '-C', str(ROOT), 'show', f'd6716b8:{relative}']).stdout
        assert previous == file.read_bytes(), f'Retained art changed: {relative}'
        records.append({'file': relative, 'sha256': sha(previous)})
    for shot in r.SHOTS:
        assert sha((ROOT / shot['source']).read_bytes()) == shot['source_sha256']
    return {'baseline_commit': 'd6716b8', 'retained_png_count': len(records), 'files': records}


def main():
    result = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                             '-show_chapters', '-of', 'json', str(VIDEO)]).stdout)
    video = next(x for x in result['streams'] if x['codec_type'] == 'video')
    audio = next(x for x in result['streams'] if x['codec_type'] == 'audio')
    assert (video['width'], video['height'], video['avg_frame_rate']) == (1920, 1080, '24/1')
    assert video['codec_name'] == 'h264' and audio['codec_name'] == 'aac'
    assert audio['channels'] == 2 and audio['sample_rate'] == '48000'
    assert int(video['nb_frames']) == r.FRAME_COUNT
    assert abs(float(video['duration']) - r.SECONDS) < .05
    assert abs(float(audio['duration']) - r.SECONDS) < .05
    assert len(result['chapters']) == len(r.SHOTS)
    for chapter, shot in zip(result['chapters'], r.SHOTS):
        assert abs(float(chapter['start_time']) - shot['start']) < .001
        assert abs(float(chapter['end_time']) - shot['end']) < .001
    assert all(a['end'] == b['start'] for a, b in zip(r.SHOTS, r.SHOTS[1:]))
    subtitles_result = subtitles()
    narration_result = narration()
    film = r.Film()
    motion_result = motion(film)
    camera_result = camera(film)
    retained = retained_sources()
    for file in list((P / 'assets').glob('*.png')) + list((P / 'assets/animation').glob('*.png')) + list((P / 'previews').glob('*.png')):
        with Image.open(file) as image:
            image.verify()
    run(['ffmpeg', '-v', 'error', '-i', str(VIDEO), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    measure = run(['ffmpeg', '-hide_banner', '-i', str(VIDEO), '-map', '0:a:0',
                   '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json', '-f', 'null', '-'])
    stderr = measure.stderr.decode()
    measured, _ = json.JSONDecoder().raw_decode(stderr[stderr.rfind('{'):])
    assert -18 <= float(measured['input_i']) <= -14
    assert float(measured['input_tp']) < 0
    report = {'status': 'Technical checks passed; creative approval remains with the user',
              'file': VIDEO.name, 'sha256': sha(VIDEO.read_bytes()), 'bytes': VIDEO.stat().st_size,
              'video': {'width': 1920, 'height': 1080, 'fps': r.FPS, 'frames': r.FRAME_COUNT,
                        'seconds': r.SECONDS, 'codec': video['codec_name'], 'chapters': len(result['chapters'])},
              'audio': {'codec': audio['codec_name'], 'rate': 48000, 'channels': 2,
                        'integrated_lufs': float(measured['input_i']), 'true_peak_dbtp': float(measured['input_tp']),
                        'normalization_target': {'lufs': -16, 'true_peak_dbtp': -1.5}},
              'subtitles': subtitles_result, 'narration': narration_result,
              'encoded_voice_coverage': encoded_voice(),
              'native_motion_checks': motion_result, 'encoded_camera_checks': camera_result,
              'retained_sources': retained, 'full_video_and_audio_decode': 'passed',
              'visual_review': 'Read actual encoded contact sheet and all scene/key previews. Technical checks do not establish user acceptance.'}
    (P / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'video': report['video'], 'audio': report['audio'],
                      'source_pngs_preserved': retained['retained_png_count']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
