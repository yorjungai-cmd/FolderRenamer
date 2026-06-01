import time
from dataclasses import dataclass
from typing import List
from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class TranslationJob:
    file_id: str
    japanese_segments: List[str]   # texts to send to API
    segment_indices: List[int]     # positions in the Segment list for reconstruction


def process_jobs(jobs, provider, batch_size, delay_ms,
                 on_status, on_result, on_error, on_progress, on_eta, cancel_flag):
    """Pure processing loop — no Qt dependency, fully testable."""
    total = len(jobs)
    done = 0
    batch_times: List[float] = []

    for i in range(0, total, batch_size):
        if cancel_flag():
            break
        batch = jobs[i:i + batch_size]

        for job in batch:
            on_status(job.file_id, "translating")

        # Flatten all texts in this batch
        all_texts, text_map = [], []
        for j, job in enumerate(batch):
            for k, text in enumerate(job.japanese_segments):
                all_texts.append(text)
                text_map.append((j, k))

        t0 = time.monotonic()
        try:
            translated = provider.translate(all_texts)
            job_results = {j: {} for j in range(len(batch))}
            for idx, (j, k) in enumerate(text_map):
                job_results[j][k] = translated[idx] if idx < len(translated) else all_texts[idx]

            for j, job in enumerate(batch):
                trans_texts = [job_results[j].get(k, job.japanese_segments[k])
                               for k in range(len(job.japanese_segments))]
                on_result(job.file_id, job.segment_indices, trans_texts)
                on_status(job.file_id, "done")
                done += 1
                on_progress(done, total)
        except Exception as e:
            for job in batch:
                on_error(job.file_id, str(e))
                on_status(job.file_id, "error")
                done += 1
                on_progress(done, total)

        elapsed = time.monotonic() - t0
        batch_times.append(elapsed)
        if len(batch_times) > 10:
            batch_times.pop(0)

        if done < total and not cancel_flag():
            avg = sum(batch_times) / len(batch_times)
            remaining_batches = (total - done) / max(batch_size, 1)
            on_eta(avg * remaining_batches)
            time.sleep(delay_ms / 1000.0)


class TranslationWorker(QThread):
    file_status_changed = pyqtSignal(str, str)
    translation_result  = pyqtSignal(str, list, list)
    translation_error   = pyqtSignal(str, str)
    progress_updated    = pyqtSignal(int, int)
    eta_updated         = pyqtSignal(float)

    def __init__(self, provider, jobs: List[TranslationJob],
                 batch_size: int = 50, delay_ms: int = 200):
        super().__init__()
        self.provider = provider
        self.jobs = jobs
        self.batch_size = batch_size
        self.delay_ms = delay_ms
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        process_jobs(
            self.jobs, self.provider, self.batch_size, self.delay_ms,
            on_status=self.file_status_changed.emit,
            on_result=self.translation_result.emit,
            on_error=self.translation_error.emit,
            on_progress=self.progress_updated.emit,
            on_eta=self.eta_updated.emit,
            cancel_flag=lambda: self._cancel,
        )
