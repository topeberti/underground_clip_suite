import time
import msvcrt
from pathlib import Path

from rich.console import Console

console = Console()


def _fmt_ms(ms: int) -> str:
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}.{ms:03d}"


def _load_audio(path: Path):
    """Return (samples, sr, duration_ms). samples shaped for sounddevice."""
    import librosa
    console.print(f"[dim]Loading {path.name}…[/dim]")
    samples, sr = librosa.load(str(path), sr=None, mono=False)
    if samples.ndim == 2:
        samples = samples.T  # (channels, n) → (n, channels)
    duration_ms = int(len(samples) / sr * 1000)
    console.print(f"  [dim]{_fmt_ms(duration_ms)}  |  {sr} Hz[/dim]")
    return samples, sr, duration_ms


def _capture_taps(samples, sr: int, duration_ms: int, countdown: int) -> list[int]:
    import sounddevice as sd

    while True:
        console.print()
        console.print("[bold]TAP PHASE[/bold]")
        for i in range(countdown, 0, -1):
            console.print(f"  [bold]{i}…[/bold]", end="\r")
            time.sleep(1)
        console.print()
        console.print("[dim]  SPACE=mark  BACKSPACE=undo  R=restart  Q=stop early[/dim]")
        console.print()
        console.print(f"  [dim][auto] {_fmt_ms(0)}[/dim]")

        taps: list[int] = []
        sd.play(samples, sr)
        t0 = time.perf_counter()
        restart = False

        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                tap_ms = int((time.perf_counter() - t0) * 1000)  # timestamp captured right after key read
                if ch == b' ':
                    taps.append(tap_ms)
                    console.print(f"  [cyan][{len(taps)}][/cyan]  {_fmt_ms(tap_ms)}")
                elif ch in (b'\x08', b'\x7f'):
                    if taps:
                        undone = taps.pop()
                        console.print(f"  [yellow]Undone:[/yellow] {_fmt_ms(undone)}")
                elif ch in (b'r', b'R'):
                    console.print("\n  [yellow]Restarting tap phase…[/yellow]")
                    restart = True
                    break
                elif ch in (b'q', b'Q'):
                    break
            elif int((time.perf_counter() - t0) * 1000) >= duration_ms:
                break
            time.sleep(0.001)

        sd.stop()
        if not restart:
            return taps


def _assign_lyrics(taps: list[int], duration_ms: int, samples, sr: int) -> list[dict]:
    import sounddevice as sd

    starts = taps
    ends = taps[1:] + [duration_ms]
    n = len(taps)

    console.print()
    console.print(f"[bold]LYRIC PHASE — {n} segment(s)[/bold]")
    console.print("[dim]  Enter=replay  .=skip segment  !r=restart from seg 1  !q=save & quit[/dim]")
    console.print()

    while True:
        entries: list[dict] = []
        index = 1
        restart = False

        for i, (start_ms, end_ms) in enumerate(zip(starts, ends)):
            start_sample = int(start_ms * sr / 1000)
            end_sample = int(end_ms * sr / 1000)
            segment = samples[start_sample:end_sample]

            while True:
                console.print(f"[bold]Segment {i + 1}/{n}[/bold]  {_fmt_ms(start_ms)} → {_fmt_ms(end_ms)}")
                sd.play(segment, sr)
                text = input("  Lyric: ").strip()
                sd.stop()

                if text == "":
                    continue
                elif text == ".":
                    break
                elif text == "!r":
                    console.print("  [yellow]Restarting from segment 1…[/yellow]\n")
                    restart = True
                    break
                elif text == "!q":
                    return entries
                else:
                    entries.append({
                        "index": index,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "text": text,
                    })
                    index += 1
                    break

            if restart:
                break

        if not restart:
            return entries


def run(audio: Path, output: Path | None, countdown: int) -> None:
    samples, sr, duration_ms = _load_audio(audio)

    taps = _capture_taps(samples, sr, duration_ms, countdown)
    taps.insert(0, 0)

    console.print(f"\n[green]{len(taps)} tap(s) captured (including auto 00:00).[/green]")
    entries = _assign_lyrics(taps, duration_ms, samples, sr)

    if not entries:
        console.print("[yellow]No lyrics assigned — nothing written.[/yellow]")
        return

    out_path = output if output is not None else audio.with_suffix(".srt")
    from src.lyrics.srt_writer import write_srt
    write_srt(entries, out_path)
    console.print(f"\n[green bold]Wrote {len(entries)} line(s) → {out_path}[/green bold]")
